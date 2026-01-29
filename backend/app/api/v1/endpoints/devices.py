"""
设备相关 API 端点模块;

本模块提供连接设备、获取文件列表以及下载设备文件的功能;
"""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
from datetime import datetime
from sqlmodel import Session
import uuid
from pathlib import Path

# Fix: Import specific exceptions
from requests.exceptions import RequestException

from app.api import deps
from app.schemas import api_models
from app.crud import file as crud
from app.services.storage import StorageService
from app.core.logger import logger
from app.models.sensor_file import SensorFile, PhysicalFile
from app.core.database import engine
from app.models.dictionary import TestType, TestSubType
from sqlmodel import select
from app.services.metadata import parse_filename, ensure_test_types_exist

# Import zstandard for streaming compression
import zstandard as zstd
import hashlib

router = APIRouter()

# --- Helpers ---
# Moved to app.services.metadata

@router.get("/devices/list", response_model=api_models.DeviceFilesResponse)
def list_device_files(
    url: str = Query(..., description="Device base URL"),
    session: Session = Depends(deps.get_db)
) -> api_models.DeviceFilesResponse:
    """
    连接设备并获取文件列表;
    
    Args:
        url: 设备的基础 URL (e.g. http://192.168.1.100:8080);
        
    Returns:
        DeviceFilesResponse: 包含文件列表和状态;
    """
    logger.info(f"Connecting to device at {url}...")
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to connect to device: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    device_files: List[api_models.DeviceFile] = []
    
    for link in links:
        relative_url = link['href']
        
        # Filter logic (same as script)
        if 'download?file=' not in relative_url:
            continue
            
        try:
            filename = unquote(relative_url.split('file=')[-1])
        except IndexError:
            continue
            
        # Parse logic
        full_url = urljoin(url, relative_url)
        
        # Check DB status
        # Note: We check by filename only because we don't have the hash yet
        # If user re-uploads same name, backend handles renaming suffix, but here we just want to know if "a file with this name" was uploaded.
        # Ideally we check exact match, but without hash, name match is the best hint.
        
        # Check if filename roughly matches the "uploaded" pattern
        # The crud method `get_file_by_name_and_size` checks strictly.
        # We can implement a simpler check in CRUD or reuse exact match logic if we had size/hash.
        # For now, let's just check if ANY file with this name exists. 
        # But wait, existing crud does not have "get_any_file_by_filename".
        # Let's add a quick helper or just iterate. 
        # Actually `crud.get_files(search=filename)` handles partial match.
        
        # Let's use a direct query for efficiency or add to CRUD later.
        # For now, we assume if we find a file with exact name, it's uploaded.
        
        # Since we cannot modify crud right now without context switch, let's use `get_files` with search.
        # But strict check is better. Let's do a simple check.
        # We can assume `crud.get_next_naming_suffix(session, filename)` returns "" if NO file exists?
        # No, that returns the NEXT suffix.
        
        # Let's query crud.listing
        # Optimize: Batch check later if performance issue.
        matches, _ = crud.get_files(session, limit=1, search=filename)
        is_uploaded = False
        
        # If search found something, verify exact filename match (because search is partial)
        for m in matches:
            if m.filename == filename:
                is_uploaded = True
                break
                
        # Parse Date
        date_str = None
        match = re.search(r'_(\d{8})_', filename)
        if match:
            date_str = match.group(1)
            
        device_files.append(api_models.DeviceFile(
            filename=filename,
            url=full_url,
            size="Unknown", # HTML listing usually doesn't show size in the <a> tag text unless parsed from nearby text
            date=date_str,
            is_uploaded=is_uploaded
        ))
        
    return api_models.DeviceFilesResponse(items=device_files, total=len(device_files))


# ... existing code ...

import threading
from concurrent.futures import ThreadPoolExecutor

# ... imports ...


class DownloadManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DownloadManager, cls).__new__(cls)
                    cls._instance.executor = ThreadPoolExecutor(max_workers=5)
                    cls._instance.cancel_event = threading.Event()
                    cls._instance.task_states = {} # filename -> status
        return cls._instance

    def start_download(self, url: str, filename: str):
        # Reset state to queued
        self.task_states[filename] = 'queued'
        self.executor.submit(self._download_task, url, filename)

    def stop_all(self):
        logger.info("Stopping all downloads...")
        self.cancel_event.set()
        
    def reset(self):
        self.cancel_event.clear()
        self.task_states.clear()

    def reset_cancel(self):
        """Only reset the cancellation flag, keeping task history."""
        self.cancel_event.clear()

    def get_tasks(self):
        return self.task_states

    def _download_task(self, url: str, filename: str):
        if self.cancel_event.is_set():
            self.task_states[filename] = 'cancelled'
            return

        self.task_states[filename] = 'processing'
        logger.info(f"Starting background download for {filename} (Thread: {threading.get_ident()})")
        
        try:
             # Logic copied from original download_worker but with cancel check
             with Session(engine) as session:
                 resp = requests.get(url, stream=True, timeout=600)
                 resp.raise_for_status()
                 total_size = int(resp.headers.get('content-length', 0))
                 
                 temp_dir = StorageService.get_raw_dir()
                 temp_path = temp_dir / f"temp_{uuid.uuid4()}.zst"
                 
                 md5 = hashlib.md5()
                 dctx = zstd.ZstdCompressor(level=3)
                 
                 with temp_path.open("wb") as f_out:
                     with dctx.stream_writer(f_out) as compressor:
                         for chunk in resp.iter_content(chunk_size=8192):
                             # CANCEL CHECK POINT
                             if self.cancel_event.is_set():
                                 self.task_states[filename] = 'cancelled'
                                 return 

                             if chunk:
                                 md5.update(chunk)
                                 compressor.write(chunk)
                                 
                 if self.cancel_event.is_set():
                     if temp_path.exists(): temp_path.unlink()
                     self.task_states[filename] = 'cancelled'
                     return

                 file_hash = md5.hexdigest()
                 final_path = StorageService.get_raw_path(file_hash)
                 compressed_size = temp_path.stat().st_size
                 
                 # Deduplication
                 if final_path.exists():
                     logger.info(f"File {filename} ({file_hash}) already exists physically.")
                     temp_path.unlink()
                 else:
                     temp_path.rename(final_path)
                     logger.info(f"Saved {filename} to {final_path}")

                 # DB Registration
                 phy_file = crud.get_physical_file(session, file_hash)
                 if not phy_file:
                    phy_file = PhysicalFile(hash=file_hash, size=compressed_size, path=str(final_path))
                    crud.create_physical_file(session, phy_file)
                    
                 exact_match = crud.get_exact_match_file(session, file_hash, filename)
                 if exact_match:
                     logger.info(f"File {filename} ({file_hash}) already registered. Skipping.")
                     self.task_states[filename] = 'success'
                     return

                 file_id = str(uuid.uuid4())
                 name_suffix = crud.get_next_naming_suffix(session, filename)
                 
                 # Size string logic...
                 if total_size < 1024: size_str = f"{total_size} B"
                 elif total_size < 1024**2: size_str = f"{total_size/1024:.1f} KB"
                 elif total_size < 1024**3: size_str = f"{total_size/1024**2:.1f} MB"
                 else: size_str = f"{total_size/1024**3:.1f} GB"

                 processed_dir = StorageService.get_processed_dir(file_hash)
                 initial_status = "idle"
                 if processed_dir.exists() and any(processed_dir.iterdir()):
                     initial_status = "processed"

                 # Parse Filename Metadata
                 meta = parse_filename(filename)
                 
                 # Auto-Insert Dictionary
                 if meta.get("test_type_l1"):
                     ensure_test_types_exist(session, meta.get("test_type_l1"), meta.get("test_type_l2"))

                 new_sf = SensorFile(
                     id=file_id,
                     file_hash=file_hash,
                     filename=filename,
                     deviceType=meta.get("deviceType", "Watch"), # Default to Watch or parsed
                     deviceModel="Unknown",
                     size=size_str,
                     file_size_bytes=total_size,
                     name_suffix=name_suffix,
                     uploadTime=datetime.utcnow().isoformat(),
                     status=initial_status,
                     processedDir=str(processed_dir),
                     
                     # New Fields
                     test_type_l1=meta.get("test_type_l1", "Unknown"),
                     test_type_l2=meta.get("test_type_l2", "--"),
                     tester=meta.get("tester", ""),
                     mac=meta.get("mac", ""),
                     collection_time=meta.get("collection_time", "")
                 )
                 crud.create_file(session, new_sf)
                 logger.info(f"Registered {filename} as {file_id}")
                 self.task_states[filename] = 'success'
                 
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            self.task_states[filename] = 'failed'
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()


download_manager = DownloadManager()

@router.post("/devices/import")
def import_device_files(
    request: api_models.DeviceDownloadRequest,
    # background_tasks: BackgroundTasks, # Dropped in favor of ThreadPool
    session: Session = Depends(deps.get_db)
) -> dict:
    download_manager.reset_cancel()
    
    count = 0
    for file in request.files:
        if not file.url.startswith("http"):
             file.url = urljoin(request.device_ip, "download?file=" + file.filename)
        
        download_manager.start_download(file.url, file.filename)
        count += 1
        
    return {"message": f"Queued {count} files for download.", "count": count}

@router.post("/devices/stop")
def stop_import() -> dict:
    """停止所有下载任务"""
    download_manager.stop_all()
    return {"message": "Stop signal sent."}

@router.get("/devices/tasks")
def get_device_tasks() -> dict:
    """获取当前任务状态"""
    return download_manager.get_tasks()


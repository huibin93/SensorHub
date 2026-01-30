"""
设备相关 API 端点模块;

本模块提供连接设备、获取文件列表以及下载设备文件的功能;
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
from sqlmodel import Session

# Fix: Import specific exceptions
from requests.exceptions import RequestException

from app.api import deps
from app.schemas import api_models
from app.crud import file as crud
from app.core.logger import logger
from app.services.device_import import download_manager

router = APIRouter()

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
        db_size = "Unknown"
        for m in matches:
            if m.filename == filename:
                is_uploaded = True
                db_size = m.size
                break
                
        # Parse Date
        date_str = None
        match = re.search(r'_(\d{8})_', filename)
        if match:
            date_str = match.group(1)
            
        device_files.append(api_models.DeviceFile(
            filename=filename,
            url=full_url,
            size=db_size if is_uploaded else "Unknown", # Use DB size if uploaded
            date=date_str,
            is_uploaded=is_uploaded
        ))
        
    return api_models.DeviceFilesResponse(items=device_files, total=len(device_files))


from app.services.device_import import download_manager


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


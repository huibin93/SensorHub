"""
设备文件导入服务模块;

本模块提供从远程设备下载文件的后台任务管理功能;
"""
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from pathlib import Path
import uuid
import hashlib
import zstandard as zstd
from datetime import datetime
from sqlmodel import Session

from app.services.storage import StorageService
from app.core.logger import logger
from app.core.database import engine
from app.crud import file as crud
from app.models.sensor_file import SensorFile, PhysicalFile
from app.services.metadata import parse_filename, ensure_test_types_exist


class DownloadManager:
    """
    设备文件下载管理器（单例模式）;
    
    管理多个并发下载任务，支持取消和状态跟踪;
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DownloadManager, cls).__new__(cls)
                    cls._instance.executor = ThreadPoolExecutor(max_workers=5)
                    cls._instance.cancel_event = threading.Event()
                    cls._instance.task_states = {}  # filename -> status
        return cls._instance

    def start_download(self, url: str, filename: str):
        """
        启动文件下载任务;
        
        Args:
            url: 文件下载链接;
            filename: 文件名;
        """
        self.task_states[filename] = 'queued'
        self.executor.submit(self._download_task, url, filename)

    def stop_all(self):
        """停止所有正在进行的下载任务;"""
        logger.info("Stopping all downloads...")
        self.cancel_event.set()
        
    def reset(self):
        """重置管理器状态和任务列表;"""
        self.cancel_event.clear()
        self.task_states.clear()

    def reset_cancel(self):
        """重置取消标志，保留任务历史;"""
        self.cancel_event.clear()

    def get_tasks(self) -> dict:
        """
        获取所有任务的状态;
        
        Returns:
            dict: 文件名到状态的映射;
        """
        return self.task_states

    def _download_task(self, url: str, filename: str):
        """
        后台下载任务;
        
        Args:
            url: 下载链接;
            filename: 文件名;
        """
        if self.cancel_event.is_set():
            self.task_states[filename] = 'cancelled'
            return

        self.task_states[filename] = 'processing'
        logger.info(f"Starting background download for {filename} (Thread: {threading.get_ident()})")
        
        temp_path = None
        try:
            with Session(engine) as session:
                # 下载文件流
                resp = requests.get(url, stream=True, timeout=600)
                resp.raise_for_status()
                
                temp_dir = StorageService.get_raw_dir()
                temp_path = temp_dir / f"temp_{uuid.uuid4()}.zst"
                
                md5 = hashlib.md5()
                frame_index = []  # 帧索引表
                try:
                    # 1. 准备流式处理变量
                    compressor = zstd.ZstdCompressor(level=6)
                    raw_buffer = bytearray()
                    
                    # 帧切分参数
                    MIN_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB
                    MAX_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
                    
                    offset = 0          # 当前解压数据偏移量 (总累计)
                    compressed_offset = 0 # 当前压缩文件偏移量
                    
                    metadata_extracted = False
                    metadata_dict = {}
                    
                    with temp_path.open("wb") as f_out:
                        for chunk in resp.iter_content(chunk_size=64 * 1024):
                            if self.cancel_event.is_set():
                                break
                            
                            if chunk:
                                raw_buffer.extend(chunk)
                                md5.update(chunk)
                                
                                # Metadata Extraction (从前 64KB 提取)
                                if not metadata_extracted and len(raw_buffer) >= 1024:
                                    try:
                                        # 仅取头部解码
                                        peek_len = min(len(raw_buffer), 64 * 1024) 
                                        peek_content = raw_buffer[:peek_len].decode('utf-8', errors='ignore')
                                        from app.services.metadata_parser import extract_metadata_from_content
                                        metadata_dict = extract_metadata_from_content(peek_content)
                                        metadata_extracted = True
                                        logger.info(f"Metadata extracted for {filename}: {metadata_dict.get('device_mac', 'N/A')}")
                                    except Exception as ex:
                                        logger.warning(f"Failed to extract metadata during download: {ex}")
                                        metadata_extracted = True # Avoid processing again

                                # Streaming Chunk Processing
                                # 当缓冲区足够大 (超过最大块大小 OR 只要超过最小块大小且有换行符?)
                                # 为了简单且高效，我们尽可能攒够 4MB 或者直到遇到换行
                                while len(raw_buffer) >= MAX_CHUNK_SIZE:
                                    # 在区间 [MIN, MAX] 寻找换行符
                                    # 但 Buffer 可能直接非常大?
                                    # 切分逻辑:
                                    # 1. 截取前 MAX_CHUNK_SIZE
                                    # 2. 在 [MIN, MAX] 范围内找换行
                                    
                                    # 如果 buffer 甚至还不够 MIN，但我们已经知道它 > MAX? (逻辑上 impossible unless MIN > MAX)
                                    search_start = MIN_CHUNK_SIZE
                                    search_end = MAX_CHUNK_SIZE
                                    
                                    newline_pos = raw_buffer.find(b'\n', search_start, search_end)
                                    
                                    cut_pos = 0
                                    ends_with_newline = False
                                    
                                    if newline_pos != -1:
                                        cut_pos = newline_pos + 1
                                        ends_with_newline = True
                                    else:
                                        # 未找到换行，强制在 MAX 处截断
                                        cut_pos = MAX_CHUNK_SIZE
                                        # Check if accidentally ended with newline
                                        if raw_buffer[cut_pos-1] == 10: # 10 is \n
                                            ends_with_newline = True

                                    # Extract, Compress, Write
                                    chunk_data = raw_buffer[:cut_pos]
                                    del raw_buffer[:cut_pos] # Remove processed
                                    
                                    compressed_chunk = compressor.compress(chunk_data)
                                    f_out.write(compressed_chunk)
                                    
                                    c_len = len(compressed_chunk)
                                    d_len = len(chunk_data)
                                    
                                    frame_index.append({
                                        "cs": compressed_offset,
                                        "cl": c_len,
                                        "ds": offset,
                                        "dl": d_len,
                                        "nl": ends_with_newline
                                    })
                                    
                                    compressed_offset += c_len
                                    offset += d_len

                        # 处理剩余数据 (End of Stream)
                        if not self.cancel_event.is_set() and len(raw_buffer) > 0:
                            # 如果此时还没提取元数据 (文件极小)，尝试提取
                            if not metadata_extracted:
                                try:
                                    peek_content = raw_buffer.decode('utf-8', errors='ignore')
                                    from app.services.metadata_parser import extract_metadata_from_content
                                    metadata_dict = extract_metadata_from_content(peek_content)
                                except:
                                    pass

                            # 循环处理剩余 buffer (若剩余 > MAX_CHUNK_SIZE, 虽不太可能因为上面循环处理了, 但以防万一)
                            while raw_buffer:
                                cut_pos = min(len(raw_buffer), MAX_CHUNK_SIZE)
                                # 尝试找换行
                                if len(raw_buffer) >= MIN_CHUNK_SIZE:
                                    limit = min(len(raw_buffer), MAX_CHUNK_SIZE)
                                    nl = raw_buffer.find(b'\n', MIN_CHUNK_SIZE, limit)
                                    if nl != -1:
                                        cut_pos = nl + 1
                                
                                ends_with_newline = False
                                if cut_pos > 0 and raw_buffer[cut_pos-1] == 10:
                                    ends_with_newline = True
                                    
                                chunk_data = raw_buffer[:cut_pos]
                                del raw_buffer[:cut_pos]
                                
                                compressed_chunk = compressor.compress(chunk_data)
                                f_out.write(compressed_chunk)
                                
                                c_len = len(compressed_chunk)
                                d_len = len(chunk_data)
                                
                                frame_index.append({
                                    "cs": compressed_offset,
                                    "cl": c_len,
                                    "ds": offset,
                                    "dl": d_len,
                                    "nl": ends_with_newline
                                })
                                compressed_offset += c_len
                                offset += d_len

                except Exception as stream_err:
                     logger.error(f"Streaming error: {stream_err}")
                     raise stream_err
                     
                if self.cancel_event.is_set():
                    self.task_states[filename] = 'cancelled'
                    return
                
                downloaded_bytes = offset
                
                # 释放内存 (accumulator already cleared)
                
                file_hash = md5.hexdigest()
                final_path = StorageService.get_raw_path(file_hash)
                compressed_size = temp_path.stat().st_size
                
                # ... standard dedup logic ...

                # 文件去重
                if final_path.exists():
                    logger.info(f"File {filename} ({file_hash}) already exists physically.")
                    temp_path.unlink()
                else:
                    temp_path.rename(final_path)
                    logger.info(f"Saved {filename} to {final_path}")

                # 构建完整的帧索引
                complete_frame_index = {
                    "version": 2,
                    "frameSize": MIN_CHUNK_SIZE,
                    "maxFrameSize": MAX_CHUNK_SIZE,
                    "lineAligned": True,
                    "originalSize": downloaded_bytes,
                    "compressedSize": compressed_size,
                    "frames": frame_index
                }

                phy_file = crud.get_physical_file(session, file_hash)
                if not phy_file:
                    phy_file = PhysicalFile(
                        hash=file_hash, 
                        size=compressed_size, 
                        path=str(final_path),
                        frame_index=complete_frame_index
                    )
                    crud.create_physical_file(session, phy_file)
                elif not phy_file.frame_index:
                    phy_file.frame_index = complete_frame_index
                    session.add(phy_file)
                    session.commit()
                    
                exact_match = crud.get_exact_match_file(session, file_hash, filename)
                if exact_match:
                    logger.info(f"File {filename} ({file_hash}) already registered. Skipping.")
                    self.task_states[filename] = 'success'
                    return

                file_id = str(uuid.uuid4())
                name_suffix = crud.get_next_naming_suffix(session, filename)
                
                # ... existing size formatting ...
                # 格式化文件大小
                total_size = downloaded_bytes
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024**2:
                    size_str = f"{total_size/1024:.1f} KB"
                elif total_size < 1024**3:
                    size_str = f"{total_size/1024**2:.1f} MB"
                else:
                    size_str = f"{total_size/1024**3:.1f} GB"

                processed_dir = StorageService.get_processed_dir(file_hash)
                initial_status = "idle"
                if processed_dir.exists() and any(processed_dir.iterdir()):
                    initial_status = "processed"

                # 解析文件名元数据 (fallback or supplementary)
                meta_from_name = parse_filename(filename)
                
                # 优先使用 metadata_dict 中的数据
                # Clean device name (remove parens)
                device_val = metadata_dict.get('device', '')
                if '(' in device_val:
                    device_val = device_val.split('(')[0].strip()
                
                # Merge or select
                final_test_type_l1 = meta_from_name.get("test_type_l1", "Unknown")
                final_test_type_l2 = meta_from_name.get("test_type_l2", "--")
                
                if final_test_type_l1 != "Unknown":
                     ensure_test_types_exist(session, final_test_type_l1, final_test_type_l2)

                new_sf = SensorFile(
                    id=file_id,
                    file_hash=file_hash,
                    filename=filename,
                    deviceType=meta_from_name.get("deviceType", "Watch"), 
                    deviceModel="Unknown",
                    size=size_str,
                    file_size_bytes=total_size,
                    name_suffix=name_suffix,
                    uploadTime=datetime.utcnow().isoformat(),
                    status=initial_status,
                    processedDir=str(processed_dir),
                    
                    test_type_l1=final_test_type_l1,
                    test_type_l2=final_test_type_l2,
                    tester=meta_from_name.get("tester", ""),
                    mac=meta_from_name.get("mac", ""),
                    collection_time=meta_from_name.get("collection_time", ""),
                    
                    # New Metadata Fields
                    start_time=metadata_dict.get('startTime', ''),
                    device_name=device_val,
                    device_mac=metadata_dict.get('device_mac', ''),
                    device_version=metadata_dict.get('device version', '') or metadata_dict.get('device_version', ''),
                    user_name=metadata_dict.get('user_name', ''),
                    content_meta=metadata_dict
                )
                crud.create_file(session, new_sf)
                logger.info(f"Registered {filename} as {file_id} with metadata")
                self.task_states[filename] = 'success'
                
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            self.task_states[filename] = 'failed'
            if temp_path and temp_path.exists():
                temp_path.unlink()


# 单例实例
download_manager = DownloadManager()

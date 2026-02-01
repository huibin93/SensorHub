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
                compressor = zstd.ZstdCompressor(level=6)
                
                # 先下载到内存缓冲区, 然后分块压缩
                # (对于大文件, 可以改为边下载边写入临时原始文件)
                raw_buffer = bytearray()
                
                for chunk in resp.iter_content(chunk_size=8192):
                    # 取消检查点
                    if self.cancel_event.is_set():
                        self.task_states[filename] = 'cancelled'
                        return 

                    if chunk:
                        raw_buffer.extend(chunk)
                        md5.update(chunk)
                
                if self.cancel_event.is_set():
                    self.task_states[filename] = 'cancelled'
                    return
                
                downloaded_bytes = len(raw_buffer)
                
                # 换行对齐分块压缩
                MIN_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB minimum
                MAX_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB maximum
                compressed_offset = 0
                offset = 0
                
                with temp_path.open("wb") as f_out:
                    while offset < downloaded_bytes:
                        # 计算初始结束位置 (至少 2MB)
                        end = min(offset + MIN_CHUNK_SIZE, downloaded_bytes)
                        ends_with_newline = False
                        
                        # 如果不是文件末尾, 向后搜索换行符
                        if end < downloaded_bytes:
                            max_end = min(offset + MAX_CHUNK_SIZE, downloaded_bytes)
                            
                            # 从 end 向后搜索 \n (最多到 max_end)
                            newline_pos = raw_buffer.find(b'\n', end, max_end)
                            if newline_pos != -1:
                                end = newline_pos + 1  # 包含换行符
                                ends_with_newline = True
                            else:
                                end = max_end  # 未找到, 取到 max_end
                        
                        # 检查最后一个字符是否为换行
                        if not ends_with_newline and end > 0 and raw_buffer[end - 1:end] == b'\n':
                            ends_with_newline = True
                        
                        # 提取并压缩
                        raw_chunk = bytes(raw_buffer[offset:end])
                        chunk_len = len(raw_chunk)
                        compressed_chunk = compressor.compress(raw_chunk)
                        f_out.write(compressed_chunk)
                        
                        # 记录索引信息
                        compressed_len = len(compressed_chunk)
                        frame_index.append({
                            "cs": compressed_offset,
                            "cl": compressed_len,
                            "ds": offset,
                            "dl": chunk_len,
                            "nl": ends_with_newline  # 是否以换行结束
                        })
                        
                        compressed_offset += compressed_len
                        offset = end
                
                # 释放内存
                del raw_buffer

                file_hash = md5.hexdigest()
                final_path = StorageService.get_raw_path(file_hash)
                compressed_size = temp_path.stat().st_size
                
                # 文件去重
                if final_path.exists():
                    logger.info(f"File {filename} ({file_hash}) already exists physically.")
                    temp_path.unlink()
                else:
                    temp_path.rename(final_path)
                    logger.info(f"Saved {filename} to {final_path}")

                # 构建完整的帧索引
                complete_frame_index = {
                    "version": 2,  # 版本号升级
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

                # 解析文件名元数据
                meta = parse_filename(filename)
                
                # 自动插入字典条目
                if meta.get("test_type_l1"):
                    ensure_test_types_exist(session, meta.get("test_type_l1"), meta.get("test_type_l2"))

                new_sf = SensorFile(
                    id=file_id,
                    file_hash=file_hash,
                    filename=filename,
                    deviceType=meta.get("deviceType", "Watch"),
                    deviceModel="Unknown",
                    size=size_str,
                    file_size_bytes=total_size,
                    name_suffix=name_suffix,
                    uploadTime=datetime.utcnow().isoformat(),
                    status=initial_status,
                    processedDir=str(processed_dir),
                    
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
            if temp_path and temp_path.exists():
                temp_path.unlink()


# 单例实例
download_manager = DownloadManager()

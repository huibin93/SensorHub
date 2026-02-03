"""
文件服务模块;

封装文件相关的业务逻辑，如后台校验、批量处理等;
"""
import zipfile
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlmodel import Session

from app.core.logger import logger
from app.core.database import engine
from app.crud import file as crud
from app.services.storage import StorageService
from app.models.sensor_file import SensorFile

class FileService:
    """
    文件业务逻辑服务;
    """

    @staticmethod
    def verify_upload_task(file_id: str, md5: str, path: str):
        """
        后台校验任务: 检查文件完整性并更新 DB Status
        """
        logger.info(f"Starting background verification for file {file_id}")
        try:
            # 验证文件完整性
            is_valid = StorageService.verify_integrity(Path(path), md5)
            
            with Session(engine) as session:
                if is_valid:
                    # Metadata Parsing
                    update_data = {"status": "idle"}
                    try:
                        from app.services.metadata_parser import extract_metadata_from_zstd
                        metadata_dict = extract_metadata_from_zstd(Path(path))
                        
                        if metadata_dict:
                            # Clean device name
                            device_val = metadata_dict.get('device', '')
                            if '(' in device_val:
                                device_val = device_val.split('(')[0].strip()
                                
                            update_data.update({
                                "start_time": metadata_dict.get('startTime', ''),
                                "device_name": device_val,
                                "device_mac": metadata_dict.get('device_mac', ''),
                                "device_version": metadata_dict.get('device version', '') or metadata_dict.get('device_version', ''),
                                "user_name": metadata_dict.get('user_name', ''),
                                "content_meta": metadata_dict
                            })
                            logger.info(f"Metadata extracted for uploaded file {file_id}: {device_val}")
                    except Exception as meta_err:
                        logger.warning(f"Failed to extract metadata for uploaded file {file_id}: {meta_err}")

                    crud.update_file(session, file_id, update_data)
                    logger.info(f"File {file_id} verified successfully.")
                else:
                    msg = "Integrity Check Failed"
                    crud.update_file(session, file_id, {"status": "error", "notes": msg, "error_message": msg})
                    logger.error(f"File {file_id} validation failed.")
        except Exception as e:
            logger.error(f"Error in verify_upload_task: {e}")
            with Session(engine) as session:
                msg = f"Verification Error: {str(e)}"
                crud.update_file(session, file_id, {"status": "error", "notes": msg, "error_message": msg})

    @staticmethod
    def create_batch_zip(files: List[SensorFile]) -> str:
        """
        创建包含多个文件的 Zip 包;
        
        Args:
            files: 要打包的文件对象列表;
            
        Returns:
            str: 生成的 Zip 文件路径;
        """
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix="batch_")
        tmp_zip.close() # 关闭句柄，让 zipfile 打开
        
        try:
            with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_STORED) as zf:
                for file in files:
                    raw_path = StorageService.get_raw_path(file.file_hash)
                    if not raw_path.exists():
                        logger.warning(f"Batch download skipping missing file: {file.id} ({file.file_hash})")
                        continue
                    
                    # 构建 Zip 内的文件名
                    base_name = file.filename
                    suffix = file.name_suffix or ""
                    
                    if suffix:
                        if base_name.lower().endswith(".rawdata"):
                            # data.rawdata + (1) -> data (1).rawdata.zst
                            stem = base_name[:-8]
                            zip_entry_name = f"{stem}{suffix}.rawdata.zst"
                        else:
                            zip_entry_name = f"{base_name}{suffix}.zst"
                    else:
                        zip_entry_name = f"{base_name}.zst"
                    
                    # 添加到 Zip
                    zf.write(raw_path, arcname=zip_entry_name)
            
            return tmp_zip.name
            
        except Exception as e:
            # 如果出错, 尝试清理
            if Path(tmp_zip.name).exists():
                Path(tmp_zip.name).unlink()
            raise e

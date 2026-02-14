"""
文件服务模块;

封装文件相关的业务逻辑，如后台校验、批量处理等;
"""
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlmodel import Session

from app.core.logger import logger
from app.core.database import engine
from app.crud import file as crud
from app.crud import device_mapping as device_mapping_crud
from app.crud import parse_result as parse_result_crud
from app.services.storage import StorageService
from app.services.metadata_parser import extract_metadata_from_zstd
from app.models.sensor_file import SensorFile

class FileService:
    """
    文件业务逻辑服务;
    """

    @staticmethod
    def verify_upload_task(file_id: str, md5: str, path: str):
        """
        后台校验任务: 检查文件完整性并更新 DB Status;
        校验通过后创建 ParseResult 并提取 metadata;
        """
        logger.info(f"Starting background verification for file {file_id}")
        try:
            # 验证文件完整性 并 按需重建索引
            verify_res = StorageService.verify_and_rebuild_index(Path(path), md5)
            is_valid = verify_res["valid"]
            
            with Session(engine) as session:
                if is_valid:
                    # 标记文件为 verified
                    update_data = {"file_status": "verified"}
                    
                    # 如果发生了重建或生成了新索引，更新 PhysicalFile
                    if verify_res.get("frame_index"):
                        phy_file = crud.get_physical_file(session, md5)
                        if phy_file:
                            phy_file.frame_index = verify_res["frame_index"]
                            # 如果重建了，文件大小可能会微调(压缩率差异)，更新 size?
                            # 严格来说 size 是 physical size, path 是 disk path.
                            # verify_and_rebuild_index 替换了原文件，所以 disk size 变了。
                            # update phy_file.size = Path(path).stat().st_size
                            phy_file.size = Path(path).stat().st_size
                            
                            session.add(phy_file)
                            session.commit()
                            logger.info(f"Updated PhysicalFile {md5} with rebuilt frame_index")

                    # 用于创建 ParseResult 的数据
                    parse_data = {"status": "idle"}
                    
                    try:
                        metadata_dict = extract_metadata_from_zstd(Path(path))
                        
                        if metadata_dict:
                            # Clean device name and ensure uppercase
                            device_val = metadata_dict.get('device', '')
                            if '(' in device_val:
                                device_val = device_val.split('(')[0].strip()
                            
                            # Force uppercase for standardization
                            device_val = device_val.upper() if device_val else "UNKNOWN"
                            
                            # Resolve device_type from DeviceMapping
                            resolved = device_mapping_crud.resolve_device_info(session, device_val)
                                
                            update_data.update({
                                "start_time": metadata_dict.get('startTime', ''),
                                "device_name": device_val,
                                "device_mac": metadata_dict.get('device_mac', ''),
                                "device_version": metadata_dict.get('device version', '') or metadata_dict.get('device_version', ''),
                                "user_name": metadata_dict.get('user_name', ''),
                            })
                            
                            # content_meta 和 device_type_used 写入 ParseResult
                            parse_data.update({
                                "content_meta": metadata_dict,
                                "device_type_used": resolved["device_type"],
                            })
                            
                            logger.info(f"Metadata extracted for uploaded file {file_id}: Device={device_val}, Resolved={resolved}")
                    except Exception as meta_err:
                        logger.warning(f"Failed to extract metadata for uploaded file {file_id}: {meta_err}")

                    crud.update_file(session, file_id, update_data)
                    
                    # 创建 ParseResult
                    parse_result_crud.create_or_update(session, file_id, parse_data)
                    
                    logger.info(f"File {file_id} verified successfully.")
                else:
                    msg = "Integrity Check Failed"
                    crud.update_file(session, file_id, {"file_status": "error"})
                    logger.error(f"File {file_id} validation failed.")
        except Exception as e:
            logger.error(f"Error in verify_upload_task: {e}")
            with Session(engine) as session:
                msg = f"Verification Error: {str(e)}"
                crud.update_file(session, file_id, {"file_status": "error"})

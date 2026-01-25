"""
文件存储服务模块。

本模块提供文件上传、存储和删除的相关功能。
"""
import gzip
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import uuid
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.logger import logger


class StorageService:
    """
    文件存储服务。

    负责管理原始文件和处理后文件的存储。
    """

    @staticmethod
    def get_raw_dir() -> Path:
        """获取原始文件存储目录。"""
        settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
        return settings.RAW_DIR

    @staticmethod
    def get_processed_dir(file_id: str) -> Path:
        """获取处理后文件的存储目录。"""
        path = settings.PROCESSED_DIR / file_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def save_rawdata_file(file: UploadFile, file_id: str) -> Dict[str, Any]:
        """
        流式 gzip 压缩保存 .rawdata 文件。

        Args:
            file: 上传文件对象。
            file_id: 文件 ID。

        Returns:
            Dict: 包含 raw_path 的存储结果。
        """
        raw_dir = StorageService.get_raw_dir()
        # 保存为 file_id.rawdata.gz
        destination = raw_dir / f"{file_id}.rawdata.gz"
        
        def _stream_compress():
            with gzip.open(destination, 'wb') as gz_file:
                # 分块读取,边接收边压缩
                while chunk := file.file.read(8192):  # 8KB chunks
                    gz_file.write(chunk)
        
        await run_in_threadpool(_stream_compress)
        
        file_size = destination.stat().st_size
        logger.info(f"Saved rawdata with streaming gzip: {destination} ({file_size} bytes)")
        
        return {
            "raw_path": str(destination),
            "file_size": file_size,
            "extracted_files": []
        }

    @staticmethod
    async def save_zip_file(file: UploadFile) -> List[Dict[str, Any]]:
        logger.info("### EXECUTING NEW SAVE_ZIP_FILE LOGIC ###")
        """
        保存 .zip 文件: 解压并独立处理每个 .rawdata 文件。
        
        Args:
            file: 上传的 zip 文件。
            
        Returns:
            List[Dict]: 处理成功的文件列表,每个元素包含 file_id, raw_path 等信息。
        """
        raw_dir = StorageService.get_raw_dir()
        temp_id = str(uuid.uuid4())
        raw_zip_path = raw_dir / f"temp_{temp_id}.zip"
        
        # 1. 保存临时 Zip 文件
        logger.info(f"Streaming temp zip to: {raw_zip_path}")
        with raw_zip_path.open("wb") as buffer:
            while chunk := await file.read(8192 * 1024):
                await run_in_threadpool(buffer.write, chunk)
                
        processed_files = []
        
        def _process_zip_contents():
            results = []
            try:
                with zipfile.ZipFile(raw_zip_path, 'r') as zf:
                    password = settings.storage.zip_pp.encode() if settings.storage.zip_pp else None
                    
                    for member in zf.namelist():
                        # 仅处理 .rawdata 文件
                        if not member.endswith('.rawdata'):
                            continue
                            
                        # 为该文件生成新的 ID
                        new_file_id = str(uuid.uuid4())
                        
                        # 像普通上传一样保存到 raw 目录 (gzip)
                        dest_path = raw_dir / f"{new_file_id}.rawdata.gz"
                        
                        # 使用流式处理避免将整个文件加载到内存
                        original_size = 0
                        try:
                            # 尝试打开文件流
                            if password:
                                src_stream = zf.open(member, pwd=password)
                            else:
                                src_stream = zf.open(member)
                                
                            with src_stream as src, gzip.open(dest_path, 'wb') as dst:
                                # shutil.copyfileobj 默认使用 chunks (通常 16KB-64KB)
                                shutil.copyfileobj(src, dst)
                                # 无法直接获取大小，需要通过 info 获取或在 copy 时计数
                                # 这里使用 zip info 获取原始大小
                                original_size = zf.getinfo(member).file_size
                                
                        except RuntimeError as e:
                            # 密码相关错误可能表现为 RuntimeError
                            if "encrypted" in str(e) and not password:
                                logger.warning(f"Password required for {member}, skipping")
                                continue
                            raise
                        except zipfile.BadZipFile:
                            logger.error(f"Bad zip entry: {member}")
                            continue

                        file_size = dest_path.stat().st_size
                        
                        results.append({
                            "file_id": new_file_id,
                            "filename": Path(member).name,
                            "original_path_in_zip": member,
                            "raw_path": str(dest_path),
                            "file_size": file_size,
                            "original_size": original_size
                        })
                        logger.info(f"Extracted from zip (streamed): {member} -> {new_file_id}")
                        
            except zipfile.BadZipFile as e:
                logger.error(f"Bad zip file: {e}")
                raise
                
            return results

        try:
            processed_files = await run_in_threadpool(_process_zip_contents)
        finally:
            # 清理临时 zip
            if raw_zip_path.exists():
                raw_zip_path.unlink()
                logger.info(f"Cleaned up temp zip: {raw_zip_path}")
                
        return processed_files

    @staticmethod
    async def save_upload_file(file: UploadFile, file_id: str) -> Dict[str, Any]:
        """
        根据文件类型选择保存策略。

        Args:
            file: FastAPI 上传文件对象。
            file_id: 文件 ID。

        Returns:
            Dict: 存储结果。
        """
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        
        if ext == ".zip":
            # Zip files should be handled via save_zip_file explicitly
            raise ValueError("Zip files must be handled via save_zip_file")
        else:
            # 默认使用流式 gzip (.rawdata 等)
            return await StorageService.save_rawdata_file(file, file_id)

    @staticmethod
    def delete_file(file_id: str) -> None:
        """
        删除文件的原始数据和处理后数据。

        Args:
            file_id: 文件 ID。
        """
        raw_dir = settings.RAW_DIR
        
        # 删除原始文件 (尝试多种扩展名)
        for pattern in [f"{file_id}.rawdata.gz", f"{file_id}.zip"]:
            raw_path = raw_dir / pattern
            if raw_path.exists():
                raw_path.unlink()
                logger.info(f"Deleted raw file: {raw_path}")

        # 删除处理后目录
        proc_dir = settings.PROCESSED_DIR / file_id
        if proc_dir.exists() and proc_dir.is_dir():
            shutil.rmtree(proc_dir)
            logger.info(f"Deleted processed dir: {proc_dir}")

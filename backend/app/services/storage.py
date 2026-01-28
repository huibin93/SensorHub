"""
文件存储服务模块;

本模块提供文件上传、存储和删除的相关功能;
"""
import gzip
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import uuid
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from app.core.config import settings
from app.core.logger import logger


class StorageService:
    """
    文件存储服务;

    负责管理原始文件和处理后文件的存储;
    """

    @staticmethod
    def get_raw_dir() -> Path:
        """获取原始文件存储目录;"""
        settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
        return settings.RAW_DIR

    @staticmethod
    def get_processed_dir(file_hash: str) -> Path:
        """获取处理后文件的存储目录;"""
        # 使用 Hash 作为目录名
        path = settings.PROCESSED_DIR / file_hash
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_raw_path(file_hash: str) -> Path:
        """获取原始文件路径 (Hash 命名)"""
        return settings.RAW_DIR / f"{file_hash}.raw.zst"

    @staticmethod
    async def save_zstd_stream(file: UploadFile, file_hash: str) -> Dict[str, Any]:
        """
        保存 Zstd 压缩流到磁盘 (无校验,单纯落盘);
        
        Args:
            file: 上传的文件流 (Zstd compressed);
            file_hash: 文件的 MD5 (用于生成文件名);
            
        Returns:
            Dict: 包含 raw_path, file_size (phy), file_hash;
        """
        raw_dir = StorageService.get_raw_dir()
        final_filename = f"{file_hash}.raw.zst"
        final_path = raw_dir / final_filename
        
        # 1. 如果文件已存在,直接覆盖还是复用？ 
        # 此时我们无法确认文件内容是否完好（那是 verify_integrity 的事）
        # 但如果是 Retry,我们应该允许覆盖。
        # 为了性能,如果文件已存在且大小 > 0,我们假设是上次上传残留或秒传跳过？
        # 不,秒传逻辑在 Service 层检查 DB status.
        # 如果走到这里,说明决定要写入(Re-upload or New).
        # 为了稳健,直接覆盖写入.
        
        logger.info(f"Streaming zstd upload to {final_path}")
        
        file_size = 0
        try:
            with final_path.open("wb") as buffer:
                while chunk := await file.read(8192 * 1024):
                    await run_in_threadpool(buffer.write, chunk)
                    
            file_size = final_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to save zstd file: {e}")
            # 清理残余
            if final_path.exists():
                final_path.unlink()
            raise
            
        return {
            "raw_path": str(final_path),
            "file_size": file_size,
            "file_hash": file_hash
        }

    @staticmethod
    def verify_integrity(file_path: Path, expected_md5: str) -> bool:
        """
        校验文件完整性: 解压 Zstd 流并计算 MD5;
        
        Args:
            file_path: Zstd 文件路径;
            expected_md5: 期望的原始数据 MD5;
            
        Returns:
            bool: 是否匹配;
        """
        import zstandard as zstd
        import hashlib
        
        if not file_path.exists():
            logger.error(f"File not found for verification: {file_path}")
            return False
            
        logger.info(f"Verifying integrity for {file_path} ...")
        
        dctx = zstd.ZstdDecompressor()
        hasher = hashlib.md5()
        
        try:
            with file_path.open('rb') as ifh:
                 with dctx.stream_reader(ifh) as reader:
                    first_chunk = True
                    while True:
                        chunk = reader.read(65536) # 64KB
                        if not chunk:
                            break
                        
                        # Basic Magic Number Check (Reject PDF renamed as rawdata)
                        if first_chunk:
                            if chunk.startswith(b'%PDF'):
                                logger.error(f"File {file_path} rejected: PDF signature detected.")
                                return False
                            first_chunk = False

                        hasher.update(chunk)
            
            calculated = hasher.hexdigest()
            match = (calculated == expected_md5)
            
            if match:
                logger.info(f"Verification PASSED for {file_path}")
            else:
                logger.error(f"Verification FAILED for {file_path}. Expected {expected_md5}, got {calculated}")
                
            return match
            
        except Exception as e:
            logger.error(f"Verification error (corruption?): {e}")
            return False

    @staticmethod
    def delete_physical_file(file_hash: str) -> None:
        """
        根据 Hash 删除物理文件 (Raw + Processed);
        此操作不可逆，应仅在引用计数为 0 时调用。
        """
        # 1. 删除 Raw 数据
        raw_path = StorageService.get_raw_path(file_hash)
        if raw_path.exists():
            try:
                raw_path.unlink()
                logger.info(f"Deleted physical raw file: {raw_path}")
            except Exception as e:
                logger.error(f"Failed to delete processed dir {raw_path}: {e}")

        # 2. 删除 Processed 数据 (目录)
        proc_dir = StorageService.get_processed_dir(file_hash)
        if proc_dir.exists():
            try:
                shutil.rmtree(proc_dir)
                logger.info(f"Deleted physical processed dir: {proc_dir}")
            except Exception as e:
                logger.error(f"Failed to delete processed dir {proc_dir}: {e}")

    @staticmethod
    def delete_file(file_id: str) -> None:
       """
       Deprecated: Use delete_physical_file(hash) instead.
       """
       pass

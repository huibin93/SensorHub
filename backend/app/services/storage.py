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
    def get_processed_dir(file_id: str) -> Path:
        """获取处理后文件的存储目录;"""
        path = settings.PROCESSED_DIR / file_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def save_rawdata_file(file: UploadFile, file_id: str) -> Dict[str, Any]:
        """
        流式 gzip 压缩保存 .rawdata 文件，并计算 Hash 实现物理去重;

        Returns:
            Dict: 包含 raw_path, file_size, file_hash 的存储结果;
        """
        import hashlib
        import os
        
        raw_dir = StorageService.get_raw_dir()
        # 1. 保存临时文件
        temp_filename = f"temp_{file_id}_{uuid.uuid4()}.gz"
        temp_path = raw_dir / temp_filename
        
        hasher = hashlib.md5()
        file_size = 0
        
        def _stream_compress_and_hash():
            nonlocal file_size
            with gzip.open(temp_path, 'wb') as gz_file:
                while chunk := file.file.read(8192):
                    # 注意: Hash 是基于原始数据还是压缩数据? 
                    # 通常基于原始文件内容(便于跨格式比对)，但这里我们只能拿到原始流
                    # 如果要跟 Zstd 互通，应该 Hash 原始数据。
                    # 这里的 chunk 是原始数据。
                    hasher.update(chunk)
                    gz_file.write(chunk)
            nonlocal file_size 
            file_size = temp_path.stat().st_size
        
        await run_in_threadpool(_stream_compress_and_hash)
        
        file_hash = hasher.hexdigest()
        
        # 2. 物理去重检查
        final_filename = f"{file_hash}.rawdata.gz"
        final_path = raw_dir / final_filename
        
        deduplicated = False
        if final_path.exists():
            # 已存在，删除临时文件
            if temp_path.exists():
                temp_path.unlink()
            deduplicated = True
            file_size = final_path.stat().st_size # 使用现有文件大小
            logger.info(f"Physical deduplication hit: {file_hash}")
        else:
            # 不存在，重命名
            temp_path.rename(final_path)
            logger.info(f"Saved new physical file: {final_path}")
            
        return {
            "raw_path": str(final_path),
            "file_size": file_size,  # 物理文件大小
            "file_hash": file_hash,
            "deduplicated": deduplicated,
            "extracted_files": []
        }

    @staticmethod
    async def save_zip_file(file: UploadFile) -> List[Dict[str, Any]]:
        logger.info("### EXECUTING NEW SAVE_ZIP_FILE LOGIC ###")
        """
        保存 .zip 文件: 解压并独立处理每个 .rawdata 文件;
        
        Args:
            file: 上传的 zip 文件;
            
        Returns:
            List[Dict]: 处理成功的文件列表,每个元素包含 file_id, raw_path 等信息;
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
                        
                        # 临时保存路径
                        dest_path_temp = raw_dir / f"temp_{new_file_id}.gz"
                        
                        # 使用流式处理避免将整个文件加载到内存
                        original_size = 0
                        try:
                            # 尝试打开文件流
                            if password:
                                src_stream = zf.open(member, pwd=password)
                            else:
                                src_stream = zf.open(member)
                                
                            with src_stream as src, gzip.open(dest_path_temp, 'wb') as dst:
                                # 边读边 Hash 边写
                                import hashlib
                                hasher = hashlib.md5()
                                while True:
                                    chunk = src.read(8192)
                                    if not chunk:
                                        break
                                    hasher.update(chunk)
                                    dst.write(chunk)
                                
                                # 获取原始大小
                                original_size = zf.getinfo(member).file_size
                                file_hash = hasher.hexdigest()

                        except RuntimeError as e:
                            # 密码相关错误可能表现为 RuntimeError
                            if "encrypted" in str(e) and not password:
                                logger.warning(f"Password required for {member}, skipping")
                                continue
                            raise
                        except zipfile.BadZipFile:
                            logger.error(f"Bad zip entry: {member}")
                            continue
                        
                        # 物理去重
                        final_filename = f"{file_hash}.rawdata.gz"
                        final_path = raw_dir / final_filename
                        deduplicated = False
                        
                        if final_path.exists():
                             if dest_path_temp.exists():
                                 dest_path_temp.unlink()
                             deduplicated = True
                             file_size = final_path.stat().st_size
                        else:
                             dest_path_temp.rename(final_path)
                             file_size = final_path.stat().st_size
                        
                        results.append({
                            "file_id": new_file_id, # 仍生成一个 ID 用于 Session 里的临时引用，但最终 SensorFile ID 会根据 Hash 决定
                            "filename": Path(member).name,
                            "original_path_in_zip": member,
                            "raw_path": str(final_path),
                            "file_size": file_size,
                            "original_size": original_size,
                            "file_hash": file_hash,
                            "deduplicated": deduplicated
                        })
                        logger.info(f"Extracted zip entry {member} -> {file_hash} (Dedup: {deduplicated})")
                        
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
        根据文件类型选择保存策略;

        Args:
            file: FastAPI 上传文件对象;
            file_id: 文件 ID;

        Returns:
            Dict: 存储结果;
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
        删除文件的原始数据和处理后数据;

        Args:
            file_id: 文件 ID;
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

    @staticmethod
    async def verify_and_save_zstd(file: UploadFile, file_hash: str) -> Dict[str, Any]:
        """
        保存并校验 Zstd 压缩文件;
        
        Args:
            file: 上传的 .zst 文件流;
            file_hash: 前端计算的原始文件 Hash (Expectation);
            
        Returns:
            Dict: 存储结果 (如果有错误则抛出异常);
        """
        import zstandard as zstd
        import hashlib
        
        raw_dir = StorageService.get_raw_dir()
        # 命名规则: {hash}.zst
        # 注意: 如果不同用户传相同文件，hash相同，会覆盖还是复用？
        # 秒传逻辑下，如果Hash已存在，通常不再调 Upload;
        # 如果Hash不存在，这里保存;
        # 为了避免文件名冲突(万一不同内容Hash碰撞? MD5有可能)，可以加UUID?
        # 但秒传依赖 Hash 唯一性;我们假设 Hash 足够强 (MD5/SHA256);
        # 用户需求: storage/{x_original_hash}.zst
        zst_path = raw_dir / f"{file_hash}.zst"
        deduplicated = False
        if zst_path.exists():
            # 已存在，假设完好 (可以加 Size 校验)
            logger.info(f"Zst physical file exists: {zst_path}")
            deduplicated = True
            # 我们仍然计算 Hash 来校验上传的文件是否匹配 (Double Check)
            # 或者如果是秒传，应该在上层拦截。
            # 如果走到这里，说明是新上传，但 Hash 碰巧一样？或者强制覆盖？
            # 这里的逻辑是存盘。如果文件已存在，我们可以跳过写入，但必须校验 Hash。
            # 为了简单，我们每次都写入（覆盖），或者写临时文件校验后再覆盖。
            # 鉴于 `StorageService` 应该只管存储，我们先写临时，校验通过后 rename/覆盖。
        
        temp_zst_path = raw_dir / f"temp_{file_hash}_{uuid.uuid4()}.zst"
        
        # 1. 保存 .zst 文件
        # 注意: 这一步只是暂存，如果校验失败需要删除
        # 但为了性能，直接写入目标位置
        logger.info(f"Saving zst file to {temp_zst_path}")
        try:
            with temp_zst_path.open("wb") as buffer:
                # 使用 copyfileobj 高效写入
                await run_in_threadpool(shutil.copyfileobj, file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save zst file: {e}")
            raise
            
        # 2. 边解压边计算 Hash
        logger.info("Verifying zst integrity...")
        dctx = zstd.ZstdDecompressor()
        # 根据前端 SparkMD5，这里也用 MD5;如果未来改前端，这里必须同步;
        hasher = hashlib.md5() 
        
        def _verify():
            with temp_zst_path.open('rb') as ifh:
                with dctx.stream_reader(ifh) as reader:
                    while True:
                        chunk = reader.read(65536) # 64KB
                        if not chunk:
                            break
                        hasher.update(chunk)
            return hasher.hexdigest()
            
        try:
            calculated_hash = await run_in_threadpool(_verify)
        except Exception as e:
            # 解压失败，可能是文件损坏
            logger.error(f"Zstd decompression failed: {e}")
            if temp_zst_path.exists():
                temp_zst_path.unlink()
            raise ValueError("Corrupted zstd file")
            
        logger.info(f"Expected: {file_hash}, Calculated: {calculated_hash}")
        
        if calculated_hash != file_hash:
            # 校验失败
            if temp_zst_path.exists():
                temp_zst_path.unlink()
            raise ValueError(f"Hash mismatch! Expected {file_hash} but got {calculated_hash}")
        
        # 校验成功，移动到最终位置
        if zst_path.exists():
             if temp_zst_path.exists():
                 temp_zst_path.unlink()
             deduplicated = True
        else:
             temp_zst_path.rename(zst_path)
             
        return {
            "raw_path": str(zst_path),
            "file_size": zst_path.stat().st_size,
            "file_hash": file_hash,
            "deduplicated": deduplicated
        }

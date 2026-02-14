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
    def verify_and_rebuild_index(file_path: Path, expected_md5: str, existing_index: Dict = None) -> Dict[str, Any]:
        """
        校验文件完整性，并按需重建帧索引 (Frame Index);
        
        策略:
        1. 全量解压读取，计算真实 MD5。
        2. 同时进行重压缩 (Re-compression)，生成标准化的帧索引 (2MB Chunk, Line Aligned)。
        3. 如果源文件 MD5 匹配但索引缺失/无效，用新生成的临时文件替换源文件 (或仅更新索引，视情况而定)。
           为简化逻辑，若决定重建，统一用新文件替换旧文件，确保 Data 与 Index 绝对一致。
        
        Args:
            file_path: Zstd 文件路径;
            expected_md5: 期望的原始数据 MD5 (必填);
            existing_index: 数据库中已有的索引 (可选,用于参考);
            
        Returns:
            Dict: {
                "valid": bool,           # MD5 是否匹配
                "rebuilt": bool,         # 是否发生了重建/替换
                "frame_index": dict,     # 最终有效的帧索引 (原样或新建)
                "file_size_bytes": int   # 解压后的实际大小
            }
        """
        import zstandard as zstd
        import hashlib
        import os
        
        if not file_path.exists():
            logger.error(f"File not found for verification: {file_path}")
            return {"valid": False, "rebuilt": False, "frame_index": None, "file_size_bytes": 0}

        logger.info(f"Verifying and potentially rebuilding {file_path} (Expected MD5: {expected_md5})")
        
        # 1. 准备重建环境
        temp_path = file_path.with_name(f"rebuild_{uuid.uuid4()}.zst")
        
        dctx = zstd.ZstdDecompressor()
        cctx = zstd.ZstdCompressor(level=6)
        
        hasher = hashlib.md5()
        
        # 重建状态
        new_frame_index_list = []
        raw_buffer = bytearray()
        
        MIN_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB
        MAX_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
        
        offset = 0          # 解压数据累计偏移
        upload_offset = 0   # 压缩文件累计偏移 (新文件)
        
        try:
            with file_path.open('rb') as ifh, temp_path.open('wb') as ofh:
                with dctx.stream_reader(ifh) as reader:
                    while True:
                        # 每次读取 64KB 解压数据
                        chunk = reader.read(64 * 1024)
                        if not chunk:
                            break
                        
                        hasher.update(chunk)
                        raw_buffer.extend(chunk)
                        
                        # 处理缓冲区: 切分帧
                        while len(raw_buffer) >= MAX_CHUNK_SIZE:
                            # 寻找换行符
                            search_start = MIN_CHUNK_SIZE
                            search_end = MAX_CHUNK_SIZE
                            
                            newline_pos = raw_buffer.find(b'\n', search_start, search_end)
                            
                            cut_pos = 0
                            ends_with_newline = False
                            
                            if newline_pos != -1:
                                cut_pos = newline_pos + 1
                                ends_with_newline = True
                            else:
                                cut_pos = MAX_CHUNK_SIZE
                                if raw_buffer[cut_pos-1] == 10:
                                    ends_with_newline = True
                            
                            # 切分并压缩
                            chunk_data = raw_buffer[:cut_pos]
                            del raw_buffer[:cut_pos]
                            
                            compressed = cctx.compress(chunk_data)
                            ofh.write(compressed)
                            
                            c_len = len(compressed)
                            d_len = len(chunk_data)
                            
                            new_frame_index_list.append({
                                "cs": upload_offset,
                                "cl": c_len,
                                "ds": offset,
                                "dl": d_len,
                                "nl": ends_with_newline
                            })
                            
                            upload_offset += c_len
                            offset += d_len
                
                # 处理剩余数据
                while raw_buffer:
                    cut_pos = min(len(raw_buffer), MAX_CHUNK_SIZE)
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
                    
                    compressed = cctx.compress(chunk_data)
                    ofh.write(compressed)
                    
                    c_len = len(compressed)
                    d_len = len(chunk_data)
                    
                    new_frame_index_list.append({
                        "cs": upload_offset,
                        "cl": c_len,
                        "ds": offset,
                        "dl": d_len,
                        "nl": ends_with_newline
                    })
                    upload_offset += c_len
                    offset += d_len

            # 计算最终 MD5
            calculated_md5 = hasher.hexdigest()
            total_size_bytes = offset
            
            if calculated_md5 != expected_md5:
                logger.error(f"Integrity check failed! Expected {expected_md5}, got {calculated_md5}")
                if temp_path.exists():
                    os.remove(temp_path)
                return {"valid": False, "rebuilt": False, "frame_index": None, "file_size_bytes": 0}
            
            # MD5 正确。构建完整 Frame Index 对象
            complete_new_index = {
                "version": 2,
                "frameSize": MIN_CHUNK_SIZE,
                "maxFrameSize": MAX_CHUNK_SIZE,
                "lineAligned": True,
                "originalSize": total_size_bytes,
                "compressedSize": upload_offset,
                "frames": new_frame_index_list
            }
            
            # 决策: 是否替换原文件?
            # 如果原文件没有 index, 或者原文件的 index 在逻辑上看起来不对 (简单判断 version/originalSize),
            # 或者我们为了统一标准, 只要重新跑了就替换?
            # 策略: Always Replace. 这样保证了磁盘上的 .zst 结构与我们生成的 index 100% 匹配.
            # 尤其是前端上传的 zst 可能压缩等级不同, 或者分块不同.
            
            logger.info(f"Rebuild success. Replacing original file {file_path} with standardized zst.")
            
            # Windows 上 rename 需要先 remove 目标 (或者用 replace)
            # shutil.move or os.replace (atomic on POSIX, replacing on Win Py3.3+)
            os.replace(temp_path, file_path)
            
            return {
                "valid": True,
                "rebuilt": True,
                "frame_index": complete_new_index,
                "file_size_bytes": total_size_bytes
            }

        except Exception as e:
            logger.error(f"Error during verify_and_rebuild: {e}")
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except:
                    pass
            return {"valid": False, "rebuilt": False, "frame_index": None, "file_size_bytes": 0}

    @staticmethod
    def verify_integrity(file_path: Path, expected_md5: str) -> bool:
        """Deprecated. Use verify_and_rebuild_index instead."""
        res = StorageService.verify_and_rebuild_index(file_path, expected_md5)
        return res["valid"]

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
       已弃用: 请改用 delete_physical_file(hash)。
       """
       pass

    @staticmethod
    def read_zstd_file(file_hash: str, offset: int = 0, limit_bytes: int = 1024 * 1024) -> dict:
        """
        读取 Zstd 压缩文件的内容（分段读取）;
        
        Args:
            file_hash: 文件 Hash (MD5);
            offset: 从原始数据的哪个字节开始读取;
            limit_bytes: 最多读取多少字节;
            
        Returns:
            dict: {
                "content": str,      # 解码后的文本内容
                "offset": int,       # 本次读取的起始偏移量
                "bytes_read": int,   # 本次实际读取的字节数
                "total_size": int,   # 原始文件总大小
                "has_more": bool     # 是否还有更多内容
            }
            
        Raises:
            FileNotFoundError: 文件不存在;
            ValueError: offset 超出范围;
            UnicodeDecodeError: 解码失败（非文本文件）;
        """
        import zstandard as zstd
        
        raw_path = StorageService.get_raw_path(file_hash)
        if not raw_path.exists():
            raise FileNotFoundError(f"File not found: {file_hash}")
        
        logger.info(f"Reading zstd file {file_hash} from offset {offset}, limit {limit_bytes}")
        
        dctx = zstd.ZstdDecompressor()
        
        try:
            # 第一步：扫描整个文件以获取总大小（可能需要缓存优化）
            total_size = 0
            with raw_path.open('rb') as ifh:
                with dctx.stream_reader(ifh) as reader:
                    while True:
                        chunk = reader.read(65536)
                        if not chunk:
                            break
                        total_size += len(chunk)
            
            # 检查 offset 是否有效
            if offset < 0:
                raise ValueError("Offset cannot be negative")
            if offset >= total_size:
                # offset 超出文件末尾，返回空内容
                return {
                    "content": "",
                    "offset": offset,
                    "bytes_read": 0,
                    "total_size": total_size,
                    "has_more": False
                }
            
            # 第二步：从指定 offset 开始读取内容
            current_pos = 0
            content_bytes = bytearray()
            target_end = min(offset + limit_bytes, total_size)
            
            with raw_path.open('rb') as ifh:
                with dctx.stream_reader(ifh) as reader:
                    while current_pos < target_end:
                        chunk_size = min(65536, target_end - current_pos)
                        chunk = reader.read(chunk_size)
                        if not chunk:
                            break
                        
                        chunk_start = current_pos
                        chunk_end = current_pos + len(chunk)
                        
                        # 判断是否在目标范围内
                        if chunk_end > offset:
                            # 计算实际需要的部分
                            read_start = max(0, offset - chunk_start)
                            read_end = min(len(chunk), target_end - chunk_start)
                            content_bytes.extend(chunk[read_start:read_end])
                        
                        current_pos = chunk_end
            
            # 解码为文本
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    content = content_bytes.decode('gbk')
                    logger.warning(f"File {file_hash} decoded using GBK encoding")
                except UnicodeDecodeError:
                    raise UnicodeDecodeError(
                        'utf-8', content_bytes[:100], 0, min(100, len(content_bytes)),
                        'Unable to decode file content. File may not be a text file.'
                    )
            
            bytes_read = len(content_bytes)
            has_more = (offset + bytes_read) < total_size
            
            logger.info(f"Read {bytes_read} bytes from {file_hash}, has_more: {has_more}")
            
            return {
                "content": content,
                "offset": offset,
                "bytes_read": bytes_read,
                "total_size": total_size,
                "has_more": has_more
            }
            
        except Exception as e:
            logger.error(f"Error reading zstd file {file_hash}: {e}")
            raise

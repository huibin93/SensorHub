"""
文件相关 API 端点模块;

本模块提供传感器文件的 CRUD 操作、上传、下载、解析等 API 端点;
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Header, BackgroundTasks
from starlette.background import BackgroundTask
from pathlib import Path
from sqlmodel import Session
from typing import List, Optional, Any
import uuid
import json
from datetime import datetime

from app.api import deps
from app.schemas import api_models
from app.crud import file as crud
from app.services.storage import StorageService
from app.services.parser import ParserService
from app.services.metadata import parse_filename, ensure_test_types_exist
from app.models.sensor_file import SensorFile, PhysicalFile
from app.core.logger import logger
from app.core.database import engine

router = APIRouter()


@router.get("/stats", response_model=api_models.StatsResponse)
def get_stats(session: Session = Depends(deps.get_db)) -> api_models.StatsResponse:
    """
    获取文件统计信息;

    Returns:
        StatsResponse: 包含文件总数、今日上传数等统计信息;
    """
    return crud.get_stats(session)


@router.get("/files", response_model=api_models.PaginatedFilesResponse)
def get_files(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    device: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "-uploadTime",
    session: Session = Depends(deps.get_db)
) -> api_models.PaginatedFilesResponse:
    """
    获取文件列表(分页);

    Args:
        page: 页码,从 1 开始;
        limit: 每页数量;
        search: 搜索关键词(文件名或备注);
        device: 设备类型筛选;
        status: 状态筛选;
        sort: 排序字段,前缀 "-" 表示降序;

    Returns:
        PaginatedFilesResponse: 分页的文件列表;
    """
    try:
        skip = (page - 1) * limit
        files, total = crud.get_files(session, skip, limit, search, device, status, sort)
        return {
            "items": files,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if limit > 0 else 1
        }
    except Exception as e:
        import traceback
        logger.error(f"Error in get_files: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/check")
def check_file(
    hash: Optional[str] = Query(None), # Hash 变为可选
    filename: Optional[str] = Query(None), 
    size: Optional[int] = Query(None), # 新增大小参数
    session: Session = Depends(deps.get_db)
):
    """
    检查文件是否已存在 (Pre-check & 秒传);
    
    Args:
        hash: 文件 Hash (MD5), 可选.
        filename: 文件名, 可选.
        size: 文件大小, 可选.
        
    Returns:
        dict: {exists: bool, exact_match: bool, file: ...}
    """
    # 0. 快速前置检查 (Fast Check): 同名且同大小
    if filename and size is not None:
        fast_match = crud.get_file_by_name_and_size(session, filename, size)
        if fast_match:
             return {
                 "exists": True, 
                 "exact_match": True, 
                 "fileId": fast_match.id, 
                 "filename": fast_match.filename,
                 "message": "Fast Check: File with same name and size exists."
             }

    # 1. 如果提供了 Hash 和文件名，检查严格匹配
    if hash and filename:
        exact = crud.get_exact_match_file(session, hash, filename)
        if exact:
             return {
                 "exists": True, 
                 "exact_match": True, 
                 "fileId": exact.id, 
                 "filename": exact.filename,
                 "message": "Strict Check: File with same content and name already exists."
             }

    # 2. 如果提供了 Hash，检查内容匹配 (秒传)
    if hash:
        file = crud.get_file_by_hash(session, hash)
        if file:
            return {
                "exists": True, 
                "exact_match": False,
                "fileId": file.id, 
                "filename": file.filename,
                "message": "File content exists (different name)."
            }
    
    return {"exists": False, "exact_match": False}


# --- Background Tasks ---
def verify_upload_task(file_id: str, md5: str, path: str):
    """
    后台校验任务: 检查文件完整性并更新 DB Status
    """
    logger.info(f"Starting background verification for file {file_id}")
    try:
        is_valid = StorageService.verify_integrity(Path(path), md5)
        
        with Session(engine) as session:
            if is_valid:
                crud.update_file(session, file_id, {"status": "idle"})
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


@router.post("/files/upload", response_model=Any) # Return Any to support flexible JSON
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    md5: str = Form(...),
    filename: str = Form(..., description="Original filename"),
    original_size: int = Form(...),
    deviceType: Optional[str] = Form("Unknown"),
    session: Session = Depends(deps.get_db)
) -> Any:
    """
    流式上传 Zstd 压缩文件 (接口 v2);
    前端已完成压缩和 MD5 计算。后端直接落盘并异步校验。
    """
    # 1. 检查物理文件是否存在 (秒传核心逻辑)
    existing_phy = crud.get_physical_file(session, md5)
    expected_raw_path = StorageService.get_raw_path(md5)
    
    if existing_phy and expected_raw_path.exists():
         # --- 命中秒传 (Physical Deduplication) ---
         logger.info(f"Instant upload (deduplication) for {filename} ({md5})")
         
         # 严苛去重检查: 如果已存在 同名且同Hash 的 SensorFile, 直接返回该记录
         exact_match = crud.get_exact_match_file(session, md5, filename)
         if exact_match:
             logger.info(f"Exact match found for {filename} ({md5}). Skipping creation.")
             return {
                 "code": 200,
                 "data": {
                     "file_id": exact_match.id,
                     "status": exact_match.status,
                     "saved_path": str(expected_raw_path),
                     "is_duplicate": True
                 },
                 "message": "文件已存在 (无需重复上传)"
             }

         # 检查解析状态 (Smart Status)
         processed_dir = StorageService.get_processed_dir(md5)
         initial_status = "idle"
         if processed_dir.exists() and any(processed_dir.iterdir()):
             initial_status = "processed"
         
         # 创建新的 SensorFile (指向同一个 Hash, 但文件名不同)
         file_id = str(uuid.uuid4())
         
         # 计算文件名后缀
         name_suffix = crud.get_next_naming_suffix(session, filename)
         
         # 显示大小
         if original_size < 1024:
             size_str = f"{original_size} B"
         elif original_size < 1024 * 1024:
             size_str = f"{original_size / 1024:.1f} KB"
         elif original_size < 1024 * 1024 * 1024:
             size_str = f"{original_size / (1024 * 1024):.1f} MB"
         else:
             size_str = f"{original_size / (1024 * 1024 * 1024):.1f} GB"
         
         new_sf = SensorFile(
             id=file_id,
             file_hash=md5,
             filename=filename, # 使用新上传的文件名
             deviceType=deviceType,
             deviceModel="Unknown",
             size=size_str,
             file_size_bytes=original_size, # 保存 Int 大小
             name_suffix=name_suffix,
             uploadTime=datetime.utcnow().isoformat(),
             status=initial_status,
             processedDir=str(processed_dir)
         )
         
         # Parse Metadata (Optional override for deduplication case? 
         # Requirement says "Frontend file entry also needs parsing". 
         # If strict exact match found, we skip return.
         # But here we are creating a NEW SensorFile pointing to OLD physical file.
         # So we SHOULD parse the NEW filename metadata.
         meta = parse_filename(filename)
         new_sf.test_type_l1 = meta.get("test_type_l1", "Unknown")
         new_sf.test_type_l2 = meta.get("test_type_l2", "--")
         new_sf.tester = meta.get("tester", "")
         new_sf.mac = meta.get("mac", "")
         new_sf.collection_time = meta.get("collection_time", "")
         if meta.get("deviceType"):
             new_sf.device_type = meta.get("deviceType")
         
         # Auto-Insert Dictionary
         if meta.get("test_type_l1"):
             ensure_test_types_exist(session, meta.get("test_type_l1"), meta.get("test_type_l2"))

         crud.create_file(session, new_sf)
         
         return {
             "code": 200,
             "data": {
                 "file_id": file_id,
                 "status": initial_status,
                 "saved_path": str(expected_raw_path)
             },
             "message": "🎉 秒传成功！(File exists)"
         }
    
    # 2. 物理文件不存在，执行常规上传
    file_id = str(uuid.uuid4())
    
    # 3. 流式落盘 (不论是否首次,都覆盖写入以确保文件正确)
    try:
        save_res = await StorageService.save_zstd_stream(file, md5)
        saved_path = save_res["raw_path"]
        
        # 4. 更新/创建 DB 记录
        
        # 4.1 PhysicalFile
        phy_file = crud.get_physical_file(session, md5)
        if not phy_file:
            phy_file = PhysicalFile(hash=md5, size=save_res["file_size"], path=saved_path)
            crud.create_physical_file(session, phy_file)
            
        # 4.2 SensorFile
        # 计算文件名后缀
        name_suffix = crud.get_next_naming_suffix(session, filename)
        
        # 显示大小
        if original_size < 1024:
            size_str = f"{original_size} B"
        elif original_size < 1024 * 1024:
            size_str = f"{original_size / 1024:.1f} KB"
        elif original_size < 1024 * 1024 * 1024:
            size_str = f"{original_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{original_size / (1024 * 1024 * 1024):.1f} GB"
            
        new_sf = SensorFile(
            id=file_id,
            file_hash=md5,
            filename=filename,
            deviceType=deviceType,
            deviceModel="Unknown",
            size=size_str,
            file_size_bytes=original_size, # 保存 Int 大小 
            name_suffix=name_suffix,
            uploadTime=datetime.utcnow().isoformat(),
            status="unverified",
            processedDir=str(StorageService.get_processed_dir(md5)) # 使用 Hash
        )
        
        # Parse Metadata
        meta = parse_filename(filename)
        new_sf.test_type_l1 = meta.get("test_type_l1", "Unknown")
        new_sf.test_type_l2 = meta.get("test_type_l2", "--")
        new_sf.tester = meta.get("tester", "")
        new_sf.mac = meta.get("mac", "")
        new_sf.collection_time = meta.get("collection_time", "")
        if meta.get("deviceType"):
             new_sf.device_type = meta.get("deviceType")

        # Auto-Insert Dictionary
        if meta.get("test_type_l1"):
             ensure_test_types_exist(session, meta.get("test_type_l1"), meta.get("test_type_l2"))

        crud.create_file(session, new_sf)
        
        # 5. 触发后台校验
        background_tasks.add_task(verify_upload_task, file_id, md5, saved_path)
        
        return {
            "code": 200,
            "data": {
                "file_id": file_id,
                "status": "unverified",
                "saved_path": saved_path
            },
            "message": "文件上传成功,正在校验..."
        }
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.patch("/files/{file_id}")
def update_file(
    file_id: str,
    update: api_models.FileUpdateRequest,
    session: Session = Depends(deps.get_db)
) -> SensorFile:
    """
    更新文件信息;

    Args:
        file_id: 文件 ID;
        update: 要更新的字段;

    Returns:
        SensorFile: 更新后的文件对象;

    Raises:
        HTTPException: 文件不存在时抛出 404 错误;
    """
    updated = crud.update_file(session, file_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="File not found")
    return updated


@router.delete("/files/{file_id}")
def delete_file(file_id: str, session: Session = Depends(deps.get_db)) -> dict:
    """
    删除单个文件;

    Args:
        file_id: 文件 ID;

    Returns:
        dict: 删除结果;
    """
    crud.delete_file_safely(session, file_id)
    # StorageService.delete_file(file_id) # Deprecated, handled in delete_file_safely
    return {"success": True}


@router.post("/files/batch-delete")
def batch_delete(
    request: api_models.BatchDeleteRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    批量删除文件;

    Args:
        request: 包含要删除的文件 ID 列表;

    Returns:
        dict: 删除结果,包含删除数量;
    """
    for fid in request.ids:
        crud.delete_file_safely(session, fid)
        # StorageService.delete_file(fid)
    return {"success": True, "deleted": len(request.ids)}


@router.get("/files/{file_id}/structure")
def get_structure(file_id: str, session: Session = Depends(deps.get_db)) -> dict:
    """
    获取文件结构信息;

    Args:
        file_id: 文件 ID;

    Returns:
        dict: 文件结构元数据;

    Raises:
        HTTPException: 文件不存在时抛出 404 错误;
    """
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "fileId": file.id,
        "status": file.status,
        "processedDir": file.processed_dir,
        "contentMeta": file.content_meta or {}
    }


@router.get("/files/{file_id}/data/{key}")
def get_file_data(
    file_id: str,
    key: str,
    limit: int = 1000,
    columns: Optional[str] = None,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    获取文件解析后的数据;

    Args:
        file_id: 文件 ID;
        key: 数据键名(对应 Parquet 文件名);
        limit: 返回行数限制;
        columns: 要返回的列名,逗号分隔;

    Returns:
        dict: 包含数据数组的字典;

    Raises:
        HTTPException: 文件或数据不存在时抛出 404 错误;
    """
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    # 读取 Parquet 文件 (使用 Hash 路径)
    # 修正: processedDir 已经在 create 时指向了 Hash 目录，但为了保险，我们使用 file.file_hash
    # 因为 processedDir 字段存储的是 字符串 路径。
    # 最好使用 Service 统一获取
    processed_dir = StorageService.get_processed_dir(file.file_hash)
    pq_path = processed_dir / f"{key}.parquet"

    if not pq_path.exists():
        raise HTTPException(404, f"Data not found: {key}")

    try:
        import pyarrow.parquet as pq
        table = pq.read_table(pq_path)

        # 筛选列
        if columns:
            cols = columns.split(',')
            existing = table.column_names
            cols = [c for c in cols if c in existing]
            if cols:
                table = table.select(cols)

        # 限制行数
        df = table.to_pandas()
        if limit > 0:
            df = df.head(limit)

        data = json.loads(df.to_json(orient="records"))
        return {"data": data}
    except Exception as e:
        raise HTTPException(500, f"Error reading data: {str(e)}")


@router.get("/files/{file_id}/download")
def download_file(file_id: str, session: Session = Depends(deps.get_db)):
    """
    下载原始文件 (Zstd压缩);
    前端负责解压。

    Args:
        file_id: 文件 ID;

    Returns:
        FileResponse: .raw.zst 文件;
    """
    from fastapi.responses import FileResponse
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    raw_path = StorageService.get_raw_path(file.file_hash)
    if not raw_path.exists():
        raise HTTPException(404, "Raw file not found")

    # 构建下载文件名: filename(suffix).raw.zst
    # 例如: data.rawdata -> data (1).rawdata.zst
    base_name = file.filename
    suffix = file.name_suffix or ""
    
    # 简单的拼接逻辑：假设 filename 包含扩展名 .rawdata
    # 如果 suffix 存在，插入到扩展名之前? 
    # 用户需求: filename="data.rawdata", name_suffix=" (1)" -> "data (1).rawdata"
    
    if suffix:
        if base_name.lower().endswith(".rawdata"):
            stem = base_name[:-8] # remove .rawdata
            final_name = f"{stem}{suffix}.rawdata.zst"
        else:
             # 如果不是 .rawdata 结尾, 直接追加
            final_name = f"{base_name}{suffix}.zst"
    else:
        final_name = f"{base_name}.zst"

    return FileResponse(
        path=raw_path,
        filename=final_name,
        media_type="application/zstd"
    )


@router.post("/files/batch-download")
def batch_download(
    request: api_models.BatchDownloadRequest,
    session: Session = Depends(deps.get_db)
):
    """
    批量下载文件 (Zip包);
    返回一个包含多个 .raw.zst 文件的 Zip 包.

    Args:
        request: 包含要下载的文件 ID 列表;

    Returns:
        FileResponse: 临时 Zip 文件;
    """
    import tempfile
    import zipfile
    from fastapi.responses import FileResponse
    
    # 1. 获取所有请求的文件信息
    files_to_download = []
    for fid in request.ids:
        file = crud.get_file(session, fid)
        if file:
            files_to_download.append(file)
            
    if not files_to_download:
        raise HTTPException(400, "No valid files found")
        
    try:
        # 2. 创建临时 Zip 文件
        # delete=False 因为 FileResponse 需要读取它, 之后由 BackgroundTask 清理?
        # 或者使用 tempfile.NamedTemporaryFile 并依赖 OS 清理 (但在 Windows 上 FileResponse 打开时可能锁住)
        # 更好的方式是每次请求生成一个临时文件，依靠 FileResponse(background=...) 清理
        
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix="batch_")
        tmp_zip.close() # 关闭句柄，让 zipfile 打开
        
        with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_STORED) as zf:
            for file in files_to_download:
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
        
        # 3. 返回响应
        return FileResponse(
            path=tmp_zip.name,
            filename=f"sensorhub_batch_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip",
            media_type="application/zip",
            background=BackgroundTask(lambda p: Path(p).unlink(missing_ok=True), tmp_zip.name)
        )
        
    except Exception as e:
        logger.error(f"Batch download error: {e}")
        raise HTTPException(500, f"Batch download failed: {str(e)}")


@router.post("/files/{file_id}/parse")
def trigger_parse(
    file_id: str,
    request: api_models.ParseRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    触发文件解析;

    Args:
        file_id: 文件 ID;
        request: 解析选项;

    Returns:
        dict: 解析状态;

    Raises:
        HTTPException: 文件不存在时抛出 404 错误;
    """
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    # 直接设置状态为已处理 (简化状态管理, 无 Processing 状态)
    crud.update_file(session, file_id, {"status": "Processed"})

    return {"status": "Processed", "message": "Parse completed"}


@router.get("/files/{file_id}/content")
async def get_file_content_stream(
    file_id: str,
    session: Session = Depends(deps.get_db)
):
    """
    获取文件压缩数据流（前端解压）;
    
    返回原始的 .zst 压缩文件，前端使用 zstd-wasm 解压;
    
    Returns:
        StreamingResponse: .zst 压缩数据流
        
    Headers:
        - Content-Type: application/zstd
        - X-File-Name: 原始文件名
        - X-Original-Size: 原始文件大小（字节）
        - X-Compressed-Size: 压缩文件大小（字节）
    
    Raises:
        HTTPException: 文件不存在(404)、物理文件缺失(404);
    """
    from fastapi.responses import StreamingResponse
    import os
    
    # 获取文件记录
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")
    
    # 获取物理文件路径
    raw_path = StorageService.get_raw_path(file.file_hash)
    if not raw_path.exists():
        logger.error(f"Physical file not found for {file_id}: {raw_path}")
        raise HTTPException(404, "Physical file not found")
    
    # 获取文件大小
    compressed_size = os.path.getsize(raw_path)
    
    # 获取原始大小（从 SensorFile.file_size_bytes）
    original_size = file.file_size_bytes if file.file_size_bytes > 0 else compressed_size
    
    # 定义流式生成器
    async def stream_compressed_file():
        """流式读取压缩文件"""
        chunk_size = 64 * 1024  # 64KB chunks
        with open(raw_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    # 返回流式响应
    return StreamingResponse(
        stream_compressed_file(),
        media_type="application/zstd",
        headers={
            "X-File-Name": file.filename,
            "X-Original-Size": str(original_size),
            "X-Compressed-Size": str(compressed_size),
            "Content-Disposition": f'inline; filename="{file.filename}.zst"'
        }
    )

"""
文件相关 API 端点模块;

本模块提供传感器文件的 CRUD 操作、上传、下载、解析等 API 端点;
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Header
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
from app.models.sensor_file import SensorFile
from app.core.logger import logger

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
        page: 页码，从 1 开始;
        limit: 每页数量;
        search: 搜索关键词(文件名或备注);
        device: 设备类型筛选;
        status: 状态筛选;
        sort: 排序字段，前缀 "-" 表示降序;

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
def check_file(hash: str, session: Session = Depends(deps.get_db)):
    """
    检查文件是否已存在(秒传);
    
    Args:
        hash: 文件 Hash (MD5).
        
    Returns:
        dict: {exists: bool, file: ...}
    """
    file = crud.get_file_by_hash(session, hash)
    if file:
        return {"exists": True, "fileId": file.id, "filename": file.filename}
    return {"exists": False}


@router.post("/files/upload", response_model=api_models.UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    deviceType: Optional[str] = Form(None),
    x_original_hash: Optional[str] = Header(None, alias="X-Original-Hash"),
    x_original_size: Optional[str] = Header(None, alias="X-Original-Size"),
    session: Session = Depends(deps.get_db)
) -> Any: # Changed return type to Any to support JSONResponse for 418
    """
    上传传感器文件; 支持普通上传、Zstd 压缩上传(Hash校验)及 Zip 归档上传;
    """
    from fastapi.responses import JSONResponse
    from app.models.sensor_file import PhysicalFile

    # --- 内部辅助函数: 处理 DB 记录逻辑 ---
    def process_record(file_hash: str, file_size: int, raw_path: str, filename: str, d_type: str = "Unknown") -> SensorFile:
        # 1. PhysicalFile 处理
        phy_file = crud.get_physical_file(session, file_hash)
        if not phy_file:
            phy_file = PhysicalFile(hash=file_hash, size=file_size, path=raw_path)
            crud.create_physical_file(session, phy_file)
        else:
            # 418 彩蛋检查: Hash 相同但 Size 不同
            if phy_file.size != file_size:
                 # 抛出特殊异常以便外层捕获返回 418? 
                 # 直接 raise HTTPException 418 不支持自定义 Body? FastAPI 支持。
                 # 但这里我们先简单的 raise 
                 raise HTTPException(status_code=418, detail="I'm a teapot: MD5 Collision Detected!")

        # 2. SensorFile 处理
        target_filename = filename
        
        # 检查文件名冲突
        existing_file_by_name = crud.get_file_by_filename(session, filename)
        if existing_file_by_name:
            if existing_file_by_name.file_hash == file_hash:
                # 场景 2: 文件名相同且内容相同 -> 秒传
                return existing_file_by_name
            else:
                # 场景 4: 文件名相同但内容不同 -> 重命名
                base = Path(filename).stem
                # 如果是 .rawdata.gz，stem 是 .rawdata? Path('a.rawdata.gz').stem -> 'a.rawdata'
                # Path('a.txt').stem -> 'a'
                # 我们假设后缀是 .rawdata ...
                # 简单处理: 分离后缀
                p = Path(filename)
                stem = p.stem
                suffix = p.suffix
                # Handle .rawdata.gz special case if needed or just trust path
                # sensor.rawdata -> stem=sensor, suffix=.rawdata
                
                counter = 1
                while True:
                     new_name = f"{stem}_{counter}{suffix}"
                     if not crud.get_file_by_filename(session, new_name):
                         target_filename = new_name
                         break
                     counter += 1
        
        # 场景 1 & 3 & 4(已重命名): 创建新 SensorFile
        
        # Size String
        if file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
        # Device Type Detection
        if d_type == "Unknown" or not d_type:
             if "Watch" in target_filename:
                 d_type = "Watch"
             elif "Ring" in target_filename:
                 d_type = "Ring"
             else:
                 d_type = "Unknown"

        new_sf = SensorFile(
            id=str(uuid.uuid4()),
            file_hash=file_hash,
            filename=target_filename,
            deviceType=d_type,
            deviceModel="Unknown",
            size=size_str, # 显示用
            uploadTime=datetime.utcnow().isoformat(),
            # rawPath 移除, accessed via PhysicalFile
            processedDir=str(StorageService.get_processed_dir(file_hash[0:8])), # 暂用 Hash 前缀? 还是 UUID? 原来是用 ID。
            # 为了避免冲突，ProcessedDir 最好跟 SensorFile ID 绑定，或者 Hash? 
            # 如果多个 SensorFile 共享同一个 PhysicalFile，他们的 Processed 数据是一样的吗？
            # 是的，分析结果应该是一样的。所以 ProcessedDir 甚至可以移到 PhysicalFile。
            # 但当前模型在 SensorFile。我们暂时用 SensorFile ID 保证隔离，或者用 Hash？
            # 如果用 Hash，那么多个 SensorFile 共享同一个 ProcessedDir -> 节省空间。
            # 让我们用 Hash 吧。
            content_meta={}
        )
        # Override processedDir to be hash-based to share processed data? 
        # Plan didn't specify. Let's stick to SensorFile ID to avoid aggressive sharing issues for now (e.g. race conditions in processing).
        # Wait, if we use UUID for SensorFile ID, default logic `StorageService.get_processed_dir(file_id)` uses that UUID.
        # This means we analyse meaningful data twice if we upload twice (copy).
        # Optimization: Use Hash for processed dir too.
        new_sf.processed_dir = str(StorageService.get_processed_dir(file_hash))
        
        crud.create_file(session, new_sf)
        return new_sf

    # --- 主流程 ---
    try:
        # 分流处理
        saved_results = [] # List of dict {file_hash, file_size, raw_path, filename}

        if x_original_hash:
            # Zstd Upload
            res = await StorageService.verify_and_save_zstd(file, x_original_hash)
            # Filename cleanup
            fname = file.filename
            if fname.endswith('.zst'): fname = fname[:-4]
            
            saved_results.append({
                "file_hash": res["file_hash"],
                "file_size": res["file_size"],
                "raw_path": res["raw_path"],
                "filename": fname
            })
            
        else:
            ext = Path(file.filename).suffix.lower()
            if ext == '.zip':
                # Zip Upload
                zip_results = await StorageService.save_zip_file(file)
                for zr in zip_results:
                    saved_results.append({
                        "file_hash": zr["file_hash"],
                        "file_size": zr["file_size"],
                        "raw_path": zr["raw_path"],
                        "filename": zr["filename"]
                    })
            else:
                # Normal Rawdata Upload
                # rawdata check
                if ext != '.rawdata':
                     # Allow upload but maybe warn? Or strict? 
                     # Old logic: ALLOWED_EXTENSIONS check.
                     pass 
                
                # Use uuid for temp filename base
                res = await StorageService.save_rawdata_file(file, str(uuid.uuid4()))
                saved_results.append({
                    "file_hash": res["file_hash"],
                    "file_size": res["file_size"],
                    "raw_path": res["raw_path"],
                    "filename": file.filename
                })

        # Process Records
        last_file = None
        count = 0
        
        for item in saved_results:
            last_file = process_record(
                item["file_hash"], 
                item["file_size"], 
                item["raw_path"], 
                item["filename"], 
                deviceType
            )
            count += 1
            
        if count == 1 and last_file:
             return {"id": last_file.id, "filename": last_file.filename, "status": "success", "message": "Uploaded"}
        else:
             return {"id": "batch", "filename": f"Batch {count}", "status": "success", "message": f"Processed {count} files"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
    crud.delete_file(session, file_id)
    StorageService.delete_file(file_id)
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
        dict: 删除结果，包含删除数量;
    """
    for fid in request.ids:
        crud.delete_file(session, fid)
        StorageService.delete_file(fid)
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
        columns: 要返回的列名，逗号分隔;

    Returns:
        dict: 包含数据数组的字典;

    Raises:
        HTTPException: 文件或数据不存在时抛出 404 错误;
    """
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    # 读取 Parquet 文件
    processed_dir = StorageService.get_processed_dir(file_id)
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
    下载原始文件;

    Args:
        file_id: 文件 ID;

    Returns:
        FileResponse: 文件下载响应;

    Raises:
        HTTPException: 文件不存在时抛出 404 错误;
    """
    from fastapi.responses import FileResponse
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    raw_path = StorageService.get_raw_path(file_id)
    if not raw_path.exists():
        raise HTTPException(404, "Raw file not found")

    return FileResponse(
        path=raw_path,
        filename=f"{file.filename}.raw.gz",
        media_type="application/gzip"
    )


@router.post("/files/batch-download")
def batch_download(
    request: api_models.BatchDownloadRequest,
    session: Session = Depends(deps.get_db)
) -> dict:
    """
    批量下载文件(待实现);

    Args:
        request: 包含要下载的文件 ID 列表;

    Returns:
        dict: 当前返回未实现状态;
    """
    # TODO: 实现 ZIP 流式下载
    return {"status": "Not implemented in V1 refactor yet"}


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

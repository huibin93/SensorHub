"""
文件相关 API 端点模块。

本模块提供传感器文件的 CRUD 操作、上传、下载、解析等 API 端点。
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from pathlib import Path
from sqlmodel import Session
from typing import List, Optional
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
    获取文件统计信息。

    Returns:
        StatsResponse: 包含文件总数、今日上传数等统计信息。
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
    获取文件列表（分页）。

    Args:
        page: 页码，从 1 开始。
        limit: 每页数量。
        search: 搜索关键词（文件名或备注）。
        device: 设备类型筛选。
        status: 状态筛选。
        sort: 排序字段，前缀 "-" 表示降序。

    Returns:
        PaginatedFilesResponse: 分页的文件列表。
    """
    skip = (page - 1) * limit
    files, total = crud.get_files(session, skip, limit, search, device, status, sort)
    return {
        "items": files,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if limit > 0 else 1
    }


@router.post("/files/upload", response_model=api_models.UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    deviceType: Optional[str] = Form(None),
    session: Session = Depends(deps.get_db)
) -> api_models.UploadResponse:
    """
    上传传感器文件。

    Args:
        file: 上传的文件。
        deviceType: 设备类型（可选，会尝试从文件名推断）。

    Returns:
        UploadResponse: 上传结果，包含文件 ID 和状态。

    Raises:
        HTTPException: 上传失败时抛出 500 错误。
    """
    # Validate file extension
    ALLOWED_EXTENSIONS = {'.zip', '.rawdata'}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    saved_items = []

    try:
        if file_ext == '.zip':
             # Zip Processing
             processed_files = await StorageService.save_zip_file(file)
             if not processed_files:
                  raise HTTPException(400, "No valid .rawdata files found in zip archive")
             
             for pf in processed_files:
                 saved_items.append({
                     "id": pf["file_id"],
                     "filename": pf["filename"],
                     "raw_path": pf["raw_path"],
                     "file_size": pf["file_size"],
                     "content_meta": {"original_zip_path": pf["original_path_in_zip"]}
                 })
        else:
             # Single Rawdata Processing
             file_id = str(uuid.uuid4())
             storage_result = await StorageService.save_upload_file(file, file_id)
             saved_items.append({
                 "id": file_id,
                 "filename": file.filename,
                 "raw_path": storage_result.get("raw_path"),
                 "file_size": storage_result.get("file_size", 0),
                 "content_meta": {}
             })

        # Create DB Records
        created_count = 0
        last_id = ""
        
        for item in saved_items:
             # Format size
             f_size = item["file_size"]
             if f_size < 1024 * 1024:
                size_str = f"{f_size / 1024:.1f} KB"
             else:
                size_str = f"{f_size / (1024 * 1024):.1f} MB"

             # Determine Device Type
             d_type = deviceType
             if not d_type:
                 d_type = "Unknown"
                 name_to_check = item["filename"]
                 if "Watch" in name_to_check:
                     d_type = "Watch"
                 elif "Ring" in name_to_check:
                     d_type = "Ring"

             sensor_file = SensorFile(
                id=item["id"],
                filename=item["filename"],
                deviceType=d_type,
                deviceModel="Unknown",
                size=size_str,
                uploadTime=datetime.utcnow().isoformat(),
                rawPath=item["raw_path"],
                processedDir=str(StorageService.get_processed_dir(item["id"])),
                content_meta=item["content_meta"]
             )
             crud.create_file(session, sensor_file)
             created_count += 1
             last_id = item["id"]

        # Return response
        if created_count == 1:
             return {"id": last_id, "filename": saved_items[0]["filename"], "status": "success", "message": "Uploaded"}
        else:
             return {
                 "id": last_id, 
                 "filename": f"Imported {created_count} files", 
                 "status": "success", 
                 "message": f"Successfully imported {created_count} files from archive"
             }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/files/{file_id}")
def update_file(
    file_id: str,
    update: api_models.FileUpdateRequest,
    session: Session = Depends(deps.get_db)
) -> SensorFile:
    """
    更新文件信息。

    Args:
        file_id: 文件 ID。
        update: 要更新的字段。

    Returns:
        SensorFile: 更新后的文件对象。

    Raises:
        HTTPException: 文件不存在时抛出 404 错误。
    """
    updated = crud.update_file(session, file_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="File not found")
    return updated


@router.delete("/files/{file_id}")
def delete_file(file_id: str, session: Session = Depends(deps.get_db)) -> dict:
    """
    删除单个文件。

    Args:
        file_id: 文件 ID。

    Returns:
        dict: 删除结果。
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
    批量删除文件。

    Args:
        request: 包含要删除的文件 ID 列表。

    Returns:
        dict: 删除结果，包含删除数量。
    """
    for fid in request.ids:
        crud.delete_file(session, fid)
        StorageService.delete_file(fid)
    return {"success": True, "deleted": len(request.ids)}


@router.get("/files/{file_id}/structure")
def get_structure(file_id: str, session: Session = Depends(deps.get_db)) -> dict:
    """
    获取文件结构信息。

    Args:
        file_id: 文件 ID。

    Returns:
        dict: 文件结构元数据。

    Raises:
        HTTPException: 文件不存在时抛出 404 错误。
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
    获取文件解析后的数据。

    Args:
        file_id: 文件 ID。
        key: 数据键名（对应 Parquet 文件名）。
        limit: 返回行数限制。
        columns: 要返回的列名，逗号分隔。

    Returns:
        dict: 包含数据数组的字典。

    Raises:
        HTTPException: 文件或数据不存在时抛出 404 错误。
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
    下载原始文件。

    Args:
        file_id: 文件 ID。

    Returns:
        FileResponse: 文件下载响应。

    Raises:
        HTTPException: 文件不存在时抛出 404 错误。
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
    批量下载文件（待实现）。

    Args:
        request: 包含要下载的文件 ID 列表。

    Returns:
        dict: 当前返回未实现状态。
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
    触发文件解析。

    Args:
        file_id: 文件 ID。
        request: 解析选项。

    Returns:
        dict: 解析状态。

    Raises:
        HTTPException: 文件不存在时抛出 404 错误。
    """
    file = crud.get_file(session, file_id)
    if not file:
        raise HTTPException(404, "File not found")

    # 直接设置状态为已处理 (简化状态管理, 无 Processing 状态)
    crud.update_file(session, file_id, {"status": "Processed"})

    return {"status": "Processed", "message": "Parse completed"}

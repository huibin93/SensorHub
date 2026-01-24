from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
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

router = APIRouter()

@router.get("/stats", response_model=api_models.StatsResponse)
def get_stats(session: Session = Depends(deps.get_db)):
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
):
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
):
    file_id = str(uuid.uuid4())
    try:
        raw_path = await StorageService.save_upload_file(file, file_id)
        
        # Determine device type
        d_type = deviceType or "Unknown"
        if "Watch" in file.filename: d_type = "Watch"
        elif "Ring" in file.filename: d_type = "Ring"
        
        sensor_file = SensorFile(
            id=file_id,
            filename=file.filename,
            deviceType=d_type,
            deviceModel="Unknown",
            size="0 KB", # Placeholder, implement size calculation in service
            uploadTime=datetime.utcnow().isoformat(),
            rawPath=str(raw_path),
            processedDir=str(StorageService.get_processed_dir(file_id))
        )
        crud.create_file(session, sensor_file)
        
        return {"id": file_id, "filename": file.filename, "status": "success", "message": "Uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/files/{file_id}")
def update_file(
    file_id: str,
    update: api_models.FileUpdateRequest,
    session: Session = Depends(deps.get_db)
):
    updated = crud.update_file(session, file_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="File not found")
    return updated

@router.delete("/files/{file_id}")
def delete_file(file_id: str, session: Session = Depends(deps.get_db)):
    crud.delete_file(session, file_id)
    StorageService.delete_file(file_id)
    return {"success": True}

@router.post("/files/batch-delete")
def batch_delete(
    request: api_models.BatchDeleteRequest,
    session: Session = Depends(deps.get_db)
):
    for fid in request.ids:
        crud.delete_file(session, fid)
        StorageService.delete_file(fid)
    return {"success": True, "deleted": len(request.ids)}

@router.get("/files/{file_id}/structure")
def get_structure(file_id: str, session: Session = Depends(deps.get_db)):
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
):
    # Retrieve data logic (Previously in main.py)
    # Using Service? StorageService?
    # Ideally logic should be in a service. New architecture!
    # For now, simplistic implementation mimicking old main.py but cleaner.
    
    file = crud.get_file(session, file_id)
    if not file: raise HTTPException(404, "File not found")
    
    # Read parquet
    processed_dir = StorageService.get_processed_dir(file_id)
    pq_path = processed_dir / f"{key}.parquet"
    
    if not pq_path.exists():
        raise HTTPException(404, f"Data not found: {key}")
        
    try:
        import pyarrow.parquet as pq
        table = pq.read_table(pq_path)
        
        # Filter columns
        if columns:
            cols = columns.split(',')
            # Validate cols exist
            existing = table.column_names
            cols = [c for c in cols if c in existing]
            if cols:
                table = table.select(cols)
                
        # Limit rows
        df = table.to_pandas()
        if limit > 0:
            df = df.head(limit)
            
        data = json.loads(df.to_json(orient="records"))
        return {"data": data}
    except Exception as e:
        raise HTTPException(500, f"Error reading data: {str(e)}")

@router.get("/files/{file_id}/download")
def download_file(file_id: str, session: Session = Depends(deps.get_db)):
    from fastapi.responses import FileResponse
    file = crud.get_file(session, file_id)
    if not file: raise HTTPException(404, "File not found")
    
    raw_path = StorageService.get_raw_path(file_id)
    if not raw_path.exists():
        raise HTTPException(404, "Raw file not found")
        
    return FileResponse(
        path=raw_path, 
        filename=f"{file.filename}.raw.gz",
        media_type="application/gzip"
    )

@router.post("/files/batch-download")
def batch_download(request: api_models.BatchDownloadRequest, session: Session = Depends(deps.get_db)):
    # TODO: Implement zip streaming (Service layer)
    # Placeholder
    return {"status": "Not implemented in V1 refactor yet"}

@router.post("/files/{file_id}/parse")
def trigger_parse(
    file_id: str, 
    request: api_models.ParseRequest, 
    session: Session = Depends(deps.get_db)
):
    file = crud.get_file(session, file_id)
    if not file: raise HTTPException(404, "File not found")
    
    # call service
    crud.update_file(session, file_id, {"status": "Processing"})
    
    # Check if we can run background task
    # ParserService.parse_file(file_id, ...)
    
    return {"status": "Processing", "message": "Parse triggered"}


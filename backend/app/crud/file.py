from typing import List, Optional, Tuple
from sqlmodel import Session, select, func, desc, or_
from app.models.sensor_file import SensorFile

def get_stats(session: Session) -> dict:
    total_files = session.exec(select(func.count(SensorFile.id))).one()
    # today_uploads... (skip complex date logic for now, or implement simply)
    return {
        "totalFiles": total_files,
        "todayUploads": 0, # Placeholder
        "pendingTasks": 0, # Placeholder
        "storageUsed": "0 GB", # Placeholder
        "lastUpdated": ""
    }

def get_files(
    session: Session, 
    skip: int = 0, 
    limit: int = 20, 
    search: Optional[str] = None,
    device: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "-uploadTime"
) -> Tuple[List[SensorFile], int]:
    
    query = select(SensorFile)
    
    if search:
        query = query.where(or_(
            SensorFile.filename.contains(search),
            SensorFile.notes.contains(search)
        ))
    if device and device != "All":
        query = query.where(SensorFile.device_type == device)
        
    if status and status != "All":
        query = query.where(SensorFile.status == status)
        
    # Count total (inefficient but simple)
    # total = session.exec(select(func.count()).select_from(query.subquery())).one()
    # Or just count matches
    total = len(session.exec(query).all())
    
    # Sort
    sort_key = sort[1:] if sort.startswith("-") else sort
    descending = sort.startswith("-")
    
    # Map frontend camelCase to backend snake_case
    field_map = {
        "uploadTime": "upload_time",
        "deviceType": "device_type",
        "deviceModel": "device_model",
        "testTypeL1": "test_type_l1",
        "testTypeL2": "test_type_l2",
        "rawPath": "raw_path",
        "processedDir": "processed_dir",
        "errorMessage": "error_message",
        "contentMeta": "content_meta"
    }
    
    db_field = field_map.get(sort_key, sort_key)
    
    if hasattr(SensorFile, db_field):
        field = getattr(SensorFile, db_field)
        if descending:
            query = query.order_by(desc(field))
        else:
            query = query.order_by(field)

        
    query = query.offset(skip).limit(limit)
    files = session.exec(query).all()
    
    return files, total

def get_file(session: Session, file_id: str) -> Optional[SensorFile]:
    return session.get(SensorFile, file_id)

def create_file(session: Session, file: SensorFile) -> SensorFile:
    session.add(file)
    session.commit()
    session.refresh(file)
    return file

def update_file(session: Session, file_id: str, updates: dict) -> Optional[SensorFile]:
    file = session.get(SensorFile, file_id)
    if not file:
        return None
        
    for k, v in updates.items():
        setattr(file, k, v)
        
    session.add(file)
    session.commit()
    session.refresh(file)
    return file

def delete_file(session: Session, file_id: str):
    file = session.get(SensorFile, file_id)
    if file:
        session.delete(file)
        session.commit()

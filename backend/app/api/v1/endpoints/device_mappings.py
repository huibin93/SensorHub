"""
设备映射 API 端点模块;

提供设备映射的 CRUD API;
设备映射变更会自动级联到所有关联的 SensorFile;
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.models.device_mapping import DeviceMapping
from app.crud import device_mapping as crud
from app.core.logger import logger
from pydantic import BaseModel


router = APIRouter()


class DeviceMappingCreate(BaseModel):
    """设备映射创建模型;"""
    device_name: str
    device_type: str
    device_model: str


class DeviceMappingUpdate(BaseModel):
    """设备映射更新模型;"""
    device_type: str | None = None
    device_model: str | None = None


@router.get("/", response_model=List[DeviceMapping])
def list_device_mappings(session: Session = Depends(get_session)):
    """获取所有设备映射;"""
    return crud.get_device_mappings(session)


@router.get("/{device_name}", response_model=DeviceMapping)
def get_device_mapping(device_name: str, session: Session = Depends(get_session)):
    """根据设备名称获取映射;"""
    mapping = crud.get_device_mapping(session, device_name)
    if not mapping:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return mapping


@router.post("/", response_model=DeviceMapping)
def create_device_mapping(
    data: DeviceMappingCreate,
    session: Session = Depends(get_session)
):
    """
    创建设备映射;
    创建后会自动级联更新所有匹配 device_name 的 SensorFile;
    """
    # 检查是否已存在
    existing = crud.get_device_mapping(session, data.device_name)
    if existing:
        raise HTTPException(status_code=400, detail="Device mapping already exists")
    
    mapping = DeviceMapping(**data.model_dump())
    result = crud.create_device_mapping(session, mapping)
    
    # 级联更新已有文件
    affected = crud.cascade_mapping_to_files(
        session, 
        data.device_name, 
        result.device_type, 
        result.device_model
    )
    if affected > 0:
        logger.info(f"[DeviceMapping] Created mapping '{data.device_name}' → {result.device_type}/{result.device_model}, cascaded to {affected} files")
    
    return result


@router.put("/{device_name}", response_model=DeviceMapping)
def update_device_mapping(
    device_name: str,
    data: DeviceMappingUpdate,
    session: Session = Depends(get_session)
):
    """
    更新设备映射;
    如果 device_type 变更，所有关联的已解析文件(processed)会重置为 idle;
    """
    # 获取旧值用于比较
    old_mapping = crud.get_device_mapping(session, device_name)
    if not old_mapping:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    
    old_device_type = old_mapping.device_type
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    mapping = crud.update_device_mapping(session, device_name, updates)
    if not mapping:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    
    # 级联更新已有文件 (如果 device_type 变了，重置 processed → idle)
    affected = crud.cascade_mapping_to_files(
        session,
        device_name,
        mapping.device_type,
        mapping.device_model,
        old_device_type=old_device_type
    )
    if affected > 0:
        type_changed = old_device_type != mapping.device_type
        logger.info(
            f"[DeviceMapping] Updated mapping '{device_name}' → {mapping.device_type}/{mapping.device_model}, "
            f"cascaded to {affected} files" + (" (type changed, processed→idle)" if type_changed else "")
        )
    
    return mapping


@router.delete("/{device_name}")
def delete_device_mapping(device_name: str, session: Session = Depends(get_session)):
    """删除设备映射;"""
    success = crud.delete_device_mapping(session, device_name)
    if not success:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return {"message": "Device mapping deleted successfully"}

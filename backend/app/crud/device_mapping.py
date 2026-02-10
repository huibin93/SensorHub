"""
DeviceMapping CRUD 操作模块;

提供设备映射的增删改查操作;
"""
from typing import List, Optional, Dict
from sqlmodel import Session, select
from app.models.device_mapping import DeviceMapping
from app.models.sensor_file import SensorFile
from app.models.parse_result import ParseResult


def get_device_mappings(session: Session) -> List[DeviceMapping]:
    """
    获取所有设备映射;
    
    Args:
        session: 数据库会话;
        
    Returns:
        List[DeviceMapping]: 设备映射列表;
    """
    return session.exec(select(DeviceMapping)).all()


def get_device_mapping(session: Session, device_name: str) -> Optional[DeviceMapping]:
    """
    根据设备名称获取映射;
    
    Args:
        session: 数据库会话;
        device_name: 设备名称;
        
    Returns:
        Optional[DeviceMapping]: 映射对象;
    """
    # 大小写不敏感查询
    statement = select(DeviceMapping).where(
        DeviceMapping.device_name.ilike(device_name)
    )
    return session.exec(statement).first()


def create_device_mapping(session: Session, mapping: DeviceMapping) -> DeviceMapping:
    """
    创建设备映射;
    
    Args:
        session: 数据库会话;
        mapping: 映射对象;
        
    Returns:
        DeviceMapping: 创建后的映射;
    """
    # 设备型号转大写
    mapping.device_model = mapping.device_model.upper()
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    return mapping


def update_device_mapping(
    session: Session, 
    device_name: str, 
    updates: dict
) -> Optional[DeviceMapping]:
    """
    更新设备映射;
    
    Args:
        session: 数据库会话;
        device_name: 设备名称;
        updates: 更新字段;
        
    Returns:
        Optional[DeviceMapping]: 更新后的映射;
    """
    mapping = session.get(DeviceMapping, device_name)
    if not mapping:
        return None
    
    for key, value in updates.items():
        if key == "device_model":
            value = value.upper()
        setattr(mapping, key, value)
    
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    return mapping


def delete_device_mapping(session: Session, device_name: str) -> bool:
    """
    删除设备映射;
    
    Args:
        session: 数据库会话;
        device_name: 设备名称;
        
    Returns:
        bool: 是否成功删除;
    """
    mapping = session.get(DeviceMapping, device_name)
    if not mapping:
        return False
    
    session.delete(mapping)
    session.commit()
    return True


def resolve_device_info(session: Session, device_name: str) -> Dict[str, str]:
    """
    根据 device_name 查找 DeviceMapping，返回 device_type 和 device_model;
    如果未找到映射，返回默认值;
    
    Args:
        session: 数据库会话;
        device_name: 设备名称;
        
    Returns:
        dict: {"device_type": ..., "device_model": ...}
    """
    if not device_name or not device_name.strip():
        return {"device_type": "Watch", "device_model": "Unknown"}
    
    mapping = get_device_mapping(session, device_name.strip())
    if mapping:
        return {
            "device_type": mapping.device_type,
            "device_model": mapping.device_model
        }
    return {"device_type": "Watch", "device_model": device_name.strip().upper()}


def cascade_mapping_to_files(
    session: Session,
    device_name: str,
    new_device_type: str,
    new_device_model: str,
    old_device_type: Optional[str] = None
) -> int:
    """
    设备映射变更时，级联更新关联文件的 ParseResult;
    如果 device_type 发生变化，将已解析文件的 ParseResult 状态重置为 idle;
    
    Args:
        session: 数据库会话;
        device_name: 设备名称;
        new_device_type: 新设备类型;
        new_device_model: 新设备型号;
        old_device_type: 旧设备类型 (用于判断是否需要重置状态);
        
    Returns:
        int: 受影响的文件数;
    """
    statement = select(SensorFile).where(
        SensorFile.device_name.ilike(device_name)
    )
    files = session.exec(statement).all()
    
    type_changed = old_device_type and old_device_type != new_device_type
    count = 0
    
    for f in files:
        # 如果设备类型变了，重置已解析的 ParseResult 为 idle
        if type_changed:
            pr = session.exec(
                select(ParseResult).where(ParseResult.sensor_file_id == f.id)
            ).first()
            if pr and pr.status == "processed":
                pr.status = "idle"
                pr.device_type_used = new_device_type
                session.add(pr)
        
        count += 1
    
    if count > 0:
        session.commit()
    
    return count

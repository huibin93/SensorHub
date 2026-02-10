"""
ParseResult CRUD 操作模块;

提供解析结果的增删改查操作;
每个 SensorFile 最多对应一条 ParseResult (1:1);
"""
from typing import Optional
from datetime import datetime
from sqlmodel import Session, select
from app.models.parse_result import ParseResult


def get_by_file_id(session: Session, sensor_file_id: str) -> Optional[ParseResult]:
    """
    根据 SensorFile ID 获取解析结果;
    
    Args:
        session: 数据库会话;
        sensor_file_id: SensorFile ID;
        
    Returns:
        Optional[ParseResult]: 解析结果, 不存在时返回 None;
    """
    return session.exec(
        select(ParseResult).where(ParseResult.sensor_file_id == sensor_file_id)
    ).first()


def create_or_update(session: Session, sensor_file_id: str, data: dict) -> ParseResult:
    """
    创建或更新解析结果 (upsert);
    
    如果已存在则更新 (覆盖), 不存在则创建;
    
    Args:
        session: 数据库会话;
        sensor_file_id: SensorFile ID;
        data: 要设置的字段;
        
    Returns:
        ParseResult: 解析结果;
    """
    existing = get_by_file_id(session, sensor_file_id)
    
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        existing.updated_at = datetime.now()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        pr = ParseResult(sensor_file_id=sensor_file_id, **data)
        session.add(pr)
        session.commit()
        session.refresh(pr)
        return pr


def update_status(session: Session, sensor_file_id: str, status: str, **kwargs) -> Optional[ParseResult]:
    """
    更新解析状态;
    
    Args:
        session: 数据库会话;
        sensor_file_id: SensorFile ID;
        status: 新状态;
        **kwargs: 其他要更新的字段;
        
    Returns:
        Optional[ParseResult]: 更新后的解析结果;
    """
    pr = get_by_file_id(session, sensor_file_id)
    if not pr:
        return None
    
    pr.status = status
    pr.updated_at = datetime.now()
    for k, v in kwargs.items():
        setattr(pr, k, v)
    
    session.add(pr)
    session.commit()
    session.refresh(pr)
    return pr


def delete_by_file_id(session: Session, sensor_file_id: str) -> bool:
    """
    删除 SensorFile 关联的解析结果;
    
    Args:
        session: 数据库会话;
        sensor_file_id: SensorFile ID;
        
    Returns:
        bool: 是否成功删除;
    """
    pr = get_by_file_id(session, sensor_file_id)
    if not pr:
        return False
    
    session.delete(pr)
    session.commit()
    return True

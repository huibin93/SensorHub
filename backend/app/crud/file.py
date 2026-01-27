"""
文件 CRUD 操作模块;

本模块提供传感器文件的数据库增删改查操作;
"""
from typing import List, Optional, Tuple
from sqlmodel import Session, select, func, desc, or_
from app.models.sensor_file import SensorFile, PhysicalFile


def get_stats(session: Session) -> dict:
    """
    获取文件统计信息;

    Args:
        session: 数据库会话;

    Returns:
        dict: 包含文件总数等统计信息;
    """
    total_files = session.exec(select(func.count(SensorFile.id))).one()
    return {
        "totalFiles": total_files,
        "todayUploads": 0,  # 占位符
        "pendingTasks": 0,  # 占位符
        "storageUsed": "0 GB",  # 占位符
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
    """
    获取文件列表(支持分页、搜索、筛选、排序);

    Args:
        session: 数据库会话;
        skip: 跳过的记录数(分页偏移);
        limit: 返回的最大记录数;
        search: 搜索关键词;
        device: 设备类型筛选;
        status: 状态筛选;
        sort: 排序字段，前缀 "-" 表示降序;

    Returns:
        Tuple[List[SensorFile], int]: 文件列表和总数;
    """
    query = select(SensorFile)

    # 搜索筛选
    if search:
        query = query.where(or_(
            SensorFile.filename.contains(search),
            SensorFile.notes.contains(search)
        ))

    # 设备类型筛选
    if device and device != "All":
        query = query.where(SensorFile.device_type == device)

    # 状态筛选
    if status and status != "All":
        query = query.where(SensorFile.status == status)

    # 计算总数
    total = len(session.exec(query).all())

    # 排序处理
    sort_key = sort[1:] if sort.startswith("-") else sort
    descending = sort.startswith("-")

    # 前端驼峰命名到数据库下划线命名的映射
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

    # 分页
    query = query.offset(skip).limit(limit)
    files = session.exec(query).all()

    return files, total


def get_file(session: Session, file_id: str) -> Optional[SensorFile]:
    """
    根据 ID 获取单个文件;

    Args:
        session: 数据库会话;
        file_id: 文件 ID;

    Returns:
        Optional[SensorFile]: 文件对象，不存在时返回 None;
    """
    return session.get(SensorFile, file_id)


def create_file(session: Session, file: SensorFile) -> SensorFile:
    """
    创建新文件记录;

    Args:
        session: 数据库会话;
        file: 文件对象;

    Returns:
        SensorFile: 创建后的文件对象;
    """
    session.add(file)
    session.commit()
    session.refresh(file)
    return file


def update_file(session: Session, file_id: str, updates: dict) -> Optional[SensorFile]:
    """
    更新文件记录;

    Args:
        session: 数据库会话;
        file_id: 文件 ID;
        updates: 要更新的字段字典;

    Returns:
        Optional[SensorFile]: 更新后的文件对象，文件不存在时返回 None;
    """
    file = session.get(SensorFile, file_id)
    if not file:
        return None

    for k, v in updates.items():
        setattr(file, k, v)

    session.add(file)
    session.commit()
    session.refresh(file)
    return file


def delete_file(session: Session, file_id: str) -> None:
    """
    删除文件记录;

    Args:
        session: 数据库会话;
        file_id: 文件 ID;
    """
    file = session.get(SensorFile, file_id)
    if file:
        session.delete(file)
        session.commit()


def get_file_by_hash(session: Session, file_hash: str) -> Optional[SensorFile]:
    """
    根据 Hash 获取文件;

    Args:
        session: 数据库会话;
        file_hash: 文件 Hash;

    Returns:
        Optional[SensorFile]: 文件对象，不存在时返回 None;
    """
    return session.exec(select(SensorFile).where(SensorFile.file_hash == file_hash)).first()


def get_physical_file(session: Session, file_hash: str) -> Optional[PhysicalFile]:
    """
    根据 Hash 获取物理文件;
    """
    return session.get(PhysicalFile, file_hash)


def create_physical_file(session: Session, file: PhysicalFile) -> PhysicalFile:
    """
    创建物理文件记录;
    """
    session.add(file)
    session.commit()
    session.refresh(file)
    return file


def get_file_by_filename(session: Session, filename: str) -> Optional[SensorFile]:
    """
    根据文件名获取文件;
    """
    return session.exec(select(SensorFile).where(SensorFile.filename == filename)).first()

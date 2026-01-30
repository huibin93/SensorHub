"""
文件 CRUD 操作模块;

本模块提供传感器文件的数据库增删改查操作;
"""
from typing import List, Optional, Tuple
from datetime import date
from sqlmodel import Session, select, func, desc, or_, cast, Date
from app.models.sensor_file import SensorFile, PhysicalFile


def get_stats(session: Session) -> dict:
    """
    获取文件统计信息;

    Args:
        session: 数据库会话;

    Returns:
        dict: 包含文件总数等统计信息;
    """
    # 计算总文件数
    total_files = session.exec(select(func.count(SensorFile.id))).one()

    # 计算今日上传
    today_count = session.exec(
        select(func.count(SensorFile.id))
        .where(func.date(SensorFile.upload_time) == date.today())
    ).one()

    # 计算今日待处理 (pendingTasks)
    # 定义: 今日上传且状态为 'idle' 或 'unverified'
    pending_count = session.exec(
        select(func.count(SensorFile.id))
        .where(func.date(SensorFile.upload_time) == date.today())
        .where(or_(SensorFile.status == 'idle', SensorFile.status == 'unverified'))
    ).one()

    # 计算总存储空间 (基于 PhysicalFile)
    total_bytes = session.exec(select(func.sum(PhysicalFile.size))).one() or 0
    
    return {
        "totalFiles": total_files,
        "todayUploads": today_count,
        "pendingTasks": pending_count, 
        "storageUsed": total_bytes
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
        sort: 排序字段,前缀 "-" 表示降序;

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
        Optional[SensorFile]: 文件对象,不存在时返回 None;
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
        Optional[SensorFile]: 更新后的文件对象,文件不存在时返回 None;
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


def delete_file_safely(session: Session, file_id: str) -> bool:
    """
    安全删除文件: 只有当物理文件引用计数为 0 时才真正删除物理文件;
    
    Args:
        session: 数据库会话;
        file_id: 文件 ID;
        
    Returns:
        bool: 是否成功删除;
    """
    # 局部导入以避免循环依赖
    from app.services.storage import StorageService
    from app.core.logger import logger
    
    # 1. 找到要删的文件记录
    sensor_file = session.get(SensorFile, file_id)
    if not sensor_file:
        return False
        
    target_hash = sensor_file.file_hash
    
    # 2. 删除业务记录
    session.delete(sensor_file)
    session.flush() # 提交变更,确保下面的 count 是准的
    
    # 3. 检查是否还有其他记录引用此 Hash
    # (注意：flush 后，当前 sensor_file 已经不在统计范围内了)
    statement = select(SensorFile).where(SensorFile.file_hash == target_hash)
    results = session.exec(statement).all()
    
    if len(results) == 0:
        # 4. 没人用了，执行物理清除
        # a. 删 DB 物理记录
        physical_file = session.get(PhysicalFile, target_hash)
        if physical_file:
            session.delete(physical_file)
            
        # b. 删磁盘文件 (调用 Service)
        StorageService.delete_physical_file(target_hash)
        logger.info(f"Physical file {target_hash} garbage collected.")
    else:
        logger.info(f"Physical file {target_hash} retained. Ref count: {len(results)}")
        
    session.commit()
    return True

def delete_file(session: Session, file_id: str) -> None:
    """
    Deprecated: Use delete_file_safely instead.
    """
    delete_file_safely(session, file_id)


def get_file_by_hash(session: Session, file_hash: str) -> Optional[SensorFile]:
    """
    根据 Hash 获取文件;

    Args:
        session: 数据库会话;
        file_hash: 文件 Hash;

    Returns:
        Optional[SensorFile]: 文件对象,不存在时返回 None;
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


def get_exact_match_file(session: Session, file_hash: str, filename: str) -> Optional[SensorFile]:
    """
    根据 Hash 和 文件名 获取文件 (完全匹配);
    用于检查严苛的去重条件 (同名且同内容).
    """
    return session.exec(
        select(SensorFile)
        .where(SensorFile.file_hash == file_hash)
        .where(SensorFile.filename == filename)
    ).first()


def get_file_by_name_and_size(session: Session, filename: str, size: int) -> Optional[SensorFile]:
    """
    根据 文件名 和 大小 获取文件 (快速前置检查);
    用于 Fast Check: 如果库里已有同名且大小一致的文件,视为重复,跳过 MD5 计算.
    """
    return session.exec(
        select(SensorFile)
        .where(SensorFile.filename == filename)
        .where(SensorFile.file_size_bytes == size)
    ).first()


def get_next_naming_suffix(session: Session, filename: str) -> str:
    """
    计算下一个文件名后缀;
    例如: filename 已存在 -> 返回 " (1)"
    filename 和 filename (1) 已存在 -> 返回 " (2)"
    """
    # 查找所有同名文件 (不区分后缀, 因为 filename 字段本身是不变的)
    # 注意: 我们存储的 filename 是原始文件名 (例如 test.rawdata)
    # 所有的变体也是存储为 filename="test.rawdata", suffix=" (1)" 吗?
    # 用户说: "SensorFile 再添加一个 数字序号的字符" ... "变成文件名...与这个序号的拼接"
    # 这意味着所有重名文件的 `filename` 字段都是 IDENTICAL (一样的), 
    # 区别仅仅在于 `name_suffix` 字段。
    
    # 查询所有 filename = target 的记录的 suffix
    statement = select(SensorFile.name_suffix).where(SensorFile.filename == filename)
    suffixes = session.exec(statement).all()
    
    if not suffixes:
        return ""
    
    # 解析现有的 suffixes
    # "" -> 0
    # " (1)" -> 1
    # " (2)" -> 2
    max_idx = 0
    has_empty = False
    
    import re
    pattern = re.compile(r" \((\d+)\)$")
    
    for suf in suffixes:
        if suf == "":
            has_empty = True
            continue
        match = pattern.match(suf)
        if match:
            idx = int(match.group(1))
            if idx > max_idx:
                max_idx = idx
                
    if not has_empty:
        # 理论上不应该发生 "有 (1) 但没有 空" 的情况 (除非被删了)
        # 如果没有原始文件，那我们就是原始文件
        return ""
        
    # 下一个序号
    next_idx = max_idx + 1
    return f" ({next_idx})"

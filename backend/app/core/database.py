"""
数据库模块;

本模块负责创建数据库引擎、初始化表结构，并提供数据库会话生成器;
初始化时会填充最基础的字典数据;
"""
from sqlmodel import SQLModel, create_engine, Session, select
from app.core.config import settings
from app.core.logger import logger

# 创建数据库引擎
engine = create_engine(settings.SQLITE_URL, echo=settings.database.echo)


def init_db() -> None:
    """
    初始化数据库;

    创建所有 SQLModel 定义的表结构，并填充最基础的字典数据;
    应在应用启动时调用;
    """
    # 确保模型已被导入以注册 metadata
    from app.models.sensor_file import SensorFile, PhysicalFile
    SQLModel.metadata.create_all(engine)
    
    # 初始化最基础的字典数据
    _init_base_data()


def _init_base_data() -> None:
    """
    初始化最基础的字典数据;

    仅在表为空时填充：
    - TestType: 'unknown' 类型
    
    DeviceType 和 DeviceModel 由前端添加或解析时自动创建;
    """
    from app.models.dictionary import TestType, TestSubType
    
    with Session(engine) as session:
        # 仅检查并添加 unknown 测试类型
        if not session.exec(select(TestType)).first():
            session.add(TestType(id="unknown", name="Unknown"))
            session.add(TestSubType(test_type_id="unknown", name="--"))
            session.commit()
            logger.info("Initialized base test type: unknown")


def get_session():
    """
    获取数据库会话生成器;

    Yields:
        Session: SQLModel 数据库会话对象;
    """
    with Session(engine) as session:
        yield session

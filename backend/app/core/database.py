"""
数据库模块;

本模块负责创建数据库引擎、初始化表结构,并提供数据库会话生成器;
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

    创建所有 SQLModel 定义的表结构,并填充最基础的字典数据;
    应在应用启动时调用;
    """
    # 确保模型已被导入以注册 metadata
    from app.models.sensor_file import SensorFile, PhysicalFile
    from app.models.parse_result import ParseResult
    from app.models.dictionary import TestType, TestSubType
    from app.models.user import User, SharedLink
    from app.models.device_mapping import DeviceMapping
    SQLModel.metadata.create_all(engine)
    
    # 初始化最基础的字典数据
    _init_base_data()


def _init_base_data() -> None:
    """
    初始化最基础的字典数据和管理员用户;

    仅在表为空时填充：
    - TestType: 'unknown' 类型
    - Admin 用户: 从环境变量读取配置
    
    DeviceMapping 由前端添加或解析时自动创建;
    """
    from app.models.dictionary import TestType, TestSubType
    from app.models.user import User
    from app.core import security
    
    with Session(engine) as session:
        # 1. 初始化测试类型
        if not session.exec(select(TestType)).first():
            session.add(TestType(id="unknown", name="Unknown"))
            session.add(TestSubType(test_type_id="unknown", name="--"))
            session.commit()
            logger.info("Initialized base test type: unknown")
        
        # 2. 初始化管理员用户
        admin_username = settings.security.ADMIN_USER
        admin_user = session.exec(
            select(User).where(User.username == admin_username)
        ).first()
        
        if not admin_user:
            # 创建管理员用户
            hashed_password = security.get_password_hash(settings.security.ADMIN_PASSWORD)
            admin_user = User(
                username=admin_username,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
                is_deletable=False  # 管理员不可删除
            )
            session.add(admin_user)
            session.commit()
            logger.info(f"Created admin user: {admin_username}")


def get_session():
    """
    获取数据库会话生成器;

    Yields:
        Session: SQLModel 数据库会话对象;
    """
    with Session(engine) as session:
        yield session

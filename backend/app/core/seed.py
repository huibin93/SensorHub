"""
数据库种子数据模块(已弃用);

本模块保留用于测试目的;生产环境的基础数据初始化已移至 database.py;
字典数据应通过前端 API 添加，或在数据解析时自动创建;
"""
from sqlmodel import Session


def seed_data(session: Session) -> None:
    """
    种子数据入口(空实现);

    生产环境不再通过此函数填充数据;
    基础数据初始化已移至 database.py 的 init_db();

    Args:
        session: SQLModel 数据库会话对象;
    """
    pass

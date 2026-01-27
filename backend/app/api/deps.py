"""
API 依赖注入模块;

本模块提供 FastAPI 路由中使用的依赖项，如数据库会话;
"""
from typing import Generator
from sqlmodel import Session
from app.core.database import get_session


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话依赖;

    用于 FastAPI 的 Depends() 依赖注入;

    Yields:
        Session: SQLModel 数据库会话对象;
    """
    yield from get_session()

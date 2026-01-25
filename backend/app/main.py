"""
FastAPI 应用入口模块。

本模块创建 FastAPI 应用实例，配置中间件和路由，
并在启动时初始化数据库和种子数据。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import files, dictionaries
from app.core.config import settings
from app.core.database import init_db, engine
from app.core import seed
from sqlmodel import Session
from app.core.logger import logger

# 创建 FastAPI 应用实例
app = FastAPI(title=settings.PROJECT_NAME)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    应用启动事件处理器。

    初始化数据库表结构并填充种子数据。
    """
    init_db()
    with Session(engine) as session:
        seed.seed_data(session)


# 挂载 API 路由
app.include_router(dictionaries.router, prefix=f"{settings.API_V1_STR}", tags=["dictionaries"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}", tags=["files"])

logger.info("Application startup complete.")

# 可选：挂载静态文件存储（如需要）

"""
FastAPI 应用入口模块;

本模块创建 FastAPI 应用实例,配置中间件和路由,
并在启动时初始化数据库和种子数据;
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import files, dictionaries, devices, users, device_mappings
from app.core.config import settings
from app.core.database import init_db

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
    应用启动事件处理器;

    初始化数据库表结构;
    重置残留的 processing 状态为 idle (防止上次异常退出);
    """
    init_db()

    # 重置残留的 processing 状态
    from app.core.database import engine
    from sqlmodel import Session, select
    from app.models.parse_result import ParseResult

    with Session(engine) as session:
        stale = session.exec(
            select(ParseResult).where(ParseResult.status == "processing")
        ).all()
        if stale:
            for pr in stale:
                pr.status = "idle"
                pr.progress = None
                pr.error_message = None
                session.add(pr)
            session.commit()
            logger.info(f"[startup] Reset {len(stale)} stale 'processing' records to 'idle'")

# 挂载 API 路由
app.include_router(dictionaries.router, prefix=f"{settings.API_V1_STR}", tags=["dictionaries"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}", tags=["files"])
app.include_router(devices.router, prefix=f"{settings.API_V1_STR}", tags=["devices"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(device_mappings.router, prefix=f"{settings.API_V1_STR}/device-mappings", tags=["device-mappings"])

from app.api.v1.endpoints import auth, log_parser
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}", tags=["auth"])
app.include_router(log_parser.router, prefix=f"{settings.API_V1_STR}/log-parser", tags=["log-parser"])

logger.info("Application startup complete.")

# 可选：挂载静态文件存储(如需要)

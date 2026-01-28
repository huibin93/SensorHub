"""
日志配置模块;

本模块使用 loguru 配置应用日志,提供统一的日志格式和输出;
"""
import sys
from loguru import logger

# 移除默认处理器,使用自定义格式
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    # level="INFO",
    level="TRACE",
)

# 可选：添加文件日志
# logger.add("logs/app.log", rotation="500 MB")

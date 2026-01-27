"""
数据库检查脚本;

本脚本用于检查数据库内容，输出文件、设备型号和测试类型的统计信息;

使用方法：
    cd backend
    $env:PYTHONPATH="."; uv run python test/check_db.py
"""
from sqlmodel import Session, create_engine, select
from app.core.logger import logger
from app.models.sensor_file import SensorFile
from app.models.dictionary import DeviceModel, TestType
from app.core.config import settings

# 输出目标数据库信息
logger.info(f"Checking DB at: {settings.SQLITE_URL}")

engine = create_engine(settings.SQLITE_URL)

try:
    with Session(engine) as session:
        files = session.exec(select(SensorFile)).all()
        devices = session.exec(select(DeviceModel)).all()
        test_types = session.exec(select(TestType)).all()

        logger.info(f"Total Files: {len(files)}")
        logger.info(f"Total Device Models: {len(devices)}")
        logger.info(f"Total Test Types: {len(test_types)}")

        if len(files) > 0:
            logger.info("\nExample File:")
            logger.info(files[0])
except Exception as e:
    logger.error(f"Error accessing database: {e}")

"""
测试数据库初始化脚本;

本脚本用于创建和初始化测试数据库 (test.db)，包括：
1. 强制切换到测试数据库模式
2. 创建数据库表结构
3. 填充字典数据和模拟测试文件数据

使用方法：
    cd backend
    $env:PYTHONPATH="."; uv run python test/test_db.py
"""
import json
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.core.logger import logger
from app.core import seed
from app.models.sensor_file import SensorFile


# 1. 强制使用测试数据库
logger.info(f"[test_db] Original USE_TEST_DB config: {settings.USE_TEST_DB}")
logger.info("[test_db] Forcing test database mode...")
settings.database.use_test_db = True


def seed_mock_files(session: Session) -> None:
    """
    向测试数据库插入模拟文件数据;

    仅在 sensor_files 表为空时执行插入，避免重复数据;

    Args:
        session: SQLModel 数据库会话对象;
    """
    if session.exec(select(SensorFile)).first():
        logger.info("[test_db] Mock files already exist, skipping insertion")
        return

    mock_files = [
        {
            "id": "550e8405",
            "filename": "watch_raw_pending.raw",
            "deviceType": "Watch",
            "status": "Idle",
            "size": "64 MB",
            "duration": "--",
            "deviceModel": "Watch S9",
            "testTypeL1": "Unknown",
            "testTypeL2": "--",
            "notes": "Waiting for manual processing",
            "uploadTime": "2023-10-27T12:30:00",
            "packets": "[]",
        },
        {
            "id": "550e8400",
            "filename": "watch_run_001.raw",
            "deviceType": "Watch",
            "status": "Ready",
            "size": "256 MB",
            "duration": "01:30:00",
            "deviceModel": "Watch S8",
            "testTypeL1": "Run",
            "testTypeL2": "Outdoor",
            "notes": "Test for dropped frames",
            "uploadTime": "2023-10-27T10:30:00",
            "packets": json.dumps([
                {"name": "ACC", "freq": "100Hz", "count": 54000, "present": True},
                {"name": "PPG", "freq": "25Hz", "count": 13500, "present": True},
            ]),
        }
    ]

    for f in mock_files:
        obj = SensorFile(**f)
        session.add(obj)

    session.commit()
    logger.info("[test_db] Inserted mock files")


def main() -> None:
    """
    测试数据库初始化主函数;

    执行以下步骤：
    1. 创建测试数据库引擎
    2. 如果数据库不存在，创建表结构
    3. 填充字典数据和模拟文件数据
    """
    logger.info(f"[test_db] Target DB URL: {settings.SQLITE_URL}")

    # 创建测试专用引擎
    test_engine = create_engine(settings.SQLITE_URL, echo=settings.database.echo)

    # 检查数据库文件是否存在
    db_path = settings.DB_DIR / "test.db"
    if db_path.exists():
        logger.info(f"[test_db] Database file '{db_path}' already exists")
    else:
        logger.info(f"[test_db] Database file '{db_path}' not found, initializing...")

        # 创建表结构
        SQLModel.metadata.create_all(test_engine)
        logger.info("[test_db] Tables created")

    # 填充数据(字典 + 模拟文件)
    with Session(test_engine) as session:
        seed.seed_data(session)
        seed_mock_files(session)

    logger.info("[test_db] Test database initialization complete")


if __name__ == "__main__":
    main()

from sqlmodel import Session, select
from app.models.sensor_file import SensorFile
from app.models.dictionary import DeviceModel, TestType, TestSubType
from datetime import datetime
import json

from app.core.config import settings

def seed_data(session: Session):
    seed_dictionary(session)
    # Only seed mock files if using test database
    if settings.USE_TEST_DB:
        seed_mock_files(session)
    else:
        print("[Seed] Skipping mock files (Production DB)")

def seed_dictionary(session: Session):
    # Device Models
    if not session.exec(select(DeviceModel)).first():
        models = [
            ("Watch", "Apple Watch Series 9"),
            ("Watch", "Samsung Galaxy Watch 6"),
            ("Watch", "Fitbit Sense 2"),
            ("Watch", "Garmin Forerunner 965"),
            ("Ring", "Oura Ring Gen 3"),
            ("Ring", "Samsung Galaxy Ring"),
            ("Ring", "Circular Ring Slim"),
            ("Ring", "Ultrahuman Ring AIR"),
        ]
        for dtype, name in models:
            session.add(DeviceModel(deviceType=dtype, modelName=name))
        session.commit()
        print("Seeded device models")

    # Test Types
    if not session.exec(select(TestType)).first():
        types_data = [
            ("unknown", "Unknown", ["--"]),
            ("run", "Run", ["Outdoor", "Indoor", "Treadmill"]),
            ("walk", "Walk", ["Outdoor", "Indoor"]),
            ("sleep", "Sleep", ["Night Rest", "Nap"]),
            ("stress", "Stress", ["Work", "Exercise", "Daily"]),
            ("yoga", "Yoga", ["Meditation", "Flow", "Power"]),
            ("cycle", "Cycle", ["Outdoor", "Indoor", "Stationary"]),
        ]
        
        for tid, name, subtypes in types_data:
            session.add(TestType(id=tid, name=name))
            for sub in subtypes:
                session.add(TestSubType(test_type_id=tid, name=sub))
        session.commit()
        print("Seeded test types")

def seed_mock_files(session: Session):
    if session.exec(select(SensorFile)).first():
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
        # ... Add one or two representatives
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
    print("Seeded mock files")

from sqlmodel import Session, create_engine, select
from app.models.sensor_file import SensorFile
from app.core.config import settings

def check_latest():
    engine = create_engine(settings.SQLITE_URL)
    with Session(engine) as session:
        statement = select(SensorFile).order_by(SensorFile.upload_time.desc()).limit(1)
        result = session.exec(statement).first()
        if result:
            print(f"Latest file: {result.filename}")
            print(f"Device Type: {result.device_type}")
            print(f"Size: {result.size}")
            print(f"Raw Path: {result.raw_path}")
            print(f"Processed Dir: {result.processed_dir}")
            print(f"Meta: {result.content_meta}")
        else:
            print("No files found.")

if __name__ == "__main__":
    check_latest()

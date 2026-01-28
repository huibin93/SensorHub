from sqlmodel import Session, select, create_engine
from app.models.sensor_file import SensorFile

sqlite_file_name = "sensorhub.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

with Session(engine) as session:
    files = session.exec(select(SensorFile)).all()
    print(f"Total files: {len(files)}")
    for f in files:
        print(f"ID: {f.id}")
        print(f"  Filename: '{f.filename}'")
        print(f"  NameSuffix: '{f.name_suffix}'")
        print(f"  Size: {f.size}")
        print("-" * 20)

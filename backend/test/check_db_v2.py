import sys
from pathlib import Path
from sqlmodel import Session, select, create_engine
from app.models.sensor_file import SensorFile

# Add backend to sys.path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.core.config import settings

def inspect():
    url = settings.SQLITE_URL
    print(f"Connecting to: {url}")
    engine = create_engine(url)

    with Session(engine) as session:
        files = session.exec(select(SensorFile)).all()
        print(f"Total files: {len(files)}")
        for f in files:
            print(f"ID: {f.id}")
            print(f"  Filename: '{f.filename}'")
            print(f"  Suffix:   '{f.name_suffix}'") # Check actual value
            print(f"  Size:     {f.size} ({f.file_size_bytes} bytes)")
            print("-" * 30)

if __name__ == "__main__":
    inspect()

import sys
from pathlib import Path
import sqlite3

# Add backend to sys.path so we can import app
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.core.config import settings

def migrate():
    # Parse DB path from URL: sqlite:///path/to/db
    url = settings.SQLITE_URL
    print(f"Settings SQLITE_URL: {url}")
    
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
    else:
        print("❌ Unsupported URL format")
        return

    print(f"Target DB Path: {db_path}") 
    
    if not Path(db_path).exists():
        print(f"❌ DB file not found at {db_path}")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # List tables
    res = cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in res.fetchall()]
    print(f"Tables found: {tables}")

    if "sensor_files" not in tables:
        print("❌ Table 'sensor_files' still missing! (Check if you are using test.db?)")
    
    # 1. Add file_size_bytes
    try:
        cur.execute("ALTER TABLE sensor_files ADD COLUMN file_size_bytes INTEGER DEFAULT 0")
        print("✅ Added column: file_size_bytes")
    except Exception as e:
        print(f"⚠️  file_size_bytes: {e}")

    # 2. Add name_suffix
    try:
        cur.execute("ALTER TABLE sensor_files ADD COLUMN name_suffix TEXT DEFAULT ''")
        print("✅ Added column: name_suffix")
    except Exception as e:
        print(f"⚠️  name_suffix: {e}")

    con.commit()
    con.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()

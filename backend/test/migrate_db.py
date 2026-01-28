import sqlite3
import os

print(f"CWD: {os.getcwd()}")
db_path = "sensorhub.db"
if not os.path.exists(db_path):
    print(f"❌ DB file not found at {db_path}")
    exit(1)

print(f"Migrating {db_path}...")

con = sqlite3.connect(db_path)
cur = con.cursor()

# List tables
res = cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in res.fetchall()]
print(f"Tables: {tables}")

if "sensor_files" not in tables:
    print("❌ Table 'sensor_files' missing!")
else:
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

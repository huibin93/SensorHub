import zipfile
from pathlib import Path

ZIP_PATH = Path(r"c:\Users\acang\Desktop\SensorHub\test_data\4_2026_01_25_22_29_51.zip")

def inspect_zip():
    if not ZIP_PATH.exists():
        print("Zip not found")
        return

    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        print(f"Files in zip: {len(zf.namelist())}")
        for name in zf.namelist():
            print(f"- {name}")

if __name__ == "__main__":
    inspect_zip()

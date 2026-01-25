"""
Test upload of large zip file with 4 internal files.
"""
import httpx
import asyncio
from pathlib import Path

UPLOAD_URL = "http://localhost:8000/api/files/upload"
TEST_FILE = Path(r"C:\Users\acang\Desktop\SensorHub\test_data\4_2026_01_25_22_29_51.zip")

async def main():
    print("=" * 60)
    print(f"Uploading: {TEST_FILE.name}")
    print(f"Size: {TEST_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    print("=" * 60)
    
    # Use longer timeout for large file
    async with httpx.AsyncClient(timeout=600) as client:
        try:
            with open(TEST_FILE, "rb") as f:
                files = {"file": (TEST_FILE.name, f, "application/zip")}
                print("Uploading... (this may take a while)")
                response = await client.post(UPLOAD_URL, files=files)
            
            print(f"\nStatus: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"File ID: {data.get('id')}")
                print(f"Message: {data.get('message')}")
                print(f"Response: {data}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

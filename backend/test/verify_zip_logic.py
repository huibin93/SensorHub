import httpx
import asyncio
from pathlib import Path

# Path to the specific test zip
ZIP_PATH = Path(r"c:\Users\acang\Desktop\SensorHub\test_data\4_2026_01_25_22_29_51.zip")
UPLOAD_URL = "http://localhost:8000/api/files/upload"

async def test_zip_upload():
    if not ZIP_PATH.exists():
        print(f"Error: File {ZIP_PATH} not found.")
        return

    print(f"Testing upload of: {ZIP_PATH.name}")
    print(f"Size: {ZIP_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    
    async with httpx.AsyncClient(timeout=600.0) as client:  # Long timeout for large file
        try:
            with open(ZIP_PATH, "rb") as f:
                # Use 'application/zip' or let it auto-detect, but extensions check is based on filename in backend
                files = {"file": (ZIP_PATH.name, f, "application/zip")}
                print("Sending request...")
                response = await client.post(UPLOAD_URL, files=files)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print("SUCCESS!")
                print(f"Message: {data.get('message')}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_zip_upload())

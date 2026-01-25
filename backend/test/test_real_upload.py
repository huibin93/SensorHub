"""
Test upload with real files from test_data directory.
"""
import httpx
import asyncio
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
UPLOAD_URL = "http://localhost:8000/api/files/upload"

async def upload_file(filepath: Path):
    """Upload a single file and print results."""
    print(f"\n{'='*60}")
    print(f"Uploading: {filepath.name}")
    print(f"Size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")
    
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            with open(filepath, "rb") as f:
                files = {"file": (filepath.name, f, "application/octet-stream")}
                response = await client.post(UPLOAD_URL, files=files)
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"File ID: {data.get('id')}")
                print(f"Message: {data.get('message')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Failed: {e}")

async def main():
    print("=" * 60)
    print("UPLOAD TEST WITH REAL FILES")
    print("=" * 60)
    
    # List test files
    test_files = list(TEST_DATA_DIR.glob("*"))
    print(f"\nFound {len(test_files)} files in test_data:")
    for f in test_files:
        print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Test with one small rawdata file first
    rawdata_files = list(TEST_DATA_DIR.glob("*.rawdata"))
    zip_files = list(TEST_DATA_DIR.glob("*.zip"))
    
    # Test 1: Upload smallest rawdata file
    if rawdata_files:
        smallest_rawdata = min(rawdata_files, key=lambda f: f.stat().st_size)
        print("\n--- TEST 1: Streaming Gzip for .rawdata ---")
        await upload_file(smallest_rawdata)
    
    # Test 2: Upload smallest zip file
    if zip_files:
        smallest_zip = min(zip_files, key=lambda f: f.stat().st_size)
        print("\n--- TEST 2: Zip Extraction ---")
        await upload_file(smallest_zip)
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

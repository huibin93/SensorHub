import httpx
import asyncio

async def test_validation():
    url = "http://localhost:8000/api/files/upload"
    
    # Test 1: Invalid extension (.txt)
    print("Test 1: Uploading .txt (Expect 400)")
    files_invalid = {'file': ('test.txt', b'content', 'text/plain')}
    async with httpx.AsyncClient() as client:
        try:
            r1 = await client.post(url, files=files_invalid)
            print(f"Status: {r1.status_code}")
            print(f"Response: {r1.text}")
        except Exception as e:
            print(f"Failed: {e}")

    print("-" * 20)

    # Test 2: Valid extension (.rawdata)
    print("Test 2: Uploading .rawdata (Expect 200)")
    files_valid = {'file': ('test.rawdata', b'content', 'application/octet-stream')}
    async with httpx.AsyncClient() as client:
        try:
            r2 = await client.post(url, files=files_valid)
            print(f"Status: {r2.status_code}")
            print(f"Response: {r2.text}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_validation())

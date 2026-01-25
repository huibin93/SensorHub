import httpx
import asyncio

async def test_upload():
    url = "http://localhost:8000/api/files/upload"
    files = {'file': ('test_file.txt', b'hello world', 'text/plain')}
    # Optional: data = {'deviceType': 'Watch'}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, files=files)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload())

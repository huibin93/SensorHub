import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Login
login_data = {
    "username": "admin",
    "password": "admin"
}
response = requests.post(f"{BASE_URL}/login/access-token", data=login_data)
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login successful")

# 2. Get File ID
response = requests.get(f"{BASE_URL}/files?limit=1", headers=headers)
if response.status_code != 200:
    print(f"Get files failed: {response.text}")
    exit(1)

files = response.json()["items"]
if not files:
    print("No files found")
    exit(0)

file_id = files[0]["id"]
print(f"Testing with file ID: {file_id}")

# 3. PATCH Update (using camelCase keys)
update_data = {
    "deviceType": "Ring",
    "deviceModel": "Oura Gen3",
    "deviceName": "Test Device via Script",
    "notes": "Updated via Python script"
}

print(f"Sending PATCH request with data: {json.dumps(update_data, indent=2)}")
response = requests.patch(f"{BASE_URL}/files/{file_id}", json=update_data, headers=headers)

if response.status_code == 200:
    print("Update successful!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Update failed with status {response.status_code}")
    print(response.text)

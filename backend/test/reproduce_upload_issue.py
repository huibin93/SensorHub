import requests
import hashlib
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
FILE_CONTENT = b"This is a test file for upload permission reproduction."
FILENAME = "repro_test.rawdata"

def get_token():
    url = f"{BASE_URL}/login/access-token"
    data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    }
    print(f"Logging in as {ADMIN_USER}...")
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("Login successful.")
            return token
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def upload_file(token):
    url = f"{BASE_URL}/files/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    md5 = hashlib.md5(FILE_CONTENT).hexdigest()
    
    files = {
        "file": (FILENAME, FILE_CONTENT, "application/octet-stream")
    }
    
    data = {
        "md5": md5,
        "filename": FILENAME,
        "original_size": len(FILE_CONTENT),
        "deviceType": "TestDevice"
    }
    
    print(f"Uploading file {FILENAME} (MD5: {md5})...")
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Upload request failed: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        upload_file(token)

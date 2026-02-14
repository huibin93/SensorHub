
import sys
import os
import hashlib
import json
import zstandard as zstd
from pathlib import Path
from sqlmodel import Session, select

# Adjust path to include backend root
# Assuming we are running from backend/tests/verify_rebuild.py or similar
# We want to add 'backend' to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir) # Go up one level from tests to backend
sys.path.append(backend_dir)

from app.services.storage import StorageService
from app.services.file_service import FileService
from app.core.database import engine
from app.models.sensor_file import PhysicalFile, SensorFile

TEST_DATA_DIR = Path(r"c:\Users\acang\Desktop\SensorHub\test_data")
TEMP_DIR = TEST_DATA_DIR # Use existing test_data dir

def create_dummy_zst(filename="test_rebuild.raw.zst", content=b"Hello World" * 100):
    """Create a simple zstd file."""
    cctx = zstd.ZstdCompressor()
    compressed = cctx.compress(content)
    
    md5 = hashlib.md5(content).hexdigest()
    path = TEMP_DIR / filename
    with open(path, "wb") as f:
        f.write(compressed)
    
    return path, md5, len(content)

def test_rebuild_logic():
    print("=== Testing Rebuild Logic ===")
    
    # 1. Create a dummy zst file WITHOUT index
    path, expected_md5, original_size = create_dummy_zst()
    print(f"Created dummy file: {path} (MD5: {expected_md5})")
    
    # 2. Call verify_and_rebuild_index
    print("Calling verify_and_rebuild_index...")
    result = StorageService.verify_and_rebuild_index(path, expected_md5)
    
    print(f"Result: {json.dumps(result, default=str, indent=2)}")
    
    assert result["valid"] == True
    assert result["rebuilt"] == True
    assert result["frame_index"] is not None
    assert result["file_size_bytes"] == original_size
    
    print("✅ Test 1 Passed: Rebuild from no index successful.")
    
    # Clean up
    if path.exists():
        os.remove(path)
        
    print("\n=== All Tests Passed ===")

if __name__ == "__main__":
    test_rebuild_logic()

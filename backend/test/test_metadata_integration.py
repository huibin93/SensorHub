import logging
import sys
import os
import zstandard as zstd
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.metadata_parser import extract_metadata_from_content, extract_metadata_from_zstd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_CONTENT = """
{
 'startTime': '2024-06-24 14:39:43',
 'device': 'OFFLINE_LW10(9ff2)',
 'device_mac': 'f4:4e:fd:64:9f:f2',
 'device version': '1.0.42',
 'reference': '',
 'reference_mac': '',
 'phone': 'Xiaomi 2107119DC',
 'phone_version': 'RKQ1.210503.001',
 'app version': 'v1.0.0',
 'user_name': 'Frederick',
 'algorithm_info': '&&'
}
start collecting
some data...
"""

def test_string_extraction():
    logger.info("Testing string extraction...")
    meta = extract_metadata_from_content(SAMPLE_CONTENT)
    logger.info(f"Extracted: {meta}")
    
    assert meta['startTime'] == '2024-06-24 14:39:43'
    assert meta['device_mac'] == 'f4:4e:fd:64:9f:f2'
    assert meta['user_name'] == 'Frederick'
    logger.info("String extraction PASSED")

def test_zstd_extraction():
    logger.info("Testing ZSTD extraction...")
    
    # Create temp zstd file
    temp_file = Path("test_metadata.zst")
    cctx = zstd.ZstdCompressor()
    with open(temp_file, "wb") as f:
        f.write(cctx.compress(SAMPLE_CONTENT.encode('utf-8')))
        
    try:
        # Test extraction
        meta = extract_metadata_from_zstd(temp_file)
        logger.info(f"Extracted from ZSTD: {meta}")
        
        assert meta['startTime'] == '2024-06-24 14:39:43'
        assert meta['device_mac'] == 'f4:4e:fd:64:9f:f2'
        
    finally:
        if temp_file.exists():
            temp_file.unlink()
            
    logger.info("ZSTD extraction PASSED")

if __name__ == "__main__":
    test_string_extraction()
    test_zstd_extraction()

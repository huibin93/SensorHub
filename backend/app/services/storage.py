import shutil
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings

class StorageService:
    @staticmethod
    def get_raw_path(file_id: str) -> Path:
        return settings.RAW_DIR / f"{file_id}.raw.gz"
        
    @staticmethod
    def get_processed_dir(file_id: str) -> Path:
        return settings.PROCESSED_DIR / file_id

    @staticmethod
    async def save_upload_file(file: UploadFile, file_id: str) -> Path:
        """Save uploaded file to raw storage."""
        settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
        
        destination = StorageService.get_raw_path(file_id)
        
        # Directly save the file stream
        # Future improvement: Gzip compression if not already compressed
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return destination

    @staticmethod
    def delete_file(file_id: str):
        """Delete raw and processed files."""
        # Delete raw
        raw_path = StorageService.get_raw_path(file_id)
        if raw_path.exists():
            raw_path.unlink()
            
        # Delete processed dir
        proc_dir = StorageService.get_processed_dir(file_id)
        if proc_dir.exists() and proc_dir.is_dir():
            shutil.rmtree(proc_dir)

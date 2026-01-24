from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class SensorFile(SQLModel, table=True):
    __tablename__ = "sensor_files"
    
    id: str = Field(primary_key=True)
    filename: str
    device_type: str = Field(alias="deviceType")
    status: str = Field(default="Idle")
    size: str
    duration: str = Field(default="--")
    device_model: str = Field(alias="deviceModel")
    test_type_l1: str = Field(default="Unknown", alias="testTypeL1")
    test_type_l2: str = Field(default="--", alias="testTypeL2")
    notes: str = Field(default="")
    upload_time: str = Field(alias="uploadTime")
    packets: str = Field(default="[]")
    
    # Optional fields
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: Optional[int] = None
    
    # New fields in Phase 5
    content_meta: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    raw_path: Optional[str] = Field(default=None, alias="rawPath")
    processed_dir: Optional[str] = Field(default=None, alias="processedDir")
    
    class Config:
        populate_by_name = True

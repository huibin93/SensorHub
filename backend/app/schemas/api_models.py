from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- Stats ---
class StatsResponse(BaseModel):
    totalFiles: int
    todayUploads: int
    pendingTasks: int
    storageUsed: str
    lastUpdated: str

# --- Files ---
class SensorFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: str
    filename: str
    deviceType: str = Field(validation_alias="device_type")
    status: str
    size: str
    duration: str
    deviceModel: str = Field(validation_alias="device_model")
    testTypeL1: str = Field(validation_alias="test_type_l1")
    testTypeL2: str = Field(validation_alias="test_type_l2")
    notes: str
    uploadTime: str = Field(validation_alias="upload_time")
    packets: Any # List[Any] or string? DB is string, but Model might return list if we parsed it? 
                 # SensorFile model has `packets: str`. So response should handle str or list.
                 # Let's keep it Any for now, but frontend expects array. 
                 # If DB sends string "[]", frontend might need parsing or we parse here.
    
    errorMessage: Optional[str] = Field(None, validation_alias="error_message")
    progress: Optional[int] = None
    contentMeta: Optional[dict] = Field(None, validation_alias="content_meta")
    rawPath: Optional[str] = Field(None, validation_alias="raw_path")
    processedDir: Optional[str] = Field(None, validation_alias="processed_dir")

class PaginatedFilesResponse(BaseModel):
    items: List[SensorFileResponse]
    total: int
    page: int
    limit: int
    totalPages: int

class FileUpdateRequest(BaseModel):
    notes: Optional[str] = None
    deviceType: Optional[str] = None
    deviceModel: Optional[str] = None
    testTypeL1: Optional[str] = None
    testTypeL2: Optional[str] = None

class BatchDeleteRequest(BaseModel):
    ids: List[str]

class UploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class ParseRequest(BaseModel):
    options: Optional[dict] = None

class BatchDownloadRequest(BaseModel):
    ids: List[str]

# --- Config/Dictionary ---
class DeviceType(BaseModel):
    type: str
    models: List[str]

class DevicesResponse(BaseModel):
    devices: List[DeviceType]

class AddDeviceModelRequest(BaseModel):
    deviceType: str
    modelName: str

class TestType(BaseModel):
    id: str
    name: str # Primary type (L1)
    subTypes: List[str] # L2 types

class TestTypesResponse(BaseModel):
    types: List[TestType]

class AddTestTypeRequest(BaseModel):
    name: str

class AddSubTypeRequest(BaseModel):
    name: str

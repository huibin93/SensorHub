"""
API 数据模型模块;

本模块定义 API 请求和响应使用的 Pydantic 模型;
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- 统计相关 ---

class StatsResponse(BaseModel):
    """文件统计响应模型;"""
    totalFiles: int
    todayUploads: int
    pendingTasks: int
    storageUsed: int



# --- 文件相关 ---

class SensorFileResponse(BaseModel):
    """
    传感器文件响应模型;

    用于 API 返回文件信息;
    通过 JOIN DeviceMapping 和 ParseResult 展平返回，保持前端兼容;
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    filename: str
    deviceType: str = Field(default="Watch")  # ← JOIN DeviceMapping
    status: str = Field(default="unverified")  # ← 合并 file_status / ParseResult.status
    size: str
    duration: str = Field(default="--")  # ← ParseResult
    deviceModel: str = Field(default="Unknown")  # ← JOIN DeviceMapping
    testTypeL1: str = Field(default="Unknown", validation_alias="test_type_l1")
    testTypeL2: str = Field(default="--", validation_alias="test_type_l2")
    notes: str = Field(default="")
    uploadTime: str = Field(validation_alias="upload_time")
    packets: Any = Field(default="[]")  # ← ParseResult

    errorMessage: Optional[str] = Field(None)  # ← ParseResult
    progress: Optional[int] = None  # ← ParseResult
    contentMeta: Optional[dict] = Field(None)  # ← ParseResult
    rawPath: Optional[str] = Field(None, validation_alias="raw_path")
    processedDir: Optional[str] = Field(None)  # ← ParseResult
    nameSuffix: Optional[str] = Field(None, validation_alias="name_suffix")
    
    # Metadata fields (2026-02-04)
    deviceName: Optional[str] = Field(None, validation_alias="device_name")
    startTime: Optional[str] = Field(None, validation_alias="start_time")
    collectionTime: Optional[str] = Field(None, validation_alias="collection_time")
    timezone: Optional[str] = Field(None, validation_alias="timezone")
    deviceMac: Optional[str] = Field(None, validation_alias="device_mac")
    deviceVersion: Optional[str] = Field(None, validation_alias="device_version")
    userName: Optional[str] = Field(None, validation_alias="user_name")


class PaginatedFilesResponse(BaseModel):
    """分页文件列表响应模型;"""
    items: List[SensorFileResponse]
    total: int
    page: int
    limit: int
    totalPages: int


class FileUpdateRequest(BaseModel):
    """文件更新请求模型;"""
    notes: Optional[str] = None
    device_name: Optional[str] = Field(None, validation_alias="deviceName")
    device_type: Optional[str] = Field(None, validation_alias="deviceType")
    device_model: Optional[str] = Field(None, validation_alias="deviceModel")
    test_type_l1: Optional[str] = Field(None, validation_alias="testTypeL1")
    test_type_l2: Optional[str] = Field(None, validation_alias="testTypeL2")


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型;"""
    ids: List[str]


class UploadResponse(BaseModel):
    """文件上传响应模型;"""
    id: str
    filename: str
    status: str
    message: str


class ParseRequest(BaseModel):
    """文件解析请求模型;"""
    options: Optional[dict] = None


# --- 配置/字典相关 ---

class DeviceType(BaseModel):
    """设备类型模型(包含型号列表);"""
    type: str
    models: List[str]


class DevicesResponse(BaseModel):
    """设备列表响应模型;"""
    devices: List[DeviceType]


class TestType(BaseModel):
    """测试类型模型(包含子类型列表);"""
    id: str
    name: str
    subTypes: List[str]


class TestTypesResponse(BaseModel):
    """测试类型列表响应模型;"""
    types: List[TestType]


class AddTestTypeRequest(BaseModel):
    """添加测试类型请求模型;"""
    name: str


class AddSubTypeRequest(BaseModel):
    """添加测试子类型请求模型;"""
    name: str


# --- 设备直接对接相关 ---

class DeviceFile(BaseModel):
    """设备端文件模型;"""
    filename: str
    url: str
    size: Optional[str] = "Unknown"
    date: Optional[str] = None
    is_uploaded: bool = False # 是否已存在于平台数据库

class DeviceFilesResponse(BaseModel):
    items: List[DeviceFile]
    total: int

class DeviceDownloadRequest(BaseModel):
    """设备文件下载请求;"""
    device_ip: str
    files: List[DeviceFile] # 包含 url 和 filename


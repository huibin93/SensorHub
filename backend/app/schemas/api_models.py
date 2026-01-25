"""
API 数据模型模块。

本模块定义 API 请求和响应使用的 Pydantic 模型。
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- 统计相关 ---

class StatsResponse(BaseModel):
    """文件统计响应模型。"""
    totalFiles: int
    todayUploads: int
    pendingTasks: int
    storageUsed: str
    lastUpdated: str


# --- 文件相关 ---

class SensorFileResponse(BaseModel):
    """
    传感器文件响应模型。

    用于 API 返回文件信息，支持从数据库模型自动转换。
    """
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
    packets: Any  # 数据库存储为字符串，前端期望数组

    errorMessage: Optional[str] = Field(None, validation_alias="error_message")
    progress: Optional[int] = None
    contentMeta: Optional[dict] = Field(None, validation_alias="content_meta")
    rawPath: Optional[str] = Field(None, validation_alias="raw_path")
    processedDir: Optional[str] = Field(None, validation_alias="processed_dir")


class PaginatedFilesResponse(BaseModel):
    """分页文件列表响应模型。"""
    items: List[SensorFileResponse]
    total: int
    page: int
    limit: int
    totalPages: int


class FileUpdateRequest(BaseModel):
    """文件更新请求模型。"""
    notes: Optional[str] = None
    deviceType: Optional[str] = None
    deviceModel: Optional[str] = None
    testTypeL1: Optional[str] = None
    testTypeL2: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型。"""
    ids: List[str]


class UploadResponse(BaseModel):
    """文件上传响应模型。"""
    id: str
    filename: str
    status: str
    message: str


class ParseRequest(BaseModel):
    """文件解析请求模型。"""
    options: Optional[dict] = None


class BatchDownloadRequest(BaseModel):
    """批量下载请求模型。"""
    ids: List[str]


# --- 配置/字典相关 ---

class DeviceType(BaseModel):
    """设备类型模型（包含型号列表）。"""
    type: str
    models: List[str]


class DevicesResponse(BaseModel):
    """设备列表响应模型。"""
    devices: List[DeviceType]


class AddDeviceModelRequest(BaseModel):
    """添加设备型号请求模型。"""
    deviceType: str
    modelName: str


class TestType(BaseModel):
    """测试类型模型（包含子类型列表）。"""
    id: str
    name: str
    subTypes: List[str]


class TestTypesResponse(BaseModel):
    """测试类型列表响应模型。"""
    types: List[TestType]


class AddTestTypeRequest(BaseModel):
    """添加测试类型请求模型。"""
    name: str


class AddSubTypeRequest(BaseModel):
    """添加测试子类型请求模型。"""
    name: str

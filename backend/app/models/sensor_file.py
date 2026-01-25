"""
传感器文件数据模型模块。

本模块定义传感器文件的数据库模型。
"""
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class SensorFile(SQLModel, table=True):
    """
    传感器文件模型。

    存储上传的传感器数据文件及其元信息。

    Attributes:
        id: 文件唯一标识符（UUID）。
        filename: 原始文件名。
        device_type: 设备类型（Watch/Ring）。
        status: 处理状态（Idle/Processed/Failed）。
        size: 文件大小。
        duration: 记录时长。
        device_model: 设备型号。
        test_type_l1: 一级测试类型。
        test_type_l2: 二级测试类型。
        notes: 备注。
        upload_time: 上传时间。
        packets: 数据包信息（JSON 字符串）。
        error_message: 错误信息。
        progress: 处理进度。
        content_meta: 内容元数据（JSON）。
        raw_path: 原始文件存储路径。
        processed_dir: 处理后文件目录路径。
    """
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

    # 可选字段
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: Optional[int] = None

    # Phase 5 新增字段
    content_meta: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    raw_path: Optional[str] = Field(default=None, alias="rawPath")
    processed_dir: Optional[str] = Field(default=None, alias="processedDir")

    class Config:
        """Pydantic 配置。"""
        populate_by_name = True

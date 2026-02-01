"""
传感器文件数据模型模块;

本模块定义传感器文件的数据库模型;
"""
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON


class PhysicalFile(SQLModel, table=True):
    """
    物理存储表;
    核心职责：去重。只要 Hash 相同,硬盘上只存一份,数据库里只有这一行。
    """
    __tablename__ = "physical_files"

    hash: str = Field(primary_key=True, index=True, description="文件的 MD5/SHA256,绝对唯一的主键")
    size: int = Field(description="文件大小(Bytes)")
    path: str = Field(description="Zstd 压缩文件在磁盘/S3 上的物理路径")
    
    created_at: datetime = Field(default_factory=datetime.now, description="物理文件首次入库时间")
    compression_ratio: Optional[str] = Field(default=None, description="压缩率统计")
    
    # 帧索引元数据 (用于随机读取)
    # 格式: {"version": 1, "frameSize": 2097152, "frames": [{cs, cl, ds, dl}, ...]}
    # cs: compressed_start (压缩数据起始偏移)
    # cl: compressed_length (压缩数据长度)
    # ds: decompressed_start (解压数据起始偏移)
    # dl: decompressed_length (解压数据长度)
    frame_index: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # 反向关系
    sensor_files: List["SensorFile"] = Relationship(back_populates="physical_file")


class SensorFile(SQLModel, table=True):
    """
    传感器文件模型 (业务逻辑表);

    存储上传的传感器数据文件及其元信息;

    Attributes:
        id: 文件唯一标识符(UUID);
        file_hash: 关联的物理文件 Hash;
        filename: 原始文件名;
        device_type: 设备类型(Watch/Ring);
        status: 处理状态(unverified/verified/error/processing/processed);
        size: 文件大小(显示用字符串);
        duration: 记录时长;
        device_model: 设备型号;
        test_type_l1: 一级测试类型;
        test_type_l2: 二级测试类型;
        notes: 备注;
        upload_time: 上传时间;
        packets: 数据包信息(JSON 字符串);
        error_message: 错误信息;
        progress: 处理进度; 
        content_meta: 内容元数据(JSON);
        processed_dir: 处理后文件目录路径;
    """
    __tablename__ = "sensor_files"

    id: str = Field(primary_key=True)
    
    # 外键关联
    file_hash: str = Field(foreign_key="physical_files.hash", index=True, description="关联到物理文件")
    
    filename: str
    device_type: str = Field(alias="deviceType")
    status: str = Field(default="unverified")
    
    # 这里的 size 仍保留作为显示用的字符串 (例如 "1.2 MB"),
    # 虽然物理大小在 PhysicalFile 中,但为了前端展示方便,保留快照。
    size: str 
    
    # Phase 5.5 新增: 记录文件字节数，用于快速去重 (无需计算 Hash)
    file_size_bytes: int = Field(default=0, description="文件原始字节大小")
    
    # Phase 5.6 新增: 文件名重复时的后缀 (例如 " (1)")
    name_suffix: str = Field(default="", description="文件名重复时的后缀", alias="nameSuffix")
    
    duration: str = Field(default="--")
    device_model: str = Field(alias="deviceModel")
    test_type_l1: str = Field(default="Unknown", alias="testTypeL1")
    test_type_l2: str = Field(default="--", alias="testTypeL2")
    notes: str = Field(default="")
    upload_time: str = Field(alias="uploadTime")
    packets: str = Field(default="[]")

    # 新字段 (阶段 6b)
    tester: str = Field(default="")
    mac: str = Field(default="")
    collection_time: str = Field(default="") # 格式: YYYYMMDD_HHMMSS

    # 可选字段
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: Optional[int] = None

    # Phase 5 新增字段
    content_meta: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    # raw_path 已移除,通过 PhysicalFile 获取
    processed_dir: Optional[str] = Field(default=None, alias="processedDir")
    
    # 关系属性
    physical_file: Optional[PhysicalFile] = Relationship(back_populates="sensor_files")

    class Config:
        """Pydantic 配置;"""
        populate_by_name = True

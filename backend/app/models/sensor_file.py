"""
传感器文件数据模型模块;

本模块定义传感器文件的数据库模型;
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

if TYPE_CHECKING:
    from app.models.parse_result import ParseResult


class PhysicalFile(SQLModel, table=True):
    """
    物理存储表;
    核心职责：去重。只要 Hash 相同,硬盘上只存一份,数据库里只有这一行。
    """
    __tablename__ = "physical_files" # type: ignore

    hash: str = Field(primary_key=True, index=True, description="文件的 MD5/SHA256,绝对唯一的主键")
    size: int = Field(description="文件大小(Bytes)")
    path: str = Field(description="Zstd 压缩文件在磁盘/S3 上的物理路径")
    
    created_at: datetime = Field(default_factory=datetime.now, description="物理文件首次入库时间")
    compression_ratio: Optional[str] = Field(default=None, description="压缩率统计")
    
    # 帧索引元数据 (用于随机读取和并行处理)
    # 格式: {"version": 2, "frameSize": 2097152, "maxFrameSize": 4194304, "lineAligned": true, "frames": [{cs, cl, ds, dl, nl}, ...]}
    # cs: compressed_start (压缩数据起始偏移)
    # cl: compressed_length (压缩数据长度)
    # ds: decompressed_start (解压数据起始偏移)
    # dl: decompressed_length (解压数据长度)
    # nl: ends_with_newline (是否以换行符结束, 用于并行处理)
    frame_index: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # 反向关系
    sensor_files: List["SensorFile"] = Relationship(back_populates="physical_file")


class SensorFile(SQLModel, table=True):
    """
    传感器文件模型 (业务逻辑表);

    存储上传的传感器数据文件及其元信息;
    设备信息 (device_type/device_model) 通过 device_name 关联 DeviceMapping 获取;
    解析状态和结果存储在 ParseResult 表中;

    Attributes:
        id: 文件唯一标识符(UUID);
        file_hash: 关联的物理文件 Hash;
        filename: 原始文件名;
        file_status: 文件状态(unverified/verified/error);
        size: 文件大小(显示用字符串);
        device_name: 设备名称 (关联 DeviceMapping);
        test_type_l1: 一级测试类型;
        test_type_l2: 二级测试类型;
        notes: 备注;
        upload_time: 上传时间;
    """
    __tablename__ = "sensor_files" # type: ignore

    id: str = Field(primary_key=True)
    
    # 外键关联
    file_hash: str = Field(foreign_key="physical_files.hash", index=True, description="关联到物理文件")
    
    filename: str
    file_status: str = Field(default="unverified", description="文件状态: unverified/verified/error")
    uploaded_by: str = Field(default="Unknown", description="上传者用户名")
    
    # 这里的 size 仍保留作为显示用的字符串 (例如 "1.2 MB"),
    # 虽然物理大小在 PhysicalFile 中,但为了前端展示方便,保留快照。
    size: str 
    
    # Phase 5.5 新增: 记录文件字节数，用于快速去重 (无需计算 Hash)
    file_size_bytes: int = Field(default=0, description="文件原始字节大小")
    
    # Phase 5.6 新增: 文件名重复时的后缀 (例如 " (1)")
    name_suffix: str = Field(default="", description="文件名重复时的后缀", alias="nameSuffix")
    
    test_type_l1: str = Field(default="Unknown", alias="testTypeL1")
    test_type_l2: str = Field(default="--", alias="testTypeL2")
    notes: str = Field(default="")
    upload_time: str = Field(alias="uploadTime")

    # 新字段 (阶段 6b)
    tester: str = Field(default="")
    mac: str = Field(default="") # 对应 metadata 中的 device_mac, 但保留旧字段以防万一
    collection_time: str = Field(default="", alias="collectionTime") # 格式: YYYYMMDD_HHMMSS
    
    # Metadata Parsing Integration (2026-02-04)
    start_time: str = Field(default="", alias="startTime", description="From metadata: startTime")
    device_name: str = Field(default="", alias="deviceName", description="From metadata: device (without parens), FK → DeviceMapping")
    device_mac: str = Field(default="", alias="deviceMac", description="From metadata: device_mac")
    device_version: str = Field(default="", alias="deviceVersion", description="From metadata: device version")
    user_name: str = Field(default="", alias="userName", description="From metadata: user_name")
    
    # Timezone (2026-02-09)
    timezone: str = Field(default="GMT+08:00", description="文件时区")
    
    # 关系属性
    physical_file: Optional[PhysicalFile] = Relationship(back_populates="sensor_files")
    parse_result: Optional["ParseResult"] = Relationship(back_populates="sensor_file")

    class Config:
        """Pydantic 配置;"""
        populate_by_name = True

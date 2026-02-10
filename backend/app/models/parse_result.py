"""
解析结果数据模型模块;

本模块定义文件解析结果的数据库模型;
每个 SensorFile 最多对应一条 ParseResult (1:1, UNIQUE 约束);
可重复解析，但只保留最终结果 (UPDATE 覆盖);
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, UniqueConstraint

if TYPE_CHECKING:
    from app.models.sensor_file import SensorFile


class ParseResult(SQLModel, table=True):
    """
    解析结果表;
    
    存储文件解析的状态、进度和结果;
    与 SensorFile 是 1:1 关系 (sensor_file_id 带 UNIQUE 约束);
    
    Attributes:
        id: 自增主键;
        sensor_file_id: 关联的 SensorFile ID (UNIQUE);
        device_type_used: 解析时使用的 device_type 快照;
        status: 解析状态 (idle/processing/processed/error/failing);
        progress: 解析进度 (0-100);
        duration: 记录时长;
        packets: 数据包信息 (JSON 字符串);
        error_message: 错误信息;
        content_meta: 文件头元数据 (唯一存放处);
        processed_dir: 处理后文件目录路径;
        created_at: 创建时间;
        updated_at: 更新时间;
    """
    __tablename__ = "parse_results" # type: ignore
    __table_args__ = (
        UniqueConstraint("sensor_file_id", name="uq_parse_results_sensor_file_id"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sensor_file_id: str = Field(
        foreign_key="sensor_files.id",
        index=True,
        description="关联的 SensorFile ID (1:1)"
    )
    
    # 解析时使用的设备类型快照
    device_type_used: str = Field(default="", description="解析时从 DeviceMapping 拍的 device_type 快照")
    
    # 解析状态
    status: str = Field(default="idle", description="idle/processing/processed/error/failing")
    progress: Optional[int] = Field(default=None, description="解析进度 0-100")
    
    # 解析结果
    duration: str = Field(default="--", description="记录时长")
    packets: str = Field(default="[]", description="数据包信息 JSON 字符串")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    
    # 文件头元数据 (唯一存放处)
    content_meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # 解析产物路径
    processed_dir: Optional[str] = Field(default=None, description="处理后文件目录路径")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    # 关系属性
    sensor_file: Optional["SensorFile"] = Relationship(back_populates="parse_result")

    class Config:
        """Pydantic 配置;"""
        populate_by_name = True

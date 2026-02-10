"""
设备映射模型模块;

定义 device_name 到 device_type/device_model 的映射关系;
"""
from sqlmodel import SQLModel, Field


class DeviceMapping(SQLModel, table=True):
    """
    设备映射表;
    
    用于根据 device_name 自动识别 device_type 和 device_model;
    
    Attributes:
        device_name: 设备名称 (主键, 全字匹配, 忽略大小写);
        device_type: 设备类型 (Watch/Ring);
        device_model: 设备型号 (全大写存储);
    """
    __tablename__ = "device_mappings" # type: ignore
    
    device_name: str = Field(primary_key=True, description="设备名称")
    device_type: str = Field(description="设备类型 (Watch/Ring)")
    device_model: str = Field(description="设备型号 (大写存储)")
    
    class Config:
        """Pydantic 配置;"""
        populate_by_name = True

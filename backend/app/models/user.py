"""
用户和权限相关的数据模型;
"""
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    """
    用户模型;
    仅存储普通用户,Admin 账号可能仅存在于 .env 或作为特殊 User 记录;
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedLink(SQLModel, table=True):
    """
    公开分享链接模型;
    用于生成外部访问的临时链接;
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token: str = Field(unique=True, index=True, description="随机生成的访问令牌")
    
    # 指向的文件 (物理文件 Hash 或 SensorFile ID? 
    # 需求是: 用户生成一个外链将某个图表数据开放. 
    # SensorFile 是业务对象,这里关联 SensorFile.id (str)
    sensor_file_id: str = Field(index=True) 
    
    created_by_username: str = Field(description="创建者的用户名")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expire_at: datetime = Field(description="过期时间")
    views: int = Field(default=0, description="访问次数")

    # 注意: 这里没有建立强外键关联到 User 表, 为了保持 Admin (仅在Env) 操作的灵活性

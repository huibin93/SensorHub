"""
字典数据模型模块;

本模块定义测试类型相关的数据库模型;
设备型号信息已迁移至 DeviceMapping 表;
"""
from typing import Optional
from sqlmodel import SQLModel, Field


class TestType(SQLModel, table=True):
    """
    测试类型模型(一级分类);

    Attributes:
        id: 主键 ID(字符串);
        name: 类型名称;
    """
    __tablename__ = "test_types" # type: ignore
    id: str = Field(primary_key=True)
    name: str


class TestSubType(SQLModel, table=True):
    """
    测试子类型模型(二级分类);

    Attributes:
        id: 主键 ID;
        test_type_id: 父测试类型 ID(外键);
        name: 子类型名称;
    """
    __tablename__ = "test_sub_types" # type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)
    test_type_id: str = Field(foreign_key="test_types.id")
    name: str

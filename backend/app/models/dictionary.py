from typing import Optional, List
from sqlmodel import SQLModel, Field

class DeviceModel(SQLModel, table=True):
    __tablename__ = "device_models"
    id: Optional[int] = Field(default=None, primary_key=True)
    device_type: str = Field(alias="deviceType")
    model_name: str = Field(alias="modelName")

class TestType(SQLModel, table=True):
    __tablename__ = "test_types"
    id: str = Field(primary_key=True)
    name: str

class TestSubType(SQLModel, table=True):
    __tablename__ = "test_sub_types"
    id: Optional[int] = Field(default=None, primary_key=True)
    test_type_id: str = Field(foreign_key="test_types.id")
    name: str

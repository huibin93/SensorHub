from .sensor_file import SensorFile, PhysicalFile
from .parse_result import ParseResult
from .user import User, SharedLink
from .dictionary import TestType, TestSubType
from .device_mapping import DeviceMapping

# 集中解决循环引用: SensorFile <-> ParseResult
SensorFile.model_rebuild()
ParseResult.model_rebuild()

__all__ = [
    "SensorFile", "PhysicalFile", "ParseResult",
    "User", "SharedLink",
    "TestType", "TestSubType",
    "DeviceMapping",
]

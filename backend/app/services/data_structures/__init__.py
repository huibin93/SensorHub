"""
数据结构模块
Data structures module for rawdata parsing
"""

import struct


def _unpack_from(fmt: str, buffer: bytes, offset: int):
    """
    解包辅助函数,返回解析出的字段和新的偏移量
    
    Parameters:
    -----------
    fmt : str
        struct 格式字符串
    buffer : bytes
        要解包的字节数据
    offset : int
        起始偏移量
    
    Returns:
    --------
    tuple
        (解析出的值的元组, 新的偏移量)
    """
    size = struct.calcsize(fmt)
    return struct.unpack_from(fmt, buffer, offset), offset + size


# 从各个子模块导入所有数据结构类
from .base_info import BaseInfo
from .sensor_data import ACC_Raw_Data, PPG_Raw_Data
from .wear_info import WearInfo, MotionRecognition
from .tyhx_data import TYHX_PPG_Data, TYHX_AGC_Data,TYHX_3697_Data
from .psp_data import PSP_PPG_FIFO, CREEK_HR_Data

__all__ = [
    '_unpack_from',
    'BaseInfo',
    'ACC_Raw_Data',
    'PPG_Raw_Data',
    'WearInfo',
    'MotionRecognition',
    'TYHX_PPG_Data',
    'TYHX_AGC_Data',
    'TYHX_3697_Data',
    'PSP_PPG_FIFO',
    'CREEK_HR_Data',
]

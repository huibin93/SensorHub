"""
传感器数据结构
Sensor data structures (ACC, PPG, etc.)
"""

import struct
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from . import _unpack_from
from app.core.logger import logger


@dataclass
class ACC_Raw_Data:
    """
    加速度原始数据类 (0x18)
    也用于陀螺仪 (0x19) 和地磁 (0x1A)
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    serial_number: Optional[int] = None  # RAWDATA_V2 序列号 (uint8_t)
    ms: Optional[int] = None  # RAWDATA_V2 毫秒数 (uint16_t)
    acc_scale: Optional[int] = None   # uint8_t
    reserved: Optional[List[int]] = field(default_factory=lambda: [0] * 7)  # uint8_t[7]

    acc_type: int = 0  # 类型 (uint8_t)
    arr_bit: int = 0  # 数组位 (uint8_t)
    arr_size: int = 0  # 数组大小 (uint16_t)
    freq: int = 0  # 频率 (uint16_t)
    tolerance: int = 0  # 容差 (uint8_t)
    data: List[int] = field(default_factory=lambda: [0] * 5)  # 数据 (uint8_t[5])
    acc_data: List[Tuple[int, int, int]] = field(default_factory=list)  # ACC 数据 (x, y, z)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        rawdata_v2: bool = True,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "ACC_Raw_Data":
        """
        从字节数据解析 ACC_Raw_Data
        
        Parameters:
        -----------
        data : bytes
            原始字节数据
        rawdata_v2 : bool
            是否为 RAWDATA_V2 格式
        unix_timestamp : int
            Unix 时间戳
        
        Returns:
        --------
        ACC_Raw_Data
            解析后的 ACC_Raw_Data 对象
        """
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            if rawdata_v2:
                values, offset = _unpack_from("<B H B 7B", data, offset)
                instance.serial_number = values[0]
                instance.ms = values[1]
                instance.acc_scale = values[2]
                instance.reserved = list(values[3:])

            common_values, offset = _unpack_from("<B B H H B 5B", data, offset)
            instance.acc_type = common_values[0]
            instance.arr_bit = common_values[1]
            instance.arr_size = common_values[2]
            instance.freq = common_values[3]
            instance.tolerance = common_values[4]
            instance.data = list(common_values[5:])

            acc_xyz_num = 105 if rawdata_v2 else 69
            acc_xyz_num = min(acc_xyz_num, instance.arr_size * 3)
            if acc_xyz_num > 0:
                fmt_ppg = f">{acc_xyz_num}H"
                raw_values, offset = _unpack_from(fmt_ppg, data, offset)
                signed_values = [value - 32768 for value in raw_values]
                instance.acc_data = list(
                    zip(signed_values[::3], signed_values[1::3], signed_values[2::3])
                )

        except struct.error as exc:
            logger.warning(f"解析ACC_Raw_Data失败: {exc}")

        return instance


@dataclass
class PPG_Raw_Data:
    """
    PPG 原始数据类
    用于绿光 (0x15)、红光 (0x16)、红外光 (0x17)、环境光 (0x33)
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    serial_number: Optional[int] = None  # RAWDATA_V2 序列号 (uint8_t)
    ms: Optional[int] = None  # RAWDATA_V2 毫秒数 (uint16_t)
    reserved: Optional[List[int]] = field(default_factory=lambda: [0] * 8)  # uint8_t[8]

    ppg_type: int = 0  # 类型 (uint8_t)
    arr_bit: int = 0  # 数组位 (uint8_t)
    arr_size: int = 0  # 数组大小 (uint16_t)
    freq: int = 0  # 频率 (uint16_t)
    tolerance: int = 0  # 容差 (uint8_t)
    data: List[int] = field(default_factory=lambda: [0] * 5)  # 数据 (uint8_t[5])
    ppg_data: List[int] = field(default_factory=list)  # PPG 数据数组 (uint32_t[PPG_NUM])

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        rawdata_v2: bool = True,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "PPG_Raw_Data":
        """
        从字节数据解析 PPG_Raw_Data
        
        Parameters:
        -----------
        data : bytes
            原始字节数据
        rawdata_v2 : bool
            是否为 RAWDATA_V2 格式
        unix_timestamp : int
            Unix 时间戳
        
        Returns:
        --------
        PPG_Raw_Data
            解析后的 PPG_Raw_Data 对象
        """
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            if rawdata_v2:
                values, offset = _unpack_from("<B H 8B", data, offset)
                instance.serial_number = values[0]
                instance.ms = values[1]
                instance.reserved = list(values[2:])

            common_values, offset = _unpack_from("<B B H H B 5B", data, offset)
            instance.ppg_type = common_values[0]
            instance.arr_bit = common_values[1]
            instance.arr_size = common_values[2]
            instance.freq = common_values[3]
            instance.tolerance = common_values[4]
            instance.data = list(common_values[5:])

            ppg_num = 52 if rawdata_v2 else 34
            ppg_num = min(ppg_num, instance.arr_size)
            if ppg_num > 0:
                fmt_ppg = f">{ppg_num}I"
                ppg_values, offset = _unpack_from(fmt_ppg, data, offset)
                ppg_values= list(ppg_values)
                instance.ppg_data = [value - 1_000_000 for value in ppg_values]
        except struct.error as exc:
            logger.warning(f"解析PPG_Raw_Data失败: {exc}")

        return instance

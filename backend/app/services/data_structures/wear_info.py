"""
佩戴检测相关数据结构
Wear detection and motion recognition data structures
"""

import struct
from typing import Optional
from dataclasses import dataclass
from . import _unpack_from
from app.core.logger import logger


@dataclass
class MotionRecognition:
    """
    运动识别数据类 (0x69)
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    error_code: int = 0  # uint8_t 错误码
    init_timer: int = 0  # uint32_t 用来检测是否调用初始化的参数
    motion_type_ring: int = 0  # uint8_t 运动类型 motion_type_t
    detection_state: int = 0  # uint8_t 识别状态：未检测/疑似/确认/暂停/恢复/结束
    activity_motion_time_ring: int = 0  # uint32_t 活动运动时间(秒)
    auto_detect_state: int = 0  # uint8_t 自动识别内部状态
    instant_type: int = 0  # uint8_t
    hr_rising: int = 0  # uint8_t
    hr_avg: int = 0  # uint8_t
    steps_per_minute: int = 0  # uint16_t
    acc_feature: int = 0  # uint16_t
    avg_activity_level: int = 0   # uint32_t
    wear_flag_ring: int = 0  # uint8_t
    unworn_seconds: int = 0  # uint16_t

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        unix_timestamp: int = 0,
        timestamp: str = "",
        offset: int = 0,
    ) -> "MotionRecognition":
        """
        从字节数据解析 MotionRecognition
        
        Parameters:
        -----------
        data : bytes
            原始字节数据
        unix_timestamp : int
            Unix 时间戳
        offset : int
            起始偏移量
        
        Returns:
        --------
        MotionRecognition
            解析后的 MotionRecognition 对象
        """
        offset = offset
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            values, offset = _unpack_from("<B I B B I B B B B H H I B H", data, offset)
            (
                instance.error_code,
                instance.init_timer,
                instance.motion_type_ring,
                instance.detection_state,
                instance.activity_motion_time_ring,
                instance.auto_detect_state,
                instance.instant_type,
                instance.hr_rising,
                instance.hr_avg,
                instance.steps_per_minute,
                instance.acc_feature,
                instance.avg_activity_level,
                instance.wear_flag_ring,
                instance.unworn_seconds,
            ) = values

        except struct.error as exc:
            logger.warning(f"解析MotionRecognition失败: {exc}")

        return instance




# uint8_t wear_flag;            // 0未佩戴,1佩戴,9检测中
# uint8_t error_no;             // 0表示没有异常,1输入的数据有问题
# uint8_t wear_ir_result;       // 红外的判断结果
# uint8_t confusion;            // 混淆熵特征
# uint8_t peak_cnt ;            // 波峰个数
# uint8_t wear_rr_hr;           // 根据时域ppg的波峰计算出的心率值
# uint16_t wear_acc_std;        // 根据acc计算的std,判断运动的特征
# uint8_t return_type;          // 结果返回的类型
# uint16_t green_temp_flag_encode;      // 绿灯判断的结果的二进制编码形式
# uint8_t init_timer;           // 用来检测是否调用初始化的参数
# int32_t amb_std;
# int32_t ppg_dc_value;        // 根据ppg计算的dc

# uint8_t state;                    // 内部状态
# uint8_t imu_6d_state;             // 6D状态
# uint16_t ppg_g_current;           // 绿灯电流
# uint16_t ppg_g_idac;              // 绿灯 偏置
# int32_t ppg_ir_value;             // IR 的 dc
# uint16_t wear_acc_momentum;       // 根据acc计算的运动的特征
# uint32_t entropy_geometric;       // 熵特征
# uint16_t zero_crossing_rate;      // 过零率
# uint8_t wear_green_result;    // 绿灯的判断结果
# uint8_t wear_ambient_result;  // 环境光的判断结果
@dataclass
class WearInfo:
    """
    佩戴信息数据类 (0x71)
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    serial_number: Optional[int] = None  # RAWDATA_V2 only
    reserved: Optional[bytes] = None  # RAWDATA_V2 only

    wear_flag: int = 0  # 0未佩戴,1佩戴,9检测中 uint8_t
    error_no: int = 0  # 0表示没有异常,1输入的数据有问题 uint8_t
    wear_ir_result: int = 0  # 红外的判断结果 uint8_t
    confusion: int = 0  # 混淆熵特征 uint8_t
    peak_cnt: int = 0  # 波峰个数 uint8_t
    wear_rr_hr: int = 0  # 根据时域ppg的波峰计算出的心率值 uint8_t
    wear_acc_std: int = 0  # 根据acc计算的std,判断运动的特征 uint16_t
    return_type: int = 0  # 结果返回的类型 uint8_t
    green_temp_flag_encode: int = 0  # 绿灯判断的结果的二进制编码形式 uint16_t
    init_timer: int = 0  # 用来检测是否调用初始化的参数 uint8_t
    amb_std: int = 0  #  根据环境光计算的std int32_t

    ppg_dc_value: int = 0  # 根据ppg计算的dc int32_t
    state: int = 0        # 内部佩戴状态 uint8_t
    imu_6d_state: int = 0  # 6d状态 uint8_t
    ppg_g_current: int = 0      #绿灯电流 uint16_t
    ppg_g_idac: int = 0        #绿灯 偏置  uint16_t
    ppg_ir_value: int = 0      #红外值 int32_t
    wear_acc_momentum: int = 0   # 根据acc计算的运动的特征 uint16_t
    entropy_geometric: int = 0   # 熵特征 uint32_t
    zero_crossing_rate: int = 0  # 过零率 uint16_t
    wear_green_result: int = 0   # 绿灯的判断结果 uint8_t
    wear_ambient_result: int = 0  # 环境光的判断结果 uint8_t


    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        rawdata_v2: bool,
        unix_timestamp: int,
        timestamp: str = "",
    ) -> "WearInfo":
        """
        从字节数据解析 WearInfo
        
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
        WearInfo
            解析后的 WearInfo 对象
        """
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            if rawdata_v2:
                (serial_number,), offset = _unpack_from("<B", data, offset)
                instance.serial_number = serial_number
                instance.reserved = data[offset:offset + 10]
                offset += 10

            values, offset = _unpack_from("<6B H B H B i i ", data, offset)
            (
                instance.wear_flag,
                instance.error_no,
                instance.wear_ir_result,
                instance.confusion,
                instance.peak_cnt,
                instance.wear_rr_hr,
                instance.wear_acc_std,
                instance.return_type,
                instance.green_temp_flag_encode,
                instance.init_timer,
                instance.amb_std,
                instance.ppg_dc_value,
            ) = values

            # 解析绿灯电流和偏置
            values, offset = _unpack_from("<B B H H i ", data, offset)
            (
                instance.state,
                instance.imu_6d_state,
                instance.ppg_g_current,
                instance.ppg_g_idac,
                instance.ppg_ir_value,
            ) = values

            # 解析剩余字段
            values, offset = _unpack_from("<H I H B B", data, offset)
            (
                instance.wear_acc_momentum,
                instance.entropy_geometric,
                instance.zero_crossing_rate,
                instance.wear_green_result,
                instance.wear_ambient_result,
            ) = values

        except struct.error as exc:
            logger.warning(f"解析WearInfo失败: {exc}")

        return instance

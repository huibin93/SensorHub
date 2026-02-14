"""
基础信息数据结构
BaseInfo data structure (0x00)
"""

import struct
from typing import List, Optional
from dataclasses import dataclass, field
from . import _unpack_from
from app.core.logger import logger


@dataclass
class BaseInfo:
    """
    基础信息数据类 (0x00)
    包含用户基本信息、心率、步数、血氧等综合数据
    """
    timestamp:str = ""
    unix_timestamp: int = 0
    label_hr: int = 0
    
    # 启用 RAWDATA_V2 时的字段
    serial_number: Optional[int] = None  # uint8_t
    reserved: Optional[List[int]] = None  # uint8_t[10]

    label: int = 0  # uint8_t
    heart_rate_band: int = 0  # uint8_t
    birth_year: int = 0  # uint16_t
    birth_mouth: int = 0  # uint8_t
    birth_day: int = 0  # uint8_t
    gender: int = 0  # uint8_t
    heigh: int = 0  # uint16_t
    weight: int = 0  # uint16_t
    activity_level: int = 0  # uint8_t
    heart_rate: int = 0  # uint8_t
    step: int = 0  # uint32_t
    spo2: int = 0  # uint8_t
    stress: int = 0  # uint8_t
    noise: int = 0  # uint8_t
    activity_kacl: int = 0  # uint16_t
    BMR_kacl: int = 0  # uint16_t
    exercise_duration: int = 0  # uint8_t
    stand_hour: int = 0  # uint8_t
    wear_flag: int = 0  # uint8_t
    screen_state: int = 0  # uint8_t
    gesture_label: int = 0  # uint8_t
    step_freq: int = 0  # uint16_t
    distance: int = 0  # uint32_t
    sleep_time: int = 0  # uint32_t
    getup_time: int = 0  # uint32_t
    orientation_flag: int = 0  # uint8_t
    sport_type: int = 0  # uint8_t
    max_oxygen_uptake: int = 0  # uint8_t
    tyhx_data: List[int] = field(default_factory=lambda: [0] * 20)  # uint8_t[20]

    acc_xyz: List[int] = field(default_factory=lambda: [0] * 9)  # int16_t[9]
    acc_reg: List[int] = field(default_factory=lambda: [0] * 3)  # uint8_t[3]
    update_count: int = 0  # uint8_t
    update_sch_count: int = 0  # uint8_t
    fifo_size: int = 0  # uint8_t
    timer_flag: int = 0  # uint8_t
    sleep_state: int = 0  # uint8_t
    sleep_dida_time: int = 0  # uint16_t
    stress_switch: int = 0  # uint8_t
    ntc_temperature: int = 0  # uint8_t
    one_sec_distance: int = 0  # uint32_t
    qual_value: int = 0  # uint8_t
    heartrate_measure_flag: int = 0  # uint8_t
    sport_state: int = 0  # uint8_t
    static_heartrate: int = 0  # uint8_t
    is_tachycardia: int = 0  # uint8_t
    spo2_motion: int = 0  # uint8_t
    motor_vibration_flag: int = 0  # uint8_t
    power_average_sec: int = 0  # uint16_t
    mets: int = 0  # uint8_t
    sport_mode: int = 0  # uint8_t
    floors_climb: int = 0  # uint16_t
    lift_total: int = 0  # uint32_t
    decent_total: int = 0  # uint32_t
    space: int = 0  # uint32_t
    interval: int = 0  # uint16_t
    exercise_type: int = 0  # uint8_t 锻炼类型

    @classmethod
    def from_bytes(cls, data: bytes, rawdata_v2: bool = True, label_hr: int = 0, unix_timestamp: int = 0, timestamp: str = "") -> "BaseInfo":
        """
        从字节数据解析 BaseInfo
        
        Parameters:
        -----------
        data : bytes
            原始字节数据
        rawdata_v2 : bool
            是否为 RAWDATA_V2 格式
        label_hr : int
            标签心率
        unix_timestamp : int
            Unix 时间戳
        
        Returns:
        --------
        BaseInfo
            解析后的 BaseInfo 对象
        """
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, label_hr=label_hr, timestamp=timestamp)

        try:
            if rawdata_v2:
                values, offset = _unpack_from("<B10B", data, offset)
                instance.serial_number = values[0]
                instance.reserved = list(values[1:])

            part1, offset = _unpack_from(
                "<B B H B B B H H B B I B B B H H B B B B B H I I I B B B",
                data,
                offset,
            )
            (
                instance.label,
                instance.heart_rate_band,
                instance.birth_year,
                instance.birth_mouth,
                instance.birth_day,
                instance.gender,
                instance.heigh,
                instance.weight,
                instance.activity_level,
                instance.heart_rate,
                instance.step,
                instance.spo2,
                instance.stress,
                instance.noise,
                instance.activity_kacl,
                instance.BMR_kacl,
                instance.exercise_duration,
                instance.stand_hour,
                instance.wear_flag,
                instance.screen_state,
                instance.gesture_label,
                instance.step_freq,
                instance.distance,
                instance.sleep_time,
                instance.getup_time,
                instance.orientation_flag,
                instance.sport_type,
                instance.max_oxygen_uptake,
            ) = part1

            tyhx_values, offset = _unpack_from("<20B", data, offset)
            instance.tyhx_data = list(tyhx_values)

            acc_xyz_values, offset = _unpack_from("<9h", data, offset)
            instance.acc_xyz = list(acc_xyz_values)

            acc_reg_values, offset = _unpack_from("<3B", data, offset)
            instance.acc_reg = list(acc_reg_values)

            rest_values, offset = _unpack_from(
                "<B B B B B H B B I B B B B B B B H B B H I I I H B",
                data,
                offset,
            )
            (
                instance.update_count,
                instance.update_sch_count,
                instance.fifo_size,
                instance.timer_flag,
                instance.sleep_state,
                instance.sleep_dida_time,
                instance.stress_switch,
                instance.ntc_temperature,
                instance.one_sec_distance,
                instance.qual_value,
                instance.heartrate_measure_flag,
                instance.sport_state,
                instance.static_heartrate,
                instance.is_tachycardia,
                instance.spo2_motion,
                instance.motor_vibration_flag,
                instance.power_average_sec,
                instance.mets,
                instance.sport_mode,
                instance.floors_climb,
                instance.lift_total,
                instance.decent_total,
                instance.space,
                instance.interval,
                instance.exercise_type,
            ) = rest_values

        except struct.error as exc:
            logger.warning(f"解析BaseInfo失败: {exc}")

        return instance

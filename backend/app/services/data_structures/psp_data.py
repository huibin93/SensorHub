"""
PSP (Pulse Signal Processing) 相关数据结构

包含用于解析 PSP PPG FIFO 和 CREEK 心率数据的类定义。
"""

import struct
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from . import _unpack_from
from app.core.logger import logger



@dataclass
class PSP_PPG_FIFO:
    """
    PSP PPG FIFO 数据结构 (0x91)
    
    用于解析 PSP(Pulse Signal Processing)PPG(Photoplethysmography)FIFO 数据。
    包含心率、血氧、呼吸等生理指标以及原始 PPG 数据。

    #pragma pack(1)
    typedef struct{
        uint8_t serial_number;							//序列号
        uint8_t psp_index;								//序列号
        uint8_t psp_id;									//ID
        uint8_t offset;									//offset
        uint8_t exponent;								//exponent	
        uint16_t ms;
        uint8_t rhr;							
        uint8_t rhr_qual;							
        uint8_t breathe;							
        uint8_t breathe_qual;							
        uint8_t cnt;
        uint8_t hr;
        uint8_t hr_qual;
        uint8_t spo2;
        uint8_t spo2_qual;
        uint16_t ppg_data[32];
        uint8_t adcgain[4];
        uint8_t ppg_g_quality; // 信号质量,但目前为0
        uint8_t heartrate; // 心率值
        uint8_t is_valid; //
    } psp_ppg_fifo_t;
    #pragma pack()

    Attributes:
        unix_timestamp: Unix 时间戳
        serial_number: 序列号(仅 rawdata_v2)
        psp_index: PSP 索引(仅 rawdata_v2)
        psp_id: PSP ID(仅 rawdata_v2)
        offset: 偏移量(仅 rawdata_v2)
        exponent: 指数(仅 rawdata_v2)
        ms: 毫秒(仅 rawdata_v2)
        rhr: 静息心率(仅 rawdata_v2)
        rhr_qual: 静息心率质量(仅 rawdata_v2)
        breathe: 呼吸率(仅 rawdata_v2)
        breathe_qual: 呼吸率质量(仅 rawdata_v2)
        cnt: 计数
        hr: 心率
        hr_qual: 心率质量
        spo2: 血氧饱和度
        spo2_qual: 血氧质量
        ppg_data: PPG 原始数据(32个数据点)
        adcgain: ADC 增益(4个通道)
        ppg_g_quality: PPG 信号质量
        heartrate: 心率值
        is_valid: 数据有效性标志
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    serial_number: Optional[int] = None
    psp_index: Optional[int] = None
    psp_id: Optional[int] = None
    offset: Optional[int] = None
    exponent: Optional[int] = None
    ms: Optional[int] = None
    rhr: Optional[int] = None
    rhr_qual: Optional[int] = None
    breathe: Optional[int] = None
    breathe_qual: Optional[int] = None

    cnt: int = 0
    hr: int = 0
    hr_qual: int = 0
    spo2: int = 0
    spo2_qual: int = 0
    ppg_data: List[int] = field(default_factory=lambda: [0] * 32)
    adcgain: List[int] = field(default_factory=lambda: [0] * 4)
    ppg_g_quality: int = 0
    heartrate: int = 0
    is_valid: int = 0

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        rawdata_v2: bool = True,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "PSP_PPG_FIFO":
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            if rawdata_v2:
                values, offset = _unpack_from("<BBBBBHBBBB", data, offset)
                (
                    instance.serial_number,
                    instance.psp_index,
                    instance.psp_id,
                    instance.offset,
                    instance.exponent,
                    instance.ms,
                    instance.rhr,
                    instance.rhr_qual,
                    instance.breathe,
                    instance.breathe_qual,
                ) = values

            common_values, offset = _unpack_from("<BBBBB", data, offset)
            (
                instance.cnt,
                instance.hr,
                instance.hr_qual,
                instance.spo2,
                instance.spo2_qual,
            ) = common_values

            ppg_values, offset = _unpack_from("<32H", data, offset)
            instance.ppg_data = list(ppg_values)

            adcgain_values, offset = _unpack_from("<4B", data, offset)
            instance.adcgain = list(adcgain_values)

            (instance.ppg_g_quality, instance.heartrate), offset = _unpack_from("<BB", data, offset)
            (instance.is_valid,), offset = _unpack_from("<B", data, offset)

        except struct.error as exc:
            logger.warning(f"解析PSP_PPG_FIFO失败: {exc}")

        return instance


# CREEK_HR_INFO 0x99
@dataclass
class CREEK_HR_Data:
    """
    CREEK 心率数据结构 (0x99)
    
    用于解析 CREEK 心率算法的输出数据。
    包含心率、运动状态、步频、距离、信号质量等综合信息。
    
    Attributes:
        unix_timestamp: Unix 时间戳
        serial_number: 序列号(仅 rawdata_v2)
        reserved: 保留字段(仅 rawdata_v2)
        code: 代码
        ppg_size: PPG 数据大小
        ppg_channel: PPG 通道
        acc_size: 加速度计数据大小
        activity_level: 活动水平
        test_mode: 测试模式
        sport_type: 运动类型
        wear_flag: 佩戴标志
        step_freq: 步频
        distance_cm: 距离(厘米)
        gnss_enable: GNSS 启用标志
        philips_hr_activity: Philips 活动心率
        philips_hr_qi_activity: Philips 活动心率质量
        barograph_altitude_cm: 气压计高度(厘米)
        reserved_2: 保留字段2
        ppg_g_quality: PPG 绿光质量
        heartrate: 心率
        is_valid: 数据有效性
        sport_time: 运动时间
        xyz_momentum: XYZ 动量
        step_freq_result: 步频结果
        avg_distance_cm: 平均距离(厘米)
        speed_perkm: 速度(每公里)
        philips_hr_result: Philips 心率结果
        philips_hr_qi_result: Philips 心率质量结果
        init_heartrate: 初始心率
        tcn_heartrate: TCN 心率
        current_distance_cm: 当前距离(厘米)
        signal_status: 信号状态
        no_confidence_score: 无信心分数
        batter_signal_heartrate: 更好信号心率
        max_signal_heartrate: 最大信号心率
        acc_main_freq: 加速度计主频
        result_type: 结果类型
        signal_type: 信号类型
        up_down_status: 上下状态
        ppg_peaks_cnt: PPG 峰值计数
        acc_peaks_cnt: 加速度计峰值计数
    """
    timestamp: str = ""
    unix_timestamp: int = 0

    serial_number: Optional[int] = None
    reserved: Optional[List[int]] = field(default_factory=lambda: [0] * 10)

    code: int = 0
    ppg_size: int = 0
    ppg_channel: int = 0
    acc_size: int = 0

    activity_level: int = 0
    test_mode: int = 0
    sport_type: int = 0
    wear_flag: int = 0
    step_freq: int = 0
    distance_cm: int = 0
    gnss_enable: int = 0
    philips_hr_activity: int = 0
    philips_hr_qi_activity: int = 0
    barograph_altitude_cm: int = 0

    reserved_2: List[int] = field(default_factory=lambda: [0] * 20)

    ppg_g_quality: int = 0
    heartrate: int = 0
    is_valid: int = 0
    sport_time: int = 0
    xyz_momentum: int = 0
    step_freq_result: int = 0
    avg_distance_cm: int = 0
    speed_perkm: int = 0
    philips_hr_result: int = 0
    philips_hr_qi_result: int = 0
    init_heartrate: int = 0
    tcn_heartrate: int = 0
    current_distance_cm: int = 0
    signal_status: int = 0

    no_confidence_score: int = 0
    batter_signal_heartrate: int = 0
    max_signal_heartrate: int = 0
    acc_main_freq: int = 0
    result_type: int = 0
    signal_type: int = 0
    up_down_status: int = 0
    ppg_peaks_cnt: int = 0
    acc_peaks_cnt: int = 0

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        rawdata_v2: bool = True,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "CREEK_HR_Data":
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            if rawdata_v2:
                values, offset = _unpack_from("<B10B", data, offset)
                instance.serial_number = values[0]
                instance.reserved = list(values[1:])

            main_values, offset = _unpack_from("<BBBB", data, offset)
            (
                instance.code,
                instance.ppg_size,
                instance.ppg_channel,
                instance.acc_size,
            ) = main_values

            activity_values, offset = _unpack_from("<5BI3Bi", data, offset)
            (
                instance.activity_level,
                instance.test_mode,
                instance.sport_type,
                instance.wear_flag,
                instance.step_freq,
                instance.distance_cm,
                instance.gnss_enable,
                instance.philips_hr_activity,
                instance.philips_hr_qi_activity,
                instance.barograph_altitude_cm,
            ) = activity_values

            reserved2_values, offset = _unpack_from("<20B", data, offset)
            instance.reserved_2 = list(reserved2_values)

            result_values, offset = _unpack_from("<BBBIIBIIBBBBIB", data, offset)
            (
                instance.ppg_g_quality,
                instance.heartrate,
                instance.is_valid,
                instance.sport_time,
                instance.xyz_momentum,
                instance.step_freq_result,
                instance.avg_distance_cm,
                instance.speed_perkm,
                instance.philips_hr_result,
                instance.philips_hr_qi_result,
                instance.init_heartrate,
                instance.tcn_heartrate,
                instance.current_distance_cm,
                instance.signal_status,
            ) = result_values

            tracker_values, offset = _unpack_from("<HBBBBBbbb", data, offset)
            (
                instance.no_confidence_score,
                instance.batter_signal_heartrate,
                instance.max_signal_heartrate,
                instance.acc_main_freq,
                instance.result_type,
                instance.signal_type,
                instance.up_down_status,
                instance.ppg_peaks_cnt,
                instance.acc_peaks_cnt,
            ) = tracker_values

        except struct.error as exc:
            logger.warning(f"解析CREEK_HR_Data失败: {exc}")

        return instance

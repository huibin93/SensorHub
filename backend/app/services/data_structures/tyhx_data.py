"""
TYHX数据结构模块

包含TYHX传感器相关的数据类：
- TYHX_PPG_Data (0x81): PPG数据结构
- TYHX_AGC_Data (0x82): AGC数据结构
"""

import struct
from typing import List
from dataclasses import dataclass, field
from . import _unpack_from
from app.core.logger import logger


@dataclass
class TYHX_PPG_Data:
    """
    TYHX PPG数据类 (数据类型: 0x81)
    
    包含PPG传感器的完整数据,包括：
    - 电流设置 (current)
    - 偏移电流 (offset_idac)
    - 心率和血氧数据
    - AGC (自动增益控制) 参数
    
    Attributes:
        unix_timestamp: Unix时间戳
        green_current: 绿光LED电流
        green2_current: 绿光LED2电流
        red_current: 红光LED电流
        infra_current: 红外LED电流
        green_offset_idac: 绿光偏移电流
        green2_offset_idac: 绿光2偏移电流
        red_offset_idac: 红光偏移电流
        infra_offset_idac: 红外偏移电流
        infra3_current: 红外3电流
        infra3_tia: 红外3 TIA
        infra3_offset_idac: 红外3偏移电流
        heart_rate: 心率值
        spo2: 血氧值
        hrs_alg_status: 心率算法状态
        living_status: 生命体征状态
        data_cnt: 数据计数
        hr_result: 心率结果
        cal_result: 校准结果
        hr_result_qual: 心率结果质量
        hr_result_std: 心率结果标准差
        hr_mode: 心率模式
        motion: 运动状态
        motion_pow: 运动功率
        agc_FLAG: AGC标志
        agc_LED0_IDAC: LED0 IDAC
        agc_LED1_IDAC: LED1 IDAC
        agc_LED2_IDAC: LED2 IDAC
        agc_LED3_IDAC: LED3 IDAC
        agc_AMB0_IDAC: 环境光0 IDAC
        agc_AMB1_IDAC: 环境光1 IDAC
        agc_AMB2_IDAC: 环境光2 IDAC
        agc_AMB3_IDAC: 环境光3 IDAC
        agc_LED0_CUR: LED0电流
        agc_LED1_CUR: LED1电流
        agc_LED2_CUR: LED2电流
        agc_LED3_CUR: LED3电流
        agc_LED0_RF: LED0 RF
        agc_LED1_RF: LED1 RF
        agc_LED2_RF: LED2 RF
        agc_LED3_RF: LED3 RF
        agc_LED0_STEP: LED0步进
        agc_LED1_STEP: LED1步进
        agc_LED2_STEP: LED2步进
        agc_LED3_STEP: LED3步进
        agc_CAL_DELAY_CNT: AGC校准延迟计数
        agc_STATE: AGC状态
        agc_buf: AGC缓冲区 (8个整数)
    """
    timestamp: str = ""
    unix_timestamp: int = 0

    green_current: int = 0   # offet 0 
    green2_current: int = 0   
    red_current: int = 0
    infra_current: int = 0
    green_offset_idac: int = 0
    green2_offset_idac: int = 0
    red_offset_idac: int = 0
    infra_offset_idac: int = 0
    infra3_current: int = 0
    infra3_tia: int = 0
    infra3_offset_idac: int = 0

    heart_rate: int = 0
    spo2: int = 0
    hrs_alg_status: int = 0
    living_status: int = 0
    data_cnt: int = 0
    hr_result: int = 0
    cal_result: int = 0
    hr_result_qual: int = 0
    hr_result_std: int = 0
    hr_mode: int = 0
    motion: int = 0
    motion_pow: int = 0

    agc_FLAG: int = 0   
    agc_LED0_IDAC: int = 0 
    agc_LED1_IDAC: int = 0
    agc_LED2_IDAC: int = 0
    agc_LED3_IDAC: int = 0
    agc_AMB0_IDAC: int = 0
    agc_AMB1_IDAC: int = 0
    agc_AMB2_IDAC: int = 0
    agc_AMB3_IDAC: int = 0
    agc_LED0_CUR: int = 0
    agc_LED1_CUR: int = 0
    agc_LED2_CUR: int = 0
    agc_LED3_CUR: int = 0
    agc_LED0_RF: int = 0
    agc_LED1_RF: int = 0
    agc_LED2_RF: int = 0
    agc_LED3_RF: int = 0
    agc_LED0_STEP: int = 0
    agc_LED1_STEP: int = 0
    agc_LED2_STEP: int = 0
    agc_LED3_STEP: int = 0
    agc_CAL_DELAY_CNT: int = 0
    agc_STATE: int = 0

    agc_buf: List[int] = field(default_factory=lambda: [0] * 8)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "TYHX_PPG_Data":
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            format_string = "<15B"

            values, offset = _unpack_from(format_string, data, offset)
            (
            instance.green_current,   # offet 0 
            instance.green2_current,   
            instance.red_current,
            instance.infra_current,
            instance.green_offset_idac,
            instance.green2_offset_idac,
            instance.red_offset_idac,
            instance.infra_offset_idac,
            instance.infra3_current,
            instance.infra3_tia,
            instance.infra3_offset_idac,
            instance.heart_rate,
            instance.spo2,
            instance.hrs_alg_status,
            instance.living_status 
            ) = values

            format_string =  "< I B H B I B B I"
            values, offset = _unpack_from(format_string, data, offset)
            ( instance.data_cnt,
              instance.hr_result,
              instance.cal_result,
              instance.hr_result_qual,
              instance.hr_result_std,
              instance.hr_mode,
              instance.motion,
              instance.motion_pow) = values

            format_string = "< B "
            values, offset = _unpack_from(format_string, data, offset)
            (instance.agc_FLAG,) = values
            offset += 1

            # Check if offset is aligned with expected position
            if offset != 35:
                raise ValueError(f"Offset misaligned before agc_LED0_IDAC. Expected 32, got {offset}")
            

            format_string = "< 12H 4B"        
            values, offset = _unpack_from(format_string, data, offset)
            (
              instance.agc_LED0_IDAC, 
              instance.agc_LED1_IDAC,
              instance.agc_LED2_IDAC,
              instance.agc_LED3_IDAC,
              instance.agc_AMB0_IDAC,
              instance.agc_AMB1_IDAC,
              instance.agc_AMB2_IDAC,
              instance.agc_AMB3_IDAC,
              instance.agc_LED0_CUR,
              instance.agc_LED1_CUR,
              instance.agc_LED2_CUR,
              instance.agc_LED3_CUR,
              instance.agc_LED0_RF,
              instance.agc_LED1_RF,
              instance.agc_LED2_RF,
              instance.agc_LED3_RF,
            ) = values
            offset += 2

            format_string = "< 4I B B"
            values, offset = _unpack_from(format_string, data, offset)
            ( instance.agc_LED0_STEP,
              instance.agc_LED1_STEP,
              instance.agc_LED2_STEP,
              instance.agc_LED3_STEP,
              instance.agc_CAL_DELAY_CNT,
              instance.agc_STATE
            ) = values

            offset += 2
            format_string = "<8i"
            values, offset = _unpack_from(format_string, data, offset)
            instance.agc_buf = list(values)

        except (struct.error, ValueError) as exc:
            logger.warning(f"解析TYHX_PPG_Data失败: {exc}")

        return instance


@dataclass
class TYHX_AGC_Data:
    """
    TYHX AGC数据类 (数据类型: 0x82)
    
    包含AGC (自动增益控制) 的完整参数配置。
    
    Attributes:
        unix_timestamp: Unix时间戳
        flag: AGC标志
        led0_idac: LED0 IDAC值
        led1_idac: LED1 IDAC值
        led2_idac: LED2 IDAC值
        led3_idac: LED3 IDAC值
        amb0_idac: 环境光0 IDAC值
        amb1_idac: 环境光1 IDAC值
        amb2_idac: 环境光2 IDAC值
        amb3_idac: 环境光3 IDAC值
        led0_cur: LED0电流值
        led1_cur: LED1电流值
        led2_cur: LED2电流值
        led3_cur: LED3电流值
        led0_rf: LED0反馈电阻
        led1_rf: LED1反馈电阻
        led2_rf: LED2反馈电阻
        led3_rf: LED3反馈电阻
        led0_step: LED0步进值
        led1_step: LED1步进值
        led2_step: LED2步进值
        led3_step: LED3步进值
        cal_delay_cnt: 校准延迟计数
        state: AGC状态
        agc_buf: AGC缓冲区 (8个整数)
    """
    timestamp: str = ""
    unix_timestamp: int = 0

    flag: int = 0
    led0_idac: int = 0
    led1_idac: int = 0
    led2_idac: int = 0
    led3_idac: int = 0
    amb0_idac: int = 0
    amb1_idac: int = 0
    amb2_idac: int = 0
    amb3_idac: int = 0
    led0_cur: int = 0
    led1_cur: int = 0
    led2_cur: int = 0
    led3_cur: int = 0
    led0_rf: int = 0
    led1_rf: int = 0
    led2_rf: int = 0
    led3_rf: int = 0
    led0_step: int = 0
    led1_step: int = 0
    led2_step: int = 0
    led3_step: int = 0
    cal_delay_cnt: int = 0
    state: int = 0
    agc_buf: List[int] = field(default_factory=lambda: [0] * 8)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "TYHX_AGC_Data":
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            (instance.flag,), offset = _unpack_from("<B", data, offset)

            led_idac_values, offset = _unpack_from("<4H", data, offset)
            (
                instance.led0_idac,
                instance.led1_idac,
                instance.led2_idac,
                instance.led3_idac,
            ) = led_idac_values

            amb_idac_values, offset = _unpack_from("<4H", data, offset)
            (
                instance.amb0_idac,
                instance.amb1_idac,
                instance.amb2_idac,
                instance.amb3_idac,
            ) = amb_idac_values

            led_cur_values, offset = _unpack_from("<4H", data, offset)
            (
                instance.led0_cur,
                instance.led1_cur,
                instance.led2_cur,
                instance.led3_cur,
            ) = led_cur_values

            led_rf_values, offset = _unpack_from("<4B", data, offset)
            (
                instance.led0_rf,
                instance.led1_rf,
                instance.led2_rf,
                instance.led3_rf,
            ) = led_rf_values

            led_step_values, offset = _unpack_from("<4I", data, offset)
            (
                instance.led0_step,
                instance.led1_step,
                instance.led2_step,
                instance.led3_step,
            ) = led_step_values

            (instance.cal_delay_cnt,), offset = _unpack_from("<B", data, offset)
            (instance.state,), offset = _unpack_from("<B", data, offset)

            buf_values, offset = _unpack_from("<8i", data, offset)
            instance.agc_buf = list(buf_values)

        except struct.error as exc:
            logger.warning(f"解析TYHX_AGC_Data失败: {exc}")

        return instance



@dataclass
class TYHX_3697_Data:
    """
    TYHX 3697数据类 (数据类型: 0x82)
    
    包含3697传感器的AGC数据结构。
    
    Attributes:
        unix_timestamp: Unix时间戳
        cur: 调光后的电流 (8个uint8_t)
        rx1_offset: 调光后RX1的LED_OFFSET (8个uint8_t)
        rx2_offset: 调光后RX2的LED_OFFSET (8个uint8_t)
        rx1_rf: 调光后的RX1实际增益大小 (8个uint8_t)
        rx2_rf: 调光后的RX2实际增益大小 (8个uint8_t)
        rx1_led_step: 调光时的RX1 LED步长 (8个int32_t)
        rx2_led_step: 调光时的RX2 LED步长 (8个int32_t)
    """
    timestamp: str = ""
    unix_timestamp: int = 0
    cur: List[int] = field(default_factory=lambda: [0] * 8)
    rx1_offset: List[int] = field(default_factory=lambda: [0] * 8)
    rx2_offset: List[int] = field(default_factory=lambda: [0] * 8)
    rx1_rf: List[int] = field(default_factory=lambda: [0] * 8)
    rx2_rf: List[int] = field(default_factory=lambda: [0] * 8)
    rx1_led_step: List[int] = field(default_factory=lambda: [0] * 8)
    rx2_led_step: List[int] = field(default_factory=lambda: [0] * 8)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        unix_timestamp: int = 0,
        timestamp: str = "",
    ) -> "TYHX_3697_Data":
        offset = 0
        instance = cls(unix_timestamp=unix_timestamp, timestamp=timestamp)

        try:
            # CUR: 8个uint8_t
            values, offset = _unpack_from("<8B", data, offset)
            instance.cur = list(values)

            # RX1_OFFSET: 8个uint8_t
            values, offset = _unpack_from("<8B", data, offset)
            instance.rx1_offset = list(values)

            # RX2_OFFSET: 8个uint8_t
            values, offset = _unpack_from("<8B", data, offset)
            instance.rx2_offset = list(values)

            # RX1_RF: 8个uint8_t
            values, offset = _unpack_from("<8B", data, offset)
            instance.rx1_rf = list(values)

            # RX2_RF: 8个uint8_t
            values, offset = _unpack_from("<8B", data, offset)
            instance.rx2_rf = list(values)

            # RX1_LED_STEP: 8个int32_t
            values, offset = _unpack_from("<8i", data, offset)
            instance.rx1_led_step = list(values)

            # RX2_LED_STEP: 8个int32_t
            values, offset = _unpack_from("<8i", data, offset)
            instance.rx2_led_step = list(values)

        except (struct.error, ValueError) as exc:
            logger.warning(f"解析TYHX_3697_Data失败: {exc}")

        return instance

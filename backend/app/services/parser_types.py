"""解析类型定义 & 传感器通道注册表。

集中维护：
- 数据类型十六进制枚举;
- 手表/戒指的数据类型英文/中文映射;
- IPC 用 TypedDict (FrameMeta, BatchMeta, WorkerInput, WorkerOutput);
- SensorChannel 注册表 & 派生查找表。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, TypedDict


class FrameMeta(TypedDict):
    cs: int
    cl: int
    dl: int
    nl: bool


class BatchMeta(TypedDict):
    batch_id: int
    start_frame_idx: int
    end_frame_idx: int
    compressed_bytes: int
    frames: list[FrameMeta]


class WorkerInput(TypedDict):
    raw_path: str
    batch: BatchMeta
    is_ring: bool


class WorkerOutput(TypedDict):
    batch_id: int
    result: dict  # 注册表驱动的 {list_key: [...], "labels": [...], "data_types": {...}}


class DataType(str, Enum):
    BASE_INFO = "00"
    RAW_PPG_DAC = "14"
    RAW_PPG_GREEN = "15"
    RAW_PPG_RED = "16"
    RAW_PPG_IR = "17"
    RAW_ACC = "18"
    RAW_GYRO = "19"
    RAW_GEOM = "1A"
    RAW_PPG_SAR = "1B"
    RAW_ECG = "1C"
    RAW_EDA = "1D"
    RAW_BIA = "1E"
    RAW_UV = "1F"
    RAW_BLUE = "20"
    RAW_ACC_TO_PPG = "21"
    RAW_PPG_RED_IR = "26"
    RAW_GPS = "32"
    AMBIENT_INFO = "33"
    SLEEP_INFO = "67"
    HRV_INFO = "68"
    MOTION_INFO = "69"
    SWIMMING_INFO = "70"
    WEAR_INFO = "71"
    HEART_GSEN_X_INFO = "72"
    HEART_GSEN_Y_INFO = "73"
    HEART_GSEN_Z_INFO = "74"
    VO2MAX_INFO = "75"
    HEART_PPG_1_INFO = "76"
    HEART_PPG_2_INFO = "77"
    HEART_ACC_INFO = "78"
    HEART_ACC_X_INFO = "7A"
    HEART_ACC_Y_INFO = "7B"
    HEART_ACC_Z_INFO = "7C"
    PAH_DATA = "80"
    TYHX_DATA = "81"
    TYHX_AGC_OR_3697 = "82"
    GNSS_NAVIGATION_DATA = "90"
    GREEN_PSP_INFO = "91"
    RED_PSP_INFO = "92"
    IR_PSP_INFO = "93"
    SLEEP_PSP_INFO = "94"
    ADI_AGC_INFO = "95"
    TIME_PSP_INFO = "96"
    HRV_PSP_INFO = "97"
    TRAINING_LOAD_INFO = "98"
    CREEK_HR_INFO = "99"

    @classmethod
    def from_hex(cls, value: str) -> Optional["DataType"]:
        if not isinstance(value, str):
            return None
        normalized = value.upper()
        try:
            return cls(normalized)
        except ValueError:
            return None


DATA_TYPE_MAPPING = {
    DataType.BASE_INFO: "BASE_INFO",
    DataType.RAW_PPG_DAC: "RAW_PPG_DAC",
    DataType.RAW_PPG_GREEN: "RAW_PPG_GREEN",
    DataType.RAW_PPG_RED: "RAW_PPG_RED",
    DataType.RAW_PPG_IR: "RAW_PPG_IR",
    DataType.RAW_ACC: "RAW_ACC",
    DataType.RAW_GYRO: "RAW_GYRO",
    DataType.RAW_GEOM: "RAW_GEOM",
    DataType.RAW_PPG_SAR: "RAW_PPG_SAR",
    DataType.RAW_ECG: "RAW_ECG",
    DataType.RAW_EDA: "RAW_EDA",
    DataType.RAW_BIA: "RAW_BIA",
    DataType.RAW_UV: "RAW_UV",
    DataType.RAW_BLUE: "RAW_BLUE",
    DataType.RAW_ACC_TO_PPG: "RAW_ACC_TO_PPG",
    DataType.RAW_PPG_RED_IR: "RAW_PPG_RED_IR",
    DataType.RAW_GPS: "RAW_GPS",
    DataType.AMBIENT_INFO: "AMBIENT_INFO",
    DataType.SLEEP_INFO: "SLEEP_INFO",
    DataType.HRV_INFO: "HRV_INFO",
    DataType.MOTION_INFO: "MOTION_INFO",
    DataType.SWIMMING_INFO: "SWIMMING_INFO",
    DataType.WEAR_INFO: "WEAR_INFO",
    DataType.HEART_GSEN_X_INFO: "HEART_GSEN_X_INFO",
    DataType.HEART_GSEN_Y_INFO: "HEART_GSEN_Y_INFO",
    DataType.HEART_GSEN_Z_INFO: "HEART_GSEN_Z_INFO",
    DataType.VO2MAX_INFO: "VO2MAX_INFO",
    DataType.HEART_PPG_1_INFO: "HEART_PPG_1_INFO",
    DataType.HEART_PPG_2_INFO: "HEART_PPG_2_INFO",
    DataType.HEART_ACC_INFO: "HEART_ACC_INFO",
    DataType.HEART_ACC_X_INFO: "HEART_ACC_X_INFO",
    DataType.HEART_ACC_Y_INFO: "HEART_ACC_Y_INFO",
    DataType.HEART_ACC_Z_INFO: "HEART_ACC_Z_INFO",
    DataType.PAH_DATA: "PAH_DATA",
    DataType.TYHX_DATA: "TYHX_DATA",
    DataType.TYHX_AGC_OR_3697: "TYHX_AGC_DATA",
    DataType.GNSS_NAVIGATION_DATA: "GNSS_NAVIGATION_DATA",
    DataType.GREEN_PSP_INFO: "GREEN_PSP_INFO",
    DataType.RED_PSP_INFO: "RED_PSP_INFO",
    DataType.IR_PSP_INFO: "IR_PSP_INFO",
    DataType.SLEEP_PSP_INFO: "SLEEP_PSP_INFO",
    DataType.ADI_AGC_INFO: "ADI_AGC_INFO",
    DataType.TIME_PSP_INFO: "TIME_PSP_INFO",
    DataType.HRV_PSP_INFO: "HRV_PSP_INFO",
    DataType.TRAINING_LOAD_INFO: "TRAINING_LOAD_INFO",
    DataType.CREEK_HR_INFO: "CREEK_HR_INFO",
}

DATA_TYPE_CHINESE = {
    DataType.BASE_INFO: "基础信息",
    DataType.RAW_PPG_DAC: "原始PPG DAC",
    DataType.RAW_PPG_GREEN: "原始PPG绿光",
    DataType.RAW_PPG_RED: "原始PPG红光",
    DataType.RAW_PPG_IR: "原始PPG红外",
    DataType.RAW_ACC: "原始加速度",
    DataType.RAW_GYRO: "原始陀螺仪",
    DataType.RAW_GEOM: "原始地磁",
    DataType.RAW_PPG_SAR: "原始PPG SAR",
    DataType.RAW_ECG: "原始心电",
    DataType.RAW_EDA: "原始皮肤电导",
    DataType.RAW_BIA: "原始生物阻抗",
    DataType.RAW_UV: "原始紫外光感",
    DataType.RAW_BLUE: "原始蓝光感",
    DataType.RAW_ACC_TO_PPG: "原始加速度到PPG",
    DataType.RAW_PPG_RED_IR: "原始PPG红灯红外",
    DataType.RAW_GPS: "原始GPS",
    DataType.AMBIENT_INFO: "环境信息",
    DataType.SLEEP_INFO: "睡眠信息",
    DataType.HRV_INFO: "心率变异性信息",
    DataType.MOTION_INFO: "运动识别",
    DataType.SWIMMING_INFO: "游泳信息",
    DataType.WEAR_INFO: "佩戴信息",
    DataType.HEART_GSEN_X_INFO: "心率重力感应X轴",
    DataType.HEART_GSEN_Y_INFO: "心率重力感应Y轴",
    DataType.HEART_GSEN_Z_INFO: "心率重力感应Z轴",
    DataType.VO2MAX_INFO: "最大摄氧量信息",
    DataType.HEART_PPG_1_INFO: "心率PPG1信息",
    DataType.HEART_PPG_2_INFO: "心率PPG2信息",
    DataType.HEART_ACC_INFO: "心率加速度信息",
    DataType.HEART_ACC_X_INFO: "心率加速度X轴",
    DataType.HEART_ACC_Y_INFO: "心率加速度Y轴",
    DataType.HEART_ACC_Z_INFO: "心率加速度Z轴",
    DataType.PAH_DATA: "PAH数据",
    DataType.TYHX_DATA: "TYHX数据",
    DataType.TYHX_AGC_OR_3697: "TYHX AGC数据",
    DataType.GNSS_NAVIGATION_DATA: "GNSS导航数据",
    DataType.GREEN_PSP_INFO: "绿光PSP信息",
    DataType.RED_PSP_INFO: "红光PSP信息",
    DataType.IR_PSP_INFO: "红外PSP信息",
    DataType.SLEEP_PSP_INFO: "睡眠PSP信息",
    DataType.ADI_AGC_INFO: "ADI AGC信息",
    DataType.TIME_PSP_INFO: "时间PSP信息",
    DataType.HRV_PSP_INFO: "心率变异性PSP信息",
    DataType.TRAINING_LOAD_INFO: "训练负荷信息",
    DataType.CREEK_HR_INFO: "CREEK心率信息",
}

DATA_TYPE_MAPPING_RING = {
    **DATA_TYPE_MAPPING,
    DataType.TYHX_AGC_OR_3697: "TYHX_3697_Data",
}

DATA_TYPE_CHINESE_RING = {
    **DATA_TYPE_CHINESE,
    DataType.TYHX_AGC_OR_3697: "TYHX 3697 数据",
}


# ===================================================================
# 传感器通道注册表
# ===================================================================

class MergeStrategy(str, Enum):
    """合并策略枚举。"""
    NONE = "none"                          # 不合并 (BaseInfo, WearInfo, TYHX 等)
    CONSECUTIVE_ACC = "consecutive_acc"    # ACC 类: 按 serial_number 合并 acc_data
    CONSECUTIVE_PPG = "consecutive_ppg"    # PPG 类: 按 serial_number 合并 ppg_data


@dataclass(frozen=True)
class SensorChannel:
    """描述一个传感器数据通道的完整流水线配置。"""

    # --- 解析阶段 ---
    data_type: DataType                 # 对应的 hex 数据类型枚举
    list_key: str                       # 中间结果 list 的 key, 如 "acc", "ppg_green"

    # --- 解析器 ---
    parser_class_name: str              # data_structures 中类名, 如 "ACC_Raw_Data"
    parser_extra_kwargs: dict | None = None  # 额外 from_bytes 参数 (如 offset=149)
    needs_rawdata_v2: bool = True       # from_bytes 是否接收 rawdata_v2 参数
    needs_unix_timestamp: bool = True   # from_bytes 是否接收 unix_timestamp 参数

    # --- 合并阶段 ---
    merge_strategy: MergeStrategy = MergeStrategy.NONE

    # --- DataFrame 阶段 ---
    df_key: str = ""                    # build_dataframes 输出 key, 如 "acc_df"
    parquet_name: str = ""              # parquet 文件名 (不含 .parquet)
    add_timestamp_ms: bool = False      # 是否添加 unix_timestamp_ms 列
    rename_columns: dict | None = None  # 列重命名映射, 如 {"acc_data": "gyro_data"}
    ppg_channel_num: int = -1           # >= 0 时执行 process_ppg_dataframe
    force_channel_num: int | None = None  # ppg_r_ir 场景, 强制写入 channel_num

    # --- 戒指特殊分支 (仅用于 0x82) ---
    ring_variant: bool = False          # True => 仅在 is_ring 时解析
    watch_variant: bool = False         # True => 仅在非 is_ring 时解析


# ---------------------------------------------------------------------------
# 全局注册表
# ---------------------------------------------------------------------------
SENSOR_CHANNELS: list[SensorChannel] = [
    # ---- 基础 & 佩戴 ----
    SensorChannel(
        data_type=DataType.BASE_INFO,
        list_key="base_info",
        parser_class_name="BaseInfo",
        needs_rawdata_v2=True,
        df_key="base_info_df",
        parquet_name="base_info",
    ),
    SensorChannel(
        data_type=DataType.WEAR_INFO,
        list_key="wear_info",
        parser_class_name="WearInfo",
        needs_rawdata_v2=True,
        df_key="wear_info_df",
        parquet_name="wear_info",
    ),
    # ---- ACC / Gyro ----
    SensorChannel(
        data_type=DataType.RAW_ACC,
        list_key="acc",
        parser_class_name="ACC_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_ACC,
        df_key="acc_df",
        parquet_name="acc",
        add_timestamp_ms=True,
    ),
    SensorChannel(
        data_type=DataType.RAW_GYRO,
        list_key="gyro",
        parser_class_name="ACC_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_ACC,
        df_key="gyro_df",
        parquet_name="gyro",
        add_timestamp_ms=True,
        rename_columns={"acc_data": "gyro_data"},
    ),
    # ---- PPG ----
    SensorChannel(
        data_type=DataType.RAW_PPG_GREEN,
        list_key="ppg_green",
        parser_class_name="PPG_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_PPG,
        df_key="ppg_g_df",
        parquet_name="ppg_green",
        add_timestamp_ms=True,
        ppg_channel_num=0,
    ),
    SensorChannel(
        data_type=DataType.RAW_PPG_RED,
        list_key="ppg_red",
        parser_class_name="PPG_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_PPG,
        df_key="ppg_r_df",
        parquet_name="ppg_red",
        add_timestamp_ms=True,
        ppg_channel_num=1,
    ),
    SensorChannel(
        data_type=DataType.RAW_PPG_IR,
        list_key="ppg_ir",
        parser_class_name="PPG_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_PPG,
        df_key="ppg_ir_df",
        parquet_name="ppg_ir",
        add_timestamp_ms=True,
        ppg_channel_num=1,
    ),
    SensorChannel(
        data_type=DataType.RAW_PPG_RED_IR,
        list_key="ppg_red_ir",
        parser_class_name="PPG_Raw_Data",
        needs_rawdata_v2=True,
        merge_strategy=MergeStrategy.CONSECUTIVE_PPG,
        df_key="ppg_r_ir_df",
        parquet_name="ppg_red_ir",
        add_timestamp_ms=True,
        ppg_channel_num=1,
        force_channel_num=1,
    ),
    # ---- 运动识别 ----
    SensorChannel(
        data_type=DataType.MOTION_INFO,
        list_key="motion_recognition",
        parser_class_name="MotionRecognition",
        parser_extra_kwargs={"offset": 149},
        needs_rawdata_v2=False,
        df_key="motion_recognition_df",
        parquet_name="motion_recognition",
    ),
    # ---- TYHX ----
    SensorChannel(
        data_type=DataType.TYHX_DATA,
        list_key="tyhx_data",
        parser_class_name="TYHX_PPG_Data",
        needs_rawdata_v2=False,
        df_key="TYHX_data_df",
        parquet_name="tyhx_data",
    ),
    SensorChannel(
        data_type=DataType.TYHX_AGC_OR_3697,
        list_key="tyhx_agc",
        parser_class_name="TYHX_AGC_Data",
        needs_rawdata_v2=False,
        watch_variant=True,
        df_key="TYHX_agc_data_df",
        parquet_name="tyhx_agc",
    ),
    SensorChannel(
        data_type=DataType.TYHX_AGC_OR_3697,
        list_key="tyhx_3697",
        parser_class_name="TYHX_3697_Data",
        needs_rawdata_v2=False,
        ring_variant=True,
        df_key="TYHX_3697_data_df",
        parquet_name="tyhx_3697",
    ),
    # ---- PSP FIFO ----
    SensorChannel(
        data_type=DataType.GREEN_PSP_INFO,
        list_key="psp_fifo",
        parser_class_name="PSP_PPG_FIFO",
        needs_rawdata_v2=True,
        df_key="psp_fifo_df",
        parquet_name="psp_fifo",
    ),
]


# ---------------------------------------------------------------------------
# 派生查找表 (启动时生成一次)
# ---------------------------------------------------------------------------

def _build_lookup() -> dict[str, Any]:
    """构建各种方便查询的索引。"""
    by_type: dict[DataType, list[SensorChannel]] = {}
    for ch in SENSOR_CHANNELS:
        by_type.setdefault(ch.data_type, []).append(ch)

    by_key: dict[str, SensorChannel] = {ch.list_key: ch for ch in SENSOR_CHANNELS}
    df_to_pq: dict[str, str] = {ch.df_key: ch.parquet_name for ch in SENSOR_CHANNELS}
    all_list_keys: list[str] = [ch.list_key for ch in SENSOR_CHANNELS]

    return {
        "by_type": by_type,
        "by_key": by_key,
        "df_to_pq": df_to_pq,
        "all_list_keys": all_list_keys,
    }


_LOOKUP = _build_lookup()

CHANNEL_BY_TYPE: dict[DataType, list[SensorChannel]] = _LOOKUP["by_type"]
CHANNEL_BY_KEY: dict[str, SensorChannel] = _LOOKUP["by_key"]
DF_KEY_TO_FILENAME: dict[str, str] = _LOOKUP["df_to_pq"]
ALL_LIST_KEYS: list[str] = _LOOKUP["all_list_keys"]

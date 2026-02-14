"""
解析执行模块（干活模块）。

职责：
- 逐行解析 raw 文本行 (注册表驱动);
- 合并跨包的 ACC/PPG 连续片段;
- 构建 DataFrame 与后处理。
"""

import json
import time
from typing import Any, Dict, Iterable, List, cast

import numpy as np
import pandas as pd

from app.core.logger import logger
from app.services import data_structures as _ds
from app.services.parser_types import (
    DataType,
    SENSOR_CHANNELS,
    CHANNEL_BY_TYPE,
    ALL_LIST_KEYS,
    MergeStrategy,
    SensorChannel,
)


class ParserWorker:
    """解析执行器。"""

    @staticmethod
    def process_ppg_dataframe(ppg_df, channel_num=0):
        if ppg_df is None or ppg_df.empty:
            return ppg_df

        if channel_num > 0:
            ppg_df["channel_num"] = channel_num
        else:
            def _extract_ch(d):
                if isinstance(d, (list, np.ndarray)) and len(d) > 0:
                    return int(d[0])
                return 1

            ppg_df["channel_num"] = ppg_df["data"].map(_extract_ch)

        max_channel = int(ppg_df["channel_num"].max()) if not ppg_df.empty else 0
        if max_channel <= 0:
            return ppg_df

        if (ppg_df["channel_num"] == 1).all():
            ppg_df["ppg_data_0"] = ppg_df["ppg_data"]
            for ch in range(1, max_channel):
                ppg_df[f"ppg_data_{ch}"] = [np.array([])] * len(ppg_df)
        else:
            empty_arr = np.array([])
            for ch in range(max_channel):
                ppg_df[f"ppg_data_{ch}"] = [empty_arr] * len(ppg_df)

            mask_1 = ppg_df["channel_num"] == 1
            if mask_1.any():
                ppg_df.loc[mask_1, "ppg_data_0"] = ppg_df.loc[mask_1, "ppg_data"]

            for ch_val in range(2, max_channel + 1):
                mask = ppg_df["channel_num"] == ch_val
                if not mask.any():
                    continue
                indices = ppg_df.index[mask]
                for idx in indices:
                    ppg_data = ppg_df.at[idx, "ppg_data"]
                    if not isinstance(ppg_data, np.ndarray) or len(ppg_data) == 0:
                        continue
                    for ch in range(min(ch_val, max_channel)):
                        ppg_df.at[idx, f"ppg_data_{ch}"] = ppg_data[ch::ch_val]

        return ppg_df

    @staticmethod
    def parse_lines(lines: Iterable[str], is_ring: bool = False, merge_consecutive: bool = False) -> dict:
        """
        逐行解析原始文本行, 使用注册表驱动分派。

        Args:
            lines: 原始文本行迭代器
            is_ring: 是否为戒指设备
            merge_consecutive: 兼容参数, 不再影响返回 key 命名

        Returns:
            dict: {list_key: [parsed_items], "labels": [...], "data_types": {...}}
        """
        # 初始化所有通道的收集列表
        collectors: dict[str, list] = {ch.list_key: [] for ch in SENSOR_CHANNELS}
        labels: list = []
        data_type_dict: Dict[str, int] = {}
        last_unix_timestamp = 0

        # 构建 data_type -> 适用通道 的快速查找表 (考虑 ring/watch variant)
        dispatch: dict[DataType, SensorChannel] = {}
        for dt, channels in CHANNEL_BY_TYPE.items():
            for ch in channels:
                if ch.ring_variant and not is_ring:
                    continue
                if ch.watch_variant and is_ring:
                    continue
                dispatch[dt] = ch

        # 解析器类缓存 (按 class_name -> class)
        parser_cache: dict[str, type] = {}

        def _get_parser(class_name: str):
            if class_name not in parser_cache:
                parser_cache[class_name] = getattr(_ds, class_name)
            return parser_cache[class_name]

        # 合并状态: list_key -> pending item
        pending: dict[str, Any] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("202"):
                data = line.replace(", ", ",").split(",")
                if len(data) < 11 or data[3] != "52":
                    continue

                data_type_raw = data[4]
                try:
                    unix_timestamp = int("".join(data[6:10]), 16)
                    label_hr = int(data[2], 16)
                    data_bytes = bytes.fromhex("".join(data[10:]))
                except (ValueError, IndexError):
                    continue

                last_unix_timestamp = unix_timestamp
                rawdata_v2 = len(data) == 243
                parsed_timestamp = data[0]

                data_type = data_type_raw.upper()
                data_type_dict[data_type] = data_type_dict.get(data_type, 0) + 1
                data_type_enum = DataType.from_hex(data_type)

                if data_type_enum is None:
                    continue

                channel = dispatch.get(data_type_enum)
                if channel is None:
                    continue

                # 构建 from_bytes 参数
                parser_cls = _get_parser(channel.parser_class_name)
                kwargs: dict = {"timestamp": parsed_timestamp}
                if channel.needs_unix_timestamp:
                    kwargs["unix_timestamp"] = unix_timestamp
                if channel.needs_rawdata_v2:
                    kwargs["rawdata_v2"] = rawdata_v2
                # BaseInfo 需要 label_hr
                if channel.data_type == DataType.BASE_INFO:
                    kwargs["label_hr"] = label_hr
                # 额外参数 (如 MotionRecognition 的 offset)
                if channel.parser_extra_kwargs:
                    kwargs.update(channel.parser_extra_kwargs)

                parsed_item = parser_cls.from_bytes(data_bytes, **kwargs)

                # 合并或直接收集
                if channel.merge_strategy == MergeStrategy.NONE:
                    collectors[channel.list_key].append(parsed_item)
                else:
                    data_field = "acc_data" if channel.merge_strategy == MergeStrategy.CONSECUTIVE_ACC else "ppg_data"
                    key = channel.list_key
                    prev = pending.get(key)
                    if merge_consecutive and prev is not None and prev.serial_number == parsed_item.serial_number:
                        prev_data = getattr(prev, data_field)
                        prev_data += getattr(parsed_item, data_field)
                        prev.arr_size += parsed_item.arr_size
                    else:
                        if merge_consecutive and prev is not None:
                            collectors[key].append(prev)
                        if merge_consecutive:
                            pending[key] = parsed_item
                        else:
                            collectors[key].append(parsed_item)

            elif line.startswith("{") and line.endswith("}"):
                try:
                    json_data = json.loads(line)
                    if "label" in json_data and "timestamp" in json_data:
                        json_data["unix_timestamp"] = last_unix_timestamp
                        labels.append(json_data)
                except json.JSONDecodeError:
                    continue

        # flush pending
        if merge_consecutive:
            for key, item in pending.items():
                if item is not None:
                    collectors[key].append(item)

        result: dict = dict(collectors)
        result["labels"] = labels
        result["data_types"] = data_type_dict
        return result

    # ------------------------------------------------------------------
    # 合并 (泛型)
    # ------------------------------------------------------------------

    @staticmethod
    def merge_consecutive_items(raw_items: list, data_field: str) -> list:
        """
        按 serial_number 合并连续同序列号的项, 拼接 data_field 字段。

        Args:
            raw_items: 原始解析项列表
            data_field: 要拼接的数据字段名 ("acc_data" 或 "ppg_data")

        Returns:
            合并后的列表
        """
        if not raw_items:
            return []
        merged: list = []
        pending = raw_items[0]
        for item in raw_items[1:]:
            if pending.serial_number == item.serial_number:
                getattr(pending, data_field).extend(getattr(item, data_field))
                pending.arr_size += item.arr_size
            else:
                merged.append(pending)
                pending = item
        merged.append(pending)
        return merged

    # ------------------------------------------------------------------
    # partial result 工具
    # ------------------------------------------------------------------

    @staticmethod
    def empty_partial_result() -> dict:
        """返回空的部分解析结果字典。"""
        result: dict = {key: [] for key in ALL_LIST_KEYS}
        result["labels"] = []
        result["data_types"] = {}
        return result

    @staticmethod
    def merge_partial_results(partial_results: list[dict]) -> dict:
        """
        合并多个 batch 的部分解析结果, 然后对需要合并的通道执行连续合并。

        Returns:
            合并后的 dict, 可直接传给 build_dataframes()。
        """
        merged = ParserWorker.empty_partial_result()
        for item in partial_results:
            for key in ALL_LIST_KEYS:
                merged[key].extend(item.get(key, []))
            merged["labels"].extend(item.get("labels", []))
            for dt, count in item.get("data_types", {}).items():
                merged["data_types"][dt] = merged["data_types"].get(dt, 0) + count

        # 对需要合并的通道执行 serial_number 连续合并
        for ch in SENSOR_CHANNELS:
            if ch.merge_strategy == MergeStrategy.NONE:
                continue
            data_field = "acc_data" if ch.merge_strategy == MergeStrategy.CONSECUTIVE_ACC else "ppg_data"
            merged[ch.list_key] = ParserWorker.merge_consecutive_items(
                merged[ch.list_key], data_field
            )

        return merged

    @staticmethod
    def finalize_parallel_results(partial_results: list[dict]) -> dict:
        """并行解析完成后: 合并 partial → 构建 DataFrame。"""
        merged = ParserWorker.merge_partial_results(partial_results)
        return ParserWorker.build_dataframes(merged)

    # ------------------------------------------------------------------
    # DataFrame 构建 (注册表驱动)
    # ------------------------------------------------------------------

    @staticmethod
    def build_dataframes(parsed: dict) -> dict:
        """
        将解析结果列表转为 DataFrame, 使用注册表驱动。

        Args:
            parsed: {list_key: [items], "labels": [...], "data_types": {...}}

        Returns:
            dict: {df_key: DataFrame, "labels": [...], "data_types": {...}}
        """
        t_total = time.time()
        result: dict = {}

        def _to_df(items: list, label: str = "") -> pd.DataFrame:
            t = time.time()
            df = pd.DataFrame.from_records([vars(o) for o in items])
            elapsed = time.time() - t
            if elapsed > 0.05:
                logger.info(f"[build_dataframes] {label}: {len(items)} rows in {elapsed:.2f}s")
            return df

        for ch in SENSOR_CHANNELS:
            items = parsed.get(ch.list_key)
            if not items:
                continue

            df = _to_df(items, ch.parquet_name)

            # 添加 unix_timestamp_ms
            if ch.add_timestamp_ms and "unix_timestamp" in df.columns and "ms" in df.columns:
                df["unix_timestamp_ms"] = df["unix_timestamp"] + df["ms"] / 1000

            # 列重命名 (如 gyro: acc_data -> gyro_data)
            if ch.rename_columns:
                df.rename(columns=ch.rename_columns, inplace=True)

            # PPG 后处理
            if ch.ppg_channel_num >= 0:
                t_ppg = time.time()
                df = ParserWorker.process_ppg_dataframe(df, ch.ppg_channel_num)
                logger.info(f"[build_dataframes] process_ppg({ch.parquet_name}): {time.time()-t_ppg:.2f}s")

            # 强制 channel_num (ppg_red_ir)
            if ch.force_channel_num is not None:
                df["channel_num"] = ch.force_channel_num

            result[ch.df_key] = df

        result["labels"] = parsed.get("labels", [])
        result["data_types"] = parsed.get("data_types", {})

        logger.info(f"[build_dataframes] Total: {time.time()-t_total:.2f}s")
        return result

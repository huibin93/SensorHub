"""
文件解析服务模块;

本模块提供原始传感器文件的解析功能,将其转换为结构化的 Parquet 文件;
解析流程: 解压 .zst -> 逐行解析传感器数据 -> 生成 DataFrame -> 存储为 Parquet

包含:
- ParserDispatcher: 帧索引校验 + 多进程/单线程解压调度
- ParserService:    编排入口 + Parquet 存储 + manifest 生成
"""
import io
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from os import cpu_count
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

import numpy as np
import pandas as pd
import zstandard as zstd

from app.services.parser_types import (
    DataType,
    DATA_TYPE_MAPPING,
    DATA_TYPE_CHINESE,
    DATA_TYPE_MAPPING_RING,
    DATA_TYPE_CHINESE_RING,
    DF_KEY_TO_FILENAME,
    BatchMeta,
    FrameMeta,
    WorkerInput,
    WorkerOutput,
)
from app.services.parse_progress import parse_progress, map_parallel_progress
from app.services.parser_worker import ParserWorker
from app.services.storage import StorageService
from app.core.logger import logger
from app.core.database import engine
from app.crud import parse_result as parse_result_crud
from app.models.sensor_file import PhysicalFile, SensorFile
from sqlmodel import Session


# ===================================================================
# 模块级函数 — 必须保持模块级以支持 ProcessPoolExecutor pickle 序列化
# ===================================================================

MIN_BATCH_FRAMES = 10
MAX_PROCESS_WORKERS = 8


def _normalize_frames(frames: list[dict]) -> list[FrameMeta]:
    normalized: list[FrameMeta] = []
    for frame in frames:
        normalized.append({
            "cs": int(frame["cs"]),
            "cl": int(frame["cl"]),
            "dl": int(frame["dl"]),
            "nl": bool(frame.get("nl", False)),
        })
    return normalized


def _build_batches(frames: list[FrameMeta], min_batch_frames: int = MIN_BATCH_FRAMES) -> list[BatchMeta]:
    batches: list[BatchMeta] = []
    pending_frames: list[FrameMeta] = []
    pending_start_idx = 0

    for idx, frame in enumerate(frames):
        if not pending_frames:
            pending_start_idx = idx
        pending_frames.append(frame)

        if len(pending_frames) >= min_batch_frames and frame["nl"]:
            batches.append({
                "batch_id": len(batches),
                "start_frame_idx": pending_start_idx,
                "end_frame_idx": idx,
                "compressed_bytes": sum(item["cl"] for item in pending_frames),
                "frames": list(pending_frames),
            })
            pending_frames = []

    if pending_frames:
        batches.append({
            "batch_id": len(batches),
            "start_frame_idx": pending_start_idx,
            "end_frame_idx": len(frames) - 1,
            "compressed_bytes": sum(item["cl"] for item in pending_frames),
            "frames": list(pending_frames),
        })

    return batches


def _worker_parse_batch(worker_input: WorkerInput) -> WorkerOutput:
    raw_path = worker_input["raw_path"]
    batch = worker_input["batch"]
    is_ring = worker_input["is_ring"]

    frame_text_parts: list[str] = []
    try:
        with open(raw_path, "rb") as file_obj:
            dctx = zstd.ZstdDecompressor()
            for frame in batch["frames"]:
                file_obj.seek(frame["cs"])
                compressed_data = file_obj.read(frame["cl"])
                decompressed = dctx.decompress(compressed_data, max_output_size=frame["dl"])
                frame_text_parts.append(decompressed.decode("utf-8", errors="replace"))

        parsed = ParserWorker.parse_lines(
            "".join(frame_text_parts).splitlines(),
            is_ring=is_ring,
            merge_consecutive=False,
        )
        return {
            "batch_id": batch["batch_id"],
            "result": parsed,
        }
    except Exception as exc:
        raise RuntimeError(
            f"batch_id={batch['batch_id']} frame_range={batch['start_frame_idx'] + 1}-{batch['end_frame_idx'] + 1} parse failed"
        ) from exc


# ===================================================================
# ParserDispatcher — 解析调度器
# ===================================================================

class ParserDispatcher:
    """解析调度器: 帧索引校验 + 多进程/单线程解压调度。"""

    @staticmethod
    def validate_frame_index(frame_index: Optional[dict], compressed_size: Optional[int]) -> tuple[bool, str]:
        if frame_index is None:
            return False, "frame_index is None"
        if not isinstance(frame_index, dict):
            return False, "frame_index is not dict"

        frames = frame_index.get("frames")
        if not isinstance(frames, list) or len(frames) == 0:
            return False, "frames is empty or invalid"

        prev_end = 0
        for idx, frame in enumerate(frames):
            if not isinstance(frame, dict):
                return False, f"frame[{idx}] is not dict"

            for key in ("cs", "cl", "dl"):
                value = frame.get(key)
                if not isinstance(value, int):
                    return False, f"frame[{idx}].{key} is not int"
                if value < 0:
                    return False, f"frame[{idx}].{key} < 0"

            cs = frame["cs"]
            cl = frame["cl"]
            if idx == 0 and cs != 0:
                return False, "first frame cs != 0"
            if idx > 0 and cs != prev_end:
                return False, f"frame[{idx}] cs is not contiguous"

            prev_end = cs + cl

        if isinstance(compressed_size, int) and compressed_size > 0 and prev_end > compressed_size:
            return False, "frame compressed range exceeds file size"

        return True, "ok"

    @staticmethod
    def decompress_and_parse_parallel(
        raw_path: Path,
        frame_index: Optional[dict],
        is_ring: bool = False,
        progress_cb: Optional[Callable] = None,
        total_bytes: Optional[int] = None,
    ) -> dict:
        if frame_index is None:
            raise ValueError("frame_index is required for parallel parser")

        raw_frames = frame_index.get("frames", [])
        if not isinstance(raw_frames, list) or not raw_frames:
            raise ValueError("frame_index.frames is empty or invalid")

        frames = _normalize_frames(raw_frames)
        batches = _build_batches(frames, min_batch_frames=MIN_BATCH_FRAMES)
        total_batches = len(batches)
        if total_batches == 0:
            raise ValueError("no batches generated from frame_index")

        worker_count = min(MAX_PROCESS_WORKERS, max(1, cpu_count() or 1), total_batches)
        logger.info(
            f"[parallel] start process parse: frames={len(frames)}, batches={total_batches}, workers={worker_count}, min_batch_frames={MIN_BATCH_FRAMES}"
        )

        ordered_results: dict[int, dict] = {}
        completed_batches = 0

        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    _worker_parse_batch,
                    {
                        "raw_path": str(raw_path),
                        "batch": batch,
                        "is_ring": is_ring,
                    },
                ): batch["batch_id"]
                for batch in batches
            }

            for future in as_completed(futures):
                batch_id = futures[future]
                try:
                    worker_output = future.result()
                except Exception as exc:
                    for pending in futures:
                        pending.cancel()
                    logger.error(f"[parallel] batch {batch_id} failed, terminate parse")
                    raise RuntimeError(f"parallel parse failed at batch {batch_id}") from exc

                ordered_results[worker_output["batch_id"]] = worker_output["result"]
                completed_batches += 1
                progress = map_parallel_progress(completed_batches, total_batches, 0, 90)
                logger.info(
                    f"[parallel] batch {worker_output['batch_id'] + 1}/{total_batches} done -> {progress}%"
                )
                if progress_cb:
                    progress_cb(progress)

        ordered_partials: list[dict] = []
        for batch_id in range(total_batches):
            if batch_id not in ordered_results:
                raise RuntimeError(f"missing parallel batch result: {batch_id}")
            ordered_partials.append(ordered_results[batch_id])

        if progress_cb:
            progress_cb(90)

        return ParserWorker.finalize_parallel_results(ordered_partials)

    @staticmethod
    def decompress_and_parse_single(
        raw_path: Path,
        is_ring: bool = False,
        progress_cb: Optional[Callable] = None,
    ) -> dict:
        logger.info(f"[single] start process parse: {raw_path}")
        if progress_cb:
            progress_cb(10)

        with open(raw_path, "rb") as file_obj:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(file_obj) as reader:
                with io.TextIOWrapper(reader, encoding="utf-8", errors="replace") as text_stream:
                    parsed = ParserWorker.parse_lines(
                        text_stream,
                        is_ring=is_ring,
                        merge_consecutive=True,
                    )

        if progress_cb:
            progress_cb(90)
        return ParserWorker.build_dataframes(parsed)


class ParserService:
    """
    文件解析服务;

    负责解析原始传感器数据文件并生成处理后的 Parquet 数据文件;
    """

    @staticmethod
    def _strip_parse_generated_meta(content_meta: Optional[dict]) -> dict:
        """移除解析过程写入的派生字段, 仅保留业务元数据。"""
        if not isinstance(content_meta, dict):
            return {}

        cleaned = dict(content_meta)
        for key in ("manifest", "parse_summary", "duration_seconds", "raw_file_size"):
            cleaned.pop(key, None)
        return cleaned

    @staticmethod
    def _create_progress_cb(file_id: str) -> Callable[[int], None]:
        _last_reported = [0]

        def progress_cb(progress: int):
            if progress <= _last_reported[0]:
                return
            _last_reported[0] = progress
            logger.debug(f"[progress_cb] file={file_id} progress={progress}%")
            parse_progress.update(file_id, progress, "processing")

        return progress_cb

    @staticmethod
    def parse_file_task(file_id: str, file_hash: str, device_type: str = "Watch"):
        """
        后台解析任务入口 (由 BackgroundTasks 调用);

        自行管理 DB session,更新 ParseResult 状态;

        Args:
            file_id: SensorFile UUID;
            file_hash: 文件 MD5 Hash;
            device_type: 设备类型快照;
        """
        logger.info(f"Starting parse task for file {file_id} (hash={file_hash})")
        start_time = time.time()

        try:
            is_ring = device_type.lower() == "ring"

            # Fetch frame_index from PhysicalFile for parallel decompression
            frame_index = None
            compressed_size = None
            filename = ""
            content_meta = None
            with Session(engine) as session:
                pf = session.get(PhysicalFile, file_hash)
                sf = session.get(SensorFile, file_id)
                existing_pr = parse_result_crud.get_by_file_id(session, file_id)
                if sf:
                    filename = sf.filename
                if existing_pr and existing_pr.content_meta:
                    content_meta = ParserService._strip_parse_generated_meta(existing_pr.content_meta)

                if pf and pf.frame_index:
                    frame_index = pf.frame_index
                    compressed_size = pf.size
                    n_frames = len(frame_index.get("frames", []))
                    logger.info(f"[parse_file_task] frame_index found: {n_frames} frames, "
                                f"lineAligned={frame_index.get('lineAligned')}, "
                                f"frameSize={frame_index.get('frameSize')}")
                else:
                    if pf:
                        compressed_size = pf.size
                    logger.info(f"[parse_file_task] No frame_index for hash={file_hash}")

            # 内存进度 + SSE 推送 (不写DB)
            parse_progress.update(file_id, 0, "processing")
            progress_cb = ParserService._create_progress_cb(file_id)

            # 执行核心解析
            logger.debug(f"[parse_file_task] Starting parse for {file_id} "
                        f"(device={device_type}, frame_index={'yes' if frame_index else 'no'})")
            result = ParserService.parse_file(
                file_hash, is_ring=is_ring,
                progress_cb=progress_cb,
                frame_index=frame_index,
                compressed_size=compressed_size,
                sensor_file_id=file_id,
                filename=filename,
                content_meta=content_meta,
            )

            elapsed = round(time.time() - start_time, 1)
            logger.debug(f"Parse completed for {file_id} in {elapsed}s, "
                        f"keys={list(result['parse_summary'].get('keys', {}).keys())}")

            # 更新 DB
            with Session(engine) as session:
                merged_meta = ParserService._strip_parse_generated_meta(content_meta)
                merged_meta["manifest"] = result.get("manifest", {})
                merged_meta["parse_summary"] = result["parse_summary"]
                manifest_obj = result.get("manifest", {})
                if isinstance(manifest_obj, dict):
                    merged_meta["duration_seconds"] = manifest_obj.get("duration_seconds")
                    merged_meta["raw_file_size"] = manifest_obj.get("raw_file_size")

                parse_result_crud.create_or_update(session, file_id, {
                    "status": "processed",
                    "progress": None,
                    "content_meta": merged_meta,
                    "processed_dir": result["processed_dir"],
                    "duration": result["duration"],
                    "packets": json.dumps(result["packets"], ensure_ascii=False),
                    "error_message": None,
                })

            # SSE 通知: 完成
            parse_progress.update(file_id, 100, "processed")
            logger.debug(f"[parse_file_task] COMPLETED for {file_id}")

        except Exception as e:
            logger.error(f"Parse failed for {file_id}: {e}\n{traceback.format_exc()}")
            with Session(engine) as session:
                parse_result_crud.create_or_update(session, file_id, {
                    "status": "error",
                    "progress": None,
                    "error_message": str(e),
                })
            # SSE 通知: 失败
            parse_progress.update(file_id, 0, "error")

    @staticmethod
    def parse_file(file_hash: str, is_ring: bool = False,
                   progress_cb: Optional[Callable] = None,
                   frame_index: Optional[dict] = None,
                   compressed_size: Optional[int] = None,
                   sensor_file_id: Optional[str] = None,
                   filename: Optional[str] = None,
                   content_meta: Optional[dict] = None) -> Dict[str, Any]:
        """
        核心解析方法: 解压 -> 解析 -> 存储 Parquet -> 生成 manifest;

        Args:
            file_hash: 文件 MD5, 用于定位原始文件和输出目录;
            is_ring: 是否为戒指设备;
            progress_cb: 进度回调 (int -> None), 范围 5-97;
            frame_index: 帧索引 (来自 PhysicalFile), 用于并行解压;
            compressed_size: 压缩文件大小 (优先来自 PhysicalFile.size);
            sensor_file_id: 业务文件 ID;
            filename: 原始文件名;
            content_meta: 业务元数据快照;

        Returns:
            Dict: 包含 content_meta, processed_dir, duration, packets, labels, status;
        """
        raw_path = StorageService.get_raw_path(file_hash)
        output_dir = StorageService.get_processed_dir(file_hash)

        # 优先使用数据库中的压缩大小（PhysicalFile.size）；缺失时再回退本地 stat
        file_size = compressed_size if (compressed_size is not None and compressed_size > 0) else raw_path.stat().st_size

        frame_index_valid, frame_index_reason = ParserDispatcher.validate_frame_index(frame_index, file_size)

        if frame_index_valid:
            effective_frame_index = frame_index
            n_frames = len(effective_frame_index.get("frames", [])) if isinstance(effective_frame_index, dict) else 0
            logger.info(
                f"PARALLEL parser entry: {raw_path} "
                f"({n_frames} frames, {file_size/1024/1024:.1f}MB, frame_index=yes)"
            )
            parse_result = ParserDispatcher.decompress_and_parse_parallel(
                raw_path,
                effective_frame_index,
                is_ring=is_ring,
                progress_cb=progress_cb,
                total_bytes=file_size,
            )
        else:
            logger.warning(
                f"SINGLE parser fallback: {raw_path} "
                f"({file_size/1024/1024:.1f}MB, reason={frame_index_reason})"
            )
            parse_result = ParserDispatcher.decompress_and_parse_single(
                raw_path,
                is_ring=is_ring,
                progress_cb=progress_cb,
            )

        if progress_cb:
            progress_cb(90)

        # 2. 保存 DataFrame 为 Parquet
        t_save = time.time()
        logger.info(f"[parse_file] Phase 2: Saving DataFrames to {output_dir}")
        parse_summary = ParserService._save_to_parquet(parse_result, output_dir)
        logger.info(f"[parse_file] Phase 2 done in {time.time()-t_save:.1f}s, "
                    f"keys={list(parse_summary.get('keys', {}).keys())}")

        if progress_cb:
            progress_cb(95)

        # 3. 计算 duration
        base_info_df = parse_result.get("base_info_df")
        duration = ParserService._calculate_duration(base_info_df)
        duration_seconds = ParserService._calculate_duration_seconds(base_info_df)
        logger.info(f"[parse_file] Phase 3: duration={duration}")

        # 4. 格式化 packets (根据设备类型选择映射表)
        data_types = parse_result.get("data_types", {})
        packets = ParserService._format_packets(data_types, is_ring=is_ring)

        # 5. 标签数据
        labels = parse_result.get("labels", [])

        # 6. 写入 manifest.json
        manifest = ParserService._write_manifest(
            output_dir=output_dir,
            file_hash=file_hash,
            parse_summary=parse_summary,
            duration=duration,
            duration_seconds=duration_seconds,
            is_ring=is_ring,
            data_types=data_types,
            labels=labels,
            sensor_file_id=sensor_file_id,
            filename=filename,
            content_meta=content_meta,
            raw_file_size=file_size,
            raw_filename=raw_path.name,
        )

        if progress_cb:
            progress_cb(98)

        return {
            "parse_summary": parse_summary,
            "processed_dir": str(output_dir),
            "duration": duration,
            "packets": packets,
            "labels": labels,
            "manifest": manifest,
            "status": "processed",
        }

    @staticmethod
    def _save_to_parquet(result_dict: dict, output_dir: Path) -> dict:
        """
        将解析结果中的 DataFrame 保存为 Parquet 文件;

        所有 np.ndarray 列在保存前转为 Python list;

        Args:
            result_dict: 解析结果字典 (含各 DataFrame);
            output_dir: 输出目录 (storage/processed/{hash}/);

        Returns:
            dict: parse_summary 摘要 (keys: {name: {rows, columns, file, size_kb}});
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        parse_summary = {"keys": {}, "summary": {"total_rows": 0, "size_kb": 0}}

        for df_key, pq_name in DF_KEY_TO_FILENAME.items():
            df = result_dict.get(df_key)
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                continue

            if not isinstance(df, pd.DataFrame):
                continue

            # 将所有残余的 ndarray 列转为 list
            df = ParserService._convert_ndarray_columns(df)

            pq_filename = f"{pq_name}.parquet"
            pq_path = output_dir / pq_filename

            try:
                df.to_parquet(pq_path, engine="pyarrow", compression="snappy", index=False)
                file_size_kb = round(os.path.getsize(pq_path) / 1024, 1)

                parse_summary["keys"][pq_name] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "file": pq_filename,
                    "size_kb": file_size_kb,
                }
                parse_summary["summary"]["total_rows"] += len(df)
                parse_summary["summary"]["size_kb"] += file_size_kb

                logger.info(f"Saved {pq_filename}: {len(df)} rows, {file_size_kb} KB")
            except Exception as e:
                logger.error(f"Failed to save {pq_filename}: {e}\n{traceback.format_exc()}")

        parse_summary["summary"]["size_kb"] = round(parse_summary["summary"]["size_kb"], 1)
        return parse_summary

    @staticmethod
    def _convert_ndarray_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        将 DataFrame 中所有 np.ndarray 类型的值转为 Python list;

        Args:
            df: 待转换的 DataFrame;

        Returns:
            pd.DataFrame: 转换后的 DataFrame;
        """
        df = df.copy()
        for col in df.columns:
            # 检查该列是否包含 ndarray
            sample = df[col].dropna().head(5)
            has_ndarray = any(isinstance(v, np.ndarray) for v in sample)
            if has_ndarray:
                df[col] = df[col].apply(
                    lambda x: x.tolist() if isinstance(x, np.ndarray) else x
                )
        return df

    @staticmethod
    def _write_manifest(
        output_dir: Path,
        file_hash: str,
        parse_summary: dict,
        duration: str,
        duration_seconds: Optional[int],
        is_ring: bool,
        data_types: dict,
        labels: list,
        sensor_file_id: Optional[str] = None,
        filename: Optional[str] = None,
        content_meta: Optional[dict] = None,
        raw_file_size: Optional[int] = None,
        raw_filename: Optional[str] = None,
    ) -> dict:
        """
        在 processed 目录下生成 manifest.json 清单文件;

        Args:
            output_dir: 输出目录;
            file_hash: 文件 MD5;
            parse_summary: 解析统计摘要;
            duration: 时长字符串;
            duration_seconds: 时长(秒);
            is_ring: 是否为戒指设备;
            data_types: 数据类型统计;
            labels: 标签列表;
            sensor_file_id: 业务文件 ID;
            filename: 原始文件名;
            content_meta: 业务元数据;
            raw_file_size: 原始文件大小 (bytes);
            raw_filename: 原始压缩文件名;

        Returns:
            dict: manifest 内容;
        """
        manifest = {
            "file_hash": file_hash,
            "sensor_file_id": sensor_file_id,
            "filename": filename,
            "parsed_at": datetime.now().isoformat(),
            "duration": duration,
            "duration_seconds": duration_seconds,
            "is_ring": is_ring,
            "raw_file_size": raw_file_size,
            "raw_file": {
                "name": raw_filename,
                "compressed_size": raw_file_size,
            },
            "keys": parse_summary.get("keys", {}),
            "summary": parse_summary.get("summary", {}),
            "data_types": data_types,
            "labels": labels,
            "content_meta": content_meta or {},
        }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Manifest written to {manifest_path}")
        return manifest

    @staticmethod
    def _calculate_duration(base_info_df) -> str:
        """
        从 base_info_df 的首末 unix_timestamp 计算时长;

        Args:
            base_info_df: 基础信息 DataFrame;

        Returns:
            str: 格式化的时长字符串, 如 "3h 42m" 或 "--";
        """
        if base_info_df is None or not isinstance(base_info_df, pd.DataFrame):
            return "--"
        if base_info_df.empty or "unix_timestamp" not in base_info_df.columns:
            return "--"

        try:
            ts_min = base_info_df["unix_timestamp"].min()
            ts_max = base_info_df["unix_timestamp"].max()
            diff_sec = int(ts_max - ts_min)

            if diff_sec < 0:
                return "--"
            if diff_sec < 60:
                return f"{diff_sec}s"

            hours = diff_sec // 3600
            minutes = (diff_sec % 3600) // 60
            seconds = diff_sec % 60

            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m {seconds}s"
        except Exception:
            return "--"

    @staticmethod
    def _calculate_duration_seconds(base_info_df) -> Optional[int]:
        """
        从 base_info_df 的首末 unix_timestamp 计算总时长(秒)。

        Args:
            base_info_df: 基础信息 DataFrame;

        Returns:
            Optional[int]: 时长秒数, 无法计算时返回 None;
        """
        if base_info_df is None or not isinstance(base_info_df, pd.DataFrame):
            return None
        if base_info_df.empty or "unix_timestamp" not in base_info_df.columns:
            return None

        try:
            ts_min = base_info_df["unix_timestamp"].min()
            ts_max = base_info_df["unix_timestamp"].max()
            diff_sec = int(ts_max - ts_min)
            if diff_sec < 0:
                return None
            return diff_sec
        except Exception:
            return None

    @staticmethod
    def _format_packets(data_type_dict: dict, is_ring: bool = False) -> list:
        """
        将 data_type_dict 转为前端可用的 packets 列表;

        Args:
            data_type_dict: {hex_type: count} 字典;
            is_ring: 是否为戒指设备, 决定使用哪套映射表;

        Returns:
            list: [{"type": "00", "name": "BASE_INFO", "name_cn": "...", "count": 224}, ...]
        """
        type_map = DATA_TYPE_MAPPING_RING if is_ring else DATA_TYPE_MAPPING
        cn_map = DATA_TYPE_CHINESE_RING if is_ring else DATA_TYPE_CHINESE
        packets = []
        sorted_types = sorted(data_type_dict.keys(), key=lambda x: int(x, 16))
        for dt in sorted_types:
            dt_enum = DataType.from_hex(dt)
            type_name = type_map.get(dt_enum) if dt_enum else None
            type_name_cn = cn_map.get(dt_enum) if dt_enum else None
            packets.append({
                "type": dt,
                "name": type_name or f"UNKNOWN({dt})",
                "name_cn": type_name_cn or f"Unknown({dt})",
                "count": data_type_dict[dt],
            })
        return packets

"""
Parser V2: 极简解析实现。

保留对外契约：
- 输入参数不变
- 输出结构不变
- manifest 落盘
- SSE 进度流转一致
- processing 状态写库内聚到任务内部
"""

import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from sqlmodel import Session

from app.core.database import engine
from app.core.logger import logger
from app.crud import parse_result as parse_result_crud
from app.models.sensor_file import SensorFile
from app.services.parse_progress import parse_progress
from app.services.storage import StorageService


class ParserServiceV2:
    """
    解析服务 V2（极简占位实现）。

    设计目标：
    1) 保持对外接口稳定，便于前后端/任务调度无缝切换；
    2) 只保留“任务编排 + 状态更新 + manifest 落盘”主干；
    3) 移除复杂内部解析细节，后续按需渐进填充。
    """

    @staticmethod
    def _strip_parse_generated_meta(content_meta: Optional[dict]) -> dict:
        """
        清理 content_meta 中由解析流程生成的派生字段。

        作用：
        - 避免一次解析的派生产物污染下一次解析输入；
        - 保留业务侧原始元数据（例如上传时识别出的业务字段）；
        - 在任务完成时再合并新的 manifest/summary。

        Args:
            content_meta: 旧的解析元数据快照。

        Returns:
            dict: 去除派生字段后的“干净”元数据。
        """
        if not isinstance(content_meta, dict):
            return {}
        cleaned = dict(content_meta)
        for key in ("manifest", "parse_summary", "duration_seconds", "raw_file_size"):
            cleaned.pop(key, None)
        return cleaned

    @staticmethod
    def _create_progress_cb(file_id: str) -> Callable[[int], None]:
        """
        创建进度回调函数（用于 SSE 推送）。

        约束：
        - 仅允许进度单调递增；
        - 避免重复推送同一进度值，减少前端无效刷新；
        - 状态固定为 processing，终态由任务入口统一上报。

        Args:
            file_id: 当前解析任务对应的业务文件 ID。

        Returns:
            Callable[[int], None]: 可直接传入核心解析函数的回调。
        """
        last = [0]

        def progress_cb(progress: int):
            if progress <= last[0]:
                return
            last[0] = progress
            parse_progress.update(file_id, progress, "processing")

        return progress_cb

    @staticmethod
    def parse_file_task(file_id: str, file_hash: str, device_type: str = "Watch"):
        """
        后台任务入口（由 API 触发并在 BackgroundTasks 中执行）。

        主流程：
        1) 读取当前文件与历史 ParseResult；
        2) 在任务内部写入 processing（符合“外部调用保持干净”）；
        3) 推送 SSE 起始进度；
        4) 调用 parse_file 执行核心流程（当前为极简空实现）；
        5) 写回 processed 结果与 content_meta；
        6) 若异常，写回 error 并推送 SSE 失败状态。

        Args:
            file_id: SensorFile 主键。
            file_hash: 原始压缩文件 hash（用于定位存储路径）。
            device_type: 设备类型快照（Watch/Ring）。
        """
        start_time = time.time()
        logger.info(f"[parser_v2] Starting parse task for file {file_id} (hash={file_hash})")

        try:
            # 用于控制 manifest 中 is_ring 字段以及后续可扩展分支。
            is_ring = device_type.lower() == "ring"
            filename = ""
            content_meta = None

            with Session(engine) as session:
                # 查询业务文件与历史解析记录，用于恢复 filename / content_meta。
                sf = session.get(SensorFile, file_id)
                pr = parse_result_crud.get_by_file_id(session, file_id)
                if sf:
                    filename = sf.filename
                if pr and pr.content_meta:
                    content_meta = ParserServiceV2._strip_parse_generated_meta(pr.content_meta)

                # 关键点：processing 状态写库在任务内部完成。
                # 这样外部 API 只负责触发任务，保持外部调用整洁。
                parse_result_crud.create_or_update(session, file_id, {
                    "status": "processing",
                    "device_type_used": device_type,
                    "progress": None,
                    "error_message": None,
                })

            # SSE 首帧：告知前端已进入 processing。
            parse_progress.update(file_id, 0, "processing")
            progress_cb = ParserServiceV2._create_progress_cb(file_id)

            # 调用核心解析入口。
            # 当前版本故意保持“空实现”：只做契约输出，不做重解析。
            result = ParserServiceV2.parse_file(
                file_hash=file_hash,
                is_ring=is_ring,
                progress_cb=progress_cb,
                frame_index=None,
                compressed_size=None,
                sensor_file_id=file_id,
                filename=filename,
                content_meta=content_meta,
            )

            with Session(engine) as session:
                # 合并旧业务元数据与新解析派生字段。
                merged_meta = ParserServiceV2._strip_parse_generated_meta(content_meta)
                merged_meta["manifest"] = result.get("manifest", {})
                merged_meta["parse_summary"] = result.get("parse_summary", {})
                manifest_obj = result.get("manifest", {})
                if isinstance(manifest_obj, dict):
                    merged_meta["duration_seconds"] = manifest_obj.get("duration_seconds")
                    merged_meta["raw_file_size"] = manifest_obj.get("raw_file_size")

                # 持久化终态 processed。
                parse_result_crud.create_or_update(session, file_id, {
                    "status": "processed",
                    "progress": None,
                    "content_meta": merged_meta,
                    "processed_dir": result["processed_dir"],
                    "duration": result["duration"],
                    "packets": json.dumps(result["packets"], ensure_ascii=False),
                    "error_message": None,
                })

            # SSE 终态：解析完成。
            parse_progress.update(file_id, 100, "processed")
            elapsed = round(time.time() - start_time, 1)
            logger.info(f"[parser_v2] COMPLETED for {file_id} in {elapsed}s")

        except Exception as exc:
            # 任意异常统一写回 error，避免前端卡在 processing。
            logger.error(f"[parser_v2] Parse failed for {file_id}: {exc}\n{traceback.format_exc()}")
            with Session(engine) as session:
                parse_result_crud.create_or_update(session, file_id, {
                    "status": "error",
                    "progress": None,
                    "error_message": str(exc),
                })
            # SSE 失败终态。
            parse_progress.update(file_id, 0, "error")

    @staticmethod
    def parse_file(
        file_hash: str,
        is_ring: bool = False,
        progress_cb: Optional[Callable] = None,
        frame_index: Optional[dict] = None,
        compressed_size: Optional[int] = None,
        sensor_file_id: Optional[str] = None,
        filename: Optional[str] = None,
        content_meta: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        核心解析入口（当前为“空实现占位版本”）。

        保留完整入参与返回结构，方便后续平滑替换为真实解析逻辑。

        当前行为：
        - 校验原始压缩文件存在；
        - 推送阶段进度 10 -> 90 -> 98；
        - 生成空的 parse_summary / packets / labels；
        - 写出 manifest.json；
        - 返回与旧实现一致的响应字段。

        Args:
            file_hash: 文件 hash。
            is_ring: 是否戒指设备。
            progress_cb: 进度回调。
            frame_index: 预留参数（当前未使用，保留契约）。
            compressed_size: 可选压缩大小（优先使用）。
            sensor_file_id: 业务文件 ID。
            filename: 原始文件名。
            content_meta: 业务元数据。

        Returns:
            Dict[str, Any]: 标准化解析结果。
        """
        raw_path = StorageService.get_raw_path(file_hash)
        output_dir = StorageService.get_processed_dir(file_hash)

        # 先做硬性校验，避免后续写入“伪成功”结果。
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw file not found: {raw_path}")

        if progress_cb:
            progress_cb(10)

        # 优先采用外部传入的压缩大小（通常来自 DB），缺失时回退到文件 stat。
        file_size = compressed_size if (compressed_size is not None and compressed_size > 0) else raw_path.stat().st_size

        # 空实现结果：不生成 parquet，只提供结构化空摘要。
        parse_summary = {
            "keys": {},
            "summary": {
                "total_rows": 0,
                "size_kb": 0,
            },
        }

        # 与旧接口保持一致的字段。
        duration = "--"
        duration_seconds = 0
        data_types: dict = {}
        labels: list = []
        packets: list = []

        if progress_cb:
            progress_cb(90)

        # 即使为空解析，也要写 manifest，保证存储契约稳定。
        manifest = ParserServiceV2._write_manifest(
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

        # 返回字段保持旧版本兼容。
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
        写入 manifest.json。

        说明：
        - manifest 是解析产物的统一索引文件；
        - 前端/下载/后续处理可依赖该文件判断结构与状态；
        - 当前为空实现时仍写入，确保契约一致。

        Args:
            output_dir: 输出目录（processed/{hash}）。
            file_hash: 文件 hash。
            parse_summary: 解析摘要。
            duration: 时长文案。
            duration_seconds: 时长秒数。
            is_ring: 是否戒指设备。
            data_types: 数据类型统计。
            labels: 标签数据。
            sensor_file_id: 业务文件 ID。
            filename: 原始文件名。
            content_meta: 业务元数据。
            raw_file_size: 压缩文件大小。
            raw_filename: 压缩文件名。

        Returns:
            dict: manifest 内容（同时已写盘）。
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

        # 确保输出目录存在后再写入清单文件。
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as file_obj:
            json.dump(manifest, file_obj, ensure_ascii=False, indent=2, default=str)

        logger.info(f"[parser_v2] Manifest written to {manifest_path}")
        return manifest

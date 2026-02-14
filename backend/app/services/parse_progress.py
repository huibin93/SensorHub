"""
解析进度管理模块 (内存级)

通过 SSE (Server-Sent Events) 实时推送解析进度到前端;
进度不持久化到数据库, 仅在内存中维护;

使用方式:
    - parse_file_task 中调用 parse_progress.update(file_id, progress, status)
    - SSE 端点订阅 parse_progress.subscribe(file_id) 异步生成器
"""
import asyncio
import time
from typing import Optional
from app.core.logger import logger


class ParseProgressManager:
    """
    内存级进度管理器;

    维护每个 file_id 的最新进度, 通过 asyncio.Event 通知 SSE 订阅者;
    """

    def __init__(self):
        # {file_id: {"progress": int, "status": str, "updated_at": float}}
        self._state: dict[str, dict] = {}
        # {file_id: set[asyncio.Event]} — 每个订阅者一个 Event
        self._subscribers: dict[str, set[asyncio.Event]] = {}

    def update(self, file_id: str, progress: int, status: str = "processing"):
        """
        更新进度 (由后台线程调用);

        Args:
            file_id: SensorFile ID;
            progress: 0-100;
            status: processing / processed / error;
        """
        self._state[file_id] = {
            "progress": progress,
            "status": status,
            "updated_at": time.time(),
        }
        logger.debug(f"[ParseProgress] {file_id}: {status} {progress}%")
        # 通知所有订阅者
        for event in self._subscribers.get(file_id, set()):
            event.set()

    def get(self, file_id: str) -> Optional[dict]:
        """获取当前进度快照"""
        return self._state.get(file_id)

    def remove(self, file_id: str):
        """解析结束后清理"""
        self._state.pop(file_id, None)

    async def subscribe(self, file_id: str):
        """
        异步生成器: 每次进度变化时 yield 当前状态;

        用于 SSE 端点:
            async for data in parse_progress.subscribe(file_id):
                yield f"data: {json.dumps(data)}\\n\\n"
        """
        event = asyncio.Event()
        if file_id not in self._subscribers:
            self._subscribers[file_id] = set()
        self._subscribers[file_id].add(event)

        try:
            # 立即发送当前状态
            current = self.get(file_id)
            if current:
                yield current

            while True:
                # 等待新数据或超时 (30s heartbeat)
                try:
                    await asyncio.wait_for(event.wait(), timeout=30.0)
                    event.clear()
                except asyncio.TimeoutError:
                    # 发送 heartbeat 保持连接
                    pass

                state = self.get(file_id)
                if state:
                    yield state
                    # 终态: 解析完成或失败
                    if state["status"] in ("processed", "error"):
                        self.remove(file_id)
                        break
                else:
                    # 进度已被清理, 结束
                    break
        finally:
            self._subscribers.get(file_id, set()).discard(event)
            if file_id in self._subscribers and not self._subscribers[file_id]:
                del self._subscribers[file_id]


# 全局单例
parse_progress = ParseProgressManager()


def map_parallel_progress(
    completed_batches: int,
    total_batches: int,
    min_progress: int = 0,
    max_progress: int = 90,
) -> int:
    if total_batches <= 0:
        return min_progress
    completed = max(0, min(completed_batches, total_batches))
    if max_progress <= min_progress:
        return min_progress
    ratio = completed / total_batches
    return min_progress + int((max_progress - min_progress) * ratio)

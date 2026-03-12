from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(slots=True)
class SlotLease:
    queue_wait_ms: float


class RequestLimiter:
    """In-process limiter with per-user and per-task-key gates."""

    def __init__(self, per_user_limit: int = 2, per_task_limit: int = 2):
        self.per_user_limit = max(1, per_user_limit)
        self.per_task_limit = max(1, per_task_limit)
        self._user_semaphores: dict[str, asyncio.Semaphore] = {}
        self._task_semaphores: dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    async def _get_user_semaphore(self, user_id: str) -> asyncio.Semaphore:
        async with self._lock:
            if user_id not in self._user_semaphores:
                self._user_semaphores[user_id] = asyncio.Semaphore(self.per_user_limit)
            return self._user_semaphores[user_id]

    async def _get_task_semaphore(self, task_key: str) -> asyncio.Semaphore:
        async with self._lock:
            if task_key not in self._task_semaphores:
                self._task_semaphores[task_key] = asyncio.Semaphore(self.per_task_limit)
            return self._task_semaphores[task_key]

    @asynccontextmanager
    async def slot(self, *, user_id: str, task_key: str):
        user_sem = await self._get_user_semaphore(user_id)
        task_sem = await self._get_task_semaphore(task_key)

        start = time.perf_counter()
        await user_sem.acquire()
        try:
            await task_sem.acquire()
            wait_ms = (time.perf_counter() - start) * 1000.0
            try:
                yield SlotLease(queue_wait_ms=round(wait_ms, 3))
            finally:
                task_sem.release()
        finally:
            user_sem.release()

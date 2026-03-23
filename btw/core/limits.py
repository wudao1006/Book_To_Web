from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(slots=True)
class SlotLease:
    queue_wait_ms: float


@dataclass(slots=True)
class _SemaphoreEntry:
    semaphore: asyncio.Semaphore
    last_used: float


class RateLimitExceeded(Exception):
    """Raised when a request waits too long for a limiter slot."""


class RequestLimiter:
    """In-process limiter with per-user and per-task-key gates."""

    def __init__(
        self,
        per_user_limit: int = 2,
        per_task_limit: int = 2,
        *,
        acquire_timeout_ms: int = 5000,
        max_tracked_keys: int = 4096,
        idle_ttl_seconds: int = 300,
    ):
        self.per_user_limit = max(1, per_user_limit)
        self.per_task_limit = max(1, per_task_limit)
        self.acquire_timeout_seconds = max(1, acquire_timeout_ms) / 1000.0
        self.max_tracked_keys = max(32, max_tracked_keys)
        self.idle_ttl_seconds = max(30, idle_ttl_seconds)
        self._user_entries: dict[str, _SemaphoreEntry] = {}
        self._task_entries: dict[str, _SemaphoreEntry] = {}
        self._lock = asyncio.Lock()

    async def _get_user_entry(self, user_id: str) -> _SemaphoreEntry:
        async with self._lock:
            now = time.monotonic()
            entry = self._user_entries.get(user_id)
            if entry is None:
                entry = _SemaphoreEntry(asyncio.Semaphore(self.per_user_limit), now)
                self._user_entries[user_id] = entry
            else:
                entry.last_used = now
            self._trim_locked(self._user_entries, self.per_user_limit)
            return entry

    async def _get_task_entry(self, task_key: str) -> _SemaphoreEntry:
        async with self._lock:
            now = time.monotonic()
            entry = self._task_entries.get(task_key)
            if entry is None:
                entry = _SemaphoreEntry(asyncio.Semaphore(self.per_task_limit), now)
                self._task_entries[task_key] = entry
            else:
                entry.last_used = now
            self._trim_locked(self._task_entries, self.per_task_limit)
            return entry

    def _trim_locked(self, entries: dict[str, _SemaphoreEntry], capacity: int) -> None:
        if len(entries) <= self.max_tracked_keys:
            return

        now = time.monotonic()
        idle_keys: list[tuple[str, float]] = []
        for key, entry in entries.items():
            available = int(getattr(entry.semaphore, "_value", 0))
            is_idle = (not entry.semaphore.locked()) and available >= capacity
            if not is_idle:
                continue
            idle_keys.append((key, entry.last_used))

        if not idle_keys:
            return

        idle_keys.sort(key=lambda item: item[1])
        for key, last_used in idle_keys:
            if len(entries) <= self.max_tracked_keys:
                break
            if now - last_used >= self.idle_ttl_seconds:
                entries.pop(key, None)

        if len(entries) > self.max_tracked_keys:
            for key, _ in idle_keys:
                if len(entries) <= self.max_tracked_keys:
                    break
                entries.pop(key, None)

    async def _touch_entries(self, user_id: str, task_key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            user_entry = self._user_entries.get(user_id)
            task_entry = self._task_entries.get(task_key)
            if user_entry is not None:
                user_entry.last_used = now
            if task_entry is not None:
                task_entry.last_used = now
            self._trim_locked(self._user_entries, self.per_user_limit)
            self._trim_locked(self._task_entries, self.per_task_limit)

    @asynccontextmanager
    async def slot(self, *, user_id: str, task_key: str):
        user_entry = await self._get_user_entry(user_id)
        task_entry = await self._get_task_entry(task_key)

        start = time.perf_counter()
        user_acquired = False
        task_acquired = False
        try:
            await asyncio.wait_for(
                user_entry.semaphore.acquire(), timeout=self.acquire_timeout_seconds
            )
            user_acquired = True
            await asyncio.wait_for(
                task_entry.semaphore.acquire(), timeout=self.acquire_timeout_seconds
            )
            task_acquired = True
            wait_ms = (time.perf_counter() - start) * 1000.0
            yield SlotLease(queue_wait_ms=round(wait_ms, 3))
        except TimeoutError as exc:
            raise RateLimitExceeded(
                f"Timed out waiting for limiter slot after {self.acquire_timeout_seconds:.2f}s"
            ) from exc
        finally:
            if task_acquired:
                task_entry.semaphore.release()
            if user_acquired:
                user_entry.semaphore.release()
            await self._touch_entries(user_id, task_key)

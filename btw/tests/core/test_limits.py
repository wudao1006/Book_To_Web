from __future__ import annotations

import asyncio

import pytest

from btw.core.limits import RequestLimiter


@pytest.mark.asyncio
async def test_request_limiter_serializes_same_user() -> None:
    limiter = RequestLimiter(per_user_limit=1, per_task_limit=1)
    events: list[str] = []

    async def run(label: str, delay: float) -> None:
        async with limiter.slot(user_id="user-1", task_key="generate_component") as slot:
            events.append(f"{label}:start")
            await asyncio.sleep(delay)
            events.append(f"{label}:wait={slot.queue_wait_ms}")
            events.append(f"{label}:end")

    await asyncio.gather(run("first", 0.05), run("second", 0.01))

    assert events[0] == "first:start"
    assert events[2] == "first:end"
    assert events[3] == "second:start"
    second_wait = float(events[4].split("=")[1])
    assert second_wait > 0.0


@pytest.mark.asyncio
async def test_request_limiter_allows_different_users() -> None:
    limiter = RequestLimiter(per_user_limit=1, per_task_limit=2)

    async def run(user_id: str) -> float:
        async with limiter.slot(user_id=user_id, task_key="generate_component") as slot:
            await asyncio.sleep(0.01)
            return slot.queue_wait_ms

    waits = await asyncio.gather(run("user-a"), run("user-b"))
    assert waits[0] >= 0.0
    assert waits[1] >= 0.0

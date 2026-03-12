from __future__ import annotations

import os
import shutil
import uuid

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from btw.agents import get_registry
from btw.core.errors import BTWError, ensure_error_payload
from btw.core.limits import RequestLimiter
from btw.skills.base import get_skill_registry
from btw.storage import book_store
from btw.storage.db import (
    AgentLogRepository,
    BookRepository,
    ChapterRepository,
    ComponentVersionRepository,
    MetricsRepository,
    TaskRepository,
)

router = APIRouter()

_request_limiter = RequestLimiter(
    per_user_limit=int(os.getenv("BTW_MAX_CONCURRENT_PER_USER", "2")),
    per_task_limit=int(os.getenv("BTW_MAX_CONCURRENT_PER_TASK", "2")),
)


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id") or "anonymous"


@router.post("/books/upload")
async def upload_book(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str | None = Form(default=None),
) -> dict[str, object]:
    trace_id = request.state.trace_id
    book_id = str(uuid.uuid4())[:8]
    upload_dir = book_store.DATA_DIR.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{book_id}_{file.filename}"

    with file_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    BookRepository.create_book(
        book_id=book_id,
        title=title,
        author=author,
        file_path=str(file_path),
    )

    director = get_registry().create("director")
    async with _request_limiter.slot(user_id=_user_id(request), task_key="upload_book") as slot:
        result = await director.process(
            {
                "action": "upload_book",
                "book_id": book_id,
                "file_path": str(file_path),
                "trace_id": trace_id,
            }
        )
    if result.get("error"):
        payload = ensure_error_payload(
            result["error"],
            default_code="upload_failed",
            default_stage="upload",
            default_retriable=True,
            trace_id=trace_id,
        )
        raise BTWError(
            code=payload["code"],
            message=payload["message"],
            stage=payload["stage"],
            retriable=bool(payload["retriable"]),
            status_code=400,
            trace_id=payload["trace_id"],
            details=payload.get("details"),
        )

    return {
        "book_id": book_id,
        "task_id": result.get("task_id"),
        "title": title,
        "status": result.get("status", "queued"),
        "chapters_count": result.get("chapters_count", 0),
        "queue_wait_ms": slot.queue_wait_ms,
    }


@router.get("/books/{book_id}")
async def get_book(request: Request, book_id: str) -> dict[str, object]:
    book = BookRepository.get_book(book_id)
    if book is None:
        raise BTWError(
            code="book_not_found",
            message="Book not found",
            stage="upload",
            retriable=False,
            status_code=404,
            trace_id=request.state.trace_id,
        )
    return book


@router.get("/books/{book_id}/chapters")
async def get_chapters(request: Request, book_id: str) -> dict[str, object]:
    del request
    return {"chapters": ChapterRepository.list_by_book(book_id)}


@router.get("/books/{book_id}/chapters/{chapter_index}/versions")
async def list_component_versions(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    del request
    versions = ComponentVersionRepository.list_versions(book_id, chapter_index)
    latest = next((item for item in versions if item["is_latest"]), None)
    stable = next((item for item in versions if item["is_stable"]), None)
    return {
        "book_id": book_id,
        "chapter_index": chapter_index,
        "latest": latest,
        "stable": stable,
        "versions": versions,
    }


@router.post("/books/{book_id}/chapters/{chapter_index}/rollback")
async def rollback_component_version(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id
    restored = ComponentVersionRepository.rollback_to_stable(book_id, chapter_index)
    if restored is None:
        raise BTWError(
            code="stable_version_not_found",
            message="Stable version not found",
            stage="render",
            retriable=False,
            status_code=404,
            trace_id=trace_id,
        )

    versions = ComponentVersionRepository.list_versions(book_id, chapter_index)
    latest = next((item for item in versions if item["is_latest"]), None)
    stable = next((item for item in versions if item["is_stable"]), None)
    return {
        "book_id": book_id,
        "chapter_index": chapter_index,
        "latest": latest,
        "stable": stable,
        "versions": versions,
    }


@router.get("/skills")
async def list_skills(request: Request) -> dict[str, object]:
    del request
    registry = get_skill_registry()
    return {
        "skills": [
            {
                "name": name,
                "description": skill_class.description,
                "parameters": skill_class.parameters,
            }
            for name, skill_class in sorted(registry.skills.items())
        ]
    }


@router.get("/metrics/tasks")
async def get_task_metrics(request: Request) -> dict[str, object]:
    del request
    return MetricsRepository.task_metrics()


@router.get("/tasks/{task_id}")
async def get_task(request: Request, task_id: str) -> dict[str, object]:
    task = TaskRepository.get_task(task_id)
    if task is None:
        raise BTWError(
            code="task_not_found",
            message="Task not found",
            stage="dispatch",
            retriable=False,
            status_code=404,
            trace_id=request.state.trace_id,
        )
    return task


@router.get("/tasks/{task_id}/steps")
async def get_task_steps(request: Request, task_id: str) -> dict[str, object]:
    task = TaskRepository.get_task(task_id)
    if task is None:
        raise BTWError(
            code="task_not_found",
            message="Task not found",
            stage="dispatch",
            retriable=False,
            status_code=404,
            trace_id=request.state.trace_id,
        )
    del request
    return {"task_id": task_id, "steps": TaskRepository.list_steps(task_id)}


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(request: Request, task_id: str) -> dict[str, object]:
    task = TaskRepository.get_task(task_id)
    if task is None:
        raise BTWError(
            code="task_not_found",
            message="Task not found",
            stage="dispatch",
            retriable=False,
            status_code=404,
            trace_id=request.state.trace_id,
        )
    del request
    return {"task_id": task_id, "logs": AgentLogRepository.list_by_task(task_id)}


@router.post("/books/{book_id}/chapters/{chapter_index}/generate")
async def generate_component(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id
    director = get_registry().create("director")

    async with _request_limiter.slot(
        user_id=_user_id(request), task_key=f"generate_component:{book_id}:{chapter_index}"
    ) as slot:
        result = await director.process(
            {
                "action": "generate_component",
                "book_id": book_id,
                "chapter_index": chapter_index,
                "trace_id": trace_id,
            }
        )

    if result.get("error"):
        payload = ensure_error_payload(
            result["error"],
            default_code="generate_failed",
            default_stage="generate",
            default_retriable=True,
            trace_id=trace_id,
        )
        status_code = 404 if payload["code"] in {"chapter_not_found", "stable_version_not_found"} else 400
        raise BTWError(
            code=payload["code"],
            message=payload["message"],
            stage=payload["stage"],
            retriable=bool(payload["retriable"]),
            status_code=status_code,
            trace_id=payload["trace_id"],
            details=payload.get("details"),
        )

    result["queue_wait_ms"] = slot.queue_wait_ms
    return result


@router.get("/books/{book_id}/chapters/{chapter_index}/component")
async def get_component(
    request: Request,
    book_id: str,
    chapter_index: int,
    version: str = Query(default="latest", pattern="^(latest|stable|[0-9]+)$"),
) -> dict[str, object]:
    trace_id = request.state.trace_id
    director = get_registry().create("director")
    result = await director.process(
        {
            "action": "get_component",
            "book_id": book_id,
            "chapter_index": chapter_index,
            "trace_id": trace_id,
            "version": version,
        }
    )
    if result.get("error"):
        payload = ensure_error_payload(
            result["error"],
            default_code="component_not_found",
            default_stage="render",
            default_retriable=True,
            trace_id=trace_id,
        )
        raise BTWError(
            code=payload["code"],
            message=payload["message"],
            stage=payload["stage"],
            retriable=bool(payload["retriable"]),
            status_code=404,
            trace_id=payload["trace_id"],
            details=payload.get("details"),
        )
    return result

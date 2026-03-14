from __future__ import annotations

import os

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from btw.core.errors import BTWError, ensure_error_payload
from btw.core.limits import RateLimitExceeded, RequestLimiter
from btw.services import BookApplicationService
from btw.skills.base import get_skill_registry

router = APIRouter()
_book_service = BookApplicationService()

_request_limiter = RequestLimiter(
    per_user_limit=int(os.getenv("BTW_MAX_CONCURRENT_PER_USER", "2")),
    per_task_limit=int(os.getenv("BTW_MAX_CONCURRENT_PER_TASK", "2")),
    acquire_timeout_ms=int(os.getenv("BTW_QUEUE_TIMEOUT_MS", "5000")),
    max_tracked_keys=int(os.getenv("BTW_LIMITER_MAX_KEYS", "4096")),
    idle_ttl_seconds=int(os.getenv("BTW_LIMITER_IDLE_TTL_SECONDS", "300")),
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
    upload_record = _book_service.create_upload_record(
        file_obj=file.file,
        filename=file.filename,
        title=title,
        author=author,
    )
    book_id = str(upload_record["book_id"])
    file_path = str(upload_record["file_path"])

    try:
        async with _request_limiter.slot(
            user_id=_user_id(request), task_key="upload_book"
        ) as slot:
            result = await _book_service.dispatch_upload(
                book_id=book_id,
                file_path=file_path,
                trace_id=trace_id,
            )
    except RateLimitExceeded as exc:
        raise BTWError(
            code="rate_limited",
            message=str(exc),
            stage="upload",
            retriable=True,
            status_code=429,
            trace_id=trace_id,
        ) from exc

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


@router.get("/books")
async def list_books(request: Request) -> dict[str, object]:
    del request
    return {"books": _book_service.list_books()}


@router.get("/books/{book_id}")
async def get_book(request: Request, book_id: str) -> dict[str, object]:
    book = _book_service.get_book(book_id)
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
    return {"chapters": _book_service.list_chapters(book_id)}


@router.get("/books/{book_id}/chapters/{chapter_index}/content")
async def get_chapter_content(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    payload = _book_service.get_chapter_content(book_id, chapter_index)
    if payload is None:
        raise BTWError(
            code="chapter_not_found",
            message="Chapter not found",
            stage="read",
            retriable=False,
            status_code=404,
            trace_id=request.state.trace_id,
        )
    return payload


@router.get("/books/{book_id}/chapters/{chapter_index}/versions")
async def list_component_versions(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    del request
    return _book_service.list_component_versions(book_id, chapter_index)


@router.post("/books/{book_id}/chapters/{chapter_index}/rollback")
async def rollback_component_version(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id
    payload = _book_service.rollback_component_version(book_id, chapter_index)
    if payload is None:
        raise BTWError(
            code="stable_version_not_found",
            message="Stable version not found",
            stage="render",
            retriable=False,
            status_code=404,
            trace_id=trace_id,
        )
    return payload


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
    return _book_service.task_metrics()


@router.get("/tasks/{task_id}")
async def get_task(request: Request, task_id: str) -> dict[str, object]:
    task = _book_service.get_task(task_id)
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
    task = _book_service.get_task(task_id)
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
    return {"task_id": task_id, "steps": _book_service.get_task_steps(task_id)}


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(request: Request, task_id: str) -> dict[str, object]:
    task = _book_service.get_task(task_id)
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
    return {"task_id": task_id, "logs": _book_service.get_task_logs(task_id)}


@router.post("/books/{book_id}/chapters/{chapter_index}/generate")
async def generate_component(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id

    try:
        async with _request_limiter.slot(
            user_id=_user_id(request), task_key=f"generate_component:{book_id}:{chapter_index}"
        ) as slot:
            result = await _book_service.dispatch_generate(
                book_id=book_id,
                chapter_index=chapter_index,
                trace_id=trace_id,
            )
    except RateLimitExceeded as exc:
        raise BTWError(
            code="rate_limited",
            message=str(exc),
            stage="generate",
            retriable=True,
            status_code=429,
            trace_id=trace_id,
        ) from exc

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
    result = await _book_service.dispatch_get_component(
        book_id=book_id,
        chapter_index=chapter_index,
        trace_id=trace_id,
        version=version,
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

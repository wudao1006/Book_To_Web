from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, File, Form, Request, UploadFile

from btw.agents import get_registry
from btw.core.errors import BTWError, ensure_error_payload
from btw.skills.base import get_skill_registry
from btw.storage import book_store
from btw.storage.db import BookRepository, ChapterRepository

router = APIRouter()


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
        "title": title,
        "status": result.get("status", "queued"),
        "chapters_count": result.get("chapters_count", 0),
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


@router.post("/books/{book_id}/chapters/{chapter_index}/generate")
async def generate_component(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id
    director = get_registry().create("director")
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
        status_code = 404 if payload["code"] == "chapter_not_found" else 400
        raise BTWError(
            code=payload["code"],
            message=payload["message"],
            stage=payload["stage"],
            retriable=bool(payload["retriable"]),
            status_code=status_code,
            trace_id=payload["trace_id"],
            details=payload.get("details"),
        )
    return result


@router.get("/books/{book_id}/chapters/{chapter_index}/component")
async def get_component(
    request: Request, book_id: str, chapter_index: int
) -> dict[str, object]:
    trace_id = request.state.trace_id
    director = get_registry().create("director")
    result = await director.process(
        {
            "action": "get_component",
            "book_id": book_id,
            "chapter_index": chapter_index,
            "trace_id": trace_id,
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

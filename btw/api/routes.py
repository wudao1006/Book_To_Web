from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from btw.agents import get_registry
from btw.storage import book_store
from btw.storage.db import BookRepository, ChapterRepository

router = APIRouter()


@router.post("/books/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str | None = Form(default=None),
) -> dict[str, object]:
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
        {"action": "upload_book", "book_id": book_id, "file_path": str(file_path)}
    )

    return {
        "book_id": book_id,
        "title": title,
        "status": result.get("status", "queued"),
        "chapters_count": result.get("chapters_count", 0),
    }


@router.get("/books/{book_id}")
async def get_book(book_id: str) -> dict[str, object]:
    book = BookRepository.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/books/{book_id}/chapters")
async def get_chapters(book_id: str) -> dict[str, object]:
    return {"chapters": ChapterRepository.list_by_book(book_id)}


@router.post("/books/{book_id}/chapters/{chapter_index}/generate")
async def generate_component(book_id: str, chapter_index: int) -> dict[str, object]:
    director = get_registry().create("director")
    result = await director.process(
        {
            "action": "generate_component",
            "book_id": book_id,
            "chapter_index": chapter_index,
        }
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=str(result["error"]))
    return result


@router.get("/books/{book_id}/chapters/{chapter_index}/component")
async def get_component(book_id: str, chapter_index: int) -> dict[str, object]:
    director = get_registry().create("director")
    result = await director.process(
        {"action": "get_component", "book_id": book_id, "chapter_index": chapter_index}
    )
    if not result.get("exists"):
        raise HTTPException(
            status_code=404,
            detail=str(result.get("message", "Component not found")),
        )
    return result

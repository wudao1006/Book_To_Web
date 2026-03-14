from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from btw.agents import get_registry
from btw.storage import book_store
from btw.storage.db import (
    AgentLogRepository,
    BookRepository,
    ChapterRepository,
    ComponentVersionRepository,
    MetricsRepository,
    TaskRepository,
)


class BookApplicationService:
    """Application-layer service for BTW book and generation workflows."""

    def __init__(self) -> None:
        self._registry = get_registry()

    def create_upload_record(
        self,
        *,
        file_obj: BinaryIO,
        filename: str | None,
        title: str,
        author: str | None,
    ) -> dict[str, str]:
        book_id = str(uuid.uuid4())[:8]
        upload_dir = book_store.DATA_DIR.parent / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename or "upload.bin"
        file_path = upload_dir / f"{book_id}_{safe_name}"

        with file_path.open("wb") as handle:
            shutil.copyfileobj(file_obj, handle)

        BookRepository.create_book(
            book_id=book_id,
            title=title,
            author=author,
            file_path=str(file_path),
        )
        return {"book_id": book_id, "file_path": str(file_path), "title": title}

    async def dispatch_upload(
        self,
        *,
        book_id: str,
        file_path: str,
        trace_id: str,
    ) -> dict[str, Any]:
        director = self._registry.create("director")
        return await director.process(
            {
                "action": "upload_book",
                "book_id": book_id,
                "file_path": file_path,
                "trace_id": trace_id,
            }
        )

    async def dispatch_generate(
        self,
        *,
        book_id: str,
        chapter_index: int,
        trace_id: str,
    ) -> dict[str, Any]:
        director = self._registry.create("director")
        return await director.process(
            {
                "action": "generate_component",
                "book_id": book_id,
                "chapter_index": chapter_index,
                "trace_id": trace_id,
            }
        )

    async def dispatch_get_component(
        self,
        *,
        book_id: str,
        chapter_index: int,
        version: str,
        trace_id: str,
    ) -> dict[str, Any]:
        director = self._registry.create("director")
        return await director.process(
            {
                "action": "get_component",
                "book_id": book_id,
                "chapter_index": chapter_index,
                "trace_id": trace_id,
                "version": version,
            }
        )

    def list_books(self) -> list[dict[str, Any]]:
        return BookRepository.list_books()

    def get_book(self, book_id: str) -> dict[str, Any] | None:
        return BookRepository.get_book(book_id)

    def list_chapters(self, book_id: str) -> list[dict[str, Any]]:
        chapters = ChapterRepository.list_by_book(book_id)
        return [
            {
                "id": chapter["id"],
                "index_num": chapter["index_num"],
                "title": chapter["title"],
                "type_tag": chapter.get("type_tag"),
                "summary_path": chapter.get("summary_path"),
                "status": chapter["status"],
            }
            for chapter in chapters
        ]

    def get_chapter_content(self, book_id: str, chapter_index: int) -> dict[str, Any] | None:
        chapters = ChapterRepository.list_by_book(book_id)
        matched = next(
            (
                chapter
                for chapter in chapters
                if int(chapter.get("index_num", -1)) == chapter_index
            ),
            None,
        )
        if matched is None:
            return None

        raw_path = matched.get("content_path")
        if not raw_path:
            return None
        content_path = Path(str(raw_path))
        if not content_path.exists():
            return None

        return {
            "book_id": book_id,
            "chapter_index": chapter_index,
            "title": matched.get("title"),
            "content": content_path.read_text(encoding="utf-8"),
        }

    def list_component_versions(self, book_id: str, chapter_index: int) -> dict[str, Any]:
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

    def rollback_component_version(
        self, book_id: str, chapter_index: int
    ) -> dict[str, Any] | None:
        restored = ComponentVersionRepository.rollback_to_stable(book_id, chapter_index)
        if restored is None:
            return None
        return self.list_component_versions(book_id, chapter_index)

    def task_metrics(self) -> dict[str, Any]:
        return MetricsRepository.task_metrics()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return TaskRepository.get_task(task_id)

    def get_task_steps(self, task_id: str) -> list[dict[str, Any]]:
        return TaskRepository.list_steps(task_id)

    def get_task_logs(self, task_id: str) -> list[dict[str, Any]]:
        return AgentLogRepository.list_by_task(task_id)

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from btw.agents.base import Agent
from btw.storage.book_store import save_chapter
from btw.storage.db import BookRepository, ChapterRepository


class ParserAgent(Agent):
    name = "parser"
    description = "Parse uploaded book text into chapters."

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(input_data["file_path"])
        book_id = input_data["book_id"]
        text = file_path.read_text(encoding="utf-8")

        chapters = self._split_chapters(text)
        for chapter in chapters:
            content_path = save_chapter(book_id, chapter["index"], chapter["content"])
            ChapterRepository.upsert_chapter(
                chapter_id=f"{book_id}-ch-{chapter['index']:02d}",
                book_id=book_id,
                index_num=chapter["index"],
                title=chapter["title"],
                content_path=str(content_path),
            )

        BookRepository.update_status(book_id, "parsed")
        return {
            "book_id": book_id,
            "chapters": chapters,
            "total_chapters": len(chapters),
        }

    def _split_chapters(self, text: str) -> list[dict[str, Any]]:
        pattern = r"^(#{1,2}\s+.+)$"
        parts = re.split(pattern, text, flags=re.MULTILINE)
        chapters: list[dict[str, Any]] = []

        if len(parts) > 1:
            current_title: str | None = None
            for index in range(1, len(parts), 2):
                title = parts[index].lstrip("#").strip()
                content = parts[index + 1].strip() if index + 1 < len(parts) else ""
                if content:
                    chapters.append(
                        {"title": title, "content": content, "index": len(chapters)}
                    )
                current_title = title

            if not chapters and current_title:
                chapters.append({"title": current_title, "content": "", "index": 0})
            return chapters

        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
        if not paragraphs:
            return [{"title": "Section 1", "content": text.strip(), "index": 0}]

        chunk_size = 10
        return [
            {
                "title": f"Section {offset // chunk_size + 1}",
                "content": "\n\n".join(paragraphs[offset : offset + chunk_size]),
                "index": offset // chunk_size,
            }
            for offset in range(0, len(paragraphs), chunk_size)
        ]

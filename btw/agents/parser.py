"""Parser agent for BTW."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from btw.agents.base import Agent
from btw.skills.pdf_to_markdown import PDFToMarkdownSkill
from btw.storage.book_store import save_chapter
from btw.storage.db import BookRepository, ChapterRepository


class ParserAgent(Agent):
    name = "parser"
    description = "Parse uploaded book files (PDF, Markdown, TXT) into chapters."

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(input_data["file_path"])
        book_id = input_data["book_id"]

        print(f"Parser processing: {file_path}, suffix: {file_path.suffix}")

        # Handle PDF files
        if file_path.suffix.lower() == ".pdf":
            print("Detected PDF, converting...")
            pdf_skill = PDFToMarkdownSkill()
            result = await pdf_skill.execute(
                file_path=str(file_path),
            )
            print(f"PDF conversion result: {result.get('success')}, error: {result.get('error')}")
            if not result.get("success"):
                raise RuntimeError(f"PDF conversion failed: {result.get('error')}")
            text = result["markdown"]
        else:
            # Handle text files (Markdown, TXT)
            print(f"Reading text file: {file_path}")
            text = file_path.read_text(encoding="utf-8")

        chapters = self._split_chapters(text)
        chapter_rows: list[dict[str, Any]] = []
        for chapter in chapters:
            content_path = save_chapter(book_id, chapter["index"], chapter["content"])
            chapter_rows.append(
                {
                    "id": f"{book_id}-ch-{chapter['index']:02d}",
                    "index_num": chapter["index"],
                    "title": chapter["title"],
                    "content_path": str(content_path),
                }
            )

        ChapterRepository.bulk_upsert_chapters(book_id=book_id, chapters=chapter_rows)

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

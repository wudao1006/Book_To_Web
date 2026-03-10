from __future__ import annotations

from typing import Any

from btw.agents.base import Agent
from btw.storage.book_store import save_book_summary, save_concept_index
from btw.storage.vector_store import VectorStore


class ReaderAgent(Agent):
    name = "reader"
    description = "Generate lightweight summaries and concept indexes."

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        book_id = input_data["book_id"]
        chapters = input_data.get("chapters", [])

        chapter_summaries = [await self._summarize_chapter(chapter) for chapter in chapters]
        book_summary = await self._summarize_book(chapter_summaries)
        concepts = await self._extract_concepts(chapters)

        save_book_summary(book_id, book_summary)
        save_concept_index(book_id, concepts)
        self._index_chapters(book_id, chapters)

        return {
            "book_id": book_id,
            "summary": book_summary,
            "concepts": concepts,
            "chapters_analyzed": len(chapters),
        }

    async def _summarize_chapter(self, chapter: dict[str, Any]) -> str:
        title = chapter.get("title", "Untitled")
        content = chapter.get("content", "").strip()
        preview = content[:120] + ("..." if len(content) > 120 else "")
        return f"{title}: {preview}"

    async def _summarize_book(self, chapter_summaries: list[str]) -> str:
        if not chapter_summaries:
            return "No content"
        return "\n".join(chapter_summaries)

    async def _extract_concepts(self, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        concepts: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for chapter in chapters:
            for token in self._quoted_terms(chapter.get("content", "")):
                key = (chapter.get("title", "Untitled"), token)
                if key in seen:
                    continue
                seen.add(key)
                concepts.append(
                    {
                        "name": token,
                        "chapter": chapter.get("title", "Untitled"),
                        "source": "quoted_text",
                    }
                )
        return concepts

    def _index_chapters(self, book_id: str, chapters: list[dict[str, Any]]) -> None:
        paragraphs = []
        for chapter in chapters:
            paragraphs.append(
                {
                    "id": f"{book_id}-ch-{chapter.get('index', 0):02d}",
                    "chapter_id": f"{book_id}-ch-{chapter.get('index', 0):02d}",
                    "index_num": chapter.get("index", 0),
                    "text": chapter.get("content", ""),
                }
            )
        VectorStore().add_paragraphs(book_id, paragraphs)

    @staticmethod
    def _quoted_terms(content: str) -> list[str]:
        terms: list[str] = []
        cursor = 0
        while True:
            start = content.find('"', cursor)
            if start == -1:
                return terms
            end = content.find('"', start + 1)
            if end == -1:
                return terms
            term = content[start + 1 : end].strip()
            if term:
                terms.append(term)
            cursor = end + 1

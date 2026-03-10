from __future__ import annotations

from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency is absent
    chromadb = None
    Settings = None


class VectorStore:
    def __init__(self) -> None:
        self._paragraphs: dict[str, list[dict[str, Any]]] = {}
        # Keep the MVP deterministic and offline-friendly.
        self._client = None

    def add_paragraphs(self, book_id: str, paragraphs: list[dict[str, Any]]) -> None:
        if self._client is None:
            self._paragraphs.setdefault(book_id, []).extend(paragraphs)
            return

        collection = self._client.get_or_create_collection(name=f"book_{book_id}")
        ids = [paragraph["id"] for paragraph in paragraphs]
        documents = [paragraph["text"] for paragraph in paragraphs]
        metadatas = [
            {"chapter_id": paragraph.get("chapter_id"), "index": paragraph.get("index_num")}
            for paragraph in paragraphs
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, book_id: str, query: str, n_results: int = 5) -> dict[str, list[Any]]:
        if self._client is None:
            matches = [
                paragraph
                for paragraph in self._paragraphs.get(book_id, [])
                if query.lower() in paragraph["text"].lower()
            ]
            return {"documents": [[match["text"] for match in matches[:n_results]]]}

        collection = self._client.get_or_create_collection(name=f"book_{book_id}")
        return collection.query(query_texts=[query], n_results=n_results)

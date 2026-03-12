from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency is absent
    chromadb = None
    Settings = None


class VectorStore:
    def __init__(self, mode: str | None = None, persist_dir: Path | None = None) -> None:
        self._paragraphs: dict[str, list[dict[str, Any]]] = {}
        requested_mode = mode or os.getenv("BTW_VECTOR_STORE_MODE", "memory")
        self.mode = requested_mode
        self.fallback_reason: str | None = None
        self._client = None

        if requested_mode == "persistent":
            self._init_persistent_client(persist_dir)
        else:
            self.mode = "memory"

    def _init_persistent_client(self, persist_dir: Path | None) -> None:
        if chromadb is None or Settings is None:
            self.mode = "memory"
            self.fallback_reason = "chromadb_unavailable"
            return

        target_dir = persist_dir or (Path(__file__).resolve().parents[1] / "data" / "vectors")
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(
                path=str(target_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            self.mode = "persistent"
        except Exception as exc:  # pragma: no cover - defensive for runtime env differences
            self._client = None
            self.mode = "memory"
            self.fallback_reason = f"persistent_init_failed:{exc.__class__.__name__}"

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
                if query.lower() in str(paragraph.get("text", "")).lower()
            ]
            return {"documents": [[match["text"] for match in matches[:n_results]]]}

        collection = self._client.get_or_create_collection(name=f"book_{book_id}")
        return collection.query(query_texts=[query], n_results=n_results)

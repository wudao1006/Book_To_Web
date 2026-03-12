from __future__ import annotations

from pathlib import Path

from btw.storage.vector_store import VectorStore


def test_vector_store_memory_mode_is_deterministic() -> None:
    store = VectorStore(mode="memory")
    store.add_paragraphs(
        "book-1",
        [
            {
                "id": "p-1",
                "chapter_id": "ch-1",
                "index_num": 0,
                "text": "Demand increases price.",
            },
            {
                "id": "p-2",
                "chapter_id": "ch-1",
                "index_num": 1,
                "text": "Supply balances demand.",
            },
        ],
    )

    result = store.search("book-1", "demand", n_results=5)
    assert result["documents"][0] == ["Demand increases price.", "Supply balances demand."]
    assert store.mode == "memory"


def test_vector_store_persistent_mode_falls_back_to_memory_when_unavailable(tmp_path: Path) -> None:
    store = VectorStore(mode="persistent", persist_dir=tmp_path / "vectors")
    assert store.mode in {"persistent", "memory"}
    if store.mode == "memory":
        assert store.fallback_reason

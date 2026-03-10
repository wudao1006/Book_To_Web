import json
from pathlib import Path

import pytest

from btw.agents.reader import ReaderAgent
from btw.storage import book_store


@pytest.mark.asyncio
async def test_reader_generates_summary_and_concept_index(tmp_path: Path) -> None:
    book_store.DATA_DIR = tmp_path / "data" / "books"
    book_store.ensure_book_dir("book-001")

    reader = ReaderAgent(config={})

    result = await reader.process(
        {
            "book_id": "book-001",
            "chapters": [
                {
                    "title": "Supply",
                    "content": 'This chapter explains "Supply" and "Demand" with examples.',
                    "index": 0,
                }
            ],
        }
    )

    assert result["book_id"] == "book-001"
    assert result["chapters_analyzed"] == 1
    assert "Supply" in result["summary"]
    assert any(item["name"] == "Supply" for item in result["concepts"])

    book_dir = book_store.DATA_DIR / "book-001"
    assert (book_dir / "book_summary.md").exists()
    assert (book_dir / "concept_index.json").exists()

    stored_concepts = json.loads((book_dir / "concept_index.json").read_text(encoding="utf-8"))
    assert stored_concepts[0]["name"] == "Supply"

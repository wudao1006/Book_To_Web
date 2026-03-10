from pathlib import Path

import pytest

from btw.agents.parser import ParserAgent
from btw.storage import book_store, db


@pytest.mark.asyncio
async def test_parser_splits_markdown_and_persists_chapters(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    db.init_db()
    db.BookRepository.create_book("book-001", "Parser Test", "Tester", str(tmp_path / "source.md"))

    source = tmp_path / "source.md"
    source.write_text(
        "# Chapter One\n\nAlpha paragraph.\n\n## Chapter Two\n\nBeta paragraph.",
        encoding="utf-8",
    )

    parser = ParserAgent(config={})

    result = await parser.process({"file_path": str(source), "book_id": "book-001"})

    assert result["book_id"] == "book-001"
    assert result["total_chapters"] == 2
    assert result["chapters"][0]["title"] == "Chapter One"
    assert result["chapters"][1]["title"] == "Chapter Two"

    saved = book_store.DATA_DIR / "book-001" / "chapters" / "00" / "content.md"
    assert saved.exists()
    assert "Alpha paragraph." in saved.read_text(encoding="utf-8")

    book = db.BookRepository.get_book("book-001")
    assert book is not None
    assert book["status"] == "parsed"

from pathlib import Path

from btw.storage import db


def test_init_db_creates_database_and_tables(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"

    db.init_db()

    assert db.DB_PATH.exists()

    with db.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"books", "chapters", "paragraphs", "concepts", "agent_logs", "ai_cache"} <= tables


def test_book_repository_create_get_and_update_status(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    db.init_db()

    db.BookRepository.create_book(
        book_id="book-001",
        title="Test Book",
        author="Tester",
        file_path="/tmp/book.md",
    )

    book = db.BookRepository.get_book("book-001")
    assert book is not None
    assert book["title"] == "Test Book"
    assert book["status"] == "pending"

    db.BookRepository.update_status("book-001", "parsed")
    updated = db.BookRepository.get_book("book-001")
    assert updated is not None
    assert updated["status"] == "parsed"

from __future__ import annotations

from btw.services.book_service import BookApplicationService
from btw.storage import book_store, db
from btw.storage.book_store import save_chapter
from btw.storage.db import BookRepository, ChapterRepository


def test_list_chapters_hides_internal_paths(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    db.init_db()

    book_id = "book-1"
    BookRepository.create_book(
        book_id=book_id,
        title="Book",
        author="Author",
        file_path="/tmp/book.md",
    )
    chapter_path = save_chapter(book_id, 0, "Chapter body")
    ChapterRepository.bulk_upsert_chapters(
        book_id=book_id,
        chapters=[
            {
                "id": f"{book_id}-ch-00",
                "index_num": 0,
                "title": "Chapter One",
                "content_path": str(chapter_path),
            }
        ],
    )

    service = BookApplicationService()
    chapters = service.list_chapters(book_id)

    assert len(chapters) == 1
    assert chapters[0]["index_num"] == 0
    assert chapters[0]["title"] == "Chapter One"
    assert "content_path" not in chapters[0]


def test_get_chapter_content_returns_controlled_payload(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    db.init_db()

    book_id = "book-2"
    BookRepository.create_book(
        book_id=book_id,
        title="Book",
        author=None,
        file_path="/tmp/book.md",
    )
    chapter_path = save_chapter(book_id, 0, "Controlled chapter text")
    ChapterRepository.bulk_upsert_chapters(
        book_id=book_id,
        chapters=[
            {
                "id": f"{book_id}-ch-00",
                "index_num": 0,
                "title": "Chapter One",
                "content_path": str(chapter_path),
            }
        ],
    )

    service = BookApplicationService()
    payload = service.get_chapter_content(book_id, 0)

    assert payload is not None
    assert payload["book_id"] == book_id
    assert payload["chapter_index"] == 0
    assert payload["title"] == "Chapter One"
    assert payload["content"] == "Controlled chapter text"


def test_get_chapter_content_returns_none_when_missing(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    db.init_db()

    service = BookApplicationService()
    assert service.get_chapter_content("missing-book", 0) is None

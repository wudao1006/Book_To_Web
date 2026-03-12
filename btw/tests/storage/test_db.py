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

    assert {
        "books",
        "chapters",
        "paragraphs",
        "concepts",
        "agent_logs",
        "ai_cache",
        "tasks",
        "task_steps",
        "component_versions",
    } <= tables

    with db.get_connection() as conn:
        chapter_indexes = {
            row["name"]
            for row in conn.execute("PRAGMA index_list('chapters')").fetchall()
        }
        paragraph_indexes = {
            row["name"]
            for row in conn.execute("PRAGMA index_list('paragraphs')").fetchall()
        }

    assert "ux_chapters_book_index" in chapter_indexes
    assert "ux_paragraphs_chapter_index" in paragraph_indexes


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


def test_task_repository_create_update_and_list_steps(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    db.init_db()

    db.TaskRepository.create_task(
        task_id="task-001",
        action="generate_component",
        trace_id="trace-001",
        book_id="book-001",
        chapter_index=0,
    )
    db.TaskRepository.update_task_status("task-001", "running")
    db.TaskRepository.upsert_step("task-001", "create", "running")
    db.TaskRepository.upsert_step("task-001", "create", "succeeded")
    db.TaskRepository.upsert_step("task-001", "compile", "failed", error_code="compile_failed")
    db.TaskRepository.update_task_status(
        "task-001",
        "failed",
        error_code="compile_failed",
        error_message="Compile failed",
    )

    task = db.TaskRepository.get_task("task-001")
    assert task is not None
    assert task["status"] == "failed"
    assert task["error_code"] == "compile_failed"

    steps = db.TaskRepository.list_steps("task-001")
    assert len(steps) == 2
    assert steps[0]["stage"] == "create"
    assert steps[0]["status"] == "succeeded"
    assert steps[1]["stage"] == "compile"
    assert steps[1]["status"] == "failed"


def test_chapter_repository_deduplicates_book_index_pair(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    db.init_db()
    db.BookRepository.create_book(
        book_id="book-001",
        title="Test Book",
        author="Tester",
        file_path="/tmp/book.md",
    )

    db.ChapterRepository.upsert_chapter(
        chapter_id="book-001-ch-00-v1",
        book_id="book-001",
        index_num=0,
        title="Chapter One",
        content_path="/tmp/chapter-v1.md",
        status="parsed",
    )
    db.ChapterRepository.upsert_chapter(
        chapter_id="book-001-ch-00-v2",
        book_id="book-001",
        index_num=0,
        title="Chapter One Revised",
        content_path="/tmp/chapter-v2.md",
        status="parsed",
    )

    chapters = db.ChapterRepository.list_by_book("book-001")
    assert len(chapters) == 1
    assert chapters[0]["title"] == "Chapter One Revised"


def test_component_version_repository_records_latest_and_stable(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    db.init_db()

    first = db.ComponentVersionRepository.create_version(
        book_id="book-001",
        chapter_index=0,
        jsx_code="export default function A(){ return <div>A</div>; }",
        js_code="module.exports.default = function A(){};",
        bundle_size=120,
    )
    second = db.ComponentVersionRepository.create_version(
        book_id="book-001",
        chapter_index=0,
        jsx_code="export default function B(){ return <div>B</div>; }",
        js_code="module.exports.default = function B(){};",
        bundle_size=140,
    )

    assert first["version_num"] == 1
    assert second["version_num"] == 2
    assert second["is_latest"] is True
    assert second["is_stable"] is False

    stable = db.ComponentVersionRepository.get_component(
        book_id="book-001", chapter_index=0, version="stable"
    )
    assert stable is not None
    assert stable["version_num"] == 1

    latest = db.ComponentVersionRepository.get_component(
        book_id="book-001", chapter_index=0, version="latest"
    )
    assert latest is not None
    assert latest["version_num"] == 2

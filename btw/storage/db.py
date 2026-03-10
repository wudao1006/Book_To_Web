from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "btw.db"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                meta_json TEXT
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                index_num INTEGER NOT NULL,
                title TEXT,
                type_tag TEXT,
                content_path TEXT,
                summary_path TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (book_id) REFERENCES books(id)
            );

            CREATE TABLE IF NOT EXISTS paragraphs (
                id TEXT PRIMARY KEY,
                chapter_id TEXT NOT NULL,
                index_num INTEGER NOT NULL,
                type TEXT,
                text TEXT,
                context TEXT,
                entities_json TEXT,
                concepts_json TEXT,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                name TEXT NOT NULL,
                paragraph_ids_json TEXT,
                UNIQUE(book_id, name)
            );

            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                book_id TEXT,
                chapter_id TEXT,
                input_summary TEXT,
                output_summary TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE NOT NULL,
                model TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


class BookRepository:
    @staticmethod
    def create_book(
        book_id: str,
        title: str,
        author: str | None,
        file_path: str,
        meta_json: str | None = None,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO books (id, title, author, file_path, meta_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (book_id, title, author, file_path, meta_json),
            )
            conn.commit()

    @staticmethod
    def get_book(book_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def update_status(book_id: str, status: str) -> None:
        with get_connection() as conn:
            conn.execute("UPDATE books SET status = ? WHERE id = ?", (status, book_id))
            conn.commit()


class ChapterRepository:
    @staticmethod
    def upsert_chapter(
        chapter_id: str,
        book_id: str,
        index_num: int,
        title: str,
        content_path: str,
        status: str = "parsed",
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chapters (id, book_id, index_num, title, content_path, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    content_path = excluded.content_path,
                    status = excluded.status
                """,
                (chapter_id, book_id, index_num, title, content_path, status),
            )
            conn.commit()

    @staticmethod
    def list_by_book(book_id: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, index_num, title, type_tag, content_path, summary_path, status
                FROM chapters
                WHERE book_id = ?
                ORDER BY index_num
                """,
                (book_id,),
            ).fetchall()
        return [dict(row) for row in rows]

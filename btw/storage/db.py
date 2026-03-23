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
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    with get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in _column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    with transaction() as conn:
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
                trace_id TEXT,
                agent_name TEXT NOT NULL,
                stage TEXT,
                status TEXT,
                latency_ms REAL DEFAULT 0,
                token_cost REAL DEFAULT 0,
                book_id TEXT,
                chapter_index INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE NOT NULL,
                model TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                book_id TEXT,
                chapter_index INTEGER,
                trace_id TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                error_code TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                error_code TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, stage),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS component_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                chapter_index INTEGER NOT NULL,
                version_num INTEGER NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1,
                is_stable INTEGER NOT NULL DEFAULT 0,
                jsx_code TEXT NOT NULL,
                js_code TEXT NOT NULL,
                bundle_size INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(book_id, chapter_index, version_num)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ux_chapters_book_index
                ON chapters(book_id, index_num);

            CREATE UNIQUE INDEX IF NOT EXISTS ux_paragraphs_chapter_index
                ON paragraphs(chapter_id, index_num);

            CREATE INDEX IF NOT EXISTS ix_task_steps_task_id
                ON task_steps(task_id, id);

            CREATE INDEX IF NOT EXISTS ix_component_versions_chapter
                ON component_versions(book_id, chapter_index, version_num DESC);
            """
        )

        _ensure_column(conn, "agent_logs", "trace_id", "TEXT")
        _ensure_column(conn, "agent_logs", "stage", "TEXT")
        _ensure_column(conn, "agent_logs", "latency_ms", "REAL DEFAULT 0")
        _ensure_column(conn, "agent_logs", "token_cost", "REAL DEFAULT 0")
        _ensure_column(conn, "agent_logs", "chapter_index", "INTEGER")
        _ensure_column(conn, "agent_logs", "message", "TEXT")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_agent_logs_task_stage
                ON agent_logs(task_id, stage, id)
            """
        )


class BookRepository:
    @staticmethod
    def create_book(
        book_id: str,
        title: str,
        author: str | None,
        file_path: str,
        meta_json: str | None = None,
    ) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO books (id, title, author, file_path, meta_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (book_id, title, author, file_path, meta_json),
            )

    @staticmethod
    def get_book(book_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def list_books() -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, author, status, upload_time FROM books ORDER BY upload_time DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def update_status(book_id: str, status: str) -> None:
        with transaction() as conn:
            conn.execute("UPDATE books SET status = ? WHERE id = ?", (status, book_id))


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
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO chapters (id, book_id, index_num, title, content_path, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, index_num) DO UPDATE SET
                    id = excluded.id,
                    title = excluded.title,
                    content_path = excluded.content_path,
                    status = excluded.status
                """,
                (chapter_id, book_id, index_num, title, content_path, status),
            )

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

    @staticmethod
    def bulk_upsert_chapters(
        *, book_id: str, chapters: list[dict[str, Any]], status: str = "parsed"
    ) -> None:
        with transaction() as conn:
            for chapter in chapters:
                conn.execute(
                    """
                    INSERT INTO chapters (id, book_id, index_num, title, content_path, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(book_id, index_num) DO UPDATE SET
                        id = excluded.id,
                        title = excluded.title,
                        content_path = excluded.content_path,
                        status = excluded.status
                    """,
                    (
                        str(chapter["id"]),
                        book_id,
                        int(chapter["index_num"]),
                        str(chapter["title"]),
                        str(chapter["content_path"]),
                        status,
                    ),
                )


class TaskRepository:
    @staticmethod
    def create_task(
        task_id: str,
        action: str,
        *,
        trace_id: str,
        book_id: str | None = None,
        chapter_index: int | None = None,
        status: str = "queued",
    ) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, action, book_id, chapter_index, trace_id, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, action, book_id, chapter_index, trace_id, status),
            )

    @staticmethod
    def update_task_status(
        task_id: str,
        status: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with transaction() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, error_code = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, error_code, error_message, task_id),
            )

    @staticmethod
    def upsert_step(
        task_id: str,
        stage: str,
        status: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_steps (task_id, stage, status, error_code, error_message)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id, stage) DO UPDATE SET
                    status = excluded.status,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (task_id, stage, status, error_code, error_message),
            )

    @staticmethod
    def get_task(task_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def list_steps(task_id: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT task_id, stage, status, error_code, error_message, created_at, updated_at
                FROM task_steps
                WHERE task_id = ?
                ORDER BY id
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]


class AICacheRepository:
    @staticmethod
    def get(prompt_hash: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT prompt_hash, model, result, created_at
                FROM ai_cache
                WHERE prompt_hash = ?
                """,
                (prompt_hash,),
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def upsert(prompt_hash: str, model: str, result: str) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO ai_cache (prompt_hash, model, result)
                VALUES (?, ?, ?)
                ON CONFLICT(prompt_hash) DO UPDATE SET
                    model = excluded.model,
                    result = excluded.result,
                    created_at = CURRENT_TIMESTAMP
                """,
                (prompt_hash, model, result),
            )


class AgentLogRepository:
    @staticmethod
    def create(
        *,
        task_id: str,
        trace_id: str,
        agent_name: str,
        stage: str,
        status: str,
        latency_ms: float,
        token_cost: float = 0.0,
        book_id: str | None = None,
        chapter_index: int | None = None,
        message: str | None = None,
    ) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO agent_logs (
                    task_id,
                    trace_id,
                    agent_name,
                    stage,
                    status,
                    latency_ms,
                    token_cost,
                    book_id,
                    chapter_index,
                    message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    trace_id,
                    agent_name,
                    stage,
                    status,
                    latency_ms,
                    token_cost,
                    book_id,
                    chapter_index,
                    message,
                ),
            )

    @staticmethod
    def list_by_task(task_id: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT task_id, trace_id, agent_name, stage, status, latency_ms, token_cost,
                       book_id, chapter_index, message, created_at
                FROM agent_logs
                WHERE task_id = ?
                ORDER BY id
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]


class ComponentVersionRepository:
    @staticmethod
    def _next_version(conn: sqlite3.Connection, book_id: str, chapter_index: int) -> int:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version_num), 0) AS max_version
            FROM component_versions
            WHERE book_id = ? AND chapter_index = ?
            """,
            (book_id, chapter_index),
        ).fetchone()
        return int(row["max_version"]) + 1

    @staticmethod
    def create_version(
        *,
        book_id: str,
        chapter_index: int,
        jsx_code: str,
        js_code: str,
        bundle_size: int,
    ) -> dict[str, Any]:
        with transaction() as conn:
            version_num = ComponentVersionRepository._next_version(conn, book_id, chapter_index)
            stable_exists = conn.execute(
                """
                SELECT 1
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ? AND is_stable = 1
                LIMIT 1
                """,
                (book_id, chapter_index),
            ).fetchone()

            conn.execute(
                """
                UPDATE component_versions
                SET is_latest = 0
                WHERE book_id = ? AND chapter_index = ?
                """,
                (book_id, chapter_index),
            )

            conn.execute(
                """
                INSERT INTO component_versions (
                    book_id,
                    chapter_index,
                    version_num,
                    is_latest,
                    is_stable,
                    jsx_code,
                    js_code,
                    bundle_size
                ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    book_id,
                    chapter_index,
                    version_num,
                    0 if stable_exists else 1,
                    jsx_code,
                    js_code,
                    bundle_size,
                ),
            )

            row = conn.execute(
                """
                SELECT book_id, chapter_index, version_num, is_latest, is_stable,
                       jsx_code, js_code, bundle_size, created_at
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ? AND version_num = ?
                """,
                (book_id, chapter_index, version_num),
            ).fetchone()

        payload = dict(row) if row else {}
        payload["is_latest"] = bool(payload.get("is_latest"))
        payload["is_stable"] = bool(payload.get("is_stable"))
        return payload

    @staticmethod
    def list_versions(book_id: str, chapter_index: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT book_id, chapter_index, version_num, is_latest, is_stable,
                       bundle_size, created_at
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ?
                ORDER BY version_num DESC
                """,
                (book_id, chapter_index),
            ).fetchall()
        versions = [dict(row) for row in rows]
        for version in versions:
            version["is_latest"] = bool(version["is_latest"])
            version["is_stable"] = bool(version["is_stable"])
        return versions

    @staticmethod
    def get_component(
        *, book_id: str, chapter_index: int, version: str = "latest"
    ) -> dict[str, Any] | None:
        predicate = "is_latest = 1"
        params: tuple[Any, ...] = (book_id, chapter_index)
        if version == "stable":
            predicate = "is_stable = 1"
        elif version == "latest":
            predicate = "is_latest = 1"
        else:
            predicate = "version_num = ?"
            params = (book_id, chapter_index, int(version))

        with get_connection() as conn:
            row = conn.execute(
                f"""
                SELECT book_id, chapter_index, version_num, is_latest, is_stable,
                       jsx_code, js_code, bundle_size, created_at
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ? AND {predicate}
                ORDER BY version_num DESC
                LIMIT 1
                """,
                params,
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["is_latest"] = bool(payload["is_latest"])
        payload["is_stable"] = bool(payload["is_stable"])
        return payload

    @staticmethod
    def rollback_to_stable(book_id: str, chapter_index: int) -> dict[str, Any] | None:
        with transaction() as conn:
            stable = conn.execute(
                """
                SELECT version_num
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ? AND is_stable = 1
                ORDER BY version_num DESC
                LIMIT 1
                """,
                (book_id, chapter_index),
            ).fetchone()
            if stable is None:
                return None

            stable_version = int(stable["version_num"])
            conn.execute(
                """
                UPDATE component_versions
                SET is_latest = CASE WHEN version_num = ? THEN 1 ELSE 0 END
                WHERE book_id = ? AND chapter_index = ?
                """,
                (stable_version, book_id, chapter_index),
            )

            row = conn.execute(
                """
                SELECT book_id, chapter_index, version_num, is_latest, is_stable,
                       jsx_code, js_code, bundle_size, created_at
                FROM component_versions
                WHERE book_id = ? AND chapter_index = ? AND version_num = ?
                """,
                (book_id, chapter_index, stable_version),
            ).fetchone()

        if row is None:
            return None
        payload = dict(row)
        payload["is_latest"] = bool(payload["is_latest"])
        payload["is_stable"] = bool(payload["is_stable"])
        return payload


class MetricsRepository:
    @staticmethod
    def task_metrics() -> dict[str, float | int]:
        with get_connection() as conn:
            total_tasks = int(conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"])
            succeeded_tasks = int(
                conn.execute("SELECT COUNT(*) AS c FROM tasks WHERE status = 'succeeded'").fetchone()[
                    "c"
                ]
            )
            retried_tasks = int(
                conn.execute(
                    """
                    SELECT COUNT(DISTINCT task_id) AS c
                    FROM task_steps
                    WHERE status = 'retrying'
                    """
                ).fetchone()["c"]
            )
            compile_total = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM task_steps WHERE stage = 'compile'"
                ).fetchone()["c"]
            )
            compile_failed = int(
                conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM task_steps
                    WHERE stage = 'compile' AND status = 'failed'
                    """
                ).fetchone()["c"]
            )
            latencies = [
                float(row["latency_ms"])
                for row in conn.execute(
                    """
                    SELECT latency_ms
                    FROM agent_logs
                    WHERE latency_ms IS NOT NULL AND latency_ms > 0
                    """
                ).fetchall()
            ]

        success_rate = (succeeded_tasks / total_tasks) if total_tasks else 0.0
        retry_rate = (retried_tasks / total_tasks) if total_tasks else 0.0
        compile_failure_rate = (compile_failed / compile_total) if compile_total else 0.0

        if not latencies:
            p95_latency = 0.0
        else:
            latencies.sort()
            index = max(0, int(round((len(latencies) - 1) * 0.95)))
            p95_latency = latencies[index]

        return {
            "total_tasks": total_tasks,
            "success_rate": round(success_rate, 4),
            "retry_rate": round(retry_rate, 4),
            "compile_failure_rate": round(compile_failure_rate, 4),
            "p95_latency_ms": round(p95_latency, 2),
        }

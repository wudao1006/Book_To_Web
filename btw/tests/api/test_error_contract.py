from __future__ import annotations

import httpx
import pytest

from btw.storage.db import BookRepository
from btw.storage import book_store, db


def _assert_error_contract(payload: dict) -> None:
    for field in ("code", "message", "stage", "retriable", "trace_id"):
        assert field in payload


@pytest.mark.asyncio
async def test_not_found_error_uses_contract(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    from btw.main import create_app

    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/books/not-exist",
            headers={"x-trace-id": "trace-not-found"},
        )
    assert response.status_code == 404
    payload = response.json()
    _assert_error_contract(payload)
    assert payload["trace_id"] == "trace-not-found"
    assert payload["stage"] == "upload"
    assert payload["retriable"] is False


@pytest.mark.asyncio
async def test_generate_missing_chapter_uses_contract(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    from btw.main import create_app

    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    markdown = b"# Chapter One\n\nDemand meets supply."

    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        upload = await client.post(
            "/api/books/upload",
            data={"title": "Smoke Book", "author": "Tester"},
            files={"file": ("smoke.md", markdown, "text/markdown")},
            headers={"x-trace-id": "trace-generate"},
        )
        book_id = upload.json()["book_id"]
        response = await client.post(
            f"/api/books/{book_id}/chapters/9/generate",
            headers={"x-trace-id": "trace-generate"},
        )

    assert response.status_code == 404
    payload = response.json()
    _assert_error_contract(payload)
    assert payload["trace_id"] == "trace-generate"
    assert payload["stage"] == "generate"


@pytest.mark.asyncio
async def test_internal_errors_are_sanitized(monkeypatch, tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"
    from btw.main import create_app

    def explode(book_id: str):
        del book_id
        raise RuntimeError("secret-internal-details")

    monkeypatch.setattr(BookRepository, "get_book", explode)

    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/books/book-1",
            headers={"x-trace-id": "trace-secret"},
        )

    assert response.status_code == 500
    payload = response.json()
    _assert_error_contract(payload)
    assert payload["code"] == "internal_error"
    assert payload["message"] == "Internal server error"
    assert payload["trace_id"] == "trace-secret"
    assert "secret-internal-details" not in response.text

from __future__ import annotations

import httpx
import pytest

from btw.storage import book_store, db


@pytest.mark.asyncio
async def test_api_smoke_upload_generate_and_fetch_component(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"

    from btw.main import create_app

    transport = httpx.ASGITransport(app=create_app())
    markdown = b"# Chapter One\n\nDemand meets supply."

    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        upload = await client.post(
            "/api/books/upload",
            data={"title": "Smoke Book", "author": "Tester"},
            files={"file": ("smoke.md", markdown, "text/markdown")},
        )
        assert upload.status_code == 200
        payload = upload.json()
        assert payload["status"] == "completed"

        book_id = payload["book_id"]
        chapters = await client.get(f"/api/books/{book_id}/chapters")
        assert chapters.status_code == 200
        assert len(chapters.json()["chapters"]) == 1

        generate = await client.post(f"/api/books/{book_id}/chapters/0/generate")
        assert generate.status_code == 200
        assert generate.json()["success"] is True

        component = await client.get(f"/api/books/{book_id}/chapters/0/component")
        assert component.status_code == 200
        component_payload = component.json()
        assert component_payload["type"] == "js"
        assert "module.exports" in component_payload["code"]

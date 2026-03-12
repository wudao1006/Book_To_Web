from __future__ import annotations

import httpx
import pytest

from btw.storage import book_store, db


@pytest.mark.asyncio
async def test_api_exposes_task_metrics_and_component_versions(tmp_path) -> None:
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
            data={"title": "Versioned Book", "author": "Tester"},
            files={"file": ("versioned.md", markdown, "text/markdown")},
        )
        assert upload.status_code == 200
        book_id = upload.json()["book_id"]

        first_generate = await client.post(f"/api/books/{book_id}/chapters/0/generate")
        assert first_generate.status_code == 200

        stable_component = await client.get(
            f"/api/books/{book_id}/chapters/0/component", params={"version": "stable"}
        )
        assert stable_component.status_code == 200
        stable_code = stable_component.json()["code"]

        chapter_path = book_store.DATA_DIR / book_id / "chapters" / "00" / "content.md"
        chapter_path.write_text("# Chart\n\nThis chart shows demand data and statistics.", encoding="utf-8")

        second_generate = await client.post(f"/api/books/{book_id}/chapters/0/generate")
        assert second_generate.status_code == 200

        latest_component = await client.get(
            f"/api/books/{book_id}/chapters/0/component", params={"version": "latest"}
        )
        assert latest_component.status_code == 200
        latest_code = latest_component.json()["code"]
        assert latest_code != stable_code

        versions = await client.get(f"/api/books/{book_id}/chapters/0/versions")
        assert versions.status_code == 200
        versions_payload = versions.json()
        assert versions_payload["latest"]["version_num"] == 2
        assert versions_payload["stable"]["version_num"] == 1
        assert len(versions_payload["versions"]) == 2

        rollback = await client.post(f"/api/books/{book_id}/chapters/0/rollback")
        assert rollback.status_code == 200
        assert rollback.json()["latest"]["version_num"] == 1

        latest_after_rollback = await client.get(
            f"/api/books/{book_id}/chapters/0/component", params={"version": "latest"}
        )
        assert latest_after_rollback.status_code == 200
        assert latest_after_rollback.json()["code"] == stable_code

        metrics = await client.get("/api/metrics/tasks")
        assert metrics.status_code == 200
        metrics_payload = metrics.json()
        assert metrics_payload["total_tasks"] >= 4
        assert "success_rate" in metrics_payload
        assert "retry_rate" in metrics_payload
        assert "compile_failure_rate" in metrics_payload
        assert "p95_latency_ms" in metrics_payload

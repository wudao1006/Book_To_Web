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
        assert payload["task_id"]
        upload_task_id = payload["task_id"]

        book_id = payload["book_id"]
        upload_task = await client.get(f"/api/tasks/{upload_task_id}")
        assert upload_task.status_code == 200
        assert upload_task.json()["status"] == "succeeded"

        upload_steps = await client.get(f"/api/tasks/{upload_task_id}/steps")
        assert upload_steps.status_code == 200
        assert [step["stage"] for step in upload_steps.json()["steps"]] == ["parse", "read"]
        assert all(step["status"] == "succeeded" for step in upload_steps.json()["steps"])

        chapters = await client.get(f"/api/books/{book_id}/chapters")
        assert chapters.status_code == 200
        assert len(chapters.json()["chapters"]) == 1

        generate = await client.post(f"/api/books/{book_id}/chapters/0/generate")
        assert generate.status_code == 200
        generate_payload = generate.json()
        assert generate_payload["success"] is True

        generate_task_id = generate_payload["task_id"]
        generate_task = await client.get(f"/api/tasks/{generate_task_id}")
        assert generate_task.status_code == 200
        assert generate_task.json()["status"] == "succeeded"

        generate_steps = await client.get(f"/api/tasks/{generate_task_id}/steps")
        assert generate_steps.status_code == 200
        assert [step["stage"] for step in generate_steps.json()["steps"]] == [
            "create",
            "critic",
            "validate",
            "compile",
        ]
        assert all(step["status"] == "succeeded" for step in generate_steps.json()["steps"])

        component = await client.get(f"/api/books/{book_id}/chapters/0/component")
        assert component.status_code == 200
        component_payload = component.json()
        assert component_payload["type"] == "js"
        assert "module.exports" in component_payload["code"]


@pytest.mark.asyncio
async def test_api_skills_lists_registered_skills(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    book_store.DATA_DIR = tmp_path / "data" / "books"

    from btw.main import create_app

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/skills")

    assert response.status_code == 200
    payload = response.json()
    skills = payload["skills"]
    assert isinstance(skills, list)
    assert any(skill["name"] == "llm_call" for skill in skills)
    assert any(skill["name"] == "code_validate" for skill in skills)
    assert any(skill["name"] == "code_compile" for skill in skills)

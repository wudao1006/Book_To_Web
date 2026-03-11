from __future__ import annotations

import pytest

from btw.agents.director import DirectorAgent


@pytest.mark.asyncio
async def test_director_rejects_unknown_action() -> None:
    director = DirectorAgent(config={})
    result = await director.process({"action": "unknown", "trace_id": "trace-001"})
    assert "error" in result
    error = result["error"]
    assert error["code"] == "unknown_action"
    assert error["stage"] == "dispatch"
    assert error["retriable"] is False
    assert error["trace_id"] == "trace-001"


@pytest.mark.asyncio
async def test_director_preserves_validation_issues(monkeypatch, tmp_path) -> None:
    director = DirectorAgent(config={})

    class FakeCreator:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {"jsx_code": "export default function Demo(){ return <div/>; }"}

    class FakeEngineer:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {
                "success": False,
                "stage": "validation",
                "issues": ["import_not_allowed:echarts-for-react"],
            }

    chapter_dir = tmp_path / "book-1" / "chapters" / "00"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "content.md").write_text("chapter", encoding="utf-8")

    def fake_create(name: str):
        if name == "creator":
            return FakeCreator()
        if name == "engineer":
            return FakeEngineer()
        raise AssertionError(name)

    monkeypatch.setattr(director.registry, "create", fake_create)
    monkeypatch.setattr("btw.agents.director.book_store.DATA_DIR", tmp_path)

    result = await director.process(
        {
            "action": "generate_component",
            "book_id": "book-1",
            "chapter_index": 0,
            "trace_id": "trace-validation",
        }
    )

    error = result["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Validation failed"
    assert error["details"]["issues"] == ["import_not_allowed:echarts-for-react"]


@pytest.mark.asyncio
async def test_director_sanitizes_upload_pipeline_errors(monkeypatch) -> None:
    director = DirectorAgent(config={})

    class ExplodingParser:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            raise RuntimeError("secret-upload-details")

    def fake_create(name: str):
        if name == "parser":
            return ExplodingParser()
        raise AssertionError(name)

    monkeypatch.setattr(director.registry, "create", fake_create)

    result = await director.process(
        {
            "action": "upload_book",
            "book_id": "book-1",
            "file_path": "/tmp/book.md",
            "trace_id": "trace-upload",
        }
    )

    error = result["error"]
    assert error["code"] == "upload_pipeline_failed"
    assert error["message"] == "Upload pipeline failed"
    assert "secret-upload-details" not in error["message"]

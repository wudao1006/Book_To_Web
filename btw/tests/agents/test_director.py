from __future__ import annotations

import pytest

from btw.agents.director import DirectorAgent
from btw.storage import db


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path) -> None:
    db.DB_PATH = tmp_path / "data" / "btw.db"
    db.init_db()


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

    class FakeCritic:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {"approved": True, "issues": [], "repair_prompt": ""}

    chapter_dir = tmp_path / "book-1" / "chapters" / "00"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "content.md").write_text("chapter", encoding="utf-8")

    def fake_create(name: str):
        if name == "creator":
            return FakeCreator()
        if name == "critic":
            return FakeCritic()
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


@pytest.mark.asyncio
async def test_director_quality_loop_retries_once(monkeypatch, tmp_path) -> None:
    director = DirectorAgent(config={})
    create_calls: list[dict] = []

    class FakeCreator:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            create_calls.append(input_data)
            if input_data.get("quality_feedback"):
                return {
                    "jsx_code": "export default function Demo(){ return <article>fixed</article>; }",
                    "component_type": "narrative",
                    "dependencies": ["react"],
                }
            return {
                "jsx_code": "export default function Demo(){ return <div>draft</div>; }",
                "component_type": "narrative",
                "dependencies": ["react"],
            }

    class FakeCritic:
        def __init__(self) -> None:
            self.calls = 0

        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            self.calls += 1
            if self.calls == 1:
                return {
                    "approved": False,
                    "issues": ["semantic_structure_missing"],
                    "repair_prompt": "Use <article> for narrative output.",
                }
            return {"approved": True, "issues": [], "repair_prompt": ""}

    class FakeEngineer:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {
                "success": True,
                "stage": "compile",
                "issues": [],
                "jsx_path": "/tmp/component.jsx",
                "js_path": "/tmp/component.js",
                "bundle_size": 128,
            }

    critic = FakeCritic()

    chapter_dir = tmp_path / "book-1" / "chapters" / "00"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "content.md").write_text("chapter", encoding="utf-8")

    def fake_create(name: str):
        if name == "creator":
            return FakeCreator()
        if name == "critic":
            return critic
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
            "trace_id": "trace-quality-retry",
        }
    )

    assert result["success"] is True
    assert result["quality_retry_count"] == 1
    assert len(create_calls) == 2
    assert "quality_feedback" in create_calls[1]

    steps = db.TaskRepository.list_steps(result["task_id"])
    assert [step["stage"] for step in steps] == ["create", "critic", "validate", "compile"]
    assert all(step["status"] == "succeeded" for step in steps)


@pytest.mark.asyncio
async def test_director_returns_quality_gate_error_after_retry(monkeypatch, tmp_path) -> None:
    director = DirectorAgent(config={})

    class FakeCreator:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {
                "jsx_code": "export default function Demo(){ return <div>draft</div>; }",
                "component_type": "narrative",
                "dependencies": ["react"],
            }

    class FakeCritic:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {
                "approved": False,
                "issues": ["semantic_structure_missing"],
                "repair_prompt": "Use <article> for narrative output.",
            }

    class FakeEngineer:
        def set_context(self, context) -> None:
            del context

        async def process(self, input_data):
            del input_data
            return {"success": True, "stage": "compile", "bundle_size": 1}

    def fake_create(name: str):
        if name == "creator":
            return FakeCreator()
        if name == "critic":
            return FakeCritic()
        if name == "engineer":
            return FakeEngineer()
        raise AssertionError(name)

    chapter_dir = tmp_path / "book-1" / "chapters" / "00"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "content.md").write_text("chapter", encoding="utf-8")

    monkeypatch.setattr(director.registry, "create", fake_create)
    monkeypatch.setattr("btw.agents.director.book_store.DATA_DIR", tmp_path)

    result = await director.process(
        {
            "action": "generate_component",
            "book_id": "book-1",
            "chapter_index": 0,
            "trace_id": "trace-quality-failed",
        }
    )

    error = result["error"]
    assert error["code"] == "quality_gate_failed"
    assert error["stage"] == "critic"
    assert error["details"]["issues"] == ["semantic_structure_missing"]

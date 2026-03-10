from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from btw.agents.base import Agent, AgentContext, get_registry
from btw.storage import book_store
from btw.storage.book_store import get_component_paths


class DirectorAgent(Agent):
    """Coordinates the end-to-end workflow across agents."""

    name = "director"
    description = "Orchestrates BTW agent workflows."

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.registry = get_registry()

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action", ""))
        task_id = str(uuid.uuid4())
        if action == "upload_book":
            return await self._handle_upload(task_id, input_data)
        if action == "generate_component":
            return await self._handle_generate(task_id, input_data)
        if action == "get_component":
            return await self._handle_get_component(task_id, input_data)
        return {"error": f"Unknown action: {action}"}

    async def _handle_upload(
        self, task_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        book_id = str(input_data["book_id"])
        file_path = str(input_data["file_path"])

        parser = self.registry.create("parser")
        parser.set_context(AgentContext(task_id=task_id, book_id=book_id))
        parse_result = await parser.process({"book_id": book_id, "file_path": file_path})

        reader = self.registry.create("reader")
        reader.set_context(AgentContext(task_id=task_id, book_id=book_id))
        read_result = await reader.process(
            {"book_id": book_id, "chapters": parse_result.get("chapters", [])}
        )

        return {
            "task_id": task_id,
            "book_id": book_id,
            "chapters_count": parse_result.get("total_chapters", 0),
            "concepts": read_result.get("concepts", []),
            "status": "completed",
        }

    async def _handle_generate(
        self, task_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        book_id = str(input_data["book_id"])
        chapter_index = int(input_data["chapter_index"])
        content_path = (
            book_store.DATA_DIR / book_id / "chapters" / f"{chapter_index:02d}" / "content.md"
        )
        if not content_path.exists():
            return {"error": "Chapter not found"}

        creator = self.registry.create("creator")
        creator.set_context(AgentContext(task_id=task_id, book_id=book_id))
        create_result = await creator.process(
            {
                "book_id": book_id,
                "chapter_index": chapter_index,
                "content": content_path.read_text(encoding="utf-8"),
            }
        )

        engineer = self.registry.create("engineer")
        engineer.set_context(AgentContext(task_id=task_id, book_id=book_id))
        engineer_result = await engineer.process(
            {
                "book_id": book_id,
                "chapter_index": chapter_index,
                "jsx_code": create_result["jsx_code"],
            }
        )
        return {"task_id": task_id, "book_id": book_id, "chapter_index": chapter_index, **engineer_result}

    async def _handle_get_component(
        self, task_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        del task_id
        book_id = str(input_data["book_id"])
        chapter_index = int(input_data["chapter_index"])
        jsx_path, js_path = get_component_paths(book_id, chapter_index)
        if js_path.exists():
            return {"exists": True, "type": "js", "code": js_path.read_text(encoding="utf-8")}
        if jsx_path.exists():
            return {"exists": True, "type": "jsx", "code": jsx_path.read_text(encoding="utf-8")}
        return {"exists": False, "message": "Component not generated yet"}

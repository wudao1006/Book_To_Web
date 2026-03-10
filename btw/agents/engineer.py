from __future__ import annotations

from pathlib import Path
from typing import Any

from btw.agents.base import Agent
from btw.storage import book_store
from btw.skills.base import get_skill_registry
from btw.skills.code_compile import CodeCompileSkill
from btw.skills.code_validate import CodeValidateSkill


class EngineerAgent(Agent):
    """Validates and materializes generated component code."""

    name = "engineer"
    description = "Validates and compiles generated chapter components."

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        jsx_code = input_data.get("jsx_code", "")
        book_id = str(input_data.get("book_id", ""))
        chapter_index = int(input_data.get("chapter_index", 0))

        registry = get_skill_registry()
        validator = self._create_skill(registry, "code_validate", CodeValidateSkill)
        validation = await validator.execute(code=jsx_code)
        if not validation["valid"]:
            return {
                "success": False,
                "stage": "validation",
                "issues": validation["issues"],
            }

        chapter_dir = self._resolve_chapter_dir(book_id, chapter_index)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        jsx_path = chapter_dir / "component.jsx"
        jsx_path.write_text(jsx_code, encoding="utf-8")

        compiler = self._create_skill(registry, "code_compile", CodeCompileSkill)
        compile_result = await compiler.execute(
            jsx_code=jsx_code,
            output_path=str(chapter_dir / "component.js"),
        )
        if not compile_result["success"]:
            return {
                "success": False,
                "stage": "compile",
                "error": compile_result["error"],
            }

        return {
            "success": True,
            "stage": "compile",
            "issues": validation["issues"],
            "jsx_path": str(jsx_path),
            "js_path": compile_result["output_path"],
            "bundle_size": compile_result["bundle_size"],
        }

    @staticmethod
    def _create_skill(registry, name: str, skill_class):
        try:
            return registry.create(name)
        except KeyError:
            registry.register(skill_class)
            return registry.create(name)

    def _resolve_chapter_dir(self, book_id: str, chapter_index: int) -> Path:
        workspace_dir = self.config.get("workspace_dir")
        if workspace_dir:
            base_dir = Path(workspace_dir)
        else:
            base_dir = book_store.DATA_DIR
        return base_dir / book_id / "chapters" / f"{chapter_index:02d}"

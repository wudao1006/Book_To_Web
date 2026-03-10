from __future__ import annotations

from pathlib import Path
from typing import Any

from btw.agents.base import Agent
from btw.skills.base import get_skill_registry
from btw.skills.llm_call import LLMCallSkill


class CreatorAgent(Agent):
    """Generates interactive React components from chapter content."""

    name = "creator"
    description = "Creates interactive chapter components."

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.llm_config = self.config.get("llm", {"provider": "claude"})

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        content = input_data.get("content", "")
        content_type = self._analyze_content_type(content)
        prompt = self._build_prompt(content, content_type)

        registry = get_skill_registry()
        try:
            llm_skill = registry.create("llm_call")
        except KeyError:
            registry.register(LLMCallSkill)
            llm_skill = registry.create("llm_call")

        result = await llm_skill.execute(
            messages=[
                {"role": "system", "content": self._load_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            **self.llm_config,
        )
        jsx_code = self._extract_jsx(result.get("content", ""))
        return {
            "book_id": input_data.get("book_id"),
            "chapter_index": input_data.get("chapter_index"),
            "component_type": content_type,
            "jsx_code": jsx_code,
            "dependencies": self._extract_dependencies(jsx_code),
        }

    def _analyze_content_type(self, content: str) -> str:
        lowered = content.lower()
        if "```" in content or "code" in lowered:
            return "code"
        if any(token in lowered for token in ("equation", "formula", " = ", "variable")):
            return "formula"
        if any(token in lowered for token in ("chart", "graph", "data", "statistics")):
            return "chart"
        return "narrative"

    def _build_prompt(self, content: str, content_type: str) -> str:
        return "\n".join(
            [
                f"Content type: {content_type}",
                "Turn the following chapter excerpt into an interactive React component.",
                content[:2000],
            ]
        )

    def _load_system_prompt(self) -> str:
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "prompts"
            / "creator_system.txt"
        )
        return prompt_path.read_text(encoding="utf-8")

    def _extract_jsx(self, response: str) -> str:
        stripped = response.strip()
        if "```" not in stripped:
            return stripped

        for chunk in stripped.split("```"):
            candidate = chunk.strip()
            if candidate.startswith(("jsx", "javascript", "tsx")):
                return candidate.split("\n", 1)[1].strip()
            if "export default function" in candidate:
                return candidate
        return stripped

    def _extract_dependencies(self, jsx_code: str) -> list[str]:
        deps = ["react"]
        lowered = jsx_code.lower()
        if "echarts" in lowered:
            deps.extend(["echarts", "echarts-for-react"])
        if "katex" in lowered:
            deps.append("katex")
        if "framer-motion" in lowered or "motion." in lowered:
            deps.append("framer-motion")
        return deps

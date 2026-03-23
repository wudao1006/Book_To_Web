from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from btw.agents.base import Agent
from btw.skills.base import get_skill_registry
from btw.skills.llm_call import LLMCallSkill
from btw.storage.db import AICacheRepository


class CreatorAgent(Agent):
    """Generates interactive React components from chapter content."""

    name = "creator"
    description = "Creates interactive chapter components."

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.llm_config = self.config.get(
            "llm",
            {
                "provider": "claude",
                "route_policy": "fast_then_strong",
            },
        )
        self.enable_cache = bool(self.config.get("enable_cache", True))

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        content = str(input_data.get("content", ""))
        quality_feedback = str(input_data.get("quality_feedback", "")).strip() or None
        content_type = self._analyze_content_type(content)

        prompt = self._build_prompt(content, content_type, quality_feedback=quality_feedback)
        system_prompt = self._load_system_prompt(content_type)
        prompt_hash = self._prompt_hash(system_prompt, prompt, self.llm_config)

        cache_hit = False
        llm_model = str(self.llm_config.get("model") or "")
        token_cost = 0.0

        cached = AICacheRepository.get(prompt_hash) if self.enable_cache else None
        if cached is not None and str(cached.get("result", "")).strip():
            llm_content = str(cached["result"])
            llm_model = str(cached.get("model") or llm_model)
            cache_hit = True
        else:
            registry = get_skill_registry()
            try:
                llm_skill = registry.create("llm_call")
            except KeyError:
                registry.register(LLMCallSkill)
                llm_skill = registry.create("llm_call")

            result = await llm_skill.execute(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                **self.llm_config,
            )
            if result.get("error"):
                raise RuntimeError(f"llm_call_failed:{result['error']}")
            llm_content = str(result.get("content", ""))
            if not llm_content.strip():
                raise RuntimeError("llm_call_failed:empty_response")
            llm_model = str(result.get("model") or llm_model)
            token_cost = float(result.get("token_cost", 0.0) or 0.0)
            if self.enable_cache:
                AICacheRepository.upsert(prompt_hash, llm_model, llm_content)

        jsx_code = self._extract_jsx(llm_content)
        return {
            "book_id": input_data.get("book_id"),
            "chapter_index": input_data.get("chapter_index"),
            "component_type": content_type,
            "jsx_code": jsx_code,
            "dependencies": self._extract_dependencies(jsx_code),
            "cache_hit": cache_hit,
            "model": llm_model,
            "token_cost": token_cost,
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

    def _build_prompt(
        self,
        content: str,
        content_type: str,
        *,
        quality_feedback: str | None,
    ) -> str:
        template = self._load_template(content_type)
        sections = [
            f"Content type: {content_type}",
            "Template guidance:",
            template,
            "Chapter excerpt:",
            content[:2000],
        ]
        if quality_feedback:
            sections.extend(
                [
                    "Quality feedback from Critic:",
                    quality_feedback,
                    "Revise the component to satisfy the feedback in one pass.",
                ]
            )
        return "\n\n".join(sections)

    def _load_template(self, content_type: str) -> str:
        template_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "prompts"
            / "component_templates"
            / f"{content_type}.txt"
        )
        if template_path.exists():
            return template_path.read_text(encoding="utf-8").strip()
        return "Return one default-export React component with no external imports except react."

    def _load_system_prompt(self, content_type: str) -> str:
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "prompts"
            / "creator_system.txt"
        )
        base_prompt = prompt_path.read_text(encoding="utf-8").strip()
        return f"{base_prompt}\n\nTarget component type: {content_type}."

    def _prompt_hash(self, system_prompt: str, prompt: str, llm_config: dict[str, Any]) -> str:
        payload = {
            "system_prompt": system_prompt,
            "prompt": prompt,
            "llm_config": llm_config,
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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
        return sorted(set(deps))

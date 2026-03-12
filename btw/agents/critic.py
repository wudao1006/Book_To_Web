from __future__ import annotations

from typing import Any

from btw.agents.base import Agent


class CriticAgent(Agent):
    name = "critic"
    description = "Reviews generated chapter experiences."

    SENSITIVE_PATTERNS = (
        "eval(",
        "Function(",
        "document.cookie",
        "window.fetch",
        "fetch(",
        "localStorage",
        "sessionStorage",
    )

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        component_type = str(input_data.get("component_type") or "narrative")
        jsx_code = str(input_data.get("jsx_code") or "")

        issues = self._base_issues(jsx_code)
        issues.extend(self._component_issues(component_type, jsx_code))
        # Preserve issue order and remove duplicates.
        issues = list(dict.fromkeys(issues))

        approved = len(issues) == 0
        return {
            "agent": self.name,
            "approved": approved,
            "issues": issues,
            "score": max(0.0, 1.0 - min(len(issues), 10) * 0.1),
            "repair_prompt": "" if approved else self._build_repair_prompt(component_type, issues),
        }

    def _base_issues(self, jsx_code: str) -> list[str]:
        issues: list[str] = []
        stripped = jsx_code.strip()
        if not stripped:
            issues.append("empty_component")
            return issues
        if "export default function" not in stripped:
            issues.append("missing_default_export")
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in stripped:
                issues.append(f"unsafe_pattern:{pattern}")
        return issues

    def _component_issues(self, component_type: str, jsx_code: str) -> list[str]:
        lowered = jsx_code.lower()
        issues: list[str] = []
        if component_type == "narrative":
            if "<article" not in lowered and "<section" not in lowered:
                issues.append("semantic_structure_missing")
        elif component_type == "chart":
            if all(token not in lowered for token in ("chart", "echarts", "canvas", "svg")):
                issues.append("chart_affordance_missing")
        elif component_type == "formula":
            if all(token not in lowered for token in ("formula", "equation", "katex", "math")):
                issues.append("formula_rendering_missing")
        elif component_type == "code":
            if "<pre" not in lowered and "<code" not in lowered:
                issues.append("code_block_missing")
        return issues

    def _build_repair_prompt(self, component_type: str, issues: list[str]) -> str:
        joined = ", ".join(issues)
        return (
            f"Fix the generated {component_type} component. "
            f"Address these issues exactly: {joined}. "
            "Keep a single default-export React component and avoid any sensitive globals or network calls."
        )

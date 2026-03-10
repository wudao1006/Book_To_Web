from __future__ import annotations

from btw.skills.base import Skill


class CodeValidateSkill(Skill):
    """Performs low-cost string-based safety checks for generated JSX."""

    name = "code_validate"
    description = "Validates generated JSX before compilation."

    DANGEROUS_PATTERNS = (
        "eval(",
        "Function(",
        "document.cookie",
        "localStorage",
        "sessionStorage",
        "fetch(",
        "XMLHttpRequest",
    )

    async def execute(self, **kwargs) -> dict:
        code = kwargs.get("code", "")
        issues = [
            f"disallowed pattern: {pattern}"
            for pattern in self.DANGEROUS_PATTERNS
            if pattern in code
        ]
        return {
            "valid": not issues and bool(code.strip()),
            "issues": issues or ([] if code.strip() else ["empty code"]),
            "code_length": len(code),
        }

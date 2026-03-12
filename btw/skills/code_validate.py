from __future__ import annotations
import json
import subprocess
import tempfile
from pathlib import Path

from btw.skills.base import Skill


class CodeValidateSkill(Skill):
    """Performs low-cost string-based safety checks for generated JSX."""

    name = "code_validate"
    description = "Validates generated JSX before compilation."

    AST_TIMEOUT_SECONDS = 5
    RUNTIME_FAILURE_PREFIX = "validator_runtime_unavailable"
    DANGEROUS_PATTERNS = (
        "eval(",
        "Function(",
        "document.cookie",
        "fetch(",
        "localStorage",
        "sessionStorage",
    )

    async def execute(self, **kwargs) -> dict:
        code = kwargs.get("code", "")
        raw_issues = [
            f"disallowed pattern: {pattern}"
            for pattern in self.DANGEROUS_PATTERNS
            if pattern in code
        ]
        ast_result = self._ast_issues(code)
        ast_issues = ast_result["issues"]
        warnings = ast_result["warnings"]
        issues = list(dict.fromkeys(raw_issues + ast_issues))
        return {
            "valid": not issues and bool(code.strip()),
            "issues": issues or ([] if code.strip() else ["empty code"]),
            "code_length": len(code),
            "warnings": warnings,
        }

    def _ast_issues(self, code: str) -> dict[str, list[str]]:
        if not code.strip():
            return {"issues": [], "warnings": []}
        validator_script = Path(__file__).with_name("js_ast_validate.mjs")
        frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
        if not validator_script.exists():
            return {
                "issues": [self._runtime_issue("ast_validator_missing")],
                "warnings": [],
            }
        if not frontend_dir.exists():
            return {
                "issues": [self._runtime_issue("frontend_workspace_missing")],
                "warnings": [],
            }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsx", encoding="utf-8", delete=False
        ) as handle:
            handle.write(code)
            code_path = Path(handle.name)

        try:
            result = subprocess.run(
                ["node", str(validator_script), str(code_path)],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.AST_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                warning = result.stderr.strip() or result.stdout.strip() or "unknown"
                return {
                    "issues": [self._runtime_issue(f"ast_validator_failed:{warning}")],
                    "warnings": [],
                }
            payload = json.loads(result.stdout or "{}")
            issues = payload.get("issues", [])
            return {"issues": [str(issue) for issue in issues], "warnings": []}
        except FileNotFoundError:
            return {"issues": [self._runtime_issue("node_runtime_missing")], "warnings": []}
        except subprocess.TimeoutExpired:
            return {"issues": [self._runtime_issue("ast_validator_timeout")], "warnings": []}
        except json.JSONDecodeError:
            return {
                "issues": [self._runtime_issue("ast_validator_invalid_output")],
                "warnings": [],
            }
        finally:
            code_path.unlink(missing_ok=True)

    def _runtime_issue(self, reason: str) -> str:
        return f"{self.RUNTIME_FAILURE_PREFIX}:{reason}"

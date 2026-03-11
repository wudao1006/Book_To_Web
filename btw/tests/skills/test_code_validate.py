from __future__ import annotations

import json
import subprocess

import pytest

from btw.skills.code_validate import CodeValidateSkill


@pytest.mark.asyncio
async def test_code_validate_allows_safe_component() -> None:
    validator = CodeValidateSkill()
    result = await validator.execute(
        code="export default function Demo(){ return <div>safe</div>; }"
    )
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_code_validate_rejects_disallowed_import() -> None:
    validator = CodeValidateSkill()
    result = await validator.execute(
        code="import fs from 'fs'; export default function Demo(){ return <div/>; }"
    )
    assert result["valid"] is False
    assert any("import_not_allowed" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_code_validate_rejects_network_call() -> None:
    validator = CodeValidateSkill()
    result = await validator.execute(
        code="export default function Demo(){ fetch('/api'); return <div/>; }"
    )
    assert result["valid"] is False
    assert any("network_call_blocked" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_code_validate_rejects_runtime_only_dependencies() -> None:
    validator = CodeValidateSkill()
    result = await validator.execute(
        code="import Chart from 'echarts-for-react'; export default function Demo(){ return <Chart />; }"
    )
    assert result["valid"] is False
    assert any("import_not_allowed" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_code_validate_rejects_when_node_runtime_missing(monkeypatch) -> None:
    validator = CodeValidateSkill()

    def fake_run(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = await validator.execute(
        code="export default function Demo(){ return <div>safe</div>; }"
    )

    assert result["valid"] is False
    assert "validator_runtime_unavailable:node_runtime_missing" in result["issues"]


@pytest.mark.asyncio
async def test_code_validate_uses_timeout_for_ast_subprocess(monkeypatch) -> None:
    validator = CodeValidateSkill()
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")

        class CompletedProcess:
            returncode = 0
            stdout = json.dumps({"valid": True, "issues": []})
            stderr = ""

        return CompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = await validator.execute(
        code="export default function Demo(){ return <div>safe</div>; }"
    )

    assert result["valid"] is True
    assert captured["timeout"] == 5


@pytest.mark.asyncio
async def test_code_validate_rejects_when_ast_validator_times_out(monkeypatch) -> None:
    validator = CodeValidateSkill()

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="node", timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = await validator.execute(
        code="export default function Demo(){ return <div>safe</div>; }"
    )

    assert result["valid"] is False
    assert "validator_runtime_unavailable:ast_validator_timeout" in result["issues"]

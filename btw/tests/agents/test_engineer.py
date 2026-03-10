from pathlib import Path

import pytest

from btw.agents.engineer import EngineerAgent


@pytest.mark.asyncio
async def test_engineer_rejects_dangerous_code(tmp_path: Path):
    engineer = EngineerAgent(config={"workspace_dir": str(tmp_path)})

    result = await engineer.process(
        {
            "jsx_code": "export default function Demo() { eval('boom'); return <div />; }",
            "book_id": "book-unsafe",
            "chapter_index": 0,
        }
    )

    assert result["success"] is False
    assert result["stage"] == "validation"
    assert result["issues"]


@pytest.mark.asyncio
async def test_engineer_writes_artifacts_for_safe_code(tmp_path: Path):
    engineer = EngineerAgent(config={"workspace_dir": str(tmp_path)})

    result = await engineer.process(
        {
            "jsx_code": "export default function Demo() { return <div>safe</div>; }",
            "book_id": "book-safe",
            "chapter_index": 1,
        }
    )

    assert result["success"] is True
    assert Path(result["jsx_path"]).exists()
    assert Path(result["js_path"]).exists()
    assert result["bundle_size"] > 0
    compiled = Path(result["js_path"]).read_text(encoding="utf-8")
    assert "module.exports" in compiled
    assert "<div>safe</div>" not in compiled

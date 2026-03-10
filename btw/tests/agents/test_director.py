from __future__ import annotations

import pytest

from btw.agents.director import DirectorAgent


@pytest.mark.asyncio
async def test_director_rejects_unknown_action() -> None:
    director = DirectorAgent(config={})
    result = await director.process({"action": "unknown"})
    assert result == {"error": "Unknown action: unknown"}

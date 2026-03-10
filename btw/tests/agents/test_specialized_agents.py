from __future__ import annotations

import pytest

from btw.agents import get_registry
from btw.agents.base import AgentContext


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_name", "capability"),
    [
        ("guardian", "safety"),
        ("retriever", "retrieval"),
        ("planner", "planning"),
        ("stylist", "style"),
        ("illustrator", "art"),
        ("critic", "review"),
        ("translator", "adaptation"),
        ("conductor", "orchestration"),
        ("companion", "guidance"),
        ("persona", "roleplay"),
        ("evolver", "optimization"),
        ("curator", "curation"),
    ],
)
async def test_specialized_agents_expose_capability(
    agent_name: str, capability: str
) -> None:
    agent = get_registry().create(agent_name)
    agent.set_context(AgentContext(task_id="task-001", book_id="book-001"))

    result = await agent.process({"prompt": "ping"})

    assert result["agent"] == agent_name
    assert result["status"] == "placeholder"
    assert result["capability"] == capability

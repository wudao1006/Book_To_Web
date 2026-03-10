from __future__ import annotations

from btw.agents import ALL_AGENT_CLASSES, get_registry


def test_all_agents_registered() -> None:
    registry = get_registry()
    registered = set(registry.list_agents())
    expected = {agent_class.name for agent_class in ALL_AGENT_CLASSES}
    assert expected.issubset(registered)

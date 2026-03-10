import pytest

from btw.agents.base import Agent, AgentRegistry


class DemoAgent(Agent):
    name = "test_agent"

    async def process(self, input_data: dict) -> dict:
        return {"result": "test", "input": input_data}


def test_agent_registry_registers_class() -> None:
    registry = AgentRegistry()

    registry.register(DemoAgent)

    assert "test_agent" in registry.agents
    assert registry.get("test_agent") is DemoAgent


def test_agent_registry_creates_instance_with_config() -> None:
    registry = AgentRegistry()
    registry.register(DemoAgent)

    agent = registry.create("test_agent", config={"key": "value"})

    assert isinstance(agent, DemoAgent)
    assert agent.config == {"key": "value"}


@pytest.mark.asyncio
async def test_agent_process_returns_expected_payload() -> None:
    agent = DemoAgent(config={})

    result = await agent.process({"test": "data"})

    assert result["result"] == "test"
    assert result["input"]["test"] == "data"

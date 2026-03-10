from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type


@dataclass
class AgentContext:
    """Execution metadata shared across agent invocations."""

    task_id: str
    book_id: str | None = None
    chapter_id: str | None = None
    retry_count: int = 0


class Agent(ABC):
    """Base type for all BTW agents."""

    name: str = "base_agent"
    description: str = "Base agent class"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.context: AgentContext | None = None

    def set_context(self, context: AgentContext) -> None:
        self.context = context

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process input data and return a structured payload."""

    async def on_error(
        self, error: Exception, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        raise error


class AgentRegistry:
    """Registry for available agent classes."""

    def __init__(self):
        self.agents: dict[str, Type[Agent]] = {}

    def register(self, agent_class: Type[Agent]) -> None:
        self.agents[agent_class.name] = agent_class

    def get(self, name: str) -> Type[Agent]:
        if name not in self.agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self.agents[name]

    def create(self, name: str, config: dict[str, Any] | None = None) -> Agent:
        agent_class = self.get(name)
        return agent_class(config=config)

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())


_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry

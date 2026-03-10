from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type


@dataclass
class ChatMessage:
    role: str
    content: str


class LLMAdapter(ABC):
    """Base adapter interface for model providers."""

    name: str = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url")
        self.model = config.get("model", self.default_model())

    @abstractmethod
    def default_model(self) -> str:
        """Return the adapter's default model name."""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Generate text from chat messages."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for text inputs."""


class AdapterRegistry:
    """Registry for LLM adapters."""

    def __init__(self):
        self.adapters: dict[str, Type[LLMAdapter]] = {}

    def register(self, adapter_class: Type[LLMAdapter]) -> None:
        self.adapters[adapter_class.name] = adapter_class

    def get(self, name: str) -> Type[LLMAdapter]:
        if name not in self.adapters:
            raise KeyError(f"Adapter '{name}' not registered")
        return self.adapters[name]

    def create(self, name: str, config: dict[str, Any]) -> LLMAdapter:
        adapter_class = self.get(name)
        return adapter_class(config)

    def list_adapters(self) -> list[str]:
        return list(self.adapters.keys())


_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry

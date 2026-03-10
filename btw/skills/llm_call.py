from __future__ import annotations

from btw.models.base import get_adapter_registry
from btw.skills.base import Skill


class LLMCallSkill(Skill):
    """Local placeholder LLM dispatcher."""

    name = "llm_call"
    description = "Dispatches requests to a configured LLM adapter."
    parameters = {
        "messages": {"type": "array"},
        "provider": {"type": "string"},
        "model": {"type": "string"},
    }

    async def execute(self, **kwargs) -> dict:
        provider = kwargs.get("provider", "claude")
        model = kwargs.get("model")
        messages = kwargs.get("messages", [])

        adapter = self._create_adapter(provider, model)
        content = await adapter.chat(messages)

        return {
            "content": content,
            "provider": provider,
            "model": adapter.model,
        }

    def _create_adapter(self, provider: str, model: str | None):
        registry = get_adapter_registry()
        try:
            return registry.create(provider, {"api_key": "", "model": model})
        except KeyError:
            adapter_class = self._load_adapter_class(provider)
            registry.register(adapter_class)
            return registry.create(provider, {"api_key": "", "model": model})

    @staticmethod
    def _load_adapter_class(provider: str):
        if provider == "openai":
            from btw.models.openai_adapter import OpenAIAdapter

            return OpenAIAdapter
        if provider == "ollama":
            from btw.models.ollama_adapter import OllamaAdapter

            return OllamaAdapter

        from btw.models.claude_adapter import ClaudeAdapter

        return ClaudeAdapter

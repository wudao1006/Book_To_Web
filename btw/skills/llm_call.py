from __future__ import annotations

from typing import Any

from btw.models.base import get_adapter_registry
from btw.skills.base import Skill


class LLMCallSkill(Skill):
    """Local placeholder LLM dispatcher with model routing."""

    name = "llm_call"
    description = "Dispatches requests to a configured LLM adapter."
    parameters = {
        "messages": {"type": "array"},
        "provider": {"type": "string"},
        "model": {"type": "string"},
        "route_policy": {"type": "string"},
    }

    async def execute(self, **kwargs) -> dict:
        provider = str(kwargs.get("provider", "claude"))
        route_policy = str(kwargs.get("route_policy") or "single")
        messages = kwargs.get("messages", [])

        tried_models: list[str] = []
        failed_models: list[str] = []

        if route_policy == "fast_then_strong":
            models = self._model_route(provider, kwargs)
        else:
            models = [str(kwargs.get("model") or self._default_model(provider))]

        last_error: Exception | None = None
        for routed_model in models:
            tried_models.append(routed_model)
            try:
                content = await self._chat_with_model(provider, routed_model, messages)
                return {
                    "content": content,
                    "provider": provider,
                    "model": routed_model,
                    "route_path": tried_models,
                    "failed_models": failed_models,
                    "token_cost": round(self._estimate_token_cost(messages, content), 4),
                }
            except Exception as exc:  # pragma: no cover - exercised by fallback tests
                last_error = exc
                failed_models.append(routed_model)

        message = str(last_error) if last_error else "llm_dispatch_failed"
        return {
            "content": "",
            "provider": provider,
            "model": models[-1],
            "route_path": tried_models,
            "failed_models": failed_models,
            "token_cost": 0.0,
            "error": message,
        }

    async def _chat_with_model(self, provider: str, model: str, messages: list[dict]) -> str:
        adapter = self._create_adapter(provider, model)
        return await adapter.chat(messages)

    def _create_adapter(self, provider: str, model: str | None):
        registry = get_adapter_registry()
        try:
            return registry.create(provider, {"api_key": "", "model": model})
        except KeyError:
            adapter_class = self._load_adapter_class(provider)
            registry.register(adapter_class)
            return registry.create(provider, {"api_key": "", "model": model})

    def _model_route(self, provider: str, kwargs: dict[str, Any]) -> list[str]:
        fast_model = str(kwargs.get("route_fast_model") or self._default_fast_model(provider))
        strong_model = str(kwargs.get("route_strong_model") or kwargs.get("model") or self._default_model(provider))
        if fast_model == strong_model:
            return [fast_model]
        return [fast_model, strong_model]

    def _default_fast_model(self, provider: str) -> str:
        return {
            "claude": "claude-3-5-haiku-latest",
            "openai": "gpt-4o-mini",
            "ollama": "llama3.2:3b",
        }.get(provider, self._default_model(provider))

    def _default_model(self, provider: str) -> str:
        return {
            "claude": "claude-3-7-sonnet-latest",
            "openai": "gpt-4o",
            "ollama": "llama3.1:8b",
        }.get(provider, "default")

    def _estimate_token_cost(self, messages: list[dict], content: str) -> float:
        prompt_chars = sum(len(str(message.get("content", ""))) for message in messages)
        output_chars = len(content)
        estimated_tokens = (prompt_chars + output_chars) / 4
        # Placeholder cost estimate for observability trending.
        return estimated_tokens * 0.000001

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

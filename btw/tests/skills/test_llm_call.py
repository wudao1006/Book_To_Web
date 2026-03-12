from __future__ import annotations

import pytest

from btw.models.base import LLMAdapter, get_adapter_registry
from btw.skills.llm_call import LLMCallSkill


class RouteTestAdapter(LLMAdapter):
    name = "route_test"
    calls: list[str] = []

    def default_model(self) -> str:
        return "route-fast"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        del messages, kwargs
        RouteTestAdapter.calls.append(self.model)
        if self.model == "route-fast":
            raise RuntimeError("fast model unavailable")
        return "export default function Component(){ return <article>ok</article>; }"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 3 for _ in texts]


@pytest.mark.asyncio
async def test_llm_call_uses_fast_then_strong_fallback(monkeypatch) -> None:
    registry = get_adapter_registry()
    registry.register(RouteTestAdapter)
    RouteTestAdapter.calls = []

    skill = LLMCallSkill()
    result = await skill.execute(
        provider="route_test",
        route_policy="fast_then_strong",
        route_fast_model="route-fast",
        route_strong_model="route-strong",
        messages=[{"role": "user", "content": "build component"}],
    )

    assert result["model"] == "route-strong"
    assert result["route_path"] == ["route-fast", "route-strong"]
    assert result["token_cost"] >= 0
    assert RouteTestAdapter.calls == ["route-fast", "route-strong"]

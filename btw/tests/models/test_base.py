import pytest

from btw.models.base import AdapterRegistry, LLMAdapter


class MockAdapter(LLMAdapter):
    name = "mock"

    def default_model(self) -> str:
        return "mock-model"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "mock response"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_adapter_registry_creates_registered_adapter() -> None:
    registry = AdapterRegistry()
    registry.register(MockAdapter)

    adapter = registry.create("mock", {"api_key": "test"})

    assert isinstance(adapter, MockAdapter)


@pytest.mark.asyncio
async def test_adapter_chat_returns_text() -> None:
    adapter = MockAdapter(config={"api_key": "test"})

    result = await adapter.chat([{"role": "user", "content": "hello"}])

    assert result == "mock response"


@pytest.mark.asyncio
async def test_adapter_embed_returns_vectors() -> None:
    adapter = MockAdapter(config={})

    embeddings = await adapter.embed(["text1", "text2"])

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 3

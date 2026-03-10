from __future__ import annotations

from btw.models.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """Skeleton OpenAI adapter."""

    name = "openai"

    def default_model(self) -> str:
        return "gpt-4-turbo-preview"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        prompt = messages[-1]["content"] if messages else ""
        lowered = prompt.lower()
        body = "return <article>Interactive narrative placeholder</article>;"
        if "chart" in lowered:
            body = "return <div>Interactive chart placeholder</div>;"
        elif "formula" in lowered or "equation" in lowered:
            body = "return <div>Formula placeholder</div>;"
        elif "code" in lowered:
            body = "return <pre>{`code placeholder`}</pre>;"
        return f"export default function Component() {{ {body} }}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1536 for _ in texts]

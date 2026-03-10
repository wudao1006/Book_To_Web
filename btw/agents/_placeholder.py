from __future__ import annotations

from typing import Any

from btw.agents.base import Agent


class PlaceholderAgent(Agent):
    """Reusable skeleton for non-core agents."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": "placeholder",
            "capability": getattr(self, "capability", "generic"),
            "input": input_data,
            "context": {
                "task_id": self.context.task_id if self.context else None,
                "book_id": self.context.book_id if self.context else None,
                "chapter_id": self.context.chapter_id if self.context else None,
            },
        }

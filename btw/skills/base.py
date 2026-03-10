from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type


class Skill(ABC):
    """Base type for reusable BTW skills."""

    name: str = "base_skill"
    description: str = "Base skill class"
    parameters: dict[str, dict[str, Any]] = {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the skill."""


class SkillRegistry:
    """Registry for available skill classes."""

    def __init__(self):
        self.skills: dict[str, Type[Skill]] = {}

    def register(self, skill_class: Type[Skill]) -> None:
        self.skills[skill_class.name] = skill_class

    def get(self, name: str) -> Type[Skill]:
        if name not in self.skills:
            raise KeyError(f"Skill '{name}' not registered")
        return self.skills[name]

    def create(self, name: str) -> Skill:
        skill_class = self.get(name)
        return skill_class()

    def list_skills(self) -> list[str]:
        return list(self.skills.keys())


_skill_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry

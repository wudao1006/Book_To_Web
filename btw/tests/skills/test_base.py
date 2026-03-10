import pytest

from btw.skills.base import Skill, SkillRegistry


class DemoSkill(Skill):
    name = "test_skill"
    description = "A test skill"

    async def execute(self, **kwargs) -> dict:
        return {"executed": True, **kwargs}


def test_skill_registry_registers_class() -> None:
    registry = SkillRegistry()

    registry.register(DemoSkill)

    assert "test_skill" in registry.skills
    assert registry.get("test_skill") is DemoSkill


@pytest.mark.asyncio
async def test_skill_execute_returns_payload() -> None:
    skill = DemoSkill()

    result = await skill.execute(foo="bar")

    assert result["executed"] is True
    assert result["foo"] == "bar"

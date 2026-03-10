from __future__ import annotations

from btw.skills.base import Skill, get_skill_registry
from btw.skills.code_compile import CodeCompileSkill
from btw.skills.code_validate import CodeValidateSkill
from btw.skills.llm_call import LLMCallSkill

ALL_SKILL_CLASSES = [LLMCallSkill, CodeValidateSkill, CodeCompileSkill]


def register_all_skills() -> None:
    registry = get_skill_registry()
    for skill_class in ALL_SKILL_CLASSES:
        registry.register(skill_class)


register_all_skills()

__all__ = ["Skill", "get_skill_registry", "register_all_skills"]

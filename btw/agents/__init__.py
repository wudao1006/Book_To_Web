from __future__ import annotations

from btw.agents.base import Agent, AgentContext, get_registry
from btw.agents.companion import CompanionAgent
from btw.agents.conductor import ConductorAgent
from btw.agents.creator import CreatorAgent
from btw.agents.critic import CriticAgent
from btw.agents.curator import CuratorAgent
from btw.agents.director import DirectorAgent
from btw.agents.engineer import EngineerAgent
from btw.agents.evolver import EvolverAgent
from btw.agents.guardian import GuardianAgent
from btw.agents.illustrator import IllustratorAgent
from btw.agents.parser import ParserAgent
from btw.agents.persona import PersonaAgent
from btw.agents.planner import PlannerAgent
from btw.agents.reader import ReaderAgent
from btw.agents.retriever import RetrieverAgent
from btw.agents.stylist import StylistAgent
from btw.agents.translator import TranslatorAgent

ALL_AGENT_CLASSES = [
    DirectorAgent,
    ParserAgent,
    GuardianAgent,
    ReaderAgent,
    RetrieverAgent,
    PlannerAgent,
    StylistAgent,
    CreatorAgent,
    IllustratorAgent,
    EngineerAgent,
    CriticAgent,
    TranslatorAgent,
    ConductorAgent,
    CompanionAgent,
    PersonaAgent,
    EvolverAgent,
    CuratorAgent,
]


def register_all_agents() -> None:
    registry = get_registry()
    for agent_class in ALL_AGENT_CLASSES:
        registry.register(agent_class)


register_all_agents()

__all__ = ["Agent", "AgentContext", "ALL_AGENT_CLASSES", "get_registry", "register_all_agents"]

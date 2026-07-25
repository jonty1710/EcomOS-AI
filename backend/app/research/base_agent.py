"""ResearchAgent — the interface every one of the 11 scored dimensions implements
(SRS §4 `ResearchAgent`/`ModuleResponse`, adapted to Phase 1's `ModuleSection`).

The orchestrator (app/research/orchestrator.py) iterates a registry of these —
it does not grow per agent. Today the registry holds 2 `DeterministicAgent`
instances and 9 `PlannedForAIPhaseAgent` instances. Wiring in the AI phase later
means swapping specific registry entries for real AI-backed agents that also
implement this interface — the orchestrator loop does not change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.knowledge.schemas import KnowledgePack
from app.models.schemas import ModuleSection


@dataclass
class ResearchContext:
    """Everything an agent may read. Deterministic agents use only `manual_inputs`
    and `logistics_profile`/`category`; a future AI agent would also read
    `product_name`, `knowledge_pack` (Phase 3 — grounding context from the
    Knowledge Engine, consumed BEFORE any AI reasoning per the Phase 3 brief),
    and reach into a ResearchProvider (app/ai/providers) using it.
    """

    product_name: str
    category: str
    manual_inputs: dict[str, Any]
    knowledge_pack: KnowledgePack | None = None


class ResearchAgent(ABC):
    agent_type: str
    weight: float

    @abstractmethod
    async def run(self, context: ResearchContext) -> ModuleSection:
        raise NotImplementedError

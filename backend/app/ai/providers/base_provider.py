"""ResearchProvider — the interface every future AI backend implements.

Phase 1 ships ZERO providers. This file exists so that when the AI phase
begins, adding OpenAI / Claude / Gemini / a local model is: one class
implementing this interface, registered in `PROVIDER_REGISTRY`. Nothing about
the Research Engine (app/research/orchestrator.py), the agent interface
(app/research/base_agent.py), or the report shape (app/models/schemas.py)
changes when a provider is added — this mirrors the SRS §4 guarantee that a
13th agent is "one class + one registry entry," extended one layer down to
the model backend itself.

Per SRS §6 / PRS §12: a provider returns REASONING ONLY — structured
qualitative signals and a self-reported confidence. It must never return the
numeric sub_score or overall_score that drives a Launch/Reject decision;
that arithmetic belongs to app/scoring/*, always.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderRequest:
    agent_type: str
    prompt_template: str
    context: dict[str, Any] = field(default_factory=dict)
    prompt_version: int | None = None


@dataclass
class ProviderResponse:
    """What a provider returns. No field here is a score — see module docstring."""

    signals: dict[str, Any]
    reasoning: str
    self_reported_confidence: float  # 0.0-1.0, raw model self-report, pre-discount
    model_name: str
    latency_ms: int
    token_usage: dict[str, int] = field(default_factory=dict)
    grounded_in_sources: bool = False  # True if the provider used real web/connector grounding


class ResearchProvider(ABC):
    """One implementation per AI backend. Never called directly by an agent's
    business logic — always through this interface, so agents are provider-agnostic.
    """

    provider_name: str

    @abstractmethod
    async def generate_signals(self, request: ProviderRequest) -> ProviderResponse:
        """Run one agent's prompt against this provider and return structured signals."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Cheap liveness check — used by the orchestrator's circuit check (SRS NFR-5)
        before fanning out to every agent, so one outage produces one clear error
        instead of eleven confusing ones.
        """
        raise NotImplementedError


class ProviderUnavailableError(Exception):
    """Raised by a provider (or the registry) when no provider is configured.
    Phase 1 always raises this — see PROVIDER_REGISTRY below.
    """


# Populated in a future phase, e.g. {"openai": OpenAIProvider(), "claude": ClaudeProvider(),
# "gemini": GeminiProvider(), "local": LocalModelProvider()}. Deliberately empty now —
# any code path that reaches into this registry in Phase 1 is expected to raise
# ProviderUnavailableError and degrade to a "planned_for_ai_phase" module section
# (see app/research/agents.py PlannedForAIPhaseAgent), never to fail the whole report.
PROVIDER_REGISTRY: dict[str, ResearchProvider] = {}


def get_provider(name: str) -> ResearchProvider:
    try:
        return PROVIDER_REGISTRY[name]
    except KeyError as exc:
        raise ProviderUnavailableError(
            f"No ResearchProvider registered for '{name}'. AI providers are not "
            "implemented in Phase 1 (Foundation) — see docs/SRS.md roadmap."
        ) from exc

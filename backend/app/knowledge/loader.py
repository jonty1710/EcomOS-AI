"""Seed data loader — reads the JSON libraries in app/knowledge/data/ into
validated Pydantic models, once per process.

Caching strategy, tier 1 (seed data): each `load_*()` function is wrapped in
`functools.lru_cache` with no arguments, so the JSON file is read and
validated exactly once per process, no matter how many requests query it —
this is a pure in-memory reference table, not something that needs
per-request I/O. `clear_all_caches()` exists for tests and for a future
dev-mode hot-reload of edited seed files without restarting the process.

No network access anywhere in this module — every path here reads a local
file under app/knowledge/data/. See tests/test_knowledge_no_network.py for
the guarantee this is actually enforced, not just claimed.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.knowledge.schemas import (
    CategoryKnowledge,
    ComplianceKnowledge,
    LogisticsKnowledge,
    MarketplaceKnowledge,
    MaterialKnowledge,
    PackagingKnowledge,
    ResearchBestPractices,
    SupplierIntelligenceKnowledge,
)

DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_json(filename: str) -> dict:
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_categories() -> dict[str, CategoryKnowledge]:
    return {k: CategoryKnowledge.model_validate(v) for k, v in _read_json("categories.json").items()}


@lru_cache
def load_materials() -> dict[str, MaterialKnowledge]:
    return {k: MaterialKnowledge.model_validate(v) for k, v in _read_json("materials.json").items()}


@lru_cache
def load_packaging() -> dict[str, PackagingKnowledge]:
    return {k: PackagingKnowledge.model_validate(v) for k, v in _read_json("packaging.json").items()}


@lru_cache
def load_logistics() -> dict[str, LogisticsKnowledge]:
    return {k: LogisticsKnowledge.model_validate(v) for k, v in _read_json("logistics.json").items()}


@lru_cache
def load_marketplace_rules() -> dict[str, MarketplaceKnowledge]:
    return {k: MarketplaceKnowledge.model_validate(v) for k, v in _read_json("marketplace_rules.json").items()}


@lru_cache
def load_supplier_intelligence() -> dict[str, SupplierIntelligenceKnowledge]:
    return {k: SupplierIntelligenceKnowledge.model_validate(v) for k, v in _read_json("supplier_intelligence.json").items()}


@lru_cache
def load_compliance() -> dict[str, ComplianceKnowledge]:
    return {k: ComplianceKnowledge.model_validate(v) for k, v in _read_json("compliance.json").items()}


@lru_cache
def load_research_best_practices() -> dict[str, ResearchBestPractices]:
    return {k: ResearchBestPractices.model_validate(v) for k, v in _read_json("research_best_practices.json").items()}


_ALL_LOADERS = (
    load_categories, load_materials, load_packaging, load_logistics,
    load_marketplace_rules, load_supplier_intelligence, load_compliance,
    load_research_best_practices,
)


def clear_all_caches() -> None:
    """Test/dev-only: forces every loader to re-read its JSON file on next call."""
    for loader in _ALL_LOADERS:
        loader.cache_clear()

"""SupplierDataConnector — the interface a future sourcing-platform
integration implements to auto-populate Supplier section fields (MOQ,
lead_time_days, manufacturer_name, gst_available — see
app/collection/field_registry.py) from IndiaMART, TradeIndia, or a direct
manufacturer API.

Same pattern as app/connectors/product_connector.py and
app/ai/providers/base_provider.py: ABC + empty registry, zero implementations
in Phase 2. Every Supplier field this could ever auto-fill is, per PRS §8 and
SRS §11, ALWAYS `requires_manual_verification=True` regardless of source — a
future connector raises Evidence Score, it never removes the verification
requirement (mirrors SRS §11 Supplier Sourcing agent's own rule).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SupplierConnectorResult:
    available: bool
    leads: list[dict[str, Any]] = field(default_factory=list)  # each: subset of Supplier field keys
    source: str = ""
    retrieved_at: str | None = None


class SupplierDataConnector(ABC):
    platform: str  # "indiamart" | "tradeindia" | "manufacturer_api"

    @abstractmethod
    async def search_suppliers(self, product_name: str, category: str | None) -> SupplierConnectorResult:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError


class SupplierConnectorUnavailableError(Exception):
    """Raised when no connector is registered for a platform. Phase 2 always
    raises this — see SUPPLIER_CONNECTOR_REGISTRY below.
    """


# Populated in a future phase, e.g. {"indiamart": IndiaMartConnector(),
# "tradeindia": TradeIndiaConnector(), "manufacturer_api": ManufacturerApiConnector()}.
# Deliberately empty now.
SUPPLIER_CONNECTOR_REGISTRY: dict[str, SupplierDataConnector] = {}


def get_supplier_connector(platform: str) -> SupplierDataConnector:
    try:
        return SUPPLIER_CONNECTOR_REGISTRY[platform]
    except KeyError as exc:
        raise SupplierConnectorUnavailableError(
            f"No SupplierDataConnector registered for '{platform}'. Supplier "
            "connectors are not implemented in Phase 2 (Data Collection Engine)."
        ) from exc

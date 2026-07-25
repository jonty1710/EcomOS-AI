"""ProductDataConnector — the interface a future marketplace integration
implements to auto-populate a Product Profile's AUTO_DETECT fields (brand,
selling_price, weight, dimensions, competitor_count, review_count,
average_rating, etc. — see app/collection/field_registry.py).

This is distinct from the SRS §8 `MarketplaceConnector` (backend/app/connectors/
base_connector.py, if/when added for the AI phase's Competitive Landscape and
Pricing Intelligence agents) — that one fetches *competitor* snapshots for AI
reasoning. This one fetches the *researched product's own* listing attributes
for the Data Collection Engine. Same architectural pattern (ABC + empty
registry, per app/ai/providers/base_provider.py), different purpose.

Phase 2 ships ZERO implementations. Any code path that reaches into
`PRODUCT_CONNECTOR_REGISTRY` is expected to find nothing and fall back to
asking the user (app/collection/collector.py) — never to fail the request.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductConnectorResult:
    available: bool
    fields: dict[str, Any] = field(default_factory=dict)  # subset of field_registry keys
    source: str = ""
    retrieved_at: str | None = None


class ProductDataConnector(ABC):
    marketplace: str

    @abstractmethod
    async def fetch_product_data(self, url_or_id: str) -> ProductConnectorResult:
        """Given a marketplace product URL or id, return whatever AUTO_DETECT
        fields (field_registry.py) this connector can supply. Must never
        fabricate a value it isn't actually confident in — return it absent
        from `fields` instead, exactly like the rest of this system.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError


class ProductConnectorUnavailableError(Exception):
    """Raised when no connector is registered for a marketplace. Phase 2
    always raises this — see PRODUCT_CONNECTOR_REGISTRY below.
    """


# Populated in a future phase, e.g. {"amazon": AmazonProductConnector(),
# "flipkart": FlipkartProductConnector(), "meesho": MeeshoProductConnector()}.
# Deliberately empty now.
PRODUCT_CONNECTOR_REGISTRY: dict[str, ProductDataConnector] = {}


def get_product_connector(marketplace: str) -> ProductDataConnector:
    try:
        return PRODUCT_CONNECTOR_REGISTRY[marketplace]
    except KeyError as exc:
        raise ProductConnectorUnavailableError(
            f"No ProductDataConnector registered for '{marketplace}'. Marketplace "
            "connectors are not implemented in Phase 2 (Data Collection Engine)."
        ) from exc

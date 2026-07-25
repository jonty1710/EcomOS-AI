"""Marketplace URL parsing — deterministic string matching only. This does
NOT fetch the URL, scrape it, or make any network request — that would be
marketplace automation, explicitly out of scope for Phase 2. It only
identifies which marketplace a pasted URL belongs to, so the profile can
record `detected_marketplace` and the (currently empty) connector registry
in app/connectors/product_connector.py has something to key off of once a
real connector exists.
"""

from urllib.parse import urlparse

MARKETPLACE_DOMAINS: dict[str, list[str]] = {
    "amazon": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
    "meesho": ["meesho.com"],
    "indiamart": ["indiamart.com"],
    "tradeindia": ["tradeindia.com"],
}


def detect_marketplace(url: str | None) -> str | None:
    if not url or not url.strip():
        return None
    try:
        host = urlparse(url.strip()).netloc.lower()
    except ValueError:
        return None
    if not host:
        # Not a full URL (e.g. user pasted a bare domain) — try a plain substring match.
        host = url.strip().lower()
    for marketplace, domains in MARKETPLACE_DOMAINS.items():
        if any(domain in host for domain in domains):
            return marketplace
    return None

"""Enforces the Phase 4 brief mechanically: "Everything must remain
provider-independent. No AI. No scraping. No marketplace automation."
Same approach as tests/test_knowledge_no_network.py.
"""

import ast
from pathlib import Path

PROVENANCE_DIR = Path(__file__).resolve().parent.parent / "app" / "provenance"

FORBIDDEN_MODULES = {
    "requests", "httpx", "urllib", "urllib.request", "socket", "aiohttp",
    "http.client", "ftplib", "smtplib",
}
FORBIDDEN_PACKAGE_PREFIXES = ("app.ai", "app.connectors")


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_network_imports_anywhere_in_provenance_package():
    py_files = list(PROVENANCE_DIR.glob("*.py"))
    assert py_files, "expected app/provenance/*.py to exist"

    for path in py_files:
        imported = _imported_names(path.read_text(encoding="utf-8"))
        forbidden_hits = imported & FORBIDDEN_MODULES
        assert not forbidden_hits, f"{path.name} imports network-capable module(s): {forbidden_hits}"

        for name in imported:
            assert not name.startswith(FORBIDDEN_PACKAGE_PREFIXES), (
                f"{path.name} imports from '{name}' — the Data Source Manager must stay "
                "independent of AI providers and connectors (Phase 4 brief)."
            )

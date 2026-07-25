"""Enforces the Phase 3 brief's constraint mechanically, not just in prose:
"The Knowledge Engine must be provider-independent and must not perform web
requests." Scans the actual source of every app/knowledge/*.py file for
network-capable imports.
"""

import ast
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "app" / "knowledge"

FORBIDDEN_MODULES = {
    "requests", "httpx", "urllib", "urllib.request", "socket", "aiohttp",
    "http.client", "ftplib", "smtplib",
}
# app.ai / app.connectors are the designated seams for future provider/network
# code (app/ai/providers, app/connectors/*) — the Knowledge Engine must not
# reach into either.
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


def test_no_network_imports_anywhere_in_knowledge_package():
    py_files = list(KNOWLEDGE_DIR.glob("*.py"))
    assert py_files, "expected app/knowledge/*.py to exist"

    for path in py_files:
        imported = _imported_names(path.read_text(encoding="utf-8"))
        forbidden_hits = imported & FORBIDDEN_MODULES
        assert not forbidden_hits, f"{path.name} imports network-capable module(s): {forbidden_hits}"

        for name in imported:
            assert not name.startswith(FORBIDDEN_PACKAGE_PREFIXES), (
                f"{path.name} imports from '{name}' — the Knowledge Engine must stay "
                "independent of AI providers and connectors (Phase 3 brief)."
            )


def test_knowledge_data_directory_contains_only_local_json():
    data_dir = KNOWLEDGE_DIR / "data"
    files = list(data_dir.iterdir())
    assert files, "expected seed JSON files in app/knowledge/data/"
    assert all(f.suffix == ".json" for f in files)

"""DG-aware context assembler -- Cypher expression catalog loader (Phase 29: CTXA-02).

Mirrors the reasoner.py / connectors.py module layout: a small module-level
registry/index built from a versioned data artifact, plus a defensive
`load_*()` helper that never raises on a missing or malformed file.

`llm/cypher_catalog.json` (repo-root, NOT inside `data-service/`) is the one
externally-versioned artifact this module owns -- it documents the six
standard SWRL/Cypher rule shapes (max_limit, min_limit, range, ratio,
boolean_requirement, existence_count), each with a worked example. SWRL
convention data and the Computgraph concept catalog are read-only Python
data structures that live in the sibling `dg_knowledge.py` module (created
in plan 29-02), not in this file.

Path resolution: inside the data-service Docker container the repo root is
mounted read-only at `/mnt/repo` (see `docker-compose.yml`'s
`.:/mnt/repo:ro` volume + `DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` env var), so
`CYPHER_CATALOG_FILE` resolves to `/mnt/repo/llm/cypher_catalog.json` at
runtime with zero Dockerfile changes. Outside the container (e.g. a
repo-root venv), the same env var is unset and the path falls back to
`<repo-root>/llm/cypher_catalog.json`, computed relative to this file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


# ── Cypher expression catalog (versioned artifact: llm/cypher_catalog.json) ──

CYPHER_CATALOG_FILE = (
    Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    / "llm"
    / "cypher_catalog.json"
)

EXPECTED_SHAPE_IDS: set[str] = {
    "max_limit",
    "min_limit",
    "range",
    "ratio",
    "boolean_requirement",
    "existence_count",
}

_EMPTY_CATALOG: dict[str, Any] = {"version": 0, "shapes": []}


def load_cypher_catalog() -> dict[str, Any]:
    """Read the Cypher expression catalog from CYPHER_CATALOG_FILE.

    Defensive by design -- callers (including /context/debug, added in a
    later plan) must never 500 because of a catalog file issue. Returns
    `{"version": 0, "shapes": []}` if the file is missing, unreadable,
    malformed JSON, or does not have the expected top-level shape.
    """
    if not CYPHER_CATALOG_FILE.exists():
        return dict(_EMPTY_CATALOG)
    try:
        payload = json.loads(CYPHER_CATALOG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_EMPTY_CATALOG)
    if not isinstance(payload, dict) or not isinstance(payload.get("shapes"), list):
        return dict(_EMPTY_CATALOG)
    return payload


def cypher_shape_ids() -> set[str]:
    """Derived index of shape ids present in the currently-loaded catalog."""
    return {shape["id"] for shape in load_cypher_catalog().get("shapes", []) if "id" in shape}


# Derived shape-id index, computed once at import time from the real catalog
# on disk (mirrors reasoner.py's REASONER_IDS / connectors.py's CONNECTOR_IDS
# module-constant pattern). Call cypher_shape_ids() directly if the catalog
# file's contents might have changed since import (e.g. in tests).
CYPHER_SHAPE_IDS: set[str] = cypher_shape_ids()

"""Reasoner registry and settings persistence — HermiT/Pellet placeholder selection.

Mirrors the connectors.py / llm_gateway settings-persistence style: JSON file
under DATA_DIR, small load/save helpers, module-level file path constant.

Reasoner settings need no encryption (no secrets). The registry is structured
so real integrated reasoners can later carry status: "integrated".
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


# ── Reasoner Registry (fixed data — Phase 814 contract) ──

REASONER_REGISTRY: list[dict[str, str]] = [
    {
        "id": "hermit",
        "name": "HermiT",
        "description": "OWL 2 DL hypertableau reasoner — checks concept satisfiability and entailment for OWL 2 DL ontologies.",
        "status": "placeholder",
    },
    {
        "id": "pellet",
        "name": "Pellet",
        "description": "OWL 2 DL tableau reasoner — supports incremental classification, debugging, and rule-based reasoning over OWL 2 DL ontologies.",
        "status": "placeholder",
    },
]

REASONER_IDS: set[str] = {r["id"] for r in REASONER_REGISTRY}


# ── Persistence ──

DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
REASONER_SETTINGS_FILE = DATA_DIR / "reasoner-settings.json"


def load_settings() -> dict[str, Any]:
    """Read the reasoner settings from the JSON store.

    Returns an empty dict if the file is missing, malformed, or empty.
    """
    if not REASONER_SETTINGS_FILE.exists():
        return {}
    try:
        payload = json.loads(REASONER_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def save_settings(settings: dict[str, Any]) -> None:
    """Write the reasoner settings to the JSON store. Creates parent dir if needed."""
    REASONER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REASONER_SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2),
        encoding="utf-8",
    )

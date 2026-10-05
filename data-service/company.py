"""Project -> company map (Phase 1301, plan 05, D-20, DGCL-02).

An admin assigns each DG project to a company. The map is a minimal attribute,
not a tenancy layer: access is still decided by project membership. It is
surfaced on ``GET /projects`` and ``GET /auth/me`` memberships and is re-checked
by the delegated-token principal (``delegation.py``) on every request, so a
reassignment cuts off tokens issued under the previous company.

Storage follows the 1205 auth idiom: a JSON file next to the other auth stores
(``auth-project-companies.json``), written atomically under the shared
``auth._STORE_LOCK`` through ``auth._load`` / ``auth._save`` -- those helpers are
imported, not duplicated. The directory is derived from ``auth.MEMBERSHIPS_FILE``
at call time so a redirected auth store (tests, alternative ``DG_DATA_DIR``)
carries this file with it. No Neo4j node is added, so the Schema Change
Propagation list in CLAUDE.md is not triggered.

Company governance (vocabulary, per-company rules) is Phase 1302 scope.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import auth

COMPANIES_FILE_NAME = "auth-project-companies.json"
COMPANY_MAX_LENGTH = 120

_KEY = "companies"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / COMPANIES_FILE_NAME


def normalize_company(value: Any) -> str:
    """Trim `value`; raise ValueError unless 1..COMPANY_MAX_LENGTH printable
    characters remain."""
    if not isinstance(value, str):
        raise ValueError("company must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("company must not be empty")
    if len(cleaned) > COMPANY_MAX_LENGTH:
        raise ValueError(f"company must be at most {COMPANY_MAX_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValueError("company must not contain control characters")
    return cleaned


def company_for_project(project: str) -> str | None:
    """The company `project` is assigned to, or None when unassigned."""
    if not project:
        return None
    with auth._STORE_LOCK:
        for row in auth._load(_file(), _KEY):
            if row.get("project") == project:
                value = row.get("company")
                return value if isinstance(value, str) and value else None
    return None


def all_companies() -> dict[str, str]:
    """Every assignment as ``{project: company}`` (one read, for list views)."""
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
    return {
        row["project"]: row["company"]
        for row in rows
        if isinstance(row.get("project"), str) and isinstance(row.get("company"), str)
    }


def set_project_company(project: str, company: str) -> dict[str, Any]:
    """Upsert the assignment for `project`. Raises ValueError for an empty
    project or an invalid company (see :func:`normalize_company`)."""
    if not isinstance(project, str) or not project.strip():
        raise ValueError("project must not be empty")
    cleaned = normalize_company(company)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record: dict[str, Any] | None = None
        for row in rows:
            if row.get("project") == project:
                row["company"] = cleaned
                row["updated_at"] = int(time.time())
                record = row
                break
        if record is None:
            record = {"project": project, "company": cleaned, "updated_at": int(time.time())}
            rows.append(record)
        auth._save(_file(), _KEY, rows)
        return dict(record)

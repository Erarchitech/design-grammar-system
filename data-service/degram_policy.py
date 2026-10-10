"""Per-project DeGram provider-export policy (Phase 1301 plan 08, D-17, 1300 D-06).

Reading a project through DG (delegated token) and sending project data to a
model provider are two different permissions. This store holds the second one,
per project. Owner decision D-32 (2026-10-09, amends D-17): ``providerExportAllowed``
is ALLOWED by default, so a user does not need an admin to switch it on; an admin
can still turn it off per project. ``wholeDefinitionAllowed`` stays DENY BY DEFAULT.
Anything malformed still fails closed.

* ``providerExportAllowed`` -- project data may be sent to the relay's provider
  at all. No row (or a row without the flag) allows; an explicit False, a
  non-boolean value, or an unreadable / malformed store denies.
* ``wholeDefinitionAllowed`` -- the project allows a whole-definition context in
  addition. It still needs a per-request consent from the user (the relay
  checks that); consent never overrides a deny.

Storage is ``degram-policy.json`` under ``DG_DATA_DIR`` (resolved at call time),
written atomically (temp file + ``os.replace``). It is a plain JSON file, not a
graph node, so the Schema Change Propagation list in CLAUDE.md is not triggered.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

POLICY_FILE_NAME = "degram-policy.json"

_LOCK = threading.Lock()
_KEY = "policies"

# D-32: the default for a project with no stored policy.
_DEFAULT: dict[str, bool] = {"providerExportAllowed": True, "wholeDefinitionAllowed": False}
# Fail-closed answer for an empty project name or an unreadable / malformed store.
_DENY: dict[str, bool] = {"providerExportAllowed": False, "wholeDefinitionAllowed": False}


def policy_path() -> Path:
    return Path(os.getenv("DG_DATA_DIR", "/app/data")) / POLICY_FILE_NAME


def _load_rows_checked() -> list[dict[str, Any]] | None:
    """The stored rows, [] when the store does not exist yet, None when it exists
    but cannot be trusted (unreadable or malformed): the caller must fail closed."""
    path = policy_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rows = payload.get(_KEY) if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    if not all(isinstance(row, dict) for row in rows):
        return None
    return rows


def _load_rows() -> list[dict[str, Any]]:
    return _load_rows_checked() or []


def _save_rows(rows: list[dict[str, Any]]) -> None:
    path = policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({_KEY: rows}, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass
    last: OSError | None = None
    for attempt in range(5):  # a Windows scanner can briefly hold the target
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:  # pragma: no cover - Windows only
            last = exc
            time.sleep(0.05 * (attempt + 1))
    if last is not None:  # pragma: no cover
        raise last


def policy_for_project(project: str) -> dict[str, bool]:
    """The effective policy of `project`: a fresh dict with both flags. A flag
    that is not stored takes its D-32 default; a stored value counts only when it
    is literally boolean (anything else denies); an unreadable store denies."""
    if not isinstance(project, str) or not project:
        return dict(_DENY)
    with _LOCK:
        rows = _load_rows_checked()
    if rows is None:
        return dict(_DENY)
    for row in rows:
        if row.get("project") == project:
            return {
                flag: (row[flag] is True) if flag in row else default
                for flag, default in _DEFAULT.items()
            }
    return dict(_DEFAULT)


def set_policy(
    project: str,
    *,
    provider_export_allowed: bool | None = None,
    whole_definition_allowed: bool | None = None,
    updated_by: str | None = None,
) -> dict[str, bool]:
    """Merge the given flags into `project`'s policy (a flag left as None keeps
    its stored value) and return the effective policy. Raises ValueError for an
    empty project or a non-boolean flag."""
    if not isinstance(project, str) or not project.strip():
        raise ValueError("project must not be empty")
    for flag in (provider_export_allowed, whole_definition_allowed):
        if flag is not None and not isinstance(flag, bool):
            raise ValueError("policy flags must be booleans")
    with _LOCK:
        rows = _load_rows_checked()
        if rows is None:  # never overwrite a store that cannot be read
            raise ValueError("the policy store is unreadable")
        row = next((r for r in rows if r.get("project") == project), None)
        if row is None:
            row = {"project": project, **_DEFAULT}
            rows.append(row)
        if provider_export_allowed is not None:
            row["providerExportAllowed"] = provider_export_allowed
        if whole_definition_allowed is not None:
            row["wholeDefinitionAllowed"] = whole_definition_allowed
        row["updatedAt"] = int(time.time())
        if updated_by:
            row["updatedBy"] = updated_by
        _save_rows(rows)
    return policy_for_project(project)

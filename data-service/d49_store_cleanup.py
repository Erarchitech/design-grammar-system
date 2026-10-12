"""One-off D-49 store cleanup: retire connector credentials and remove the UAT account (D-47).

Phase 1308 plan 08 (WEBUI-11). Connector access is by per-connector grant and a
signed-in ``dgk_`` session from now on (D-04, D-26), so every ``dgc_`` credential
is retired. The throwaway UAT account ``uat-pw-bd30ce@dg.local`` and its project
``uat-pw-bd30ce`` are removed from every JSON store under ``DG_DATA_DIR``.

**Dry-run by default.** Nothing is written unless ``--apply`` is given. The
targets are hard-coded below and there is no flag to change them. This module
reads and rewrites JSON files only and never contacts a graph database.

**Invocation (owner-run, step 1308-20):**

    # dry-run in the running container (reads only):
    MSYS_NO_PATHCONV=1 docker exec data-service python d49_store_cleanup.py

    # apply with the service stopped (back up data-service/data/*.json first):
    docker compose stop data-service
    MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps data-service python d49_store_cleanup.py --apply
    docker compose start data-service

**Output:** one line per store with a count, then one status word. Tokens, token
hashes, password hashes and usernames are never printed.

**Exit codes / status words:**

- ``0`` / ``dry-run-ok`` -- dry-run: the plan was computed, nothing was written.
- ``0`` / ``applied`` -- ``--apply``: every changed store was rewritten.
- ``0`` / ``nothing-to-do`` -- no active credential and no UAT row exists; no
  file was touched (so a second ``--apply`` changes nothing).
- ``2`` / ``project-has-other-members`` -- the UAT project has a member other
  than the UAT user; nothing was written.
- ``3`` / ``store-unreadable`` -- a store exists but is malformed; nothing was
  written (repair or restore it first).

**Credentials:** each active credential gets ``revoked: true``, ``revoked_at``
(ISO-8601 UTC) and ``retired: "D-49"``. Credentials that are already revoked are
left byte-identical.

**Concurrency:** ``auth._STORE_LOCK`` is held for the whole run, but the lock is
per process, so a live data-service is not excluded by it. ``--apply`` therefore
runs with the service stopped. All changes are planned before the first write,
and a malformed store aborts before any write. Stores are written one at a time
(each atomically); an interrupted run is finished by running ``--apply`` again,
because every step is idempotent.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable

import auth
import company
import connector_access
import connector_session
import connectors
import degram_grants
import degram_pairing
import degram_policy
import delegation

UAT_USERNAME = "uat-pw-bd30ce@dg.local"
UAT_PROJECT = "uat-pw-bd30ce"
RETIRED_MARKER = "D-49"

STATUS_DRY_RUN_OK = "dry-run-ok"
STATUS_APPLIED = "applied"
STATUS_NOTHING = "nothing-to-do"
STATUS_OTHER_MEMBERS = "project-has-other-members"
STATUS_UNREADABLE = "store-unreadable"

EXIT_OK = 0
EXIT_OTHER_MEMBERS = 2
EXIT_UNREADABLE = 3

# Counts that mean "a write would happen". ``credentials_already_revoked`` is
# informational only.
_CHANGE_KEYS = (
    "credentials_to_retire",
    "connector_sessions",
    "delegated_tokens",
    "sessions",
    "degram_grants",
    "degram_grant_requests",
    "pairings",
    "connector_access_grants",
    "connector_access_requests",
    "export_policies",
    "project_companies",
    "invites",
    "memberships",
    "users",
)


class StoreUnreadable(Exception):
    """A store exists but cannot be read; ``label`` names it (never its content)."""

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.label = label


Writer = Callable[[], None]


def _iso(now: int | None) -> str:
    moment = time.time() if now is None else now
    return datetime.fromtimestamp(moment, tz=timezone.utc).isoformat()


def _plan_credentials(now: int | None) -> tuple[dict[str, int], Writer | None]:
    try:
        rows = connectors.load_credentials()
    except connectors.CredentialStoreError as exc:
        raise StoreUnreadable("connector-credentials") from exc
    active = [r for r in rows if not r.get("revoked")]
    counts = {
        "credentials_to_retire": len(active),
        "credentials_already_revoked": len(rows) - len(active),
    }
    if not active:
        return counts, None
    stamp = _iso(now)

    def write() -> None:
        for row in active:  # rows are the loaded objects, order is preserved
            row["revoked"] = True
            row["revoked_at"] = stamp
            row["retired"] = RETIRED_MARKER
        connectors.save_credentials(rows)

    return counts, write


def _norm(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _targets(username: str, project: str, *, creator: bool = False) -> Callable[[dict[str, Any]], bool]:
    """Row predicate: the row belongs to the target user or names the target project.

    ``creator`` additionally matches rows the target user created (invites).
    """

    def matches(row: dict[str, Any]) -> bool:
        if _norm(row.get("username")) == username:
            return True
        if row.get("project") == project:
            return True
        return creator and _norm(row.get("created_by")) == username

    return matches


def _plan_auth_rows(
    label: str,
    count_key: str,
    path: Any,
    key: str,
    matches: Callable[[dict[str, Any]], bool],
) -> tuple[dict[str, int], Writer | None]:
    """Plan the removal of matching rows from one ``auth._load`` style store.

    A store that does not exist is empty and stays absent. Returns the counts
    and a writer (None when nothing changes).
    """
    try:
        rows = auth._load(path, key)
    except auth.AuthStoreError as exc:
        raise StoreUnreadable(label) from exc
    kept = [row for row in rows if not matches(row)]
    removed = len(rows) - len(kept)
    if not removed:
        return {count_key: 0}, None

    def write() -> None:
        auth._save(path, key, kept)

    return {count_key: removed}, write


def _plan_connector_access(
    matches: Callable[[dict[str, Any]], bool],
) -> tuple[dict[str, int], Writer | None]:
    try:
        grants, requests = connector_access._load()
    except auth.AuthStoreError as exc:
        raise StoreUnreadable("connector-access") from exc
    kept_grants = [row for row in grants if not matches(row)]
    kept_requests = [row for row in requests if not matches(row)]
    counts = {
        "connector_access_grants": len(grants) - len(kept_grants),
        "connector_access_requests": len(requests) - len(kept_requests),
    }
    if not any(counts.values()):
        return counts, None

    def write() -> None:
        connector_access._save(kept_grants, kept_requests)

    return counts, write


def _plan_policy(
    matches: Callable[[dict[str, Any]], bool],
) -> tuple[dict[str, int], Writer | None]:
    rows = degram_policy._load_rows_checked()
    if rows is None:
        raise StoreUnreadable("degram-policy")
    kept = [row for row in rows if not matches(row)]
    removed = len(rows) - len(kept)
    if not removed:
        return {"export_policies": 0}, None

    def write() -> None:
        degram_policy._save_rows(kept)

    return {"export_policies": removed}, write


def plan_changes(
    *,
    username: str = UAT_USERNAME,
    project: str = UAT_PROJECT,
    now: int | None = None,
) -> dict[str, Any]:
    """Read every store and compute what ``--apply`` would change; write nothing.

    Returns ``{"counts": {...}, "other_members": int, "writes": [(label, fn)]}``
    with the writes in the order ``--apply`` runs them (the user row last).
    Raises :class:`StoreUnreadable` when any store is malformed.
    """
    target = _norm(username)
    matches = _targets(target, project)
    counts: dict[str, int] = {}
    writes: list[tuple[str, Writer]] = []

    def take(label: str, part: dict[str, int], writer: Writer | None) -> None:
        counts.update(part)
        if writer is not None:
            writes.append((label, writer))

    with auth._STORE_LOCK, connectors._STORE_LOCK:
        take("connector-credentials", *_plan_credentials(now))
        take(
            "connector-sessions",
            *_plan_auth_rows(
                "connector-sessions", "connector_sessions", connector_session._file(), "sessions", matches
            ),
        )
        take(
            "delegated-tokens",
            *_plan_auth_rows(
                "delegated-tokens", "delegated_tokens", delegation._file(), "tokens", matches
            ),
        )
        take(
            "sessions",
            *_plan_auth_rows("sessions", "sessions", auth.SESSIONS_FILE, "sessions", matches),
        )
        take(
            "degram-grants",
            *_plan_auth_rows(
                "degram-grants", "degram_grants", degram_grants._grants_file(), "grants", matches
            ),
        )
        take(
            "degram-grant-requests",
            *_plan_auth_rows(
                "degram-grant-requests",
                "degram_grant_requests",
                degram_grants._requests_file(),
                "requests",
                matches,
            ),
        )
        take(
            "degram-pairings",
            *_plan_auth_rows(
                "degram-pairings", "pairings", degram_pairing._file(), "pairings", matches
            ),
        )
        take("connector-access", *_plan_connector_access(matches))
        take("degram-policy", *_plan_policy(matches))
        take(
            "project-companies",
            *_plan_auth_rows(
                "project-companies", "project_companies", company._file(), "companies", matches
            ),
        )
        take(
            "invites",
            *_plan_auth_rows(
                "invites",
                "invites",
                auth.INVITES_FILE,
                "invites",
                _targets(target, project, creator=True),
            ),
        )
        # Memberships are read once more up front: the refusal needs the members
        # of the target project who are NOT the target user, which the removal
        # filter would otherwise hide.
        try:
            membership_rows = auth._load(auth.MEMBERSHIPS_FILE, "memberships")
        except auth.AuthStoreError as exc:
            raise StoreUnreadable("memberships") from exc
        other_members = sum(
            1
            for row in membership_rows
            if row.get("project") == project and _norm(row.get("username")) != target
        )
        take(
            "memberships",
            *_plan_auth_rows(
                "memberships", "memberships", auth.MEMBERSHIPS_FILE, "memberships", matches
            ),
        )
        take(
            "users",
            *_plan_auth_rows(
                "users", "users", auth.USERS_FILE, "users", lambda row: _norm(row.get("username")) == target
            ),
        )
    return {"counts": counts, "other_members": other_members, "writes": writes}


def run(
    *,
    apply: bool = False,
    username: str = UAT_USERNAME,
    project: str = UAT_PROJECT,
    now: int | None = None,
) -> tuple[int, str, dict[str, int]]:
    """Plan, then (with ``apply``) write. Returns ``(exit_code, status, counts)``."""
    with auth._STORE_LOCK, connectors._STORE_LOCK:
        try:
            plan = plan_changes(username=username, project=project, now=now)
        except StoreUnreadable:
            return EXIT_UNREADABLE, STATUS_UNREADABLE, {}
        counts = plan["counts"]
        if plan["other_members"]:
            return EXIT_OTHER_MEMBERS, STATUS_OTHER_MEMBERS, counts
        if not any(counts.get(key) for key in _CHANGE_KEYS):
            return EXIT_OK, STATUS_NOTHING, counts
        if not apply:
            return EXIT_OK, STATUS_DRY_RUN_OK, counts
        for _label, write in plan["writes"]:
            write()
        return EXIT_OK, STATUS_APPLIED, counts


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="d49_store_cleanup.py",
        description=(
            "Retire every connector credential and remove the UAT account (D-47, D-49). "
            "Dry-run by default; the targets are fixed."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes. Without it the script only reports what it would do.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    code, status, counts = run(apply=args.apply)
    if code != EXIT_UNREADABLE:
        for name in sorted(counts):
            print(f"{name}: {counts[name]}")
    print(status)
    return code


if __name__ == "__main__":
    sys.exit(main())

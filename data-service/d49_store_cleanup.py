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
import connectors

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
_CHANGE_KEYS = ("credentials_to_retire",)


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


def plan_changes(
    *,
    username: str = UAT_USERNAME,
    project: str = UAT_PROJECT,
    now: int | None = None,
) -> dict[str, Any]:
    """Read every store and compute what ``--apply`` would change; write nothing.

    Returns ``{"counts": {...}, "other_members": int, "writes": [(label, fn)]}``.
    Raises :class:`StoreUnreadable` when any store is malformed.
    """
    counts: dict[str, int] = {}
    writes: list[tuple[str, Writer]] = []
    with auth._STORE_LOCK, connectors._STORE_LOCK:
        cred_counts, cred_writer = _plan_credentials(now)
        counts.update(cred_counts)
        if cred_writer is not None:
            writes.append(("connector-credentials", cred_writer))
    return {"counts": counts, "other_members": 0, "writes": writes}


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

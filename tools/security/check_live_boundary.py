#!/usr/bin/env python3
"""Live direct-proxy and exposure checker (Phase 1205, D-16/D-18).

Read-only owner/CI tool that checks a **running** stack: the nginx `/neo4j/`
and `/n8n/` direct-proxy routes are gone (404, not a 200 SPA fallback), every
project-scoped data-service route answers 401 without a credential, the
browser-served `config.js` carries no credential key names or known-default
values, and (in the `multi-user` profile) Bolt/Neo4j-HTTP/n8n are unreachable
on the host's published ports.

This is the live half of D-16 -- the static half (parsing `ui-v2/nginx.conf`
and `docker-compose.yml` at rest) belongs to a different test, not this
script. This script exists so 1205-18/1205-19's live checkpoints run a
deterministic, repeatable check against rebuilt containers instead of ad hoc
curl commands (1205-RESEARCH.md Pitfall 4: a stale image can mask a source
change -- rebuild with `--no-cache` before trusting a run of this script).

Sends no credential of any kind, ever. Every check function returns a plain
dict (`check`, `target`, `expected`, `observed`, `result`); `result` is one of
`"pass"`, `"fail"`, or `"info"` (the `multi-user`/`local` port-check split).
The observed response body is never included beyond 200 characters, and only
when a check explicitly needs it for diagnosis.

Exit code: 0 only when every check's `result` is not `"fail"`. `"info"` rows
never affect the exit code.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any, Callable

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"

_KNOWN_DEFAULTS_SOURCE = "inline-fallback"
try:
    if str(DATA_SERVICE_DIR) not in sys.path:
        sys.path.insert(0, str(DATA_SERVICE_DIR))
    import secrets_policy  # noqa: E402

    KNOWN_DEFAULT_LITERALS: frozenset[str] = secrets_policy.KNOWN_DEFAULT_LITERALS
    KNOWN_DEFAULT_PREFIXES: tuple[str, ...] = secrets_policy.KNOWN_DEFAULT_PREFIXES
    _KNOWN_DEFAULTS_SOURCE = "data-service.secrets_policy"
except Exception:  # noqa: BLE001 - any import failure degrades to the inline copy
    # Inline fallback, kept in sync with data-service/secrets_policy.py's
    # KNOWN_DEFAULT_LITERALS/KNOWN_DEFAULT_PREFIXES. Used only when the
    # sys.path import above fails (e.g. this script is copied out of the
    # repo); `knownDefaultsSource` in the report names which copy was used.
    KNOWN_DEFAULT_LITERALS = frozenset(
        {"12345678", "minioadmin", "speckle", "neo4j", "password", "admin"}
    )
    KNOWN_DEFAULT_PREFIXES = ("change-me",)


CREDENTIAL_KEY_NAMES: tuple[str, ...] = (
    "neo4jPassword",
    "neo4jUser",
    "n8nPassword",
    "n8nUser",
    "speckleReadToken",
)
"""D-12 browser-runtime credential key names that must never appear in config.js."""

DEFAULT_UI_URL = "http://localhost:8080"
DEFAULT_DATA_SERVICE_URL = "http://localhost:8000"
DEFAULT_HOST = "127.0.0.1"

MULTI_USER_REFUSED_PORTS: tuple[int, ...] = (7687, 7474, 5678)
"""Bolt, Neo4j HTTP, n8n -- D-09's multi-user port drops (this check's D-16 half)."""

_TIMEOUT = httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0)
_MAX_BODY_CHARS = 200
"""Cap on any response-body excerpt this script ever records (never the full body)."""


def _row(
    check: str,
    target: str,
    expected: str,
    observed: str,
    result: str,
    note: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "check": check,
        "target": target,
        "expected": expected,
        "observed": observed,
        "result": result,
    }
    if note is not None:
        row["note"] = note
    return row


# ── check_proxy_removed ───────────────────────────────────────────────────────


def check_proxy_removed(client: httpx.Client, ui_url: str) -> list[dict[str, Any]]:
    """`/neo4j/` and `/n8n/` must be gone: 404, never a 200 SPA fallback."""
    targets: list[tuple[str, str]] = [
        ("GET", f"{ui_url}/neo4j/"),
        ("POST", f"{ui_url}/neo4j/db/neo4j/tx/commit"),
        ("GET", f"{ui_url}/n8n/webhook/dg/graph-query"),
    ]
    rows: list[dict[str, Any]] = []
    for method, url in targets:
        try:
            response = client.get(url) if method == "GET" else client.post(url, json={})
        except httpx.RequestError as exc:
            rows.append(
                _row(
                    "proxy_removed",
                    f"{method} {url}",
                    "404",
                    "unreachable",
                    "fail",
                    note=f"request error: {exc}",
                )
            )
            continue
        passed = response.status_code == 404
        note = None
        if response.status_code == 200:
            note = "200 SPA fallback counts as a failure -- the route is still routable"
        rows.append(
            _row(
                "proxy_removed",
                f"{method} {url}",
                "404",
                str(response.status_code),
                "pass" if passed else "fail",
                note=note,
            )
        )
    return rows


# ── check_unauthenticated ──────────────────────────────────────────────────────


def check_unauthenticated(
    client: httpx.Client, ui_url: str, data_service_url: str
) -> list[dict[str, Any]]:
    """Every project-scoped route answers 401 with no credential; the root answers 200."""
    must_401: list[tuple[str, str]] = [
        ("GET", f"{ui_url}/data-service/validation/runs/any-project"),
        ("POST", f"{ui_url}/data-service/mcp"),
        ("GET", f"{ui_url}/data-service/auth/me"),
        ("GET", f"{data_service_url}/validation/runs/any-project"),
    ]
    rows: list[dict[str, Any]] = []
    for method, url in must_401:
        try:
            response = client.get(url) if method == "GET" else client.post(url, json={})
        except httpx.RequestError as exc:
            rows.append(
                _row(
                    "unauthenticated",
                    f"{method} {url}",
                    "401",
                    "unreachable",
                    "fail",
                    note=f"request error: {exc}",
                )
            )
            continue
        passed = response.status_code == 401
        rows.append(
            _row(
                "unauthenticated",
                f"{method} {url}",
                "401",
                str(response.status_code),
                "pass" if passed else "fail",
            )
        )

    root_url = f"{ui_url}/data-service/"
    try:
        root_response = client.get(root_url)
        root_passed = root_response.status_code == 200
        rows.append(
            _row(
                "unauthenticated",
                f"GET {root_url}",
                "200",
                str(root_response.status_code),
                "pass" if root_passed else "fail",
            )
        )
    except httpx.RequestError as exc:
        rows.append(
            _row(
                "unauthenticated",
                f"GET {root_url}",
                "200",
                "unreachable",
                "fail",
                note=f"request error: {exc}",
            )
        )
    return rows


# ── check_config_js ────────────────────────────────────────────────────────────


def check_config_js(client: httpx.Client, ui_url: str) -> list[dict[str, Any]]:
    """`config.js` carries no credential key name and no known-default value."""
    url = f"{ui_url}/config.js"
    rows: list[dict[str, Any]] = []
    try:
        response = client.get(url)
    except httpx.RequestError as exc:
        rows.append(
            _row(
                "config_js",
                f"GET {url}",
                "200, no credential key/value",
                "unreachable",
                "fail",
                note=f"request error: {exc}",
            )
        )
        return rows

    if response.status_code != 200:
        rows.append(
            _row(
                "config_js",
                f"GET {url}",
                "200",
                str(response.status_code),
                "fail",
            )
        )
        return rows

    body = response.text

    found_keys = [name for name in CREDENTIAL_KEY_NAMES if name in body]
    rows.append(
        _row(
            "config_js",
            f"GET {url}",
            "no credential key name present",
            "none found" if not found_keys else f"found: {', '.join(found_keys)}",
            "pass" if not found_keys else "fail",
        )
    )

    # Matched only as a *quoted string value* ("literal" or 'literal'), never as a
    # bare substring: several known-default literals (e.g. "speckle", "admin") are
    # also common substrings of entirely legitimate identifiers such as the
    # speckleBaseUrl key name itself, so a bare substring search would permanently
    # false-positive on config.js's own non-secret keys.
    found_values = [
        literal
        for literal in sorted(KNOWN_DEFAULT_LITERALS)
        if f'"{literal}"' in body or f"'{literal}'" in body
    ]
    found_prefixes = [
        prefix
        for prefix in KNOWN_DEFAULT_PREFIXES
        if f'"{prefix}' in body or f"'{prefix}" in body
    ]
    found_defaults = found_values + found_prefixes
    rows.append(
        _row(
            "config_js",
            f"GET {url}",
            "no known-default literal value present",
            "none found" if not found_defaults else f"found: {', '.join(found_defaults)}",
            "pass" if not found_defaults else "fail",
            note=f"knownDefaultsSource={_KNOWN_DEFAULTS_SOURCE}",
        )
    )
    return rows


# ── check_ports ────────────────────────────────────────────────────────────────

ConnectFn = Callable[[str, int, float], bool]


def _default_connect(host: str, port: int, timeout: float = 1.5) -> bool:
    """Return True if a TCP connect to host:port succeeds, False on refusal/timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_ports(
    host: str,
    profile: str,
    connect: ConnectFn | None = None,
) -> list[dict[str, Any]]:
    """Multi-user: connects to Bolt/Neo4j-HTTP/n8n must be refused (fail if reachable).

    Local: the same ports are reported as informational "trusted-local" rows --
    the local profile deliberately keeps them published (1205-CONTEXT.md D-07/D-09).
    """
    connector = connect if connect is not None else _default_connect
    rows: list[dict[str, Any]] = []
    for port in MULTI_USER_REFUSED_PORTS:
        target = f"{host}:{port}"
        reachable = connector(host, port, 1.5)
        if profile == "multi-user":
            passed = not reachable
            rows.append(
                _row(
                    "ports",
                    target,
                    "refused",
                    "reachable" if reachable else "refused",
                    "pass" if passed else "fail",
                )
            )
        else:
            rows.append(
                _row(
                    "ports",
                    target,
                    "trusted-local (not enforced)",
                    "reachable" if reachable else "refused",
                    "info",
                    note="local profile keeps internal ports published as a documented "
                    "trusted-local boundary (D-07/D-09)",
                )
            )
    return rows


# ── CLI ─────────────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_live_boundary.py",
        description=(
            "Check a running stack's direct-proxy exposure and unauthenticated-access "
            "boundary (D-16/D-18): /neo4j/ and /n8n/ answer 404, data-service routes "
            "answer 401 with no credential, config.js carries no credential, and (in "
            "multi-user) Bolt/Neo4j-HTTP/n8n are unreachable on the host."
        ),
    )
    parser.add_argument("--ui-url", default=DEFAULT_UI_URL, help=f"UI origin (default: {DEFAULT_UI_URL}).")
    parser.add_argument(
        "--data-service-url",
        default=DEFAULT_DATA_SERVICE_URL,
        help=f"data-service base URL (default: {DEFAULT_DATA_SERVICE_URL}).",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to probe ports on (default: {DEFAULT_HOST}).")
    parser.add_argument(
        "--profile",
        choices=("local", "multi-user"),
        default="local",
        help="Deployment profile (default: local). multi-user enforces the port checks.",
    )
    parser.add_argument("--json-out", default=None, help="Optional path to also write the JSON report to.")
    return parser


def run_all_checks(
    ui_url: str,
    data_service_url: str,
    host: str,
    profile: str,
    client: httpx.Client | None = None,
    connect: ConnectFn | None = None,
) -> dict[str, Any]:
    """Run every check and build the report dict. Injectable client/connect for tests."""
    owns_client = client is None
    active_client = client if client is not None else httpx.Client(
        timeout=_TIMEOUT, follow_redirects=False
    )
    try:
        rows: list[dict[str, Any]] = []
        rows.extend(check_proxy_removed(active_client, ui_url))
        rows.extend(check_unauthenticated(active_client, ui_url, data_service_url))
        rows.extend(check_config_js(active_client, ui_url))
        rows.extend(check_ports(host, profile, connect=connect))
    finally:
        if owns_client:
            active_client.close()

    passed = all(row["result"] != "fail" for row in rows)
    return {
        "profile": profile,
        "uiUrl": ui_url,
        "dataServiceUrl": data_service_url,
        "host": host,
        "knownDefaultsSource": _KNOWN_DEFAULTS_SOURCE,
        "checks": rows,
        "passed": passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    report = run_all_checks(
        ui_url=args.ui_url,
        data_service_url=args.data_service_url,
        host=args.host,
        profile=args.profile,
    )

    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    print(serialized)
    if args.json_out:
        Path(args.json_out).write_text(serialized, encoding="utf-8")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

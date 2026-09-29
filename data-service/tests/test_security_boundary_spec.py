"""Spec drift test for ``spec/SECURITY-BOUNDARY.md`` (Phase 1205, plan 1205-16,
ALGN12-17..19, GATE12-05; D-14, D-17).

The spec carries four machine-checked fenced blocks (each wrapped in
``<!-- security-boundary:<name>:start/end -->`` comments, the same convention as
``spec/REPRODUCIBILITY.md``):

* ``public-routes``        == the public policy rows plus ``POST /connectors/heartbeat``
* ``route-policy``         == ``route_policy.ROUTE_POLICIES`` field by field, and
                              the registered app routes
* ``known-default-secrets`` == ``secrets_policy`` literals, prefixes and digests
* ``published-ports``      == the compose bindings, base profile and multi-user
                              override layered over it

Every comparison runs in both directions (missing and extra), and an induced
mismatch test proves the comparison is not vacuous. Assertion messages print
route keys, field names and port bindings -- never a secret value.

No test-only auth bypass: nothing here sends a request. ``DG_TEST_PRINCIPAL =
"none"`` keeps the conftest autouse fixture from pre-authorising anything.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

import route_policy
import secrets_policy
import test_compose_boundary as compose_boundary
import test_route_inventory as route_inventory

DG_TEST_PRINCIPAL = "none"

REPO_ROOT = Path(
    os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent.parent))
)
SPEC_PATH = REPO_ROOT / "spec" / "SECURITY-BOUNDARY.md"

BLOCKS = ("public-routes", "route-policy", "known-default-secrets", "published-ports")

# Public credential column: everything is "none" unless named here.
PUBLIC_CREDENTIALS = {
    ("POST", "/auth/accept-invite"): "invite-code",
    ("POST", "/connectors/heartbeat"): "connector-token",
}
HEARTBEAT = ("POST", "/connectors/heartbeat")

_HEX64 = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")


# --------------------------------------------------------------------------
# Spec parsing
# --------------------------------------------------------------------------


def _markers(name: str) -> tuple[str, str]:
    return (
        f"<!-- security-boundary:{name}:start -->",
        f"<!-- security-boundary:{name}:end -->",
    )


def block_span(text: str, name: str) -> tuple[int, int]:
    start_marker, end_marker = _markers(name)
    assert text.count(start_marker) == 1, f"block {name}: expected exactly one start marker"
    assert text.count(end_marker) == 1, f"block {name}: expected exactly one end marker"
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    assert start < end, f"block {name}: end marker precedes start marker"
    return start, end


def block_lines(text: str, name: str) -> list[str]:
    start, end = block_span(text, name)
    lines = []
    for raw in text[start:end].splitlines():
        line = raw.strip()
        if line and not line.startswith("```"):
            lines.append(line)
    return lines


def text_without_blocks(text: str, names: tuple[str, ...]) -> str:
    """The spec with the named blocks blanked out (used for the leak scans)."""
    spans = sorted(block_span(text, n) for n in names)
    out, cursor = [], 0
    for start, end in spans:
        out.append(text[cursor:start])
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def _dash(value: str) -> str | None:
    return None if value == "-" else value


def parse_route_policy_block(lines: list[str]) -> dict[tuple[str, str], tuple]:
    rows: dict[tuple[str, str], tuple] = {}
    for line in lines:
        parts = line.split("|")
        assert len(parts) == 5, f"route-policy row is not METHOD|PATH|PRINCIPALS|SOURCE|ROLE: {line!r}"
        method, path, principals, source, role = parts
        key = (method, path)
        assert key not in rows, f"route-policy block repeats {method} {path}"
        rows[key] = (frozenset(principals.split("+")), _dash(source), _dash(role))
    return rows


def parse_public_block(lines: list[str]) -> dict[tuple[str, str], str]:
    rows: dict[tuple[str, str], str] = {}
    for line in lines:
        parts = line.split("|")
        assert len(parts) == 3, f"public-routes row is not METHOD|PATH|CREDENTIAL: {line!r}"
        key = (parts[0], parts[1])
        assert key not in rows, f"public-routes block repeats {parts[0]} {parts[1]}"
        rows[key] = parts[2]
    return rows


def parse_known_default_block(lines: list[str]) -> dict[str, set[str]]:
    kinds: dict[str, set[str]] = {"literal": set(), "prefix": set(), "sha256": set()}
    for line in lines:
        kind, sep, value = line.partition("|")
        assert sep and kind in kinds, f"known-default row has an unknown kind: {kind!r}"
        kinds[kind].add(value)
    return kinds


def parse_ports_block(lines: list[str]) -> set[tuple[str, str, str, str]]:
    rows: set[tuple[str, str, str, str]] = set()
    for line in lines:
        parts = line.split("|")
        assert len(parts) == 4, f"published-ports row is not PROFILE|SERVICE|HOST_IP|HOST_PORT: {line!r}"
        rows.add((parts[0], parts[1], parts[2], parts[3]))
    return rows


# --------------------------------------------------------------------------
# Code-side truth
# --------------------------------------------------------------------------


def code_route_policy() -> dict[tuple[str, str], tuple]:
    return {
        key: (frozenset(p.principals), p.project_source, p.min_role)
        for key, p in route_policy.ROUTE_POLICIES.items()
    }


def code_public_routes() -> dict[tuple[str, str], str]:
    rows = {
        key: PUBLIC_CREDENTIALS.get(key, "none")
        for key, policy in route_policy.ROUTE_POLICIES.items()
        if route_policy.PRINCIPAL_PUBLIC in policy.principals
    }
    assert HEARTBEAT in route_policy.ROUTE_POLICIES, "the heartbeat has no policy row"
    rows[HEARTBEAT] = PUBLIC_CREDENTIALS[HEARTBEAT]
    return rows


def code_known_defaults() -> dict[str, set[str]]:
    return {
        "literal": set(secrets_policy.KNOWN_DEFAULT_LITERALS),
        "prefix": set(secrets_policy.KNOWN_DEFAULT_PREFIXES),
        "sha256": set(secrets_policy.KNOWN_DEFAULT_SHA256),
    }


def _bindings(profile: str, services: dict[str, dict], skip: set[str]) -> set[tuple[str, str, str, str]]:
    rows = set()
    for name, svc in services.items():
        if name in skip:
            continue
        for item in svc["ports"]:
            ip, host = compose_boundary.split_port(item)
            rows.add((profile, name, ip or "0.0.0.0", host))
    return rows


def compose_ports() -> set[tuple[str, str, str, str]]:
    base = compose_boundary.parse_compose(
        (REPO_ROOT / "docker-compose.yml").read_bytes().decode("utf-8")
    )
    override = compose_boundary.parse_compose(
        (REPO_ROOT / "docker-compose.multi-user.yml").read_text(encoding="utf-8")
    )
    local = _bindings("local", base, set())
    reset = {name for name, svc in override.items() if svc["ports_reset"]}
    multi_user = _bindings("multi-user", base, reset) | _bindings("multi-user", override, set())
    return local | multi_user


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


def _diff_rows(block: str, spec: dict, code: dict) -> list[str]:
    problems = []
    for key in sorted(set(code) - set(spec)):
        problems.append(f"{block}: missing from spec: {' '.join(key)}")
    for key in sorted(set(spec) - set(code)):
        problems.append(f"{block}: in spec but not in code: {' '.join(key)}")
    for key in sorted(set(spec) & set(code)):
        if spec[key] != code[key]:
            problems.append(f"{block}: changed: {' '.join(key)}")
    return problems


def collect_mismatches(text: str) -> list[str]:
    """Every difference between the four spec blocks and the code / compose
    they mirror, in both directions. An empty list means no drift."""
    problems: list[str] = []
    problems += _diff_rows(
        "route-policy",
        parse_route_policy_block(block_lines(text, "route-policy")),
        code_route_policy(),
    )
    problems += _diff_rows(
        "public-routes",
        parse_public_block(block_lines(text, "public-routes")),
        code_public_routes(),
    )
    spec_defaults = parse_known_default_block(block_lines(text, "known-default-secrets"))
    code_defaults = code_known_defaults()
    for kind in ("literal", "prefix", "sha256"):
        for value in sorted(code_defaults[kind] - spec_defaults[kind]):
            problems.append(f"known-default-secrets: {kind} entry missing from spec ({_digest_of(value)})")
        for value in sorted(spec_defaults[kind] - code_defaults[kind]):
            problems.append(f"known-default-secrets: {kind} entry in spec but not in code ({_digest_of(value)})")
    spec_ports = parse_ports_block(block_lines(text, "published-ports"))
    code_ports = compose_ports()
    for row in sorted(code_ports - spec_ports):
        problems.append("published-ports: missing from spec: " + "|".join(row))
    for row in sorted(spec_ports - code_ports):
        problems.append("published-ports: extra in spec: " + "|".join(row))
    return problems


def _digest_of(value: str) -> str:
    """Identify a known-default entry in a message without echoing it."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def route_set_mismatches(text: str) -> tuple[set, set]:
    """``(unclassified, stale)`` between the spec route-policy block and the
    (method, path) pairs registered on the FastAPI app."""
    spec_keys = set(parse_route_policy_block(block_lines(text, "route-policy")))
    return route_inventory.compare_routes(route_inventory._registered_keys(), spec_keys)


# Values used as synthetic secrets elsewhere in the suite. None may appear in
# the spec (T-1205-16-02).
def _synthetic_values() -> list[str]:
    values = ["test-master-secret", "dg-test-service-token-0123456789abcdefghijklmnop"]
    try:
        import conftest  # type: ignore

        for name in ("_TEST_SERVICE_TOKEN", "_TEST_BOOTSTRAP_ADMIN_PASSWORD"):
            value = getattr(conftest, name, None)
            if isinstance(value, str) and value:
                values.append(value)
    except ImportError:  # conftest not importable by name; the fallbacks above remain
        pass
    return values


def leak_findings(text: str) -> list[str]:
    """Secret-shaped content anywhere it must not be."""
    findings: list[str] = []
    outside = text_without_blocks(text, ("known-default-secrets",))
    if _HEX64.search(outside):
        findings.append("a 64-hex string appears outside the known-default block")
    for value in _synthetic_values():
        if value in text:
            findings.append(f"a synthetic suite secret appears in the spec ({_digest_of(value)})")
    digests = set(secrets_policy.KNOWN_DEFAULT_SHA256)
    for token in re.split(r"[\s|`'\"(),;:<>\[\]{}]+", text):
        if token and hashlib.sha256(token.encode("utf-8")).hexdigest() in digests:
            findings.append("a token in the spec hashes to a known-default digest (plaintext leak)")
    # Known-default literals belong in the known-default block only.
    for literal in ("12345678", "minioadmin"):
        if literal in outside:
            findings.append(f"known-default literal ({_digest_of(literal)}) appears outside its block")
    return findings


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Behaviours
# --------------------------------------------------------------------------


def test_spec_has_exactly_the_four_blocks(spec_text):
    for name in BLOCKS:
        start, end = _markers(name)
        assert spec_text.count(start) == 1 and spec_text.count(end) == 1, name
        assert block_lines(spec_text, name), f"{name} block is empty"


def test_blocks_parse_with_crlf_line_endings(spec_text):
    crlf = spec_text.replace("\r\n", "\n").replace("\n", "\r\n")
    for name in BLOCKS:
        assert block_lines(crlf, name) == block_lines(spec_text, name), name


def test_route_policy_block_equals_route_policies_field_by_field(spec_text):
    problems = _diff_rows(
        "route-policy",
        parse_route_policy_block(block_lines(spec_text, "route-policy")),
        code_route_policy(),
    )
    assert problems == []


def test_route_policy_block_has_every_row(spec_text):
    rows = parse_route_policy_block(block_lines(spec_text, "route-policy"))
    assert len(rows) == len(route_policy.ROUTE_POLICIES)


def test_route_policy_block_equals_the_registered_app_routes(spec_text):
    unclassified, stale = route_set_mismatches(spec_text)
    assert unclassified == set(), f"app routes missing from the spec: {sorted(unclassified)}"
    assert stale == set(), f"spec rows naming no app route: {sorted(stale)}"


def test_public_routes_block_equals_public_and_heartbeat_policies(spec_text):
    spec_rows = parse_public_block(block_lines(spec_text, "public-routes"))
    assert _diff_rows("public-routes", spec_rows, code_public_routes()) == []
    # the allowlist really is the four documented routes
    assert set(spec_rows) == {
        ("GET", "/"),
        ("POST", "/auth/login"),
        ("POST", "/auth/accept-invite"),
        HEARTBEAT,
    }


def test_known_default_block_equals_secrets_policy(spec_text):
    spec_defaults = parse_known_default_block(block_lines(spec_text, "known-default-secrets"))
    assert spec_defaults == code_known_defaults()


def test_known_default_sha256_line_is_a_digest_not_a_value(spec_text):
    spec_defaults = parse_known_default_block(block_lines(spec_text, "known-default-secrets"))
    assert len(spec_defaults["sha256"]) == 1
    for digest in spec_defaults["sha256"]:
        assert _HEX64.fullmatch(digest), "the sha256 entry is not a 64-hex digest"


def test_published_ports_block_equals_compose_for_both_profiles(spec_text):
    spec_ports = parse_ports_block(block_lines(spec_text, "published-ports"))
    code_ports = compose_ports()
    assert sorted(code_ports - spec_ports) == [], "compose bindings missing from the spec"
    assert sorted(spec_ports - code_ports) == [], "spec bindings absent from compose"


def test_multi_user_profile_drops_neo4j_and_n8n_publishes(spec_text):
    spec_ports = parse_ports_block(block_lines(spec_text, "published-ports"))
    multi_user_services = {svc for profile, svc, _ip, _port in spec_ports if profile == "multi-user"}
    local_services = {svc for profile, svc, _ip, _port in spec_ports if profile == "local"}
    assert {"neo4j", "n8n"} <= local_services
    assert not ({"neo4j", "n8n"} & multi_user_services)


def test_no_mismatch_across_all_four_blocks(spec_text):
    assert collect_mismatches(spec_text) == []


def test_spec_holds_no_secret_value(spec_text):
    assert leak_findings(spec_text) == []


# --------------------------------------------------------------------------
# Induced failures: the comparison is not vacuous
# --------------------------------------------------------------------------


def _induced_copy(text: str) -> str:
    """One route-policy row removed, one role changed, one extra port line."""
    removed = "POST|/rules/bulk-delete|member|body|editor"
    changed_from = "POST|/auth/invites|member|body|owner"
    changed_to = "POST|/auth/invites|member|body|editor"
    port_anchor = "local|neo4j|127.0.0.1|7474"
    extra_port = "local|neo4j|0.0.0.0|9999"
    for needle in (removed, changed_from, port_anchor):
        assert text.count(needle) == 1, f"induced-mismatch anchor is not unique: {needle}"
    mutated = text.replace(removed + "\n", "", 1) if (removed + "\n") in text else text.replace(
        removed + "\r\n", "", 1
    )
    mutated = mutated.replace(changed_from, changed_to, 1)
    mutated = mutated.replace(port_anchor, port_anchor + "\n" + extra_port, 1)
    assert mutated != text
    return mutated


def test_induced_mismatch_reports_three_distinct_differences(spec_text):
    problems = collect_mismatches(_induced_copy(spec_text))
    assert len(problems) == 3, problems
    assert any(p.startswith("route-policy: missing from spec: POST /rules/bulk-delete") for p in problems)
    assert any(p.startswith("route-policy: changed: POST /auth/invites") for p in problems)
    assert any(p.startswith("published-ports: extra in spec: local|neo4j|0.0.0.0|9999") for p in problems)


def test_induced_stale_route_row_is_reported_against_the_app(spec_text):
    anchor = "GET|/|public|-|-"
    assert spec_text.count(anchor) == 1
    mutated = spec_text.replace(anchor, anchor + "\nGET|/throwaway|public|-|-", 1)
    unclassified, stale = route_set_mismatches(mutated)
    assert stale == {("GET", "/throwaway")} and unclassified == set()
    dropped = spec_text.replace(anchor, "", 1)
    unclassified, stale = route_set_mismatches(dropped)
    assert unclassified == {("GET", "/")} and stale == set()


def test_induced_public_and_known_default_differences_are_reported(spec_text):
    public_anchor = "POST|/auth/login|none"
    assert spec_text.count(public_anchor) == 1
    problems = collect_mismatches(spec_text.replace(public_anchor + "\n", "", 1))
    assert any(p.startswith("public-routes: missing from spec: POST /auth/login") for p in problems)

    prefix_anchor = "prefix|change-me"
    assert spec_text.count(prefix_anchor) == 1
    problems = collect_mismatches(spec_text.replace(prefix_anchor, prefix_anchor + "\nprefix|extra-prefix", 1))
    assert any("prefix entry in spec but not in code" in p for p in problems)
    problems = collect_mismatches(spec_text.replace(prefix_anchor + "\n", "", 1))
    assert any("prefix entry missing from spec" in p for p in problems)


def test_induced_leaks_are_detected(spec_text):
    hex_string = "ab" * 32
    assert any("64-hex" in f for f in leak_findings(spec_text + "\n" + hex_string + "\n"))
    assert any("synthetic" in f for f in leak_findings(spec_text + "\n" + _synthetic_values()[0] + "\n"))
    assert any("literal" in f for f in leak_findings(spec_text + "\nthe value 12345678 here\n"))
    # a plaintext value that hashes to a registered digest is caught when the
    # digest set is extended with a synthetic value
    synthetic = "synthetic-owner-value-for-leak-test"
    original = secrets_policy.KNOWN_DEFAULT_SHA256
    secrets_policy.KNOWN_DEFAULT_SHA256 = frozenset(
        set(original) | {hashlib.sha256(synthetic.encode("utf-8")).hexdigest()}
    )
    try:
        assert any("digest" in f for f in leak_findings(spec_text + "\n" + synthetic + "\n"))
    finally:
        secrets_policy.KNOWN_DEFAULT_SHA256 = original

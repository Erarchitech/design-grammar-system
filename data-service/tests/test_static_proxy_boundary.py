"""Static nginx + vite proxy boundary test (Phase 1205, plan 1205-15,
ALGN12-18 / ALGN12-19, D-06 / D-08 / D-16 static half).

Machine-checks that the UI container's nginx config and the vite dev-server
config expose no direct Neo4j or n8n route to the browser, that the removed
routes are explicit 404 tombstones (so the SPA ``try_files`` fallback can never
answer 200 for them), that every remaining proxy targets only data-service, and
that no location injects an ``Authorization`` credential.

No nginx binary is needed: a small brace-aware parser reads the config with
comments stripped. The live half of D-16 (real HTTP against the running stack)
is ``tools/security/check_live_boundary.py``.

Assert messages name locations and rules only -- never a header value.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(
    os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent.parent))
)
NGINX_CONF = REPO_ROOT / "ui-v2" / "nginx.conf"
VITE_CONFIG = REPO_ROOT / "ui-v2" / "vite.config.js"

# WR-22: the credential routes get their own rate-limited regex location that
# proxies to data-service like /data-service/ does.
RATE_LIMITED_AUTH_LOCATION = "^/data-service/auth/(login|password|accept-invite|register)/?$"
# Phase 1301-08 (D-16): the DeGram relay streams through its own location.
RELAY_LOCATION = "/data-service/degram/v1/"
# Phase 1301-09 (D-21): Speckle geometry streams through its own unbuffered location.
SPECKLE_PROXY_LOCATION = "/data-service/speckle-proxy/"
ALLOWED_PROXY_LOCATIONS = {
    "/data-service/",
    RELAY_LOCATION,
    SPECKLE_PROXY_LOCATION,
    "/llm/",
    "/reasoner/",
    RATE_LIMITED_AUTH_LOCATION,
}
EXPECTED_VITE_PROXY_KEYS = {"/data-service", "/llm", "/reasoner"}
DATA_SERVICE_UPSTREAM = "http://data-service:8000"
FORBIDDEN_UPSTREAM = re.compile(r"\b(neo4j|n8n)\b", re.IGNORECASE)


@dataclass
class Location:
    modifier: str
    path: str
    body: str

    @property
    def statements(self) -> list[str]:
        return [s.strip() for s in self.body.split(";") if s.strip()]


def strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.replace("\r\n", "\n").split("\n"))


def parse_locations(text: str) -> list[Location]:
    """Brace-aware extraction of every ``location`` block (comments stripped)."""
    clean = strip_comments(text)
    found: list[Location] = []
    pattern = re.compile(r"\blocation\s+(?:(\^~|~\*|~|=)\s+)?(\S+)\s*\{")
    for match in pattern.finditer(clean):
        depth = 1
        i = match.end()
        while i < len(clean) and depth:
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
            i += 1
        found.append(Location(match.group(1) or "", match.group(2), clean[match.end() : i - 1]))
    return found


def violations_for(nginx_text: str) -> list[str]:
    """Return rule-named violations for an nginx config text."""
    problems: list[str] = []
    locations = parse_locations(nginx_text)
    by_key = {(loc.modifier, loc.path): loc for loc in locations}

    for loc in locations:
        variables: dict[str, str] = {}
        for stmt in loc.statements:
            m = re.match(r"set\s+(\$\w+)\s+(\S+)$", stmt)
            if m:
                variables[m.group(1)] = m.group(2)
                if FORBIDDEN_UPSTREAM.search(m.group(2)):
                    problems.append(f"set-upstream-to-neo4j-or-n8n:{loc.path}")
        for stmt in loc.statements:
            m = re.match(r"proxy_pass\s+(\S+)$", stmt)
            if not m:
                continue
            target = variables.get(m.group(1), m.group(1))
            if FORBIDDEN_UPSTREAM.search(target):
                problems.append(f"proxy-to-neo4j-or-n8n:{loc.path}")
            elif target != DATA_SERVICE_UPSTREAM:
                problems.append(f"proxy-to-unexpected-upstream:{loc.path}")
            elif loc.path not in ALLOWED_PROXY_LOCATIONS:
                problems.append(f"unexpected-proxy-location:{loc.path}")
        for stmt in loc.statements:
            header = re.match(r"(?:proxy_set_header|add_header)\s+(\S+)", stmt, re.IGNORECASE)
            if header and header.group(1).strip("\"'").lower() == "authorization":
                problems.append(f"authorization-header-injected:{loc.path}")

    for path in ("/neo4j", "/n8n"):
        tomb = by_key.get(("^~", path))
        if tomb is None:
            problems.append(f"missing-404-tombstone:{path}")
        elif tomb.statements != ["return 404"]:
            problems.append(f"tombstone-not-plain-404:{path}")

    # Belt and braces: no proxy_pass / set / rewrite anywhere outside a
    # location (server level) may mention neo4j or n8n either.
    for line in strip_comments(nginx_text).split("\n"):
        if re.search(r"\b(proxy_pass|set|rewrite)\b", line) and re.search(
            r"(neo4j|n8n)\s*:\s*\d+|https?://(neo4j|n8n)\b", line, re.IGNORECASE
        ):
            problems.append("neo4j-or-n8n-upstream-literal")
            break
    return sorted(set(problems))


def vite_proxy_keys(vite_text: str) -> set[str]:
    clean = re.sub(r"//[^\n]*", "", vite_text)
    m = re.search(r"proxy\s*:\s*\{", clean)
    assert m, "vite.config.js has no server.proxy block"
    depth, i = 1, m.end()
    while i < len(clean) and depth:
        depth += {"{": 1, "}": -1}.get(clean[i], 0)
        i += 1
    block = clean[m.end() : i - 1]
    return set(re.findall(r"""["'](/[^"']*)["']\s*:""", block))


@pytest.fixture(scope="module")
def nginx_text() -> str:
    assert NGINX_CONF.is_file(), f"missing {NGINX_CONF}"
    return NGINX_CONF.read_text(encoding="utf-8")


def test_nginx_has_no_neo4j_or_n8n_proxy(nginx_text: str) -> None:
    problems = [p for p in violations_for(nginx_text) if "neo4j-or-n8n" in p]
    assert problems == []


def test_nginx_has_404_tombstones_for_neo4j_and_n8n(nginx_text: str) -> None:
    by_key = {(loc.modifier, loc.path): loc for loc in parse_locations(nginx_text)}
    for path in ("/neo4j", "/n8n"):
        tomb = by_key.get(("^~", path))
        assert tomb is not None, f"missing ^~ {path} tombstone location"
        assert tomb.statements == ["return 404"], f"{path} tombstone body must be exactly return 404"


def test_nginx_tombstones_precede_spa_fallback(nginx_text: str) -> None:
    locations = parse_locations(nginx_text)
    order = [(loc.modifier, loc.path) for loc in locations]
    fallback = order.index(("", "/"))
    assert order.index(("^~", "/neo4j")) < fallback
    assert order.index(("^~", "/n8n")) < fallback


def test_nginx_proxies_only_to_data_service(nginx_text: str) -> None:
    proxied = set()
    for loc in parse_locations(nginx_text):
        if any(s.startswith("proxy_pass") for s in loc.statements):
            proxied.add(loc.path)
    assert proxied == ALLOWED_PROXY_LOCATIONS
    problems = [p for p in violations_for(nginx_text) if "upstream" in p or "proxy-location" in p]
    assert problems == []


def test_nginx_injects_no_authorization_header(nginx_text: str) -> None:
    assert [p for p in violations_for(nginx_text) if p.startswith("authorization")] == []
    assert not re.search(r"authorization", strip_comments(nginx_text), re.IGNORECASE)


def test_nginx_config_is_fully_clean(nginx_text: str) -> None:
    assert violations_for(nginx_text) == []


def test_vite_dev_proxy_keys_are_exactly_data_service_llm_reasoner() -> None:
    assert VITE_CONFIG.is_file(), f"missing {VITE_CONFIG}"
    assert vite_proxy_keys(VITE_CONFIG.read_text(encoding="utf-8")) == EXPECTED_VITE_PROXY_KEYS


# --- induced-regression proofs: the guard must actually detect a regression ---

RESTORED_NEO4J_BLOCK = """
  location /neo4j/ {
    set $neo4j_upstream http://neo4j:7474;
    rewrite ^/neo4j/(.*) /$1 break;
    proxy_pass $neo4j_upstream;
    proxy_set_header Host $host;
  }
"""


def test_induced_restored_neo4j_proxy_is_detected(nginx_text: str) -> None:
    tampered = re.sub(
        r"location \^~ /neo4j \{\s*return 404;\s*\}", RESTORED_NEO4J_BLOCK, nginx_text, count=1
    )
    assert tampered != nginx_text
    problems = violations_for(tampered)
    assert "proxy-to-neo4j-or-n8n:/neo4j/" in problems
    assert "set-upstream-to-neo4j-or-n8n:/neo4j/" in problems
    assert "missing-404-tombstone:/neo4j" in problems


def test_induced_missing_tombstone_is_detected(nginx_text: str) -> None:
    tampered = re.sub(r"location \^~ /n8n \{\s*return 404;\s*\}", "", nginx_text, count=1)
    assert "missing-404-tombstone:/n8n" in violations_for(tampered)


def test_induced_authorization_injection_is_detected(nginx_text: str) -> None:
    tampered = nginx_text.replace(
        "proxy_set_header Host $host;",
        'proxy_set_header Authorization "Bearer synthetic";\n    proxy_set_header Host $host;',
        1,
    )
    assert tampered != nginx_text
    assert any(p.startswith("authorization-header-injected") for p in violations_for(tampered))


def test_induced_vite_neo4j_proxy_is_detected() -> None:
    text = VITE_CONFIG.read_text(encoding="utf-8").replace(
        'proxy: {', 'proxy: {\n      "/neo4j": "http://localhost:8080",', 1
    )
    assert vite_proxy_keys(text) != EXPECTED_VITE_PROXY_KEYS


# --- Phase 1301 plan 08 (D-16, D-18): the DeGram relay streaming location ---

import sys  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "data-service"))
from degram_relay import DEGRAM_RELAY_TOTAL_TIMEOUT_S  # noqa: E402


def _relay_location(nginx_text: str) -> Location:
    matches = [loc for loc in parse_locations(nginx_text) if loc.path == RELAY_LOCATION]
    assert len(matches) == 1, f"expected exactly one {RELAY_LOCATION} location"
    return matches[0]


def _seconds(stmt_value: str) -> float:
    m = re.fullmatch(r"(\d+)(ms|s|m|h)?", stmt_value.strip())
    assert m, f"unparseable nginx time {stmt_value!r}"
    return int(m.group(1)) * {"ms": 0.001, None: 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


def test_relay_location_streams_without_buffering(nginx_text: str) -> None:
    loc = _relay_location(nginx_text)
    statements = loc.statements
    assert "proxy_http_version 1.1" in statements
    assert "proxy_buffering off" in statements
    assert 'proxy_set_header Connection ""' in statements
    assert "set $ds_upstream http://data-service:8000" in statements
    assert "proxy_pass $ds_upstream" in statements
    assert "rewrite ^/data-service/(.*) /$1 break" in statements


def test_relay_read_timeout_exceeds_the_relay_total_timeout(nginx_text: str) -> None:
    loc = _relay_location(nginx_text)
    values = [s.split(None, 1)[1] for s in loc.statements if s.startswith("proxy_read_timeout ")]
    assert len(values) == 1
    assert _seconds(values[0]) > DEGRAM_RELAY_TOTAL_TIMEOUT_S


def test_relay_body_limit_matches_the_relay_ceiling(nginx_text: str) -> None:
    loc = _relay_location(nginx_text)
    values = [s.split(None, 1)[1] for s in loc.statements if s.startswith("client_max_body_size ")]
    assert values == ["1m"]  # 1 MiB, the relay's DEGRAM_RELAY_MAX_BODY_BYTES


def test_relay_location_keeps_the_server_level_security_headers(nginx_text: str) -> None:
    """nginx stops inheriting server-level add_header the moment a location
    declares one of its own; the streaming location must declare none."""
    loc = _relay_location(nginx_text)
    assert not any(s.startswith("add_header") for s in loc.statements)
    server_level = re.split(r"\blocation\s", strip_comments(nginx_text), maxsplit=1)[0]
    for header in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
                   "Permissions-Policy", "Content-Security-Policy"):
        assert header in server_level


def test_relay_location_precedes_the_generic_data_service_location(nginx_text: str) -> None:
    order = [loc.path for loc in parse_locations(nginx_text)]
    assert order.index(RELAY_LOCATION) < order.index("/data-service/")


def test_llm_prefix_does_not_route_to_the_relay(nginx_text: str) -> None:
    """/llm/ proxies to data-service unchanged: it never rewrites into /degram/,
    and no location other than the relay one mentions the relay path."""
    for loc in parse_locations(nginx_text):
        if loc.path == "/llm/":
            assert not any(s.startswith("rewrite") for s in loc.statements)
        if loc.path != RELAY_LOCATION:
            assert "degram" not in loc.body
    assert "degram" not in re.split(r"\blocation\s", strip_comments(nginx_text), maxsplit=1)[0]


def test_relay_location_adds_no_authorization_injection(nginx_text: str) -> None:
    assert [p for p in violations_for(nginx_text) if "authorization" in p] == []


def test_induced_buffering_regression_is_detected(nginx_text: str) -> None:
    tampered = nginx_text.replace("proxy_buffering off;", "proxy_buffering on;", 1)
    assert tampered != nginx_text
    assert "proxy_buffering off" not in _relay_location(tampered).statements


# -- Phase 1301-09 (D-21): Speckle geometry proxy location ---------------------------


def _speckle_location(nginx_text: str) -> Location:
    matches = [loc for loc in parse_locations(nginx_text) if loc.path == SPECKLE_PROXY_LOCATION]
    assert len(matches) == 1, f"expected exactly one {SPECKLE_PROXY_LOCATION} location"
    return matches[0]


def test_speckle_proxy_location_streams_geometry_without_buffering(nginx_text: str) -> None:
    statements = _speckle_location(nginx_text).statements
    assert "proxy_http_version 1.1" in statements
    assert "proxy_buffering off" in statements
    assert 'proxy_set_header Connection ""' in statements
    assert "set $ds_upstream http://data-service:8000" in statements
    assert "proxy_pass $ds_upstream" in statements
    assert "rewrite ^/data-service/(.*) /$1 break" in statements


def test_speckle_proxy_read_timeout_exceeds_the_proxys_upstream_read_limit(nginx_text: str) -> None:
    import speckle_proxy  # noqa: PLC0415

    values = [s.split(None, 1)[1] for s in _speckle_location(nginx_text).statements
              if s.startswith("proxy_read_timeout ")]
    assert len(values) == 1
    assert _seconds(values[0]) > speckle_proxy.UPSTREAM_TIMEOUT.read


def test_speckle_proxy_body_limit_covers_the_proxys_ceiling(nginx_text: str) -> None:
    import speckle_proxy  # noqa: PLC0415

    values = [s.split(None, 1)[1] for s in _speckle_location(nginx_text).statements
              if s.startswith("client_max_body_size ")]
    assert values == ["4m"]
    assert speckle_proxy.MAX_BODY_BYTES == 4 * 1024 * 1024


def test_speckle_proxy_location_keeps_security_headers_and_injects_nothing(nginx_text: str) -> None:
    loc = _speckle_location(nginx_text)
    assert not any(s.startswith("add_header") for s in loc.statements)
    assert not any("authorization" in s.lower() for s in loc.statements)
    assert [p for p in violations_for(nginx_text) if "authorization" in p] == []


def test_speckle_proxy_location_precedes_the_generic_data_service_location(nginx_text: str) -> None:
    order = [loc.path for loc in parse_locations(nginx_text)]
    assert order.index(SPECKLE_PROXY_LOCATION) < order.index("/data-service/")


def test_nginx_never_proxies_straight_to_speckle(nginx_text: str) -> None:
    """The browser reaches Speckle geometry only through data-service: no nginx
    location names a Speckle upstream, so no token-free direct path exists."""
    assert not re.search(r"speckle-(server|ingress|frontend)|:3000|:8090", strip_comments(nginx_text))

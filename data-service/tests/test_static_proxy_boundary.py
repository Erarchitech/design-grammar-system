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

ALLOWED_PROXY_LOCATIONS = {"/data-service/", "/llm/", "/reasoner/"}
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

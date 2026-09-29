"""Static compose + dockerignore boundary test (Phase 1205, plan 1205-09,
ALGN12-18 / ALGN12-19, D-07 / D-09 / D-10).

Machine-checks the deployment surface without starting Docker and without
resolving ``.env``: published ports and their loopback bindings, that every
secret-bearing compose key is a required ``${VAR:?...}`` interpolation, that no
known-default literal or digest survives in the file, that the UI container
carries no credential environment, that the multi-user override drops the
Neo4j / n8n publishes with ``!reset``, and that the data-service build context
excludes runtime state.

The compose files use CRLF and the ``!reset`` tag defeats ``yaml.safe_load``, so
this uses a small explicit indentation parser (service names at two spaces
under ``services:``, ``ports:`` / ``environment:`` at four, items at six).

Assert messages name keys and services only -- never an environment value.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

import secrets_policy

REPO_ROOT = Path(
    os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent.parent))
)
BASE_COMPOSE = REPO_ROOT / "docker-compose.yml"
MULTI_USER_COMPOSE = REPO_ROOT / "docker-compose.multi-user.yml"
DOCKERIGNORE = REPO_ROOT / "data-service" / ".dockerignore"

LF = chr(10)
CRLF = chr(13) + chr(10)

EXPECTED_LOOPBACK_PORTS = {"7474", "7687", "8000", "8001", "5678", "9000", "9001", "11435"}
EXPECTED_OPEN_PORTS = {"8080", "8090"}

# (service, key) pairs that must be required interpolations (D-10).
REQUIRED_SECRET_KEYS = {
    ("neo4j", "NEO4J_AUTH", "NEO4J_PASSWORD"),
    ("dg-reasoner", "NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    ("data-service", "NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    ("data-service", "LLM_MASTER_SECRET", "LLM_MASTER_SECRET"),
    ("data-service", "DG_SERVICE_TOKEN", "DG_SERVICE_TOKEN"),
    ("data-service", "DG_BOOTSTRAP_ADMIN_USER", "DG_BOOTSTRAP_ADMIN_USER"),
    ("data-service", "DG_BOOTSTRAP_ADMIN_PASSWORD", "DG_BOOTSTRAP_ADMIN_PASSWORD"),
    ("n8n", "N8N_BASIC_AUTH_USER", "N8N_USER"),
    ("n8n", "N8N_BASIC_AUTH_PASSWORD", "N8N_PASSWORD"),
    ("n8n", "DG_SERVICE_TOKEN", "DG_SERVICE_TOKEN"),
    ("n8n", "NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    ("speckle-postgres", "POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
    ("speckle-minio", "MINIO_ROOT_USER", "MINIO_ROOT_USER"),
    ("speckle-minio", "MINIO_ROOT_PASSWORD", "MINIO_ROOT_PASSWORD"),
    ("speckle-server", "SESSION_SECRET", "SPECKLE_SESSION_SECRET"),
    ("speckle-server", "POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
    ("speckle-server", "S3_ACCESS_KEY", "MINIO_ROOT_USER"),
    ("speckle-server", "S3_SECRET_KEY", "MINIO_ROOT_PASSWORD"),
}

# Secret-named keys that are optional by design (Speckle integration is also
# configurable through /settings/speckle) and therefore use ${VAR:-}.
OPTIONAL_SECRET_KEYS = {"SPECKLE_WRITE_TOKEN", "SPECKLE_READ_TOKEN"}

SECRET_KEY_PATTERN = re.compile(
    r"(PASSWORD|SECRET|TOKEN|ACCESS_KEY|NEO4J_AUTH|BASIC_AUTH_USER|ROOT_USER|CONNECTION_STRING|QUEUE_POSTGRES_URL)"
)
_INTERP = re.compile(r"\$\{([A-Za-z_0-9]+)(:[-?])?([^}]*)\}")


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def parse_compose(text: str) -> dict[str, dict]:
    """Return ``{service: {"ports": [...], "ports_reset": bool, "environment": {...}}}``."""
    services: dict[str, dict] = {}
    in_services = False
    service: str | None = None
    section: str | None = None
    for raw in text.replace("\r", "").split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            in_services = stripped == "services:"
            service = section = None
            continue
        if not in_services:
            continue
        if indent == 2 and stripped.endswith(":"):
            service = stripped[:-1]
            services[service] = {"ports": [], "ports_reset": False, "environment": {}}
            section = None
            continue
        if service is None:
            continue
        if indent == 4:
            key, _, rest = stripped.partition(":")
            section = key if key in ("ports", "environment") else None
            if key == "ports" and "!reset" in rest:
                services[service]["ports_reset"] = True
            continue
        if section == "ports" and indent == 6 and stripped.startswith("- "):
            services[service]["ports"].append(_unquote(stripped[2:]))
        elif section == "environment" and indent == 6 and ":" in stripped:
            key, _, value = stripped.partition(": ")
            services[service]["environment"][key.strip()] = _unquote(value)
    return services


def split_port(item: str) -> tuple[str, str]:
    """Return ``(host_ip, host_port)`` for a compose short-syntax port item."""
    parts = item.split(":")
    if len(parts) == 3:
        return parts[0], parts[1]
    if len(parts) == 2:
        return "", parts[0]
    return "", parts[0]


def check_bindings(services: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    loopback: set[str] = set()
    open_: set[str] = set()
    for name, svc in services.items():
        for item in svc["ports"]:
            ip, host = split_port(item)
            if ip == "127.0.0.1":
                loopback.add(host)
            elif ip in ("", "0.0.0.0"):
                open_.add(host)
                if host not in EXPECTED_OPEN_PORTS:
                    problems.append(f"{name}: port {host} is published on all interfaces")
            else:
                problems.append(f"{name}: port {host} binds unexpected host ip")
    if loopback != EXPECTED_LOOPBACK_PORTS:
        problems.append(
            "loopback publishes differ from D-09: "
            f"missing={sorted(EXPECTED_LOOPBACK_PORTS - loopback)} extra={sorted(loopback - EXPECTED_LOOPBACK_PORTS)}"
        )
    if open_ != EXPECTED_OPEN_PORTS:
        problems.append(
            f"all-interface publishes differ from D-09: got={sorted(open_)} want={sorted(EXPECTED_OPEN_PORTS)}"
        )
    return problems


def _is_required(value: str, var: str) -> bool:
    return any(m.group(1) == var and m.group(2) == ":?" for m in _INTERP.finditer(value))


def check_required_secrets(services: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    for service, key, var in sorted(REQUIRED_SECRET_KEYS):
        value = services.get(service, {}).get("environment", {}).get(key)
        if value is None:
            problems.append(f"{service}.{key} is missing")
        elif not _is_required(value, var):
            problems.append(f"{service}.{key} is not a required ${{{var}:?...}} interpolation")
    # Every secret-named key anywhere must be a required interpolation (or an
    # explicitly optional Speckle token), and postgres URLs must interpolate the password.
    for service, svc in services.items():
        for key, value in svc["environment"].items():
            if key in OPTIONAL_SECRET_KEYS or not SECRET_KEY_PATTERN.search(key):
                continue
            if ":?" not in value:
                problems.append(f"{service}.{key} carries no required interpolation")
            if re.search(r"postgres(ql)?://", value) and not _is_required(value, "POSTGRES_PASSWORD"):
                problems.append(f"{service}.{key} does not interpolate ${{POSTGRES_PASSWORD:?...}}")
    return problems


def _candidates(text: str, services: dict[str, dict]) -> list[tuple[str, str]]:
    """(where, candidate) pairs to test against the known-default policy.

    Candidates: every whitespace/quote-delimited token of every line, every
    ``${VAR:-fallback}`` fallback, and the value of every secret-named key with
    interpolations removed.
    """
    out: list[tuple[str, str]] = []
    for lineno, line in enumerate(text.replace("\r", "").split("\n"), start=1):
        for token in re.split(r"[\s\"']+", line):
            if token:
                out.append((f"line {lineno}", token))
        for m in _INTERP.finditer(line):
            if m.group(2) == ":-" and m.group(3):
                out.append((f"line {lineno}", m.group(3)))
    for service, svc in services.items():
        for key, value in svc["environment"].items():
            # URL-shaped keys embed a database name, not a secret literal; their
            # password is covered by check_required_secrets.
            if SECRET_KEY_PATTERN.search(key) and "://" not in value:
                out.append((f"{service}.{key}", _INTERP.sub("", value).split("/")[-1]))
    return out


def check_known_defaults(text: str, services: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    literals = set(secrets_policy.KNOWN_DEFAULT_LITERALS)
    digests = set(secrets_policy.KNOWN_DEFAULT_SHA256)
    # Bare usernames such as ``neo4j`` / ``speckle`` are legitimate non-secret
    # values (NEO4J_USER, POSTGRES_USER); only secret-named keys are held to
    # the short-literal list, while the digits-only Neo4j literal and MinIO
    # default may appear nowhere.
    everywhere = {lit for lit in literals if lit in ("12345678", "minioadmin")}
    for where, cand in _candidates(text, services):
        digest = hashlib.sha256(cand.encode("utf-8")).hexdigest()
        if digest in digests:
            problems.append(f"{where}: value hashes to a known-default digest")
        if where.startswith("line "):
            if cand in everywhere or cand.startswith(secrets_policy.KNOWN_DEFAULT_PREFIXES):
                problems.append(f"{where}: known-default literal present")
        elif cand in literals or cand.lower().replace("_", "-").startswith(
            secrets_policy.KNOWN_DEFAULT_PREFIXES
        ):
            problems.append(f"{where}: secret key holds a known-default literal")
    return problems


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def base_text() -> str:
    # Normalised to LF so the mutation tests below do not depend on the
    # checkout's line endings; CRLF tolerance is tested separately.
    return BASE_COMPOSE.read_bytes().decode("utf-8").replace(CRLF, LF)


@pytest.fixture(scope="module")
def base(base_text) -> dict[str, dict]:
    return parse_compose(base_text)


@pytest.fixture(scope="module")
def override() -> dict[str, dict]:
    return parse_compose(MULTI_USER_COMPOSE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Behaviours
# --------------------------------------------------------------------------


def test_parser_reads_expected_services(base):
    for name in ("neo4j", "data-service", "n8n", "design-grammars", "speckle-server"):
        assert name in base
    assert "127.0.0.1:7474:7474" in base["neo4j"]["ports"]


def test_parser_is_crlf_tolerant(base_text, base):
    assert parse_compose(base_text.replace(LF, CRLF)) == base


def test_published_ports_match_d09(base):
    assert check_bindings(base) == []


def test_required_secrets_are_interpolated(base):
    assert check_required_secrets(base) == []


def test_speckle_optional_tokens_stay_optional(base):
    env = base["data-service"]["environment"]
    for key in OPTIONAL_SECRET_KEYS:
        assert env[key].startswith("${" + key + ":-")


def test_no_known_default_literal_or_digest(base_text, base):
    assert check_known_defaults(base_text, base) == []


def test_ui_container_has_no_credential_environment(base):
    env = base["design-grammars"]["environment"]
    bad = [k for k in env if k.startswith(("NEO4J_", "N8N_")) or k == "SPECKLE_READ_TOKEN"]
    assert bad == []
    assert env["DATA_SERVICE_URL"] == "/data-service"


def test_n8n_receives_service_token_and_env_access(base):
    env = base["n8n"]["environment"]
    for key in ("DG_SERVICE_TOKEN", "NEO4J_USER", "NEO4J_PASSWORD"):
        assert key in env, key
    assert env["N8N_BLOCK_ENV_ACCESS_IN_NODE"] == "false"


def test_data_service_profile_defaults_are_local(base):
    env = base["data-service"]["environment"]
    assert env["DG_DEPLOYMENT"] == "${DG_DEPLOYMENT:-local}"
    assert env["DG_COOKIE_SECURE"] == "${DG_COOKIE_SECURE:-false}"


def test_multi_user_override_drops_neo4j_and_n8n_publishes(override):
    assert override["neo4j"]["ports_reset"] is True
    assert override["n8n"]["ports_reset"] is True
    assert override["neo4j"]["ports"] == [] and override["n8n"]["ports"] == []
    assert override["data-service"]["environment"]["DG_DEPLOYMENT"] == "multi-user"


def test_multi_user_override_does_not_republish_anything(override):
    assert all(not svc["ports"] for svc in override.values())


def test_dockerignore_excludes_runtime_state():
    lines = {ln.strip() for ln in DOCKERIGNORE.read_text(encoding="utf-8").replace("\r", "").split("\n")}
    assert "data/" in lines
    assert ".env" in lines
    # In-container pytest is authoritative, so tests/ must remain in the image.
    assert "tests/" not in lines


# --------------------------------------------------------------------------
# Induced failure: the checks are not vacuous
# --------------------------------------------------------------------------


def test_induced_unbound_port_is_detected(base_text):
    mutated = base_text.replace('"127.0.0.1:7474:7474"', '"7474:7474"', 1)
    assert mutated != base_text
    problems = check_bindings(parse_compose(mutated))
    assert any("7474" in p for p in problems)


def test_induced_extra_publish_is_detected(base_text):
    mutated = base_text.replace('"8090:8080"', '"8090:8080"' + LF + '      - "9999:9999"', 1)
    assert mutated != base_text
    assert any("9999" in p for p in check_bindings(parse_compose(mutated)))


def test_induced_optional_secret_is_detected(base_text):
    mutated = base_text.replace("${NEO4J_PASSWORD:?", "${NEO4J_PASSWORD:-", 1)
    assert mutated != base_text
    problems = check_required_secrets(parse_compose(mutated))
    assert any("NEO4J" in p for p in problems)


def test_induced_postgres_url_without_required_password_is_detected(base_text):
    mutated = base_text.replace(
        "postgres://speckle:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env (see .env.example)}@",
        "postgres://speckle:${POSTGRES_PASSWORD:-x}@",
        1,
    )
    assert mutated != base_text
    problems = check_required_secrets(parse_compose(mutated))
    assert any("POSTGRES_PASSWORD" in p for p in problems)


def test_induced_known_default_literal_is_detected(base_text):
    literal = "".join(["1234", "5678"])
    mutated = base_text.replace(
        "${N8N_PASSWORD:?set N8N_PASSWORD in .env (see .env.example)}",
        "${N8N_PASSWORD:-" + literal + "}",
        1,
    )
    assert mutated != base_text
    problems = check_known_defaults(mutated, parse_compose(mutated))
    assert problems


def test_induced_known_default_digest_is_detected(base_text, monkeypatch):
    synthetic = "synthetic-owner-password-for-test"
    monkeypatch.setattr(
        secrets_policy,
        "KNOWN_DEFAULT_SHA256",
        frozenset(set(secrets_policy.KNOWN_DEFAULT_SHA256) | {hashlib.sha256(synthetic.encode()).hexdigest()}),
    )
    mutated = base_text.replace(
        "${N8N_PASSWORD:?set N8N_PASSWORD in .env (see .env.example)}",
        "${N8N_PASSWORD:-" + synthetic + "}",
        1,
    )
    assert mutated != base_text
    problems = check_known_defaults(mutated, parse_compose(mutated))
    assert any("digest" in p for p in problems)
    # and the pristine file is still clean under the extended digest list
    assert check_known_defaults(base_text, parse_compose(base_text)) == []


def test_induced_ui_credential_env_is_detected(base_text):
    mutated = base_text.replace(
        "      DATA_SERVICE_URL: /data-service" + LF,
        "      DATA_SERVICE_URL: /data-service" + LF + "      NEO4J_USER: neo4j" + LF,
        1,
    )
    assert mutated != base_text
    env = parse_compose(mutated)["design-grammars"]["environment"]
    assert any(k.startswith("NEO4J_") for k in env)

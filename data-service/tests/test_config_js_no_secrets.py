"""Runtime-config and built-bundle secret scan (Phase 1205, plan 1205-15,
ALGN12-18 / ALGN12-19, D-12).

Proves that nothing the UI container serves to a browser carries a credential:

* ``ui-v2/gen-config.sh`` is executed with hostile environment values and must
  emit ``window.GRAPH_CONFIG`` with exactly ``dataServiceUrl`` and
  ``speckleBaseUrl``, none of the hostile values leaking through.
* ``ui-v2/entrypoint.sh`` and ``gen-config.sh`` never name a credential key.
* Every ``*.js`` / ``*.html`` file under ``ui-v2/dist`` is scanned for
  credential key names, the Neo4j HTTP transaction path, the committed Neo4j
  default literal, the ``change-me`` placeholder prefix, and -- by hashing every
  quoted string literal -- the committed n8n password digest
  (``secrets_policy.KNOWN_DEFAULT_SHA256``).

The scan fails closed: a missing ``dist`` fails the test, it never skips.
Assert messages name rules and files only -- never a value.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import secrets_policy

REPO_ROOT = Path(
    os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent.parent))
)
UI_DIR = REPO_ROOT / "ui-v2"
DIST_DIR = UI_DIR / "dist"
GEN_CONFIG = UI_DIR / "gen-config.sh"
ENTRYPOINT = UI_DIR / "entrypoint.sh"

EXPECTED_KEYS = {"dataServiceUrl", "speckleBaseUrl"}
FORBIDDEN_KEY_NAMES = (
    "neo4jPassword",
    "neo4jUser",
    "n8nPassword",
    "n8nUser",
    "speckleReadToken",
    "neo4jHttp",
    "n8nWebhook",
    "n8nQueryWebhook",
)
# Committed Neo4j default password, taken from the policy list (never spelled out here).
NEO4J_DEFAULT_LITERAL = "12345678"
MAX_LITERAL_LEN = 256

# Synthetic hostile values: the generator must not copy any of them.
HOSTILE_ENV = {
    "NEO4J_PASSWORD": "synthetic-neo4j-pw-Zq81",
    "NEO4J_USER": "synthetic-neo4j-user-Zq81",
    "N8N_PASSWORD": "synthetic-n8n-pw-Zq81",
    "N8N_USER": "synthetic-n8n-user-Zq81",
    "SPECKLE_READ_TOKEN": "synthetic-speckle-token-Zq81",
    "NEO4J_URI": "bolt://synthetic-host-Zq81:7687",
    "DATA_SERVICE_URL": "/data-service",
}

STRING_LITERAL = re.compile(
    r"""'((?:[^'\\\n]|\\.){0,%d})'|"((?:[^"\\\n]|\\.){0,%d})"|`((?:[^`\\]|\\.){0,%d})`"""
    % (MAX_LITERAL_LEN, MAX_LITERAL_LEN, MAX_LITERAL_LEN)
)


def run_generator(out: Path, env_extra: dict[str, str]) -> str:
    sh = shutil.which("sh")
    assert sh, "sh not found on PATH; cannot run gen-config.sh"
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TMP", "TEMP", "HOME")}
    env.update(env_extra)
    proc = subprocess.run(
        [sh, GEN_CONFIG.as_posix(), out.as_posix()],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"gen-config.sh exited {proc.returncode}: {proc.stderr[:300]}"
    return out.read_text(encoding="utf-8")


def config_keys(text: str) -> set[str]:
    m = re.search(r"window\.GRAPH_CONFIG\s*=\s*\{(.*?)\}\s*;", text, re.DOTALL)
    assert m, "generated config.js has no window.GRAPH_CONFIG object"
    return set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*:", m.group(1), re.MULTILINE))


def test_generator_emits_only_two_keys_under_hostile_env(tmp_path: Path) -> None:
    text = run_generator(tmp_path / "config.js", HOSTILE_ENV)
    assert config_keys(text) == EXPECTED_KEYS
    for name, value in HOSTILE_ENV.items():
        if name == "DATA_SERVICE_URL":
            continue
        assert value not in text, f"hostile env var {name} leaked into config.js"


def test_generator_defaults_without_env(tmp_path: Path) -> None:
    text = run_generator(tmp_path / "config.js", {})
    assert config_keys(text) == EXPECTED_KEYS
    assert 'dataServiceUrl: "/data-service"' in text
    assert 'speckleBaseUrl: "http://localhost:8090"' in text


def test_generator_escapes_hostile_url_values(tmp_path: Path) -> None:
    text = run_generator(
        tmp_path / "config.js",
        {"DATA_SERVICE_URL": '/x", injected: "1', "SPECKLE_BASE_URL": "http://h\\\"\nsecondLine: 1"},
    )
    assert config_keys(text) == EXPECTED_KEYS


@pytest.mark.parametrize("path", [ENTRYPOINT, GEN_CONFIG], ids=lambda p: p.name)
def test_startup_scripts_name_no_credential_key(path: Path) -> None:
    assert path.is_file(), f"missing {path.name}"
    text = path.read_text(encoding="utf-8")
    hits = [k for k in FORBIDDEN_KEY_NAMES if k in text]
    assert hits == [], f"{path.name} names credential keys: {hits}"


def test_entrypoint_calls_generator_then_execs_nginx() -> None:
    lines = [ln.strip() for ln in ENTRYPOINT.read_text(encoding="utf-8").splitlines()]
    code = [ln for ln in lines if ln and not ln.startswith("#")]
    assert "/gen-config.sh /usr/share/nginx/html/config.js" in code
    assert code.index("/gen-config.sh /usr/share/nginx/html/config.js") < code.index(
        "exec nginx -g 'daemon off;'"
    )


def test_dockerfile_copies_generator_and_marks_it_executable() -> None:
    text = (UI_DIR / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY gen-config.sh /gen-config.sh" in text
    assert re.search(r"chmod \+x[^\n]*/gen-config\.sh", text)


def _dist_files() -> list[Path]:
    index = DIST_DIR / "index.html"
    assert index.is_file(), "run npm --prefix ui-v2 run build first"
    files = [p for p in DIST_DIR.rglob("*") if p.is_file() and p.suffix in (".js", ".html")]
    assert files, "run npm --prefix ui-v2 run build first"
    return files


def _literal_hits(text: str) -> tuple[bool, bool]:
    """(hits_known_default_sha256, hits_neo4j_default_literal) over string literals."""
    sha_hit = neo4j_hit = False
    for m in STRING_LITERAL.finditer(text):
        lit = next(g for g in m.groups() if g is not None)
        if hashlib.sha256(lit.encode("utf-8")).hexdigest() in secrets_policy.KNOWN_DEFAULT_SHA256:
            sha_hit = True
        if lit == NEO4J_DEFAULT_LITERAL:
            neo4j_hit = True
    return sha_hit, neo4j_hit


def test_dist_bundle_carries_no_credential_material() -> None:
    problems: list[str] = []
    for path in _dist_files():
        rel = path.relative_to(DIST_DIR).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for key in FORBIDDEN_KEY_NAMES:
            if key in text:
                problems.append(f"credential-key-name:{key}:{rel}")
        if "tx/commit" in text:
            problems.append(f"neo4j-tx-commit-path:{rel}")
        if re.search(r"change[-_]me", text, re.IGNORECASE):
            problems.append(f"change-me-prefix:{rel}")
        sha_hit, neo4j_hit = _literal_hits(text)
        if sha_hit:
            problems.append(f"known-default-digest-literal:{rel}")
        if neo4j_hit:
            problems.append(f"neo4j-default-literal:{rel}")
    assert problems == []


def test_scan_fails_closed_when_dist_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(f"{__name__}.DIST_DIR", tmp_path / "no-dist")
    with pytest.raises(AssertionError, match="run npm --prefix ui-v2 run build first"):
        _dist_files()


def test_literal_hash_scan_detects_an_induced_digest_match(monkeypatch: pytest.MonkeyPatch) -> None:
    probe = "induced-probe-literal"
    digest = hashlib.sha256(probe.encode("utf-8")).hexdigest()
    monkeypatch.setattr(secrets_policy, "KNOWN_DEFAULT_SHA256", frozenset({digest}))
    assert _literal_hits(f'var a="{probe}";')[0] is True
    assert _literal_hits(f"var a='{probe}';")[0] is True
    assert _literal_hits('var a="something-else";')[0] is False
    assert _literal_hits(f'var a="{NEO4J_DEFAULT_LITERAL}";')[1] is True

"""Shared pytest configuration.

Phase 35-13: registers the recognition eval harness's CLI options
(`--corpus`/`--arm`/`--arms`/`--sc1-gate`/`--permutations`, 35-AI-SPEC.md 5
"CI/CD integration") and the `eval`/`live` markers, with `not live` as the
default marker expression -- a developer running bare `pytest` must never
make a paid API call by accident.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# Phase 1205-08 (D-20): fixed test-only values. Never real secrets.
_TEST_SERVICE_TOKEN = "dg-test-service-token-0123456789abcdefghijklmnop"  # 48 chars
_TEST_BOOTSTRAP_ADMIN_USER = "test-bootstrap-admin@dg.local"
_TEST_BOOTSTRAP_ADMIN_PASSWORD = "dg-test-bootstrap-pw-not-a-secret-01"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("recognition-eval")
    group.addoption(
        "--corpus",
        action="store",
        default=None,
        help="Recognition eval: corpus name to score (e.g. urbanblock_slice).",
    )
    group.addoption(
        "--arm",
        action="store",
        default=None,
        help="Recognition eval: single ablation arm id to run (e.g. A3).",
    )
    group.addoption(
        "--arms",
        action="store",
        default=None,
        help="Recognition eval: comma-separated ablation arm ids to sweep (e.g. A0,A0f,A1,A2,A3,A4,A5).",
    )
    group.addoption(
        "--sc1-gate",
        action="store",
        default=0.60,
        type=float,
        help="Recognition eval: SC1 ship-gate M1 threshold (default 0.60).",
    )
    group.addoption(
        "--permutations",
        action="store",
        default=1,
        type=int,
        help="Recognition eval: number of few-shot example-order permutations to sweep (default 1).",
    )


def _redirect_auth_store() -> None:
    """D-20 / T-1205-08-02: point the auth stores at a session temp dir and
    override the auth-relevant secrets with test-only values, before any test
    module imports the app. The deployment-profile variable is deliberately left alone (D-18)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import auth  # noqa: PLC0415

    store_dir = tempfile.mkdtemp(prefix="dg-auth-test-")
    auth.AUTH_DIR = type(auth.USERS_FILE)(store_dir)
    auth.USERS_FILE = auth.AUTH_DIR / "auth-users.json"
    auth.SESSIONS_FILE = auth.AUTH_DIR / "auth-sessions.json"
    auth.MEMBERSHIPS_FILE = auth.AUTH_DIR / "auth-memberships.json"
    auth.INVITES_FILE = auth.AUTH_DIR / "auth-invites.json"

    os.environ["DG_SERVICE_TOKEN"] = _TEST_SERVICE_TOKEN
    os.environ["DG_BOOTSTRAP_ADMIN_USER"] = _TEST_BOOTSTRAP_ADMIN_USER
    os.environ["DG_BOOTSTRAP_ADMIN_PASSWORD"] = _TEST_BOOTSTRAP_ADMIN_PASSWORD


def pytest_configure(config: pytest.Config) -> None:
    _redirect_auth_store()
    config.addinivalue_line(
        "markers",
        "dg_principal(name): authorise the module-level TestClient `client` as "
        "'admin' (default), 'service' or 'none' for this test (D-20, 1205-08).",
    )
    config.addinivalue_line(
        "markers",
        "eval: recognition eval harness test (deterministic/replay by default, still not a unit test).",
    )
    config.addinivalue_line(
        "markers",
        "live: makes a live LLM call. Excluded by default -- pass -m live to run "
        "(and RECOGNITION_EVAL_MODE=record or =live).",
    )
    config.addinivalue_line(
        "markers",
        "integration: requires the compose network -- the `neo4j` hostname only "
        "resolves there (not from the host). Not deselected by default; select "
        "explicitly with `-k structural` or `-m integration` inside the container.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """Deselect every `live`-marked item unless the user explicitly passed
    `-m ...` themselves -- a bare `pytest` run must never make a paid API
    call by accident (35-AI-SPEC.md 5)."""
    if config.option.markexpr:
        return  # user supplied -m explicitly; respect it verbatim

    selected, deselected = [], []
    for item in items:
        if item.get_closest_marker("live") is not None:
            deselected.append(item)
        else:
            selected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


@pytest.fixture(scope="session")
def dg_test_admin():
    """The shared test admin (`test-admin@dg.local`, random password) and its
    real session token, created through the real auth store."""
    import auth_fixtures  # noqa: PLC0415

    auth_fixtures.admin_session_token()
    return auth_fixtures.TEST_ADMIN_USERNAME


@pytest.fixture(autouse=True)
def _dg_authorize_module_client(request):
    """D-20: give the test module's module-level TestClient `client` a real
    principal for the duration of each test, then remove exactly what was
    added. Principal: `dg_principal` marker > module `DG_TEST_PRINCIPAL` >
    'admin'. No dependency override, no bypass -- real credentials only."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    module_client = getattr(request.module, "client", None)
    if not isinstance(module_client, TestClient):
        yield
        return

    import auth_fixtures  # noqa: PLC0415

    marker = request.node.get_closest_marker("dg_principal")
    marker_value = marker.args[0] if marker is not None and marker.args else None
    principal = auth_fixtures.resolve_principal_name(marker_value, request.module)
    undo = auth_fixtures.authorize_client(module_client, principal)
    try:
        yield
    finally:
        undo()

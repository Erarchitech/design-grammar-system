"""Regression tests for the 1205 code-review fix round (REVIEW.md CR-*/WR-*).

Pure pytest, no Neo4j / LLM. Authentication uses the real ``auth`` /
``auth_fixtures`` machinery (D-20); nothing here overrides the auth dependency.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import auth  # noqa: E402


# --------------------------------------------------------------------------
# CR-01: /validation/view must not leak a server-wide / write Speckle token
# --------------------------------------------------------------------------

_RUN = {
    "runId": "run-1",
    "speckleProjectId": "sp",
    "baseModelId": "bm",
    "baseVersionId": "bv",
    "validationModelId": "vm",
    "validationVersionId": "vv",
    "baseResourceUrl": "u1",
    "validationResourceUrl": "u2",
    "modelViewerUrl": "u3",
}


@pytest.fixture
def speckle_env(monkeypatch):
    monkeypatch.setattr(app_module, "load_persisted_speckle_settings", lambda: {})
    monkeypatch.setenv("SPECKLE_WRITE_TOKEN", "write-secret-token")
    monkeypatch.delenv("SPECKLE_READ_TOKEN", raising=False)


class TestCr01SpeckleReadToken:
    def test_read_token_never_falls_back_to_write_token(self, speckle_env):
        settings = app_module.get_speckle_settings()
        assert settings.write_token == "write-secret-token"
        assert settings.read_token == ""

    def test_view_payload_omits_token_for_user_when_only_write_token_set(self, speckle_env):
        user = auth.Principal(kind="user", username="v@dg.local")
        payload = app_module.build_view_payload("p", _RUN, {}, principal=user)
        assert payload["readToken"] is None
        assert "write-secret-token" not in repr(payload)

    def test_view_payload_gives_read_token_to_user_only(self, speckle_env, monkeypatch):
        monkeypatch.setenv("SPECKLE_READ_TOKEN", "read-only-token")
        user = auth.Principal(kind="user", username="v@dg.local")
        connector = auth.Principal(kind="connector", bound_project="p", credential_id="c1")
        assert app_module.build_view_payload("p", _RUN, {}, principal=user)["readToken"] == "read-only-token"
        assert app_module.build_view_payload("p", _RUN, {}, principal=connector)["readToken"] is None

    def test_view_payload_fails_closed_without_principal(self, speckle_env, monkeypatch):
        monkeypatch.setenv("SPECKLE_READ_TOKEN", "read-only-token")
        assert app_module.build_view_payload("p", _RUN, {})["readToken"] is None


# --------------------------------------------------------------------------
# CR-02: knowledge update propose/confirm are project-scoped and bounded
# --------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app_module.app, raise_server_exceptions=False)


class TestCr02KnowledgeUpdateScoping:
    def test_propose_scopes_note_lookup_to_project_and_404s_on_mismatch(self, monkeypatch):
        seen = []

        def fake_read_single(query, params=None):
            seen.append((query, params))
            return None  # no such note in THIS project

        monkeypatch.setattr(app_module, "read_single", fake_read_single)
        monkeypatch.setattr(app_module, "call_n8n_sync", lambda **kw: pytest.fail("LLM must not be called"))
        resp = client.post(
            "/knowledge/update/propose",
            json={"prompt": "rewrite", "project": "proj-a", "noteIds": ["note-of-b"]},
        )
        assert resp.status_code == 404
        query, params = seen[0]
        assert "project: $project" in query
        assert params["project"] == "proj-a"

    def test_confirm_scopes_existence_check_and_set_to_project(self, monkeypatch):
        reads, writes = [], []
        monkeypatch.setattr(
            app_module, "read_single",
            lambda q, p=None: (reads.append((q, p)) or {"updatedAt": "t0", "title": "T"}),
        )
        monkeypatch.setattr(app_module, "write_query", lambda q, p=None: writes.append((q, p)))
        resp = client.post(
            "/knowledge/update/confirm",
            json={
                "prompt": "p", "project": "proj-a",
                "notes": [{"noteId": "n1", "content": "x", "updatedAt": "t0"}],
            },
        )
        assert resp.status_code == 200
        assert "project: $project" in reads[0][0] and reads[0][1]["project"] == "proj-a"
        set_query, set_params = writes[0]
        assert "SET n.content" in set_query
        assert "project: $project" in set_query and set_params["project"] == "proj-a"

    def test_confirm_404_when_note_belongs_to_another_project(self, monkeypatch):
        monkeypatch.setattr(app_module, "read_single", lambda q, p=None: None)
        monkeypatch.setattr(app_module, "write_query", lambda q, p=None: pytest.fail("must not write"))
        resp = client.post(
            "/knowledge/update/confirm",
            json={
                "prompt": "p", "project": "proj-a",
                "notes": [{"noteId": "n1", "content": "x", "updatedAt": "t0"}],
            },
        )
        assert resp.status_code == 404

    def test_propose_and_confirm_cap_fan_out(self, monkeypatch):
        monkeypatch.setattr(app_module, "read_single", lambda q, p=None: pytest.fail("bounded before any read"))
        too_many = [f"n{i}" for i in range(app_module.KNOWLEDGE_UPDATE_MAX_NOTES + 1)]
        r1 = client.post(
            "/knowledge/update/propose", json={"prompt": "p", "project": "a", "noteIds": too_many}
        )
        r2 = client.post(
            "/knowledge/update/confirm",
            json={
                "prompt": "p", "project": "a",
                "notes": [{"noteId": n, "content": "x", "updatedAt": "t"} for n in too_many],
            },
        )
        assert r1.status_code == 400 and r2.status_code == 400


# --------------------------------------------------------------------------
# CR-03 / WR-13: the project-scope proof is not forgeable, and does not reject
# ordinary function calls
# --------------------------------------------------------------------------

import dg_context  # noqa: E402


def _codes(cypher: str) -> set[str]:
    return {v["code"] for v in dg_context.check_query_project_scope(cypher)}


class TestCr03ScopeProofNotForgeable:
    @pytest.mark.parametrize(
        "cypher",
        [
            # backticked variable was skipped entirely
            "MATCH (`n`) RETURN `n`.text, $project AS p LIMIT 50",
            # block comment carrying a fake scoped pattern
            "/* (n {project: $project}) */ MATCH (n) RETURN n.text LIMIT 5",
            # line comment carrying a fake scoped pattern
            "// (n {project: $project})\nMATCH (n) RETURN n.text LIMIT 5",
            # nested braces defeated the map regex (fail-open)
            "MATCH (n {a: {b: 1}.b}) RETURN n.text, $project LIMIT 5",
            # backslash-escaped quote can desynchronise string stripping
            "MATCH (n) WHERE n.t = 'a\\' OR true //' RETURN n.text, $project",
        ],
    )
    def test_forgery_is_rejected(self, cypher):
        assert _codes(cypher), cypher

    def test_subproject_key_is_not_project_scope(self):
        codes = _codes("MATCH (n {subproject: $project}) RETURN n.text LIMIT 5")
        assert "missing_project_scope" in codes

    def test_keyword_glued_paren_is_still_a_node_pattern(self):
        # MATCH(n) is a pattern, not a function call named MATCH
        assert "missing_project_scope" in _codes("MATCH(n) RETURN n.text, $project")

    @pytest.mark.parametrize(
        "cypher",
        [
            "MATCH (n:Rule|Atom {project: $project}) RETURN n.text",
            "MATCH (n WHERE true) RETURN n.text, $project",
            "MATCH (n:Rule WHERE true) RETURN n.text, $project",
        ],
    )
    def test_unreadable_node_pattern_is_rejected_not_skipped(self, cypher):
        assert "unsupported_syntax" in _codes(cypher)

    def test_ordinary_scoped_query_still_passes(self):
        assert dg_context.check_query_project_scope(
            "MATCH (r:Rule {project: $project})-[:HAS_BODY]->(a:Atom {project: $project}) "
            "WHERE r.Rule_Id = 'R_X' RETURN a.SWRL_label LIMIT 20"
        ) == []

    def test_url_in_string_literal_is_not_a_comment(self):
        assert dg_context.check_query_project_scope(
            "MATCH (r:Rule {project: $project}) WHERE r.src = 'http://x/y' RETURN r.Rule_Id"
        ) == []


class TestWr13FunctionCallsNotFalsePositives:
    @pytest.mark.parametrize(
        "cypher",
        [
            "MATCH (a {project: $project})-[r]->(b {project: $project}) RETURN count(r)",
            "MATCH (a:Rule {project: $project}) WITH a.Rule_Id AS id RETURN toLower(id)",
            "MATCH (a:Rule {project: $project}) RETURN a.Rule_Id, timestamp() AS t",
        ],
    )
    def test_function_call_on_relationship_or_alias_is_not_a_violation(self, cypher):
        assert dg_context.check_query_project_scope(cypher) == []


# --------------------------------------------------------------------------
# CR-04: rule-ingest ownership guards are not bypassable by regex evasion
# --------------------------------------------------------------------------


class _ExplodingSession:
    def run(self, *args, **kwargs):
        raise AssertionError("must not query Neo4j")


class _FakeCollisionSession:
    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return self._rows


class _Cr04Session:
    """Reports every queried id as owned by another project."""

    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append(params)
        return [{"ruleHits": list(params["ruleIds"]), "atomHits": list(params["atomIds"])}]


class TestCr04KeyCollisionEvasion:
    @pytest.mark.parametrize(
        "cypher",
        [
            'MERGE (r:Rule {Rule_Id: "R_X"}) SET r.SWRL="a"',  # double quotes
            "MERGE (:Rule {Rule_Id: 'R_X'})",  # no variable
            "MATCH (r:Rule {Rule_Id: 'R_X'}) SET r.SWRL = 'a'",  # MATCH-then-SET
            "CREATE (r:Rule {Rule_Id: 'R_X'})",  # CREATE
        ],
    )
    def test_key_is_collected_and_owner_checked(self, cypher):
        session = _Cr04Session()
        result = dg_context.find_cross_project_key_collisions(cypher, "P1", session=session)
        assert [v["code"] for v in result] == ["cross_project_key_collision"]
        assert session.calls[0]["ruleIds"] == ["R_X"]

    def test_unkeyed_rule_pattern_fails_closed_without_db(self):
        result = dg_context.find_cross_project_key_collisions(
            "MATCH (r:Rule) SET r.SWRL = 'a'", "P1", session=_ExplodingSession()
        )
        assert result and result[0]["code"] == "unkeyed_rule_or_atom_pattern"

    def test_nonliteral_key_fails_closed_without_db(self):
        result = dg_context.find_cross_project_key_collisions(
            "MATCH (r:Rule) WHERE r.Rule_Id IN ['R_X'] SET r.SWRL = 'a'",
            "P1",
            session=_ExplodingSession(),
        )
        assert {v["code"] for v in result} & {"unanalysable_key", "unkeyed_rule_or_atom_pattern"}

    def test_atom_reached_through_relationship_is_allowed(self):
        session = _FakeCollisionSession([])
        cypher = (
            "MERGE (r:Rule {Rule_Id: 'R_X'}) "
            "MERGE (r)-[:HAS_BODY]->(a:Atom {Atom_Id: 'R_X_A1'})"
        )
        assert dg_context.find_cross_project_key_collisions(cypher, "P1", session=session) == []
        assert session.calls[0][1]["atomIds"] == ["R_X_A1"]

    def test_key_text_inside_a_string_literal_is_ignored(self):
        cypher = "MERGE (r:Rule {Rule_Id: 'R_X', SWRL: 'Rule_Id: \"Q\" and Atom_Id = 1'})"
        session = _FakeCollisionSession([])
        dg_context.find_cross_project_key_collisions(cypher, "P1", session=session)
        assert session.calls[0][1]["ruleIds"] == ["R_X"]
        assert session.calls[0][1]["atomIds"] == []


class TestCr04ForeignProjectWriteEvasion:
    @pytest.mark.parametrize(
        "cypher",
        [
            "MERGE (r:Rule {Rule_Id: 'R_X'}) SET r.`project` = 'victim'",
            "MERGE (r:Rule {Rule_Id: 'R_X'}) SET r['project'] = 'victim'",
            "MERGE (r:Rule {Rule_Id: 'R_X'}) SET r.project = other.project",
            "MERGE (r:Rule {Rule_Id: 'R_X', project: \"victim\"})",
        ],
    )
    def test_obfuscated_or_foreign_project_write_is_rejected(self, cypher):
        assert dg_context.check_foreign_project_literals(cypher, "mine")

    def test_own_literal_is_accepted(self):
        assert dg_context.check_foreign_project_literals(
            "MERGE (r:Rule {Rule_Id: 'R_X', project: 'mine'}) SET r.project = 'mine'", "mine"
        ) == []


class TestCr04ProjectRequired:
    @pytest.mark.dg_principal("service")
    @pytest.mark.parametrize("request_type", ["rule_ingest", "rule_edit"])
    def test_blank_project_is_rejected_before_generation(self, monkeypatch, request_type):
        monkeypatch.setattr(
            dg_context, "generate_validated_cypher", lambda *a, **k: pytest.fail("must not generate")
        )
        for project in (None, "", "  "):
            body = {"prompt": "p", "type": request_type}
            if project is not None:
                body["project"] = project
            response = client.post("/context/generate-cypher", json=body)
            assert response.status_code == 400


# --------------------------------------------------------------------------
# WR-01: login / password-check throttling
# --------------------------------------------------------------------------

import auth_fixtures  # noqa: E402


@pytest.fixture
def clean_throttle():
    auth.throttle_reset_all()
    yield
    auth.throttle_reset_all()


class TestWr01ThrottleCore:
    def test_free_attempts_then_exponential_backoff_capped(self, clean_throttle):
        now = 1000.0
        for _ in range(3):
            auth.throttle_record_failure("k", limit=3, now=now)
        assert auth.throttle_retry_after("k", now=now) == 0
        auth.throttle_record_failure("k", limit=3, now=now)  # 1st excess
        first = auth.throttle_retry_after("k", now=now)
        auth.throttle_record_failure("k", limit=3, now=now + first + 1)  # 2nd excess
        second = auth.throttle_retry_after("k", now=now + first + 1)
        assert 0 < first < second <= auth.THROTTLE_MAX_DELAY_SECONDS + 1
        for i in range(30):
            auth.throttle_record_failure("k", limit=3, now=now + 1000 + i)
        assert auth.throttle_retry_after("k", now=now + 1030) <= auth.THROTTLE_MAX_DELAY_SECONDS + 1

    def test_lock_expires_and_success_clears(self, clean_throttle):
        for _ in range(6):
            auth.throttle_record_failure("k", limit=1, now=50.0)
        assert auth.throttle_retry_after("k", now=50.0) > 0
        assert auth.throttle_retry_after("k", now=50.0 + auth.THROTTLE_MAX_DELAY_SECONDS + 5) == 0
        auth.throttle_record_failure("k2", limit=0, now=50.0)
        auth.throttle_clear("k2")
        assert auth.throttle_retry_after("k2", now=50.0) == 0

    def test_memory_is_bounded(self, clean_throttle, monkeypatch):
        monkeypatch.setattr(auth, "_THROTTLE_MAX_ENTRIES", 50)
        for i in range(200):
            auth.throttle_record_failure(f"k{i}", limit=5, now=10.0 + i)
        assert len(auth._THROTTLE) <= 51  # pruned before each insert


class TestWr01LoginRoute:
    @pytest.mark.dg_principal("none")
    def test_repeated_failures_lock_the_username_before_scrypt(self, clean_throttle, monkeypatch):
        import auth_routes

        record = auth_fixtures.make_user("throttle-user@dg.local")
        password = record.get("password", "unused")
        bad = {"username": "throttle-user@dg.local", "password": "definitely-wrong-password"}
        headers = {auth.CSRF_HEADER: auth_fixtures.CSRF_VALUE}
        # THROTTLE_LIMIT_USER free failures, then the next failure arms the lock.
        for _ in range(auth.THROTTLE_LIMIT_USER + 1):
            assert client.post("/auth/login", json=bad, headers=headers).status_code == 401
        # Locked now: no derivation may run for a throttled caller.
        monkeypatch.setattr(
            auth_routes.auth, "verify_password", lambda *a, **k: pytest.fail("scrypt must not run")
        )
        resp = client.post("/auth/login", json=bad, headers=headers)
        assert resp.status_code == 429
        assert int(resp.headers["retry-after"]) > 0
        assert resp.json()["detail"]["code"] == "AUTH_THROTTLED"
        # Even the correct password is refused while locked (no oracle).
        good = {"username": "throttle-user@dg.local", "password": password}
        assert client.post("/auth/login", json=good, headers=headers).status_code == 429

    @pytest.mark.dg_principal("none")
    def test_success_resets_the_user_counter(self, clean_throttle):
        record = auth_fixtures.make_user("throttle-ok@dg.local")
        password = record.get("password")
        if password is None:
            pytest.skip("user pre-existed without a known password")
        headers = {auth.CSRF_HEADER: auth_fixtures.CSRF_VALUE}
        bad = {"username": "throttle-ok@dg.local", "password": "definitely-wrong-password"}
        for _ in range(auth.THROTTLE_LIMIT_USER - 1):
            client.post("/auth/login", json=bad, headers=headers)
        good = {"username": "throttle-ok@dg.local", "password": password}
        assert client.post("/auth/login", json=good, headers=headers).status_code == 200
        assert auth.throttle_retry_after("user:throttle-ok@dg.local") == 0


# --------------------------------------------------------------------------
# WR-02: ingest postProcess never re-tags another project's node
# --------------------------------------------------------------------------

import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

# Same resolution as test_n8n_workflow_boundary: /mnt/repo in the container.
_REPO_ROOT = _Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(_Path(__file__).resolve().parents[2])))


class TestWr02PostProcessGuard:
    def _post_process(self):
        wf = _json.loads(
            (_REPO_ROOT / "n8n" / "workflows" / "rules-to-metagraph.json").read_text(encoding="utf-8")
        )
        code = next(n for n in wf["nodes"] if n["name"] == "Prepare Graph Payload")["parameters"]["functionCode"]
        start = code.index("const postProcess = [")
        end = code.index("].join(", start)
        return code[start:end]

    def test_every_retagging_statement_skips_other_projects_nodes(self):
        block = self._post_process()
        statements = [line for line in block.splitlines() if "SET n.graph" in line]
        assert len(statements) == 3
        for line in statements:
            assert "n.project IS NULL OR n.project = $project" in line, line

    def test_claim_untagged_skips_the_shared_hub_graph(self):
        assert "SpecGraph" in app_module.CLAIM_UNTAGGED_SHARED_GRAPHS
        assert "$sharedGraphs" in app_module.CLAIM_UNTAGGED_QUERY


# --------------------------------------------------------------------------
# WR-03: connector credential store is locked, atomic and fail-closed
# --------------------------------------------------------------------------

import threading  # noqa: E402

import connectors  # noqa: E402


@pytest.fixture
def cred_store(tmp_path, monkeypatch):
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    return connectors.CREDENTIALS_FILE


class TestWr03ConnectorStore:
    def test_corrupt_store_is_an_error_not_an_empty_list(self, cred_store):
        cred_store.write_text("{not json", encoding="utf-8")
        with pytest.raises(connectors.CredentialStoreError):
            connectors.load_credentials()
        # a mint must NOT wipe whatever is on disk
        with pytest.raises(connectors.CredentialStoreError):
            connectors.create_credential("grasshopper", project="p")
        assert cred_store.read_text(encoding="utf-8") == "{not json"

    def test_corrupt_store_authenticates_nobody(self, cred_store):
        cred_store.write_text("", encoding="utf-8")
        assert connectors.authenticate_token("dgc_anything") is None
        assert connectors.record_heartbeat("dgc_anything") is None

    def test_missing_store_is_empty(self, cred_store):
        assert connectors.load_credentials() == []

    def test_save_is_atomic_and_leaves_no_temp_files(self, cred_store):
        connectors.create_credential("grasshopper", project="p")
        leftovers = [p for p in cred_store.parent.iterdir() if p.name != cred_store.name]
        assert leftovers == []

    def test_heartbeats_never_resurrect_a_revoked_credential(self, cred_store):
        record, token = connectors.create_credential("grasshopper", project="p")
        stop = threading.Event()
        errors: list[BaseException] = []

        def beat():
            try:
                while not stop.is_set():
                    connectors.record_heartbeat(token)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=beat) for _ in range(4)]
        for t in threads:
            t.start()
        try:
            # the revoke must stick despite the racing heartbeats
            connectors.revoke_credential("grasshopper", record["credential_id"])
            assert connectors.authenticate_token(token) is None
            still_revoked = all(
                r["revoked"] for r in connectors.load_credentials() if r["credential_id"] == record["credential_id"]
            )
        finally:
            stop.set()
            for t in threads:
                t.join()
        assert not errors
        assert still_revoked
        assert connectors.authenticate_token(token) is None


# --------------------------------------------------------------------------
# WR-05: multi-user startup warns when the session cookie is not Secure
# --------------------------------------------------------------------------

import logging  # noqa: E402

import secrets_policy  # noqa: E402

_OK_SECRETS = {
    "NEO4J_PASSWORD": "some-strong-rotated-value-xyz",
    "LLM_MASTER_SECRET": "b" * 32,
    "DG_SERVICE_TOKEN": "a" * 32,
    "DG_BOOTSTRAP_ADMIN_PASSWORD": "x" * 12,
}


class TestWr05CookieSecureWarning:
    def test_multi_user_without_secure_cookie_warns_and_still_starts(self, caplog):
        logger = logging.getLogger("wr05-a")
        with caplog.at_level(logging.WARNING, logger="wr05-a"):
            assert secrets_policy.enforce_startup_secrets(_OK_SECRETS, "multi-user", logger) == []
        assert any("DG_COOKIE_SECURE" in r.getMessage() for r in caplog.records)

    def test_multi_user_with_secure_cookie_is_silent(self, caplog):
        logger = logging.getLogger("wr05-b")
        env = {**_OK_SECRETS, "DG_COOKIE_SECURE": "true"}
        with caplog.at_level(logging.WARNING, logger="wr05-b"):
            secrets_policy.enforce_startup_secrets(env, "multi-user", logger)
        assert not caplog.records

    def test_local_profile_never_warns_about_the_cookie(self, caplog):
        logger = logging.getLogger("wr05-c")
        with caplog.at_level(logging.WARNING, logger="wr05-c"):
            secrets_policy.enforce_startup_secrets(_OK_SECRETS, "local", logger)
        assert not caplog.records


# --------------------------------------------------------------------------
# WR-06: non-ASCII service-token header is a 401, not a 500
# --------------------------------------------------------------------------


class TestWr06ServiceTokenNonAscii:
    def test_resolver_returns_none_for_non_ascii_header(self):
        env = {"DG_SERVICE_TOKEN": "a" * 40}
        assert auth.resolve_service_principal("café-" + "a" * 40, env=env) is None
        assert auth.resolve_service_principal("\x80\x81", env=env) is None

    def test_correct_token_still_resolves(self):
        env = {"DG_SERVICE_TOKEN": "a" * 40}
        assert auth.resolve_service_principal("a" * 40, env=env).kind == "service"

    @pytest.mark.dg_principal("none")
    def test_http_request_with_high_byte_header_is_401_not_500(self):
        from fastapi.testclient import TestClient as _TC

        raw = _TC(app_module.app, raise_server_exceptions=False)
        resp = raw.get("/auth/me", headers={auth.SERVICE_TOKEN_HEADER: b"\x80\xfftoken"})
        assert resp.status_code == 401


# --------------------------------------------------------------------------
# WR-07: pulling the live canvas needs at least editor
# --------------------------------------------------------------------------

import route_policy  # noqa: E402


class TestWr07CanvasPullRole:
    def test_pull_requires_editor_not_viewer(self):
        policy = route_policy.ROUTE_POLICIES[("POST", "/computgraph/context/pull")]
        assert policy.principals == {route_policy.PRINCIPAL_MEMBER}
        assert policy.min_role == "editor"


# --------------------------------------------------------------------------
# WR-08: a Speckle project already bound to another DG project is refused
# --------------------------------------------------------------------------


class TestWr08SpeckleProjectBinding:
    BODY = {"speckleProjectId": "sp-shared", "baseModelId": "bm1"}

    def _stub(self, monkeypatch, owner_row):
        calls = {"read": [], "write": []}
        monkeypatch.setattr(
            app_module, "read_single",
            lambda q, p=None: (calls["read"].append((q, p)) or owner_row),
        )
        monkeypatch.setattr(app_module, "write_query", lambda q, p=None: calls["write"].append(p))
        monkeypatch.setattr(app_module, "get_integration_config", lambda project: None)
        return calls

    def test_binding_to_another_projects_speckle_project_is_409(self, monkeypatch):
        monkeypatch.delenv("SPECKLE_PROJECT_ID", raising=False)
        calls = self._stub(monkeypatch, {"project": "other-dg-project"})
        resp = client.put("/integration/speckle/project/mine", json=self.BODY)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "SPECKLE_PROJECT_BOUND"
        assert "other-dg-project" not in resp.text
        assert calls["write"] == []
        assert calls["read"][0][1]["project"] == "mine"

    def test_unbound_speckle_project_is_accepted(self, monkeypatch):
        monkeypatch.delenv("SPECKLE_PROJECT_ID", raising=False)
        calls = self._stub(monkeypatch, None)
        resp = client.put("/integration/speckle/project/mine", json=self.BODY)
        assert resp.status_code == 200
        assert len(calls["write"]) == 1

    def test_deployment_default_speckle_project_stays_shareable(self, monkeypatch):
        monkeypatch.setenv("SPECKLE_PROJECT_ID", "sp-shared")
        calls = self._stub(monkeypatch, {"project": "other-dg-project"})
        resp = client.put("/integration/speckle/project/mine", json=self.BODY)
        assert resp.status_code == 200
        assert calls["read"] == []


# --------------------------------------------------------------------------
# WR-09: browser tenant data does not survive logout / account change
# --------------------------------------------------------------------------

import shutil as _shutil  # noqa: E402
import subprocess as _subprocess  # noqa: E402

_UI_SRC = _REPO_ROOT / "ui-v2" / "src"


class TestWr09BrowserDataCleanup:
    @pytest.mark.skipif(_shutil.which("node") is None, reason="node not available")
    def test_clear_tenant_browser_data_keeps_only_theme(self, tmp_path):
        script = tmp_path / "check.mjs"
        script.write_text(
            "const store = new Map([['dgv2_project','a'],['dgv2_theme','dark'],"
            "['dgv2_graph_snapshots_a','{}'],['dgv2_run_shots','{}'],['other','x'],['dgv2_owner','u']]);\n"
            "globalThis.localStorage = { get length(){return store.size;}, key(i){return [...store.keys()][i]??null;},"
            " getItem:k=>store.get(k)??null, setItem:(k,v)=>store.set(k,String(v)), removeItem:k=>store.delete(k) };\n"
            f"const m = await import({(_UI_SRC / 'lib' / 'auth.js').as_uri()!r});\n"
            "m.clearTenantBrowserData();\n"
            "console.log(JSON.stringify([...store.keys()].sort()));\n",
            encoding="utf-8",
        )
        out = _subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        assert _json.loads(out.stdout.strip().splitlines()[-1]) == ["dgv2_theme", "other"]

    def test_app_wipes_on_signout_and_keys_screens_on_identity(self):
        app_src = (_UI_SRC / "App.jsx").read_text(encoding="utf-8")
        assert "clearTenantBrowserData()" in app_src
        assert "const screenKey" in app_src
        for screen in ("GraphScreen", "ModelScreen", "ProjectsScreen"):
            assert f"<{screen} key={{screenKey}}" in app_src


# --------------------------------------------------------------------------
# WR-10: provenance actor is the authenticated principal, not the request body
# --------------------------------------------------------------------------


class TestWr10ProvenanceActor:
    def _stub(self, monkeypatch):
        writes = []
        monkeypatch.setattr(
            app_module, "read_single",
            lambda q, p=None: {"ruleId": (p or {}).get("ruleId", "R"), "alreadySuperseded": False},
        )
        monkeypatch.setattr(app_module, "_require_publishable_rule", lambda rule_id, project: None)
        monkeypatch.setattr(app_module, "write_query", lambda q, p=None: writes.append(p))
        return writes

    def test_supersede_ignores_body_actor(self, monkeypatch):
        writes = self._stub(monkeypatch)
        resp = client.post(
            "/rules/supersede",
            json={"project": "p", "oldRuleId": "R_OLD", "newRuleId": "R_NEW", "actor": "someone-else@dg.local"},
        )
        assert resp.status_code == 200, resp.text
        assert writes[0]["actor"] == auth_fixtures.TEST_ADMIN_USERNAME

    def test_accept_overlap_ignores_body_actor(self, monkeypatch):
        writes = self._stub(monkeypatch)
        resp = client.post(
            "/rules/accept-overlap",
            json={"project": "p", "ruleId": "R_NEW", "conflictsWith": ["R_OLD"], "actor": "someone-else@dg.local"},
        )
        assert resp.status_code == 200, resp.text
        assert writes[0]["actor"] == auth_fixtures.TEST_ADMIN_USERNAME

    def test_actor_helper_covers_every_principal_kind(self):
        class _Req:
            def __init__(self, principal):
                self.state = type("S", (), {"principal": principal})()

        assert app_module._authenticated_actor(_Req(auth.Principal(kind="user", username="u@dg.local"))) == "u@dg.local"
        assert app_module._authenticated_actor(_Req(auth.Principal(kind="service"))) == "service"
        assert app_module._authenticated_actor(
            _Req(auth.Principal(kind="connector", credential_id="c1"))
        ) == "connector:c1"
        assert app_module._authenticated_actor(_Req(None)) == "unknown"


# --------------------------------------------------------------------------
# WR-11: ingest path containment is by path component, not string prefix
# --------------------------------------------------------------------------

from fastapi import HTTPException as _HTTPException  # noqa: E402


class TestWr11IngestPathContainment:
    def test_sibling_directory_sharing_the_prefix_is_rejected(self, tmp_path, monkeypatch):
        root = tmp_path / "repo"
        sibling = tmp_path / "repo2"
        root.mkdir()
        sibling.mkdir()
        monkeypatch.setattr(app_module, "KNOWLEDGE_REPO_ROOT", root)
        with pytest.raises(_HTTPException) as excinfo:
            app_module.validate_ingest_path("../repo2")
        assert excinfo.value.status_code == 403

    def test_directory_inside_the_root_is_accepted(self, tmp_path, monkeypatch):
        root = tmp_path / "repo"
        (root / "notes").mkdir(parents=True)
        monkeypatch.setattr(app_module, "KNOWLEDGE_REPO_ROOT", root)
        assert app_module.validate_ingest_path("notes") == (root / "notes").resolve()

    def test_parent_escape_is_rejected(self, tmp_path, monkeypatch):
        root = tmp_path / "repo"
        root.mkdir()
        monkeypatch.setattr(app_module, "KNOWLEDGE_REPO_ROOT", root)
        with pytest.raises(_HTTPException) as excinfo:
            app_module.validate_ingest_path("..")
        assert excinfo.value.status_code == 403


# --------------------------------------------------------------------------
# WR-12: catch-all failures never echo exception text to the client
# --------------------------------------------------------------------------

_SECRET_TEXT = "bolt://neo4j-internal:7687 user=neo4j token=SUPER-SECRET-TOKEN-FRAGMENT"


class TestWr12NoInternalErrorText:
    def test_helper_hides_the_exception_and_logs_it_under_a_reference(self, caplog):
        with caplog.at_level(logging.ERROR):
            exc = app_module._internal_failure(
                RuntimeError(_SECRET_TEXT), "Check logs.", "SOME_FAILED", 502, "Nothing worked."
            )
        assert exc.status_code == 502
        body = repr(exc.detail)
        assert "SUPER-SECRET" not in body and "neo4j-internal" not in body
        reference = exc.detail["error"].split("reference ")[1].rstrip(")")
        assert exc.detail["code"] == "SOME_FAILED"
        logged = " ".join(r.getMessage() for r in caplog.records)
        assert reference in logged and "SUPER-SECRET" in logged

    def test_computgraph_publish_route_does_not_leak_a_driver_exception(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError(_SECRET_TEXT)

        monkeypatch.setattr(app_module.computgraph_publish, "publish_structure", boom)
        monkeypatch.setattr(app_module, "driver", type("D", (), {"session": lambda self: _NullSession()})())
        resp = client.post(
            "/computgraph/publish", json={"project": "p", "cgContext": {"schema": "x"}}
        )
        assert resp.status_code == 502
        assert "SUPER-SECRET" not in resp.text and "neo4j-internal" not in resp.text
        assert resp.json()["detail"]["code"] == "COMPUTGRAPH_PUBLISH_FAILED"


class _NullSession:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# --------------------------------------------------------------------------
# WR-14: an invalid bootstrap username degrades like a weak password
# --------------------------------------------------------------------------


class TestWr14BootstrapUsername:
    ENV = {"DG_BOOTSTRAP_ADMIN_USER": "not a valid name!!", "DG_BOOTSTRAP_ADMIN_PASSWORD": "a-long-enough-password-1"}

    def test_local_profile_warns_and_creates_nothing(self, caplog):
        logger = logging.getLogger("wr14-local")
        before = len(auth._load(auth.USERS_FILE, "users"))
        with caplog.at_level(logging.WARNING, logger="wr14-local"):
            result = auth.ensure_bootstrap_admin(self.ENV, "local", logger)
        # a pre-existing test admin short-circuits with "exists"; when none
        # exists the invalid name is reported, never raised
        assert result in ("exists", "invalid-username")
        assert len(auth._load(auth.USERS_FILE, "users")) == before

    def test_invalid_username_path_directly(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
        logger = logging.getLogger("wr14-direct")
        with caplog.at_level(logging.WARNING, logger="wr14-direct"):
            assert auth.ensure_bootstrap_admin(self.ENV, "local", logger) == "invalid-username"
        assert "not a valid account name" in caplog.text
        assert "not a valid name" not in caplog.text.replace("not a valid account name", "")
        with pytest.raises(RuntimeError):
            auth.ensure_bootstrap_admin(self.ENV, "multi-user", logger)


# --------------------------------------------------------------------------
# WR-15: a second invite for a username that now has an account is not burned
# --------------------------------------------------------------------------


class TestWr15SecondInvite:
    CSRF = {auth.CSRF_HEADER: auth_fixtures.CSRF_VALUE}

    def _invite(self, username, project, role="editor"):
        code, _record = auth.create_invite(username, project, role, created_by="owner@dg.local")
        return code

    def test_existing_account_joins_with_its_own_password_and_code_is_consumed(self, clean_throttle):
        user = auth_fixtures.make_user("second-invite@dg.local")
        password = user.get("password")
        if password is None:
            pytest.skip("user pre-existed without a known password")
        code = self._invite("second-invite@dg.local", "PX")
        fresh = TestClient(app_module.app, raise_server_exceptions=False)
        before = auth.get_user("second-invite@dg.local")["password_hash"]
        resp = fresh.post(
            "/auth/accept-invite", json={"inviteCode": code, "password": password}, headers=self.CSRF
        )
        assert resp.status_code == 200, resp.text
        assert auth.get_role("second-invite@dg.local", "PX") == "editor"
        assert auth.get_user("second-invite@dg.local")["password_hash"] == before
        again = fresh.post(
            "/auth/accept-invite", json={"inviteCode": code, "password": password}, headers=self.CSRF
        )
        assert again.status_code == 400

    def test_wrong_password_refuses_without_burning_the_code(self, clean_throttle):
        user = auth_fixtures.make_user("second-invite-2@dg.local")
        password = user.get("password")
        if password is None:
            pytest.skip("user pre-existed without a known password")
        code = self._invite("second-invite-2@dg.local", "PY")
        fresh = TestClient(app_module.app, raise_server_exceptions=False)
        bad = fresh.post(
            "/auth/accept-invite",
            json={"inviteCode": code, "password": "definitely-not-the-password"},
            headers=self.CSRF,
        )
        assert bad.status_code == 400
        assert bad.json()["detail"]["code"] == "INVITE_INVALID"
        assert "already has an account" in bad.json()["detail"]["hint"]
        assert auth.get_role("second-invite-2@dg.local", "PY") is None
        assert auth.peek_invite(code) is not None  # not consumed
        ok = fresh.post(
            "/auth/accept-invite", json={"inviteCode": code, "password": password}, headers=self.CSRF
        )
        assert ok.status_code == 200
        assert auth.get_role("second-invite-2@dg.local", "PY") == "editor"

    def test_peek_does_not_consume(self):
        code = self._invite("peek-user@dg.local", "PZ")
        assert auth.peek_invite(code) is not None
        assert auth.peek_invite(code) is not None
        assert auth.peek_invite("dgi_unknown") is None


# --------------------------------------------------------------------------
# WR-16: nginx sends baseline security headers on every location
# --------------------------------------------------------------------------


class TestWr16SecurityHeaders:
    REQUIRED = (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Content-Security-Policy",
    )

    def _nginx(self):
        return (_REPO_ROOT / "ui-v2" / "nginx.conf").read_text(encoding="utf-8")

    def test_server_level_headers_present_and_always(self):
        text = self._nginx()
        for name in self.REQUIRED:
            line = next(ln for ln in text.splitlines() if f"add_header {name} " in ln)
            assert line.rstrip().endswith("always;"), line

    def test_spa_location_repeats_the_headers_because_it_sets_its_own(self):
        text = self._nginx()
        block = text[text.index("  location / {"): text.index("  location /llm/")]
        assert "add_header Cache-Control" in block
        for name in self.REQUIRED:
            assert f"add_header {name} " in block, name

    def test_csp_forbids_framing(self):
        text = self._nginx()
        assert "frame-ancestors 'none'" in text


# --------------------------------------------------------------------------
# WR-19: non-admins get provider/model only, no key preview or baseUrl
# --------------------------------------------------------------------------


class TestWr19LlmSettingsVisibility:
    SETTINGS = {
        "provider": "openai",
        "model": "gpt-x",
        "baseUrl": "http://internal-gateway.local:9000/v1",
    }

    def _settings(self, monkeypatch):
        encrypted = app_module.encrypt_value("sk-live-abcdef123456", os.environ["LLM_MASTER_SECRET"])
        monkeypatch.setattr(
            app_module, "load_persisted_llm_settings", lambda: {**self.SETTINGS, "apiKey": encrypted}
        )

    def test_admin_sees_everything(self, monkeypatch):
        self._settings(monkeypatch)
        body = client.get("/llm/settings").json()
        assert body["baseUrl"] == self.SETTINGS["baseUrl"]
        assert body["apiKeyPreview"]
        assert body["apiKeyConfigured"] is True

    def test_plain_member_gets_provider_model_and_status_only(self, monkeypatch):
        self._settings(monkeypatch)
        auth_fixtures.make_user("plain-member@dg.local", memberships={"P1": "viewer"})
        undo = auth_fixtures.authorize_client(client, ("user", "plain-member@dg.local"))
        try:
            resp = client.get("/llm/settings")
        finally:
            undo()
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "openai" and body["model"] == "gpt-x"
        assert body["apiKeyConfigured"] is True
        assert not body["apiKeyPreview"]
        assert body["baseUrl"] is None
        assert "internal-gateway" not in resp.text and "abcdef" not in resp.text

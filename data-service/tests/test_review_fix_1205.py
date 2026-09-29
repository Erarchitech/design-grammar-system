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
            "MATCH (n) WHERE n.t = 'a\' OR true //' RETURN n.text, $project",
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

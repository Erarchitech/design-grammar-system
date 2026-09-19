"""Tests for the rule-deletion endpoints (GET .../delete-preview, DELETE /rules/...).

Follows test_app_computgraph_pull.py: FastAPI TestClient with
raise_server_exceptions=False, monkeypatching the module-level Neo4j helpers
(`read_single` / `read_many` / `write_query`) that app.py calls, so no live
database is needed.

The behaviour under test is the orphan rule: Literal and Var nodes are SHARED
between rules by MERGE on lex/name, so deleting a rule must remove only the
args nothing else points at. Measured on a live project, deleting one height
rule would orphan Literal '75' (0 other referrers) while Literal 'true' had 12
and Var '?b' had 6 -- deleting those would have broken two other rules.
"""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import dg_context  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

RULE = "R_URB_HEIGHT_MAX_75_V"
PROJECT = "URBAN_BLOCK_V8"

# One orphan (nothing else uses '75') and three shared args, mirroring the
# real measured shape.
_ARGS = [
    {"label": "Literal", "value": "75", "otherRefs": 0},
    {"label": "Literal", "value": "true", "otherRefs": 12},
    {"label": "Var", "value": "?b", "otherRefs": 6},
    {"label": "Var", "value": "?h", "otherRefs": 4},
]
_ATOMS = [{"atomId": f"{RULE}_A{i}", "swrlLabel": f"atom{i}"} for i in range(1, 5)]


def _wire(monkeypatch, *, rule_exists=True, captured=None):
    """Point app's Neo4j helpers at in-memory fixtures."""

    def fake_read_single(query, params=None):
        return {"ruleId": RULE} if rule_exists else None

    def fake_read_many(query, params=None):
        # The args query is the one that computes otherRefs.
        return list(_ARGS) if "otherRefs" in query else list(_ATOMS)

    def fake_write_query(query, params=None):
        if captured is not None:
            captured.append((query, params))

    monkeypatch.setattr(app_module, "read_single", fake_read_single)
    monkeypatch.setattr(app_module, "read_many", fake_read_many)
    monkeypatch.setattr(app_module, "write_query", fake_write_query)


class TestRuleDeletePreview:
    def test_preview_separates_orphaned_from_shared(self, monkeypatch):
        """Only the arg nothing else references is listed for deletion."""
        _wire(monkeypatch)

        response = client.get(f"/rules/{PROJECT}/{RULE}/delete-preview")

        assert response.status_code == 200
        body = response.json()
        assert body["ruleId"] == RULE
        assert len(body["atoms"]) == 4
        assert [a["value"] for a in body["orphaned"]] == ["75"]
        assert {a["value"] for a in body["shared"]} == {"true", "?b", "?h"}

    def test_preview_is_read_only(self, monkeypatch):
        """A preview must never write -- it is what the user sees BEFORE deciding."""
        writes: list = []
        _wire(monkeypatch, captured=writes)

        client.get(f"/rules/{PROJECT}/{RULE}/delete-preview")

        assert writes == []

    def test_preview_404s_for_unknown_rule(self, monkeypatch):
        _wire(monkeypatch, rule_exists=False)

        response = client.get(f"/rules/{PROJECT}/R_DOES_NOT_EXIST/delete-preview")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "RULE_NOT_FOUND"


class TestRuleDelete:
    def test_delete_reports_what_it_removed_and_kept(self, monkeypatch):
        _wire(monkeypatch)

        response = client.delete(f"/rules/{PROJECT}/{RULE}")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "deleted"
        assert body["ruleId"] == RULE
        assert body["deletedAtoms"] == 4
        assert body["deletedArgs"] == 1  # only the orphan
        assert body["keptSharedArgs"] == 3

    def test_delete_404s_for_unknown_rule_without_writing(self, monkeypatch):
        """A missing rule must not reach the write step."""
        writes: list = []
        _wire(monkeypatch, rule_exists=False, captured=writes)

        response = client.delete(f"/rules/{PROJECT}/R_DOES_NOT_EXIST")

        assert response.status_code == 404
        assert writes == []

    def test_delete_is_scoped_to_project_and_rule(self, monkeypatch):
        """The destructive statement is parameterized, never string-built, and
        carries both the Rule_Id and the project so it cannot cross projects."""
        writes: list = []
        _wire(monkeypatch, captured=writes)

        client.delete(f"/rules/{PROJECT}/{RULE}")

        assert len(writes) == 1
        query, params = writes[0]
        assert params == {"ruleId": RULE, "project": PROJECT}
        assert "$ruleId" in query and "$project" in query
        assert RULE not in query  # value is bound, not interpolated

    def test_delete_recomputes_orphans_inside_the_write(self, monkeypatch):
        """The orphan check must live in the delete statement itself: computing
        it from the preview would race a concurrent ingest that starts
        referencing one of these args between the two calls."""
        writes: list = []
        _wire(monkeypatch, captured=writes)

        client.delete(f"/rules/{PROJECT}/{RULE}")

        query, _ = writes[0]
        assert "NOT EXISTS" in query
        assert "other <> r" in query

    def test_delete_never_touches_ontology_labels(self, monkeypatch):
        """Class/DatatypeProperty/Builtin are shared ontology entities and must
        survive: the statement only ever matches Rule/Atom and ARG targets."""
        writes: list = []
        _wire(monkeypatch, captured=writes)

        client.delete(f"/rules/{PROJECT}/{RULE}")

        query, _ = writes[0]
        for ontology_label in (":Class", ":DatatypeProperty", ":ObjectProperty", ":Builtin"):
            assert ontology_label not in query


class TestSelectionParsing:
    """dg_context._parse_selection_response(): the guard between a free-text
    model answer and a destructive action. A Rule_Id the model invents must be
    reported, never selected."""

    KNOWN = {"R_URB_HEIGHT_MAX_45_V", "R_URB_HEIGHT_MAX_60_V"}

    def test_plain_json_is_parsed(self):
        out = dg_context._parse_selection_response(
            '{"ruleIds": ["R_URB_HEIGHT_MAX_60_V"], "reason": "above 50"}', self.KNOWN
        )
        assert out["ruleIds"] == ["R_URB_HEIGHT_MAX_60_V"]
        assert out["reason"] == "above 50"

    def test_code_fenced_json_is_parsed(self):
        out = dg_context._parse_selection_response(
            '```json\n{"ruleIds": ["R_URB_HEIGHT_MAX_45_V"], "reason": "r"}\n```', self.KNOWN
        )
        assert out["ruleIds"] == ["R_URB_HEIGHT_MAX_45_V"]

    def test_json_embedded_in_prose_is_recovered(self):
        out = dg_context._parse_selection_response(
            'Sure! {"ruleIds": ["R_URB_HEIGHT_MAX_45_V"], "reason": "r"} hope that helps', self.KNOWN
        )
        assert out["ruleIds"] == ["R_URB_HEIGHT_MAX_45_V"]

    def test_hallucinated_id_is_quarantined_not_selected(self):
        out = dg_context._parse_selection_response(
            '{"ruleIds": ["R_URB_HEIGHT_MAX_45_V", "R_GHOST_RULE_V"], "reason": "r"}', self.KNOWN
        )
        assert out["ruleIds"] == ["R_URB_HEIGHT_MAX_45_V"]
        assert out["hallucinated"] == ["R_GHOST_RULE_V"]

    def test_empty_selection_is_valid(self):
        out = dg_context._parse_selection_response('{"ruleIds": [], "reason": "no match"}', self.KNOWN)
        assert out["ruleIds"] == []
        assert out["parsed"] is True

    def test_non_json_selects_nothing(self):
        """A refusal or prose answer must delete nothing, not raise."""
        out = dg_context._parse_selection_response("I cannot help with that.", self.KNOWN)
        assert out["ruleIds"] == []
        assert out["parsed"] is False

    def test_duplicate_ids_are_collapsed(self):
        out = dg_context._parse_selection_response(
            '{"ruleIds": ["R_URB_HEIGHT_MAX_45_V", "R_URB_HEIGHT_MAX_45_V"], "reason": "r"}',
            self.KNOWN,
        )
        assert out["ruleIds"] == ["R_URB_HEIGHT_MAX_45_V"]


class TestBulkDelete:
    def test_bulk_delete_requires_ids(self, monkeypatch):
        _wire(monkeypatch)
        response = client.post("/rules/bulk-delete", json={"project": PROJECT, "ruleIds": []})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "REQUEST_EMPTY"

    def test_bulk_delete_reports_missing_without_failing(self, monkeypatch):
        """A rule deleted between resolve and confirm is reported, not a 500."""
        _wire(monkeypatch, rule_exists=False)
        response = client.post(
            "/rules/bulk-delete", json={"project": PROJECT, "ruleIds": ["R_GONE_V"]}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["missing"] == ["R_GONE_V"]
        assert body["deletedRules"] == 0

    def test_resolve_rejects_empty_request(self, monkeypatch):
        _wire(monkeypatch)
        response = client.post("/rules/resolve-deletion", json={"project": PROJECT, "request": "   "})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "REQUEST_EMPTY"

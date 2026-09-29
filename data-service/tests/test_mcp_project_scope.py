"""Project-scope enforcement at the two places LLM-generated Cypher enters the
graph (Phase 1205 plan 14, ALGN12-17; D-04, research gap 4).

``POST /mcp`` (``neo4j_query`` / ``neo4j_schema``) and ``POST
/context/generate-cypher`` are n8n-only routes (service principal). These tests
fake ``app.driver`` with a session that yields duck-typed record/node objects
and, where a behaviour isolates route logic, monkeypatch the ``dg_context``
guard functions. No test touches Neo4j or an LLM.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import dg_context  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# D-04: /mcp and /context/generate-cypher are service-only.
DG_TEST_PRINCIPAL = "service"

SCOPED_QUERY = "MATCH (r:Rule {project: $project}) RETURN r LIMIT 50"
UNSCOPED_QUERY = "MATCH (r:Rule) RETURN r"


class FakeNode:
    def __init__(self, labels, props):
        self.labels = set(labels)
        self._props = dict(props)

    def get(self, key):
        return self._props.get(key)

    def __getitem__(self, key):
        return self._props[key]


class FakeRecord:
    def __init__(self, **fields):
        self._fields = fields

    def values(self):
        return list(self._fields.values())

    def data(self):
        return {
            key: (value._props if isinstance(value, FakeNode) else value)
            for key, value in self._fields.items()
        }


class FakeResult:
    def __init__(self, records, keys):
        self._records = records
        self._keys = keys

    def keys(self):
        return self._keys

    def __iter__(self):
        return iter(self._records)


class FakeSession:
    def __init__(self, records, keys, calls):
        self._records = records
        self._keys = keys
        self._calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, parameters=None):
        self._calls.append((query, parameters))
        return FakeResult(self._records, self._keys)


class FakeDriver:
    def __init__(self, records=(), keys=("r",)):
        self.calls: list = []
        self._records = list(records)
        self._keys = list(keys)

    def session(self):
        return FakeSession(self._records, self._keys, self.calls)


def _install_driver(monkeypatch, records=(), keys=("r",)):
    fake = FakeDriver(records, keys)
    monkeypatch.setattr(app_module, "driver", fake)
    return fake


def _mcp_query(cypher, parameters=None):
    arguments = {"cypher": cypher}
    if parameters is not None:
        arguments["parameters"] = parameters
    return client.post(
        "/mcp",
        json={
            "method": "tools/call",
            "id": 1,
            "params": {"name": "neo4j_query", "arguments": arguments},
        },
    )


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


class TestMcpNeo4jQuery:
    def test_project_parameter_is_required(self, monkeypatch):
        fake = _install_driver(monkeypatch)

        for parameters in (None, {}, {"project": ""}, {"project": "  "}, {"project": 7}):
            response = _mcp_query(SCOPED_QUERY, parameters)
            assert response.status_code == 400
            assert "project is required" in response.text
        assert fake.calls == []

    def test_unscoped_query_is_rejected_before_the_driver_is_called(self, monkeypatch):
        fake = _install_driver(monkeypatch)

        response = _mcp_query(UNSCOPED_QUERY, {"project": "P1"})

        assert response.status_code == 400
        assert _code(response) == "QUERY_NOT_PROJECT_SCOPED"
        # Violation codes are listed, and no other project is ever named.
        assert "missing_project_scope" in response.text or "project" in response.text
        assert "P2" not in response.text
        assert fake.calls == []

    def test_query_writing_project_literal_is_rejected(self, monkeypatch):
        fake = _install_driver(monkeypatch)

        response = _mcp_query("MATCH (r:Rule {project: 'P2'}) RETURN r", {"project": "P1"})

        assert response.status_code == 400
        assert _code(response) == "QUERY_NOT_PROJECT_SCOPED"
        assert fake.calls == []

    def test_write_query_still_rejected(self, monkeypatch):
        fake = _install_driver(monkeypatch)

        response = _mcp_query(
            "MATCH (r:Rule {project: $project}) DETACH DELETE r", {"project": "P1"}
        )

        assert response.status_code == 400
        assert fake.calls == []

    def test_foreign_project_entity_withholds_the_whole_result(self, monkeypatch):
        records = [
            FakeRecord(r=FakeNode({"Rule"}, {"Rule_Id": "R_OK", "project": "P1"})),
            FakeRecord(r=FakeNode({"Rule"}, {"Rule_Id": "R_SECRET", "project": "P2"})),
        ]
        fake = _install_driver(monkeypatch, records)

        response = _mcp_query(SCOPED_QUERY, {"project": "P1"})

        assert response.status_code == 400
        assert _code(response) == "CROSS_PROJECT_RESULT_WITHHELD"
        assert "R_OK" not in response.text
        assert "R_SECRET" not in response.text
        assert "records" not in response.text
        assert len(fake.calls) == 1

    def test_node_without_project_property_is_withheld(self, monkeypatch):
        records = [FakeRecord(r=FakeNode({"Rule"}, {"Rule_Id": "R_UNTAGGED"}))]
        _install_driver(monkeypatch, records)

        response = _mcp_query(SCOPED_QUERY, {"project": "P1"})

        assert response.status_code == 400
        assert _code(response) == "CROSS_PROJECT_RESULT_WITHHELD"

    def test_in_project_and_shared_vocabulary_nodes_are_returned(self, monkeypatch):
        records = [
            FakeRecord(
                r=FakeNode({"Rule"}, {"Rule_Id": "R_OK", "project": "P1"}),
                c=FakeNode({"Class"}, {"label": "Building"}),
            )
        ]
        fake = _install_driver(monkeypatch, records, keys=("r", "c"))

        response = _mcp_query(SCOPED_QUERY, {"project": "P1"})

        assert response.status_code == 200
        data = response.json()["result"]["data"]
        assert data["keys"] == ["r", "c"]
        assert data["records"] == [
            {"r": {"Rule_Id": "R_OK", "project": "P1"}, "c": {"label": "Building"}}
        ]
        assert fake.calls == [(SCOPED_QUERY, {"project": "P1"})]

    def test_scalar_only_results_pass(self, monkeypatch):
        records = [FakeRecord(id="R_OK"), FakeRecord(id="R_TWO")]
        _install_driver(monkeypatch, records, keys=("id",))

        response = _mcp_query(
            "MATCH (r:Rule {project: $project}) RETURN r.Rule_Id AS id", {"project": "P1"}
        )

        assert response.status_code == 200
        assert response.json()["result"]["data"]["records"] == [{"id": "R_OK"}, {"id": "R_TWO"}]


class TestMcpNeo4jSchema:
    def test_schema_does_not_list_projects(self, monkeypatch):
        class SchemaSession:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def run(self, query, *args, **kwargs):
                assert "n.project" not in query, "schema tool must not enumerate projects"

                class _Value:
                    @staticmethod
                    def value():
                        return ["x"]

                return _Value()

        class SchemaDriver:
            def session(self):
                return SchemaSession()

        monkeypatch.setattr(app_module, "driver", SchemaDriver())

        response = client.post(
            "/mcp",
            json={
                "method": "tools/call",
                "id": 1,
                "params": {"name": "neo4j_schema", "arguments": {}},
            },
        )

        assert response.status_code == 200
        data = response.json()["result"]["data"]
        assert "projects" not in data
        assert set(data) == {"labels", "relationship_types", "property_keys", "graphs"}

    def test_tools_list_no_longer_advertises_projects(self):
        response = client.post("/mcp", json={"method": "tools/list"})

        descriptions = {t["name"]: t["description"] for t in response.json()["result"]["tools"]}
        assert "projects" not in descriptions["neo4j_schema"]


class TestGenerateCypherProject:
    def test_graph_query_requires_a_project(self, monkeypatch):
        def boom(*args, **kwargs):
            raise AssertionError("must not generate without a project")

        monkeypatch.setattr(dg_context, "generate_validated_cypher", boom)

        for body in (
            {"prompt": "list rules", "type": "graph_query"},
            {"prompt": "list rules", "type": "graph_query", "project": ""},
        ):
            response = client.post("/context/generate-cypher", json=body)
            assert response.status_code == 400
            assert _code(response) == "CONTEXT_PROJECT_REQUIRED"

    @pytest.mark.parametrize("request_type", ["graph_query", "rule_ingest", "rule_edit"])
    def test_project_is_passed_to_generate_validated_cypher(self, monkeypatch, request_type):
        captured = {}

        def fake_generate(prompt, type_, *args, **kwargs):
            captured.update(prompt=prompt, type=type_, kwargs=kwargs)
            return {"valid": True, "cypher": "RETURN 1", "attempts": 1}

        monkeypatch.setattr(dg_context, "generate_validated_cypher", fake_generate)
        monkeypatch.setattr(
            dg_context, "find_cross_project_key_collisions", lambda cypher, project: []
        )

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "p", "type": request_type, "project": "P1"},
        )

        assert response.status_code == 200
        assert captured["kwargs"]["project"] == "P1"
        assert response.json() == {"valid": True, "cypher": "RETURN 1", "attempts": 1}

    def test_rule_ingest_key_collision_turns_the_result_invalid(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            dg_context,
            "generate_validated_cypher",
            lambda prompt, type_, **kw: {"valid": True, "cypher": "MERGE (r:Rule {Rule_Id: 'R_X'})", "attempts": 2},
        )

        def fake_collisions(cypher, project):
            seen.update(cypher=cypher, project=project)
            return [{"code": "cross_project_key_collision", "message": "m", "path": "R_X"}]

        monkeypatch.setattr(dg_context, "find_cross_project_key_collisions", fake_collisions)

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "p", "type": "rule_ingest", "project": "P1"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert body["attempts"] == 2
        assert [v["code"] for v in body["violations"]] == ["cross_project_key_collision"]
        assert "cypher" not in body
        assert seen == {"cypher": "MERGE (r:Rule {Rule_Id: 'R_X'})", "project": "P1"}

    def test_invalid_generation_skips_the_collision_check(self, monkeypatch):
        monkeypatch.setattr(
            dg_context,
            "generate_validated_cypher",
            lambda prompt, type_, **kw: {"valid": False, "violations": [{"code": "x"}], "attempts": 3},
        )

        def boom(*args, **kwargs):
            raise AssertionError("collision check must not run for invalid Cypher")

        monkeypatch.setattr(dg_context, "find_cross_project_key_collisions", boom)

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "p", "type": "rule_ingest", "project": "P1"},
        )

        assert response.json() == {"valid": False, "violations": [{"code": "x"}], "attempts": 3}

    def test_graph_query_result_never_runs_the_collision_check(self, monkeypatch):
        monkeypatch.setattr(
            dg_context,
            "generate_validated_cypher",
            lambda prompt, type_, **kw: {"valid": True, "cypher": "RETURN 1", "attempts": 1},
        )

        def boom(*args, **kwargs):
            raise AssertionError("collision check is for rule ingest/edit only")

        monkeypatch.setattr(dg_context, "find_cross_project_key_collisions", boom)

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "p", "type": "graph_query", "project": "P1"},
        )

        assert response.status_code == 200

    def test_collision_check_failure_fails_closed(self, monkeypatch):
        monkeypatch.setattr(
            dg_context,
            "generate_validated_cypher",
            lambda prompt, type_, **kw: {"valid": True, "cypher": "MERGE (r:Rule {Rule_Id: 'R_X'})", "attempts": 1},
        )

        def unreachable(*args, **kwargs):
            raise RuntimeError("bolt down")

        monkeypatch.setattr(dg_context, "find_cross_project_key_collisions", unreachable)

        response = client.post(
            "/context/generate-cypher",
            json={"prompt": "p", "type": "rule_ingest", "project": "P1"},
        )

        assert response.status_code == 503
        assert _code(response) == "KEY_COLLISION_CHECK_UNAVAILABLE"
        assert "bolt down" not in response.text


class TestServicePrincipalOnly:
    @pytest.mark.dg_principal(("user", "someone@dg.local"))
    def test_a_user_session_is_refused(self):
        import auth_fixtures

        auth_fixtures.make_user("someone@dg.local", memberships={"P1": "owner"})

        response = _mcp_query(SCOPED_QUERY, {"project": "P1"})

        assert response.status_code == 403

"""Contract/shape tests for POST /reason/consistency and POST /shacl/validate.

Always-on unit tier (D-13): no docker, no live Neo4j, no JRE. `reasoning.
run_consistency` / `reasoning.run_shacl` are monkeypatched so HermiT is never
actually invoked -- these tests only assert the route wiring and the D-10/
D-11 response contract. The live HermiT round-trip is Plan 821-04's
integration test.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import reasoning
from app import app

client = TestClient(app)

D10_KEYS = {"consistent", "unsatisfiable_classes", "axiom_counts", "duration_ms", "stripped_builtin_rules"}


def test_reason_consistency_returns_d10_contract(monkeypatch):
    def fake_run_consistency(project, engine="hermit", session=None):
        assert project == "x"
        assert engine == "hermit"
        return {
            "consistent": True,
            "unsatisfiable_classes": [
                {"iri": "http://example.org/dg/ex#SlidingDoor", "label": "Sliding Door"}
            ],
            "axiom_counts": {"subClassOf": 65, "domain": 101, "range": 112, "disjointWith": 2, "classDeclarations": 80},
            "duration_ms": 42,
            "stripped_builtin_rules": 1,
        }

    monkeypatch.setattr(reasoning, "run_consistency", fake_run_consistency)

    response = client.post("/reason/consistency", json={"project": "x"})

    assert response.status_code == 200
    body = response.json()
    assert D10_KEYS <= set(body.keys())
    assert body["consistent"] is True
    assert body["stripped_builtin_rules"] == 1


def test_local_name_fallback():
    from reasoning import _local_name

    assert _local_name("http://example.org/dg/ex#SlidingDoor") == "SlidingDoor"
    assert _local_name("http://example.org/dg/path/Thing") == "Thing"
    assert not _local_name("http://example.org/dg/ex#SlidingDoor").startswith("http")
    assert not _local_name("http://example.org/dg/path/Thing").startswith("http")


def test_unsatisfiable_classes_have_iri_and_label(monkeypatch):
    def fake_run_consistency(project, engine="hermit", session=None):
        assert project == "x"
        return {
            "consistent": False,
            "unsatisfiable_classes": [
                {"iri": "http://example.org/dg/ex#SlidingDoor", "label": "Sliding Door"},
                {"iri": "http://example.org/dg/ex#RevolvingDoor", "label": "RevolvingDoor"},
            ],
            "axiom_counts": {"subClassOf": 65, "domain": 101, "range": 112, "disjointWith": 2, "classDeclarations": 80},
            "duration_ms": 42,
            "stripped_builtin_rules": 0,
        }

    monkeypatch.setattr(reasoning, "run_consistency", fake_run_consistency)

    response = client.post("/reason/consistency", json={"project": "x"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["unsatisfiable_classes"]) == 2
    for entry in body["unsatisfiable_classes"]:
        assert isinstance(entry, dict)
        assert "iri" in entry
        assert "label" in entry
        assert isinstance(entry["label"], str)
        assert len(entry["label"]) > 0
        assert not entry["label"].startswith("http")


def test_reason_consistency_unknown_engine_returns_422(monkeypatch):
    def fail_if_called(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("run_consistency should not be invoked for an unknown engine")

    monkeypatch.setattr(reasoning, "run_consistency", fail_if_called)

    response = client.post("/reason/consistency", json={"project": "x", "engine": "pellet"})

    assert response.status_code == 422


def test_reason_consistency_timeout_returns_504(monkeypatch):
    def fake_timeout(project, engine="hermit", session=None):
        return {
            "consistent": None,
            "error": "timeout",
            "duration_ms": 90000,
            "stripped_builtin_rules": 3,
            "timeout_seconds": 90,
        }

    monkeypatch.setattr(reasoning, "run_consistency", fake_timeout)

    response = client.post("/reason/consistency", json={"project": "x"})

    assert response.status_code == 504
    body = response.json()
    assert body["error"] == "timeout"


def test_shacl_validate_returns_empty_shapes_contract(monkeypatch):
    def fake_run_shacl(project, run_id=None, session=None):
        assert project == "x"
        assert run_id is None
        return {"conforms": True, "results": []}

    monkeypatch.setattr(reasoning, "run_shacl", fake_run_shacl)

    response = client.post("/shacl/validate", json={"project": "x"})

    assert response.status_code == 200
    assert response.json() == {"conforms": True, "results": []}


def test_shacl_validate_with_run_id_returns_canonical_envelope(monkeypatch):
    def fake_run_shacl(project, run_id=None, session=None):
        assert project == "x"
        assert run_id == "run-123"
        return {
            "conforms": False,
            "results": [
                {
                    "severity": "violation",
                    "what": "Run is missing sendStatus",
                    "where": "Run run-123",
                    "howToFix": "Ensure the run publishes a sendStatus boolean",
                    "focusLabel": "Run run-123",
                    "shapeId": "RunStatusShape",
                }
            ],
            "counts": {"violation": 1, "warning": 0, "info": 0},
        }

    monkeypatch.setattr(reasoning, "run_shacl", fake_run_shacl)

    response = client.post("/shacl/validate", json={"project": "x", "run_id": "run-123"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["results"], list)
    assert body["conforms"] is False
    assert set(body["counts"].keys()) == {"violation", "warning", "info"}
    finding = body["results"][0]
    assert set(finding.keys()) == {"severity", "what", "where", "howToFix", "focusLabel", "shapeId"}

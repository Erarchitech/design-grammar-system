"""Unit tests for the SHACL result-mapping pipeline (Plan 823-02, SHCL-01/SHCL-02).

Always-on unit tier: no docker, no live Neo4j. Hand-built in-memory rdflib
graphs (a small results_graph fixture, and the real `ontology/dg-shapes.ttl`
shapes) exercise `_walk_shacl_results` and the per-result enrichment path
directly. `pyshacl.validate` is invoked for real (no monkeypatching) to prove
the `allow_infos=True, allow_warnings=True` gotcha (RESEARCH.md Pattern 1) is
actually handled, not just documented.

RED state (before Task 2's implementation lands): `_walk_shacl_results` /
`_enrich_shacl_result` don't exist yet on `reasoning` -- these tests fail
with AttributeError, proving they exercise real code, not vacuous
assertions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from rdflib import BNode, Graph, Literal as RDFLiteral, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SH, XSD

import reasoning

DGV = Namespace("http://example.org/design-grammar/valid#")
DGSH = Namespace("http://example.org/design-grammar/shapes#")
EX = Namespace("http://example.org/ex#")

# Repo checkout layout: <repo>/dg-reasoner/tests/ -> parents[2] is the repo root.
# Container image layout: /app/tests/ -> parents[2] is /, so fall back to the
# volume-mounted production path (same file, docker-compose ./ontology:/app/ontology:ro).
_repo_shapes = Path(__file__).resolve().parents[2] / "ontology" / "dg-shapes.ttl"
SHAPES_PATH = _repo_shapes if _repo_shapes.exists() else Path("/app/ontology/dg-shapes.ttl")


def _load_shapes() -> Graph:
    graph = Graph()
    graph.parse(str(SHAPES_PATH), format="turtle")
    return graph


def _build_results_graph(entries: list[dict]) -> Graph:
    """Hand-build a pySHACL-shaped results_graph: one sh:ValidationReport with
    sh:result edges to `entries`, each `{severity, message, focusNode, path,
    sourceShape}` (severity/path/sourceShape may be None)."""
    graph = Graph()
    report = BNode()
    graph.add((report, RDF.type, SH.ValidationReport))
    for entry in entries:
        result = BNode()
        graph.add((report, SH.result, result))
        graph.add((result, RDF.type, SH.ValidationResult))
        if entry.get("severity") is not None:
            graph.add((result, SH.resultSeverity, entry["severity"]))
        if entry.get("message") is not None:
            graph.add((result, SH.resultMessage, RDFLiteral(entry["message"])))
        if entry.get("focusNode") is not None:
            graph.add((result, SH.focusNode, entry["focusNode"]))
        if entry.get("path") is not None:
            graph.add((result, SH.resultPath, entry["path"]))
        if entry.get("sourceShape") is not None:
            graph.add((result, SH.sourceShape, entry["sourceShape"]))
    return graph


# --- (a) _walk_shacl_results maps the three severities correctly ---


def test_walk_shacl_results_maps_all_three_severities():
    results_graph = _build_results_graph(
        [
            {
                "severity": SH.Violation,
                "message": "violation message",
                "focusNode": EX.a,
                "path": RDFS.label,
                "sourceShape": DGSH.SomeShape,
            },
            {
                "severity": SH.Warning,
                "message": "warning message",
                "focusNode": EX.b,
                "path": None,
                "sourceShape": DGSH.OtherShape,
            },
            {
                "severity": SH.Info,
                "message": "info message",
                "focusNode": EX.c,
                "path": None,
                "sourceShape": DGSH.ThirdShape,
            },
        ]
    )

    raw = reasoning._walk_shacl_results(results_graph)

    assert len(raw) == 3
    by_message = {r["message"]: r for r in raw}
    assert by_message["violation message"]["severity"] == "violation"
    assert by_message["warning message"]["severity"] == "warning"
    assert by_message["info message"]["severity"] == "info"

    violation_entry = by_message["violation message"]
    assert violation_entry["focusNode"] == str(EX.a)
    assert violation_entry["path"] == str(RDFS.label)
    assert violation_entry["sourceShape"] == str(DGSH.SomeShape)
    assert isinstance(violation_entry["severity"], str)
    assert isinstance(violation_entry["message"], str)
    assert isinstance(violation_entry["focusNode"], str)
    assert isinstance(violation_entry["path"], str)
    assert isinstance(violation_entry["sourceShape"], str)


def test_walk_shacl_results_unknown_severity_defaults_to_violation():
    results_graph = _build_results_graph(
        [{"severity": None, "message": "no severity given", "focusNode": EX.a}]
    )

    raw = reasoning._walk_shacl_results(results_graph)

    assert len(raw) == 1
    assert raw[0]["severity"] == "violation"


def test_walk_shacl_results_missing_optional_fields_default_to_empty_string():
    results_graph = _build_results_graph(
        [{"severity": SH.Violation, "message": None, "focusNode": None}]
    )

    raw = reasoning._walk_shacl_results(results_graph)

    assert raw[0]["message"] == ""
    assert raw[0]["focusNode"] == ""
    assert raw[0]["path"] == ""
    assert raw[0]["sourceShape"] == ""


# --- (b) enrichment yields the six canonical keys, zero raw-RDF hygiene leaks ---


def test_enrich_shacl_result_yields_canonical_keys_with_label_and_howtofix():
    data_graph = Graph()
    focus_iri = EX.SlidingDoor
    data_graph.add((focus_iri, RDFS.label, RDFLiteral("Sliding Door")))

    shapes_graph = Graph()
    source_shape_iri = DGSH.DsKindLabelShape_label
    shapes_graph.add((source_shape_iri, DGSH.howToFix, RDFLiteral("Populate the label.")))

    raw = {
        "severity": "violation",
        "message": "Missing label.",
        "focusNode": str(focus_iri),
        "path": str(RDFS.label),
        "sourceShape": str(source_shape_iri),
    }

    finding = reasoning._enrich_shacl_result(raw, data_graph, shapes_graph)

    assert set(finding.keys()) == {"severity", "what", "where", "howToFix", "focusLabel", "shapeId"}
    assert finding["severity"] == "violation"
    assert finding["what"] == "Missing label."
    assert finding["focusLabel"] == "Sliding Door"
    assert finding["howToFix"] == "Populate the label."
    assert finding["shapeId"] == "DsKindLabelShape_label"
    assert "Sliding Door" in finding["where"]

    for value in finding.values():
        assert isinstance(value, (str, bool, type(None)))
        if isinstance(value, str):
            assert "http://www.w3.org/ns/shacl#" not in value
            assert value != "focusNode"
            assert value != "sourceShape"
            assert "http://example.org/ex#SlidingDoor" not in value
            assert "http://example.org/design-grammar/shapes#" not in value


def test_enrich_shacl_result_falls_back_to_local_name_and_generic_howtofix():
    data_graph = Graph()  # no rdfs:label for the focus node
    shapes_graph = Graph()  # no dgsh:howToFix for the source shape

    raw = {
        "severity": "warning",
        "message": "Var has no name.",
        "focusNode": "http://example.org/design-grammar/project/x/var/height",
        "path": "",
        "sourceShape": "http://example.org/design-grammar/shapes#VarNameShape_label",
    }

    finding = reasoning._enrich_shacl_result(raw, data_graph, shapes_graph)

    assert finding["focusLabel"] == "height"
    assert finding["shapeId"] == "VarNameShape_label"
    assert finding["howToFix"]  # generic per-severity fallback, never empty
    assert "http://" not in finding["focusLabel"]
    assert "http://" not in finding["shapeId"]


def test_enrich_shacl_result_handles_empty_focus_and_shape():
    data_graph = Graph()
    shapes_graph = Graph()
    raw = {"severity": "info", "message": "advisory", "focusNode": "", "path": "", "sourceShape": ""}

    finding = reasoning._enrich_shacl_result(raw, data_graph, shapes_graph)

    assert finding["focusLabel"] == ""
    assert finding["shapeId"] == ""
    assert finding["howToFix"]


# --- (c) allow_infos=True/allow_warnings=True: Info-only report still conforms ---


def _bypass_subprocess_isolation(monkeypatch):
    """Point DG_SHAPES_PATH at the real repo file and delegate
    `_run_shacl_with_timeout` straight to the synchronous `_run_pyshacl`
    helper it normally wraps in a spawn+killpg subprocess.

    The production `DG_SHAPES_PATH` default (`/app/ontology/dg-shapes.ttl`)
    only exists inside the dg-reasoner container. And `os.setsid()` (used by
    `_shacl_worker` for POSIX process-group isolation) does not exist on
    Windows, so these tests -- which exercise `run_shacl`'s real
    ABox-union/enrichment logic, not just the route wiring the existing
    `test_routes.py` monkeypatches away -- must bypass the subprocess
    mechanism itself while still exercising the real `pyshacl.validate()`
    call and result walking/enrichment end-to-end.
    """
    monkeypatch.setattr(reasoning, "DG_SHAPES_PATH", str(SHAPES_PATH))

    def _sync_run_shacl_with_timeout(data_graph, shapes_graph, timeout_seconds):
        data_nt = reasoning._serialize_nt(data_graph)
        shapes_nt = reasoning._serialize_nt(shapes_graph)
        try:
            payload = reasoning._run_pyshacl(str(data_nt), str(shapes_nt))
            return {"timeout": False, **payload}
        finally:
            data_nt.unlink(missing_ok=True)
            shapes_nt.unlink(missing_ok=True)

    monkeypatch.setattr(reasoning, "_run_shacl_with_timeout", _sync_run_shacl_with_timeout)


class _FakeResult(list):
    def single(self):
        return self[0] if self else None


class _NoOpSession:
    def run(self, query, **params):
        return _FakeResult([])


def test_run_shacl_info_only_report_conforms_true_with_nonempty_results(monkeypatch):
    """A ParamState with zero parameters trips only the Info-severity shape
    (ParamStateParameterCountShape) -- conforms must stay True (D-18) while
    results is non-empty, proving allow_infos/allow_warnings are honored."""
    _bypass_subprocess_isolation(monkeypatch)

    data_graph = Graph()
    data_graph.parse(
        data="""
        @prefix dgv: <http://example.org/design-grammar/valid#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        dgv:paramA a dgv:ParamState ;
            rdfs:label "ParamA" ;
            dgv:parameterCount 0 .
        """,
        format="turtle",
    )

    monkeypatch.setattr(reasoning.ontology_export, "build_graph", lambda session, project: data_graph)

    result = reasoning.run_shacl("x", session=_NoOpSession())

    assert result["conforms"] is True
    assert len(result["results"]) > 0
    assert all(f["severity"] == "info" for f in result["results"])
    assert result["counts"]["info"] == 1
    assert result["counts"]["violation"] == 0


def test_run_shacl_violation_flips_conforms_false(monkeypatch):
    _bypass_subprocess_isolation(monkeypatch)

    data_graph = Graph()
    data_graph.parse(
        data="""
        @prefix dgv: <http://example.org/design-grammar/valid#> .
        dgv:paramA a dgv:ParamState .
        """,
        format="turtle",
    )

    monkeypatch.setattr(reasoning.ontology_export, "build_graph", lambda session, project: data_graph)

    result = reasoning.run_shacl("x", session=_NoOpSession())

    assert result["conforms"] is False
    assert result["counts"]["violation"] >= 1


# --- (d) counts aggregates per severity ---


def test_walk_and_counts_aggregate_per_severity():
    data_graph = Graph()
    shapes_graph = _load_shapes()

    raw_results = [
        {"severity": "violation", "message": "v1", "focusNode": "", "path": "", "sourceShape": ""},
        {"severity": "violation", "message": "v2", "focusNode": "", "path": "", "sourceShape": ""},
        {"severity": "warning", "message": "w1", "focusNode": "", "path": "", "sourceShape": ""},
        {"severity": "info", "message": "i1", "focusNode": "", "path": "", "sourceShape": ""},
    ]
    findings = [reasoning._enrich_shacl_result(r, data_graph, shapes_graph) for r in raw_results]

    counts = {"violation": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding["severity"]] += 1

    assert counts == {"violation": 2, "warning": 1, "info": 1}

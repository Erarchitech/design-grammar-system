"""dg-reasoner hybrid reasoning core (REAS-05, Plan 821-03).

Owns the full `POST /reason/consistency` and `POST /shacl/validate` pipeline:

    1. `_hybrid_union(project, session)` -- union the static
       `DesignGrammar-V7.owl` TBox + the curated `ontology/dg-disjointness.ttl`
       overlay + the live project export (`ontology_export.build_graph`,
       Plan 821-02). This is the D-03 hybrid: the pipeline never reasons over
       a live-only export (the 820 false positive).
    2. `strip_hermit_unsupported` (Plan 821-02) removes `swrl:BuiltinAtom`
       rules HermiT cannot parse; the removed count is surfaced as
       `stripped_builtin_rules` (D-10).
    3. The stripped union is serialized to NTriples -- Owlready2 has no
       Turtle parser (spec/LPG-OWL-MAPPING.md #SWRL Builtin Exclusion,
       820 spike pitfall 1).
    4. Owlready2 loads the NTriples file and runs ``sync_reasoner()`` (HermiT)
       inside a ``spawn``-context ``multiprocessing.Process`` joined with a hard
       wall-clock timeout (``DG_REASONER_TIMEOUT_SECONDS``, D-09). The worker
       creates its own process group (``os.setsid()``) and on expiry the parent
       kills the entire group (``os.killpg``), which reaches the Java grandchild
       too. A clean 504-style dict is returned instead of hanging the request.
    5. `run_shacl` runs the real pySHACL pipeline against version-controlled
       shapes (`ontology/dg-shapes.ttl`, Plan 823-02, D-07/D-08), optionally
       unioning in a run-scoped ValidGraph ABox export
       (`valid_graph_export.build_valid_graph`, Plan 823-01) and mapping
       every result to a structured, raw-RDF-free finding (D-10).

Every public function accepts an injectable Neo4j-session-shaped `session`
argument (see `ontology_export.build_graph`'s duck-typed contract) so tests
can supply a fixture-backed shim and bypass a live Neo4j connection entirely.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import tempfile
import time
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

import ontology_export
import valid_graph_export
from ontology_export import strip_hermit_unsupported

# dgsh: the shapes file's own annotation namespace (howToFix remediation
# text) -- see ontology/dg-shapes.ttl.
DGSH = Namespace("http://example.org/design-grammar/shapes#")

_SEVERITY_URI_TO_STR = {SH.Violation: "violation", SH.Warning: "warning", SH.Info: "info"}

# Metagraph/OntoGraph individual types minted by ontology_export.build_graph
# (Rule/Atom/Var/Builtin ABox instances -- never the OWL.Class/DatatypeProperty
# /ObjectProperty TBox declarations, which owl:AllDifferent doesn't apply to).
_METAGRAPH_INDIVIDUAL_TYPES = (
    ontology_export.SWRL.Imp,
    ontology_export.SWRL.ClassAtom,
    ontology_export.SWRL.DatavaluedPropertyAtom,
    ontology_export.SWRL.IndividualPropertyAtom,
    ontology_export.SWRL.BuiltinAtom,
    ontology_export.SWRL.Variable,
    ontology_export.SWRL.Builtin,
)

_GENERIC_HOWTOFIX_BY_SEVERITY = {
    "violation": "Review the finding and correct the underlying data before re-publishing.",
    "warning": "Review the finding; it is not blocking but should be addressed.",
    "info": "Advisory only -- no action required unless it looks wrong.",
}

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

if not os.getenv("NEO4J_PASSWORD"):
    logger.warning(
        "NEO4J_PASSWORD is not set — falling back to default '%s'. "
        "Set NEO4J_PASSWORD in production to avoid hardcoded credentials.",
        NEO4J_PASSWORD,
    )

# Hard wall-clock bound on the HermiT/JVM subprocess (D-09). No async job
# pattern in v8.2 -- POST /reason/consistency is synchronous end-to-end.
DG_REASONER_TIMEOUT_SECONDS = int(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90"))

# Static TBox (pristine export, D-04) + curated disjointness overlay. Both
# volume-mounted read-only via ./ontology (Plan 821-01, D-07) so curating a
# new axiom is an edit + container restart, never an image rebuild.
DG_OWL_PATH = os.getenv("DG_OWL_PATH", "/app/ontology/DesignGrammar-V7.owl")
DG_DISJOINTNESS_PATH = os.getenv("DG_DISJOINTNESS_PATH", "/app/ontology/dg-disjointness.ttl")

# Version-controlled SHACL data-integrity shapes (D-07/D-08, Plan 823-02).
# Same read-only volume-mount overlay pattern as DG_DISJOINTNESS_PATH -- an
# edit + container restart picks up shape changes, no image rebuild.
DG_SHAPES_PATH = os.getenv("DG_SHAPES_PATH", "/app/ontology/dg-shapes.ttl")

SUPPORTED_ENGINES = frozenset({"hermit"})

_driver = None  # lazy singleton -- only created the first time no session is injected


def _get_driver():
    """Lazily create the module-level Neo4j driver (env-driven, dev-safe defaults).

    Mirrors `app.py`'s driver pattern. Kept lazy (not created at import time)
    so this module stays importable in tests that always inject their own
    `session` and never touch a live Neo4j connection.
    """
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase  # lazy import, mirrors ontology_export.main()

        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def _hybrid_union(project: str, session) -> Graph:
    """Union the static TBox + curated disjointness overlay + live export (D-03/D-04).

    `session` is any object satisfying `ontology_export.build_graph`'s
    duck-typed Neo4j-session contract -- a real `neo4j.Session` in production,
    a fixture-backed shim in tests.
    """
    union = Graph()
    union.parse(DG_OWL_PATH, format="xml")
    union.parse(DG_DISJOINTNESS_PATH, format="turtle")

    live_export = ontology_export.build_graph(session, project)
    for triple in live_export:
        union.add(triple)

    return union


def _axiom_counts(graph: Graph) -> dict:
    """rdflib-parsed axiom counts (never grep -- pitfall 4, RESEARCH.md #4)."""
    return {
        "subClassOf": len(list(graph.triples((None, RDFS.subClassOf, None)))),
        "domain": len(list(graph.triples((None, RDFS.domain, None)))),
        "range": len(list(graph.triples((None, RDFS.range, None)))),
        "disjointWith": len(list(graph.triples((None, OWL.disjointWith, None)))),
        "classDeclarations": len(list(graph.triples((None, RDF.type, OWL.Class)))),
    }


def _serialize_nt(graph: Graph) -> Path:
    """Serialize `graph` to a temp NTriples file. Owlready2 cannot parse Turtle."""
    fd, path_str = tempfile.mkstemp(suffix=".nt", prefix="dg-reasoner-")
    os.close(fd)
    path = Path(path_str)
    graph.serialize(destination=str(path), format="nt", encoding="utf-8")
    return path


def _local_name(iri: str) -> str:
    """Pure IRI-local-name helper (D-02 fallback label, D-13).

    Returns the substring after the last '#' if present, else the substring
    after the last '/'; if neither delimiter is present, returns `iri`
    unchanged. Never returns an empty string for a non-empty `iri`.
    """
    if "#" in iri:
        candidate = iri.rsplit("#", 1)[-1]
    elif "/" in iri:
        candidate = iri.rsplit("/", 1)[-1]
    else:
        candidate = iri
    return candidate or iri


def _reason_worker(nt_path: str, queue: "multiprocessing.Queue") -> None:
    """Runs inside the timeout-bounded child process. Never raises across the boundary."""
    os.setsid()  # own process group — parent can killpg() to reach Java grandchild
    try:
        from owlready2 import get_ontology, sync_reasoner

        onto = get_ontology(Path(nt_path).as_uri()).load()
        with onto:
            sync_reasoner()  # shells out to the bundled HermiT JAR (needs the JRE)

        try:
            inconsistent = list(onto.inconsistent_classes())
        except AttributeError:  # pragma: no cover - owlready2 API fallback
            from owlready2 import default_world

            inconsistent = list(default_world.inconsistent_classes())

        owl_nothing = "http://www.w3.org/2002/07/owl#Nothing"
        unsatisfiable_by_iri = {}
        for cls in inconsistent:
            iri = getattr(cls, "iri", str(cls))
            if iri == owl_nothing:
                continue
            labels = list(getattr(cls, "label", []) or [])
            label = str(labels[0]) if labels and str(labels[0]).strip() else _local_name(iri)
            unsatisfiable_by_iri[iri] = {"iri": iri, "label": label}

        unsatisfiable_classes = [
            unsatisfiable_by_iri[iri] for iri in sorted(unsatisfiable_by_iri)
        ]
        queue.put({"unsatisfiable_classes": unsatisfiable_classes})
    except Exception as exc:  # pragma: no cover - defensive, reported to parent
        queue.put({"error": f"{type(exc).__name__}: {exc}"})


def _reason_with_timeout(nt_path: Path, timeout_seconds: int) -> dict:
    """Run HermiT (via Owlready2) in a subprocess, killed on `timeout_seconds` expiry.

    Uses the ``spawn`` start method (not ``fork``) to avoid the deadlock hazard
    of forking mid-request from FastAPI's threaded handler (#821-REVIEW WR-03).
    The worker calls ``os.setsid()`` to create its own process group; on timeout
    the parent kills the entire group (``os.killpg``), which reaches the Java
    grandchild that Owlready2's ``sync_reasoner()`` shells out to (D-09).

    Returns ``{"timeout": True}`` on expiry, or ``{"timeout": False,
    "unsatisfiable_classes": [...]}`` on success. Propagates reasoner errors as
    ``RuntimeError``.
    """
    ctx = multiprocessing.get_context("spawn")
    queue: multiprocessing.Queue = ctx.Queue()
    process = ctx.Process(target=_reason_worker, args=(str(nt_path), queue))
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        os.killpg(process.pid, signal.SIGKILL)
        process.join(5)
        return {"timeout": True}

    if not queue.empty():
        payload = queue.get()
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return {"timeout": False, "unsatisfiable_classes": payload["unsatisfiable_classes"]}

    # Child exited without reporting (e.g. killed by the OS) -- surface as a
    # reasoner error rather than silently claiming consistency.
    raise RuntimeError(f"HermiT subprocess exited without a result (exitcode={process.exitcode})")


def run_consistency(project: str, engine: str = "hermit", session=None) -> dict:
    """Run the hybrid consistency check end-to-end and return the D-10 contract dict.

    `{consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules}`
    on success, or `{consistent: None, error: "timeout", duration_ms,
    stripped_builtin_rules, timeout_seconds}` if the hard timeout expires.

    `session`, if provided, is used instead of opening a new one against the
    module-level driver -- the injection point tests use to bypass live Neo4j.
    """
    if engine not in SUPPORTED_ENGINES:
        raise ValueError(f"Unsupported engine '{engine}'. Supported: {sorted(SUPPORTED_ENGINES)}")

    start = time.monotonic()

    owns_session = session is None
    if owns_session:
        session = _get_driver().session()
    try:
        union = _hybrid_union(project, session)
    finally:
        if owns_session:
            session.close()

    stripped_builtin_rules = strip_hermit_unsupported(union)
    axiom_counts = _axiom_counts(union)

    nt_path = _serialize_nt(union)
    try:
        result = _reason_with_timeout(nt_path, DG_REASONER_TIMEOUT_SECONDS)
    finally:
        nt_path.unlink(missing_ok=True)

    duration_ms = int((time.monotonic() - start) * 1000)

    if result.get("timeout"):
        return {
            "consistent": None,
            "error": "timeout",
            "duration_ms": duration_ms,
            "stripped_builtin_rules": stripped_builtin_rules,
            "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS,
        }

    unsatisfiable_classes = result["unsatisfiable_classes"]
    return {
        "consistent": len(unsatisfiable_classes) == 0,
        "unsatisfiable_classes": unsatisfiable_classes,
        "axiom_counts": axiom_counts,
        "duration_ms": duration_ms,
        "stripped_builtin_rules": stripped_builtin_rules,
    }


def _walk_shacl_results(results_graph: Graph) -> list[dict]:
    """Extract raw per-result dicts from a pySHACL `results_graph` (D-09).

    Returns `[{severity, message, focusNode, path, sourceShape}, ...]` --
    plain str values only, JSON-serializable across the multiprocessing
    Queue boundary. Uses `rdflib.namespace.SH` constants exclusively (never a
    hard-coded `www.w3.org/ns/shacl#` string). `sh:Violation`/`Warning`/`Info`
    map to `violation`/`warning`/`info`; an absent/unrecognized
    `sh:resultSeverity` defaults to `"violation"` (the SHACL spec default).
    """
    raw_results: list[dict] = []
    for report in results_graph.subjects(RDF.type, SH.ValidationReport):
        for result in results_graph.objects(report, SH.result):
            severity_uri = results_graph.value(result, SH.resultSeverity)
            raw_results.append(
                {
                    "severity": _SEVERITY_URI_TO_STR.get(severity_uri, "violation"),
                    "message": str(results_graph.value(result, SH.resultMessage) or ""),
                    "focusNode": str(results_graph.value(result, SH.focusNode) or ""),
                    "path": str(results_graph.value(result, SH.resultPath) or ""),
                    "sourceShape": str(results_graph.value(result, SH.sourceShape) or ""),
                }
            )
    return raw_results


def _enrich_shacl_result(raw: dict, data_graph: Graph, shapes_graph: Graph) -> dict:
    """Map one raw `_walk_shacl_results` dict to the canonical D-10 finding.

    `{severity, what, where, howToFix, focusLabel, shapeId}` -- `focusNode`
    resolves to `focusLabel` via `rdfs:label` in the DATA graph (never the
    results graph), else `_local_name()` (Phase 822's `{iri,label}` pattern,
    reused verbatim). `sourceShape` resolves to `shapeId` via `_local_name()`
    and to `howToFix` via `dgsh:howToFix` on the SHAPES graph, falling back to
    a generic per-severity hint when the shape carries none. No `sh:*` IRI,
    raw focus-node IRI, or rdflib term object ever appears in the result.
    """
    focus_iri = raw.get("focusNode") or ""
    focus_label = ""
    if focus_iri:
        label = data_graph.value(URIRef(focus_iri), RDFS.label)
        focus_label = str(label) if label else _local_name(focus_iri)

    path = raw.get("path") or ""
    if path and focus_label:
        where = f"{focus_label} ({_local_name(path)})"
    elif path:
        where = _local_name(path)
    else:
        where = focus_label

    source_shape_iri = raw.get("sourceShape") or ""
    shape_id = _local_name(source_shape_iri) if source_shape_iri else ""

    how_to_fix = None
    if source_shape_iri:
        how_to_fix_literal = shapes_graph.value(URIRef(source_shape_iri), DGSH.howToFix)
        if how_to_fix_literal:
            how_to_fix = str(how_to_fix_literal)
    if not how_to_fix:
        severity = raw.get("severity", "violation")
        how_to_fix = _GENERIC_HOWTOFIX_BY_SEVERITY.get(severity, _GENERIC_HOWTOFIX_BY_SEVERITY["violation"])

    return {
        "severity": raw.get("severity", "violation"),
        "what": raw.get("message") or "",
        "where": where,
        "howToFix": how_to_fix,
        "focusLabel": focus_label,
        "shapeId": shape_id,
    }


def _run_pyshacl(data_nt: str, shapes_nt: str) -> dict:
    """Run `pyshacl.validate()` and walk the results (D-09). Pure/synchronous --
    no subprocess/queue concerns -- so `_shacl_worker` (POSIX-only
    `os.setsid()` process-group isolation) and unit tests can both call it
    directly.

    `allow_infos=True, allow_warnings=True` is mandatory (RESEARCH.md Pattern
    1 gotcha, verified against the installed pySHACL 0.40.0 source): without
    both kwargs, ANY sh:Info/sh:Warning result flips pySHACL's own `conforms`
    to False, breaking the "Info/Warning-only reports still conform"
    contract (D-18) that `run_shacl` derives independently from severities
    anyway -- but the raw `conforms` bool returned here stays accurate only
    with these kwargs set.
    """
    from pyshacl import validate as pyshacl_validate

    conforms, results_graph, _results_text = pyshacl_validate(
        data_nt,
        shacl_graph=shapes_nt,
        inference="none",
        advanced=False,
        allow_infos=True,
        allow_warnings=True,
    )
    return {"conforms": bool(conforms), "raw_results": _walk_shacl_results(results_graph)}


def _shacl_worker(data_nt: str, shapes_nt: str, queue: "multiprocessing.Queue") -> None:
    """SHACL validation worker. Same process-group isolation pattern as _reason_worker."""
    os.setsid()  # own process group -- parent can killpg() to reach any JVM-adjacent child
    try:
        queue.put(_run_pyshacl(data_nt, shapes_nt))
    except Exception as exc:  # pragma: no cover - defensive
        queue.put({"error": f"{type(exc).__name__}: {exc}"})


def _run_shacl_with_timeout(data_graph: Graph, shapes_graph: Graph, timeout_seconds: int) -> dict:
    """Run pySHACL in a timeout-bounded subprocess (same spawn+killpg pattern as HermiT)."""
    data_nt = _serialize_nt(data_graph)
    shapes_nt = _serialize_nt(shapes_graph)
    try:
        ctx = multiprocessing.get_context("spawn")
        queue: multiprocessing.Queue = ctx.Queue()
        process = ctx.Process(
            target=_shacl_worker, args=(str(data_nt), str(shapes_nt), queue)
        )
        process.start()
        process.join(timeout_seconds)

        if process.is_alive():
            os.killpg(process.pid, signal.SIGKILL)
            process.join(5)
            return {"timeout": True}

        if not queue.empty():
            payload = queue.get()
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return {"timeout": False, "conforms": payload["conforms"], "raw_results": payload["raw_results"]}

        raise RuntimeError(
            f"SHACL subprocess exited without a result (exitcode={process.exitcode})"
        )
    finally:
        data_nt.unlink(missing_ok=True)
        shapes_nt.unlink(missing_ok=True)


def _collect_named_individuals(graph: Graph, rdf_types) -> list[URIRef]:
    """Collect distinct URIRef subjects typed as any of `rdf_types` (first-seen order)."""
    seen: list[URIRef] = []
    seen_set: set = set()
    for rdf_type in rdf_types:
        for subject in graph.subjects(RDF.type, rdf_type):
            if isinstance(subject, URIRef) and subject not in seen_set:
                seen_set.add(subject)
                seen.append(subject)
    return seen


def _remove_existing_all_different(graph: Graph) -> None:
    """Strip any `owl:AllDifferent` declarations (and their `rdf:List` cells)
    already present in `graph`, in place.

    Plan 823-01's `build_valid_graph` already emits its own UNA over the
    individuals it mints; when `run_shacl` unions that graph in, this clears
    that self-contained declaration so a single fresh batch-wide UNA (D-05)
    can be re-derived over BOTH exports' individuals, rather than trusting
    two independently-emitted `owl:AllDifferent` declarations to compose.
    """
    for all_diff in list(graph.subjects(RDF.type, OWL.AllDifferent)):
        for members_head in list(graph.objects(all_diff, OWL.distinctMembers)):
            node = members_head
            while node is not None and node != RDF.nil:
                next_node = graph.value(node, RDF.rest)
                graph.remove((node, None, None))
                node = next_node
        graph.remove((all_diff, None, None))


def run_shacl(project: str, run_id: str | None = None, session=None) -> dict:
    """Run the real pySHACL pipeline against version-controlled shapes (D-07/D-08/D-09/D-10).

    Without `run_id`, validates the project-level Metagraph/OntoGraph export
    only -- the 821 backward-compatible contract (D-03). With `run_id`,
    additionally unions in that run's ValidGraph ABox (Plan 823-01's
    `build_valid_graph`) and re-derives a single batch-wide `owl:AllDifferent`
    (UNA, D-05) over every minted individual from both exports.

    Returns the canonical envelope `{conforms, results, counts}` on success --
    `conforms` is derived as `not any(severity == "violation")`, so an
    Info/Warning-only report still conforms (D-18) -- or the unchanged 821
    timeout shape `{conforms: None, error: "timeout", timeout_seconds}`.

    Validation runs in the existing timeout-bounded spawn+killpg subprocess
    (`_run_shacl_with_timeout`, unchanged mechanism) so pathological
    shapes/ABox data cannot hang the route indefinitely (WR-04).
    """
    owns_session = session is None
    if owns_session:
        session = _get_driver().session()
    try:
        data_graph = ontology_export.build_graph(session, project)
        if run_id:
            metagraph_individuals = _collect_named_individuals(data_graph, _METAGRAPH_INDIVIDUAL_TYPES)
            valid_graph, valid_individuals = valid_graph_export.build_valid_graph(session, project, run_id)
            for triple in valid_graph:
                data_graph.add(triple)
            _remove_existing_all_different(data_graph)
            valid_graph_export.add_all_different(data_graph, metagraph_individuals + valid_individuals)
    finally:
        if owns_session:
            session.close()

    shapes_graph = Graph()
    shapes_graph.parse(DG_SHAPES_PATH, format="turtle")

    result = _run_shacl_with_timeout(data_graph, shapes_graph, DG_REASONER_TIMEOUT_SECONDS)
    if result.get("timeout"):
        return {"conforms": None, "error": "timeout", "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS}

    findings = [_enrich_shacl_result(raw, data_graph, shapes_graph) for raw in result["raw_results"]]
    counts = {"violation": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1

    conforms = not any(finding["severity"] == "violation" for finding in findings)
    return {"conforms": conforms, "results": findings, "counts": counts}

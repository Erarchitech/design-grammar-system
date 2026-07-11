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
    5. `run_shacl` runs the real pySHACL pipeline against an intentionally
       empty/placeholder shapes graph (D-11) -- plumbing proven, real shapes
       land in Phase 823.

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

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

import ontology_export
from ontology_export import strip_hermit_unsupported

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


def _shacl_worker(data_nt: str, shapes_nt: str, queue: "multiprocessing.Queue") -> None:
    """SHACL validation worker. Same process-group isolation pattern as _reason_worker."""
    os.setsid()
    try:
        from pyshacl import validate as pyshacl_validate

        conforms, _results_graph, _results_text = pyshacl_validate(
            data_nt,
            shacl_graph=shapes_nt,
            inference="none",
            advanced=False,
        )
        queue.put({"conforms": bool(conforms)})
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
            return {"timeout": False, "conforms": payload["conforms"]}

        raise RuntimeError(
            f"SHACL subprocess exited without a result (exitcode={process.exitcode})"
        )
    finally:
        data_nt.unlink(missing_ok=True)
        shapes_nt.unlink(missing_ok=True)


def run_shacl(project: str, session=None) -> dict:
    """Run the real pySHACL pipeline against an empty/placeholder shapes graph (D-11).

    Proves the plumbing (data graph built from the live export, real
    ``pyshacl.validate()`` invoked) without committing to real shapes yet --
    those land in Phase 823. Empty shapes always conform, by construction.

    Validation runs in a timeout-bounded subprocess (same spawn+killpg pattern
    as ``run_consistency``) so that heavy/pathological shapes (Phase 823) cannot
    hang the route indefinitely (WR-04).
    """
    owns_session = session is None
    if owns_session:
        session = _get_driver().session()
    try:
        data_graph = ontology_export.build_graph(session, project)
    finally:
        if owns_session:
            session.close()

    # Deliberately empty placeholder shapes graph -- Phase 823 swaps this for
    # real SHACL shapes. Clearly labelled so it's unmistakable in review.
    shapes_graph = Graph()

    result = _run_shacl_with_timeout(data_graph, shapes_graph, DG_REASONER_TIMEOUT_SECONDS)
    if result.get("timeout"):
        return {"conforms": None, "error": "timeout", "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS}

    return {"conforms": result["conforms"], "results": []}

"""ValidGraph->RDF ABox exporter (REAS-05 / SHCL-01, D-04/D-05).

Sibling to `ontology_export.py`, translating one Grasshopper VALIDATOR run
into `dgv:` named individuals per `spec/LPG-OWL-MAPPING.md`'s
"ValidGraph to RDF Sketch" (informative, promoted to real here) and
implementing the `owl:AllDifferent` (UNA) obligation Phase 821 deferred to
this phase (§"Unique Name Assumption (UNA)").

**Primary data source (D-04):** the `statePayloadJson` v2 envelope stored on
the `ValidationRun` Neo4j node (`DG.Core.Serialization.DesignStatePayloadV2Serializer`
on the write side) -- this is what data-service's live write path actually
persists (`cypher_template.txt` documents standalone `DesignState`/`Run`
graph nodes as "document-only -- NOT emitted by LLM ingest"). A defensive,
label-scoped `(n:DesignState OR n:Run)` read is also implemented per the
export-scoping mandate (spec #Export Scoping) so this exporter degrades
gracefully -- never silently -- if/when live nodes of those labels exist for
a project; it is expected to be a no-op against current data.

Public entry point: `build_valid_graph(session, project, run_id) ->
(rdflib.Graph, list[URIRef])`. `session` is the same duck-typed
Neo4j-driver-shaped object `ontology_export.build_graph` expects (`.run()`
returning an iterable of mapping-like records, `.single()` on the result).
This module never imports `neo4j` at module scope, so it is importable and
fully unit-testable without a live Neo4j connection.
"""
from __future__ import annotations

import json

from rdflib import BNode, Graph, Literal as RDFLiteral, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from ontology_export import BASE, bind_prefixes as _bind_ontology_prefixes, make_argument_list, mint

# --- namespace (spec/LPG-OWL-MAPPING.md #ValidGraph to RDF Sketch) ---
DGV = Namespace(f"{BASE}/valid#")  # dgv: ValidGraph-layer ABox vocabulary

# --- label-scoped, parameterized Cypher (Export Scoping mandate: scope by
# LABEL/key properties, never by the non-authoritative `graph` property) ---
RUN_QUERY = """
MATCH (run:ValidationRun)
WHERE run.project = $project AND run.runId = $runId
RETURN run.statePayloadJson AS statePayloadJson,
       run.ValidStatus AS validStatus,
       run.SendStatus AS sendStatus
"""

# Defensive live-node read: current write path never creates these labels
# (document-only per cypher_template.txt), but a future/legacy project could
# carry them -- this branch must not raise and should merge any found
# individuals into the same graph rather than being silently skipped.
DESIGNSTATE_QUERY = """
MATCH (n)
WHERE n.project = $project AND (n:DesignState OR n:Run)
RETURN labels(n) AS labels, properties(n) AS props
"""

_KIND_TO_RDF_TYPE: dict[str, URIRef] = {
    "objStates": DGV.ObjState,
    "paramStates": DGV.ParamState,
    "propStates": DGV.PropState,
}


def bind_prefixes(graph: Graph) -> None:
    """Bind the standard prefix set for a ValidGraph ABox export batch."""
    _bind_ontology_prefixes(graph)  # dg/dgm/ex/swrl/swrlb/owl/xsd
    graph.bind("dgv", DGV)
    graph.bind("rdfs", RDFS)


def _first_row(result) -> dict | None:
    """Extract the single record from a `.single()`-capable or plain-iterable result."""
    if hasattr(result, "single"):
        return result.single()
    for row in result:
        return row
    return None


def _state_label(kind: str, state: dict) -> str | None:
    """Pick the display label for one state child per its kind (D-04)."""
    if kind == "objStates":
        return state.get("label") or state.get("objectRef") or state.get("stateId")
    if kind == "paramStates":
        return state.get("stateId")
    if kind == "propStates":
        rule_iri = state.get("ruleIri") or ""
        if ":" in rule_iri:
            return rule_iri.split(":", 1)[-1]
        return rule_iri or state.get("stateId")
    return state.get("stateId")


def _mint_state_individuals(
    graph: Graph, project: str, envelope: dict, minted: list[URIRef]
) -> None:
    """Mint one dgv:ObjState/ParamState/PropState child per envelope entry, linked via dgv:hasState."""
    parent_state_id = envelope.get("stateId")
    if not parent_state_id:
        return
    parent_iri = mint(project, "state", parent_state_id)
    if envelope.get("label"):
        graph.add((parent_iri, RDFS.label, RDFLiteral(envelope["label"])))

    for kind, rdf_type in _KIND_TO_RDF_TYPE.items():
        for state in envelope.get(kind) or []:
            state_id = state.get("stateId")
            if not state_id:
                continue
            child_iri = mint(project, "state", state_id)
            graph.add((child_iri, RDF.type, rdf_type))
            label = _state_label(kind, state)
            if label:
                graph.add((child_iri, RDFS.label, RDFLiteral(str(label))))
            graph.add((parent_iri, DGV.hasState, child_iri))
            minted.append(child_iri)


def _mint_run_individual(
    graph: Graph, project: str, run_id: str, row: dict, minted: list[URIRef]
) -> None:
    """Mint the dgv:Run individual with sendStatus/validStatus (D-04, LPG-OWL-MAPPING §Run)."""
    run_iri = mint(project, "run", run_id)
    graph.add((run_iri, RDF.type, DGV.Run))
    minted.append(run_iri)

    send_status = row.get("sendStatus")
    if send_status is not None:
        graph.add((run_iri, DGV.sendStatus, RDFLiteral(bool(send_status), datatype=XSD.boolean)))

    valid_status = row.get("validStatus")
    if valid_status:
        bool_literals = [RDFLiteral(bool(v), datatype=XSD.boolean) for v in valid_status]
        graph.add((run_iri, DGV.validStatus, make_argument_list(graph, bool_literals)))


def build_valid_graph(session, project: str, run_id: str) -> tuple[Graph, list[URIRef]]:
    """Translate one ValidationRun's statePayloadJson v2 envelope to a dgv: ABox.

    Returns `(graph, minted_individuals)` -- the caller (Plan 823-02's
    `run_shacl`) controls whether/how to union this with
    `ontology_export.build_graph`'s Metagraph/OntoGraph individuals and the
    batch-wide `owl:AllDifferent` (this function already emits its own UNA
    over the individuals it mints, per D-05; callers unioning multiple
    export batches should re-derive `owl:AllDifferent` over the full
    combined `minted_individuals` list rather than trusting two independent
    UNA declarations to compose correctly).

    Never raises on a missing run row or a missing/malformed
    `statePayloadJson` -- both degrade to zero state individuals (D-04
    behavior contract); the caller decides how to report/log the count.
    """
    graph = Graph()
    bind_prefixes(graph)
    minted: list[URIRef] = []

    row = _first_row(session.run(RUN_QUERY, project=project, runId=run_id))
    if row is not None:
        payload_raw = row.get("statePayloadJson")
        if payload_raw:
            try:
                envelope = json.loads(payload_raw)
            except (TypeError, ValueError):
                envelope = None
            if envelope:
                _mint_state_individuals(graph, project, envelope, minted)

        _mint_run_individual(graph, project, run_id, row, minted)

    # Defensive: live DesignState/Run graph nodes, label-scoped (no-op on
    # current write-path data, but must not raise and must merge into the
    # same graph per the export-scoping mandate).
    for record in session.run(DESIGNSTATE_QUERY, project=project):
        labels = record.get("labels") or []
        props = record.get("props") or {}
        if "DesignState" in labels:
            state_id = props.get("StateId") or props.get("stateId")
            kind = props.get("kind")
            rdf_type = _KIND_TO_RDF_TYPE.get(f"{kind[0].lower()}{kind[1:]}s" if kind else "", None)
            if not state_id or rdf_type is None:
                continue
            live_iri = mint(project, "state", state_id)
            if (live_iri, RDF.type, rdf_type) not in graph:
                graph.add((live_iri, RDF.type, rdf_type))
                minted.append(live_iri)
        elif "Run" in labels:
            live_run_id = props.get("Run_Id") or props.get("runId")
            if not live_run_id:
                continue
            live_run_iri = mint(project, "run", live_run_id)
            if (live_run_iri, RDF.type, DGV.Run) not in graph:
                graph.add((live_run_iri, RDF.type, DGV.Run))
                minted.append(live_run_iri)

    add_all_different(graph, minted)
    return graph, minted


def add_all_different(graph: Graph, individuals: list[URIRef]) -> None:
    """Emit one `owl:AllDifferent` over `individuals` via `owl:distinctMembers` (D-05, UNA).

    No-op on an empty list (spec §UNA: only required "for every project
    export batch that includes named individuals").
    """
    if not individuals:
        return
    all_diff = BNode()
    graph.add((all_diff, RDF.type, OWL.AllDifferent))
    graph.add((all_diff, OWL.distinctMembers, make_argument_list(graph, individuals)))

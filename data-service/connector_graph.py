"""Named, read-only graph queries for the connector (Grasshopper) over HTTPS.

The Grasshopper plug-in reads rules, ontology classes/properties and validation
runs straight from Neo4j over Bolt in a trusted-local deployment. The
multi-user profile never hands a connector the Neo4j bundle (see
``app._neo4j_bundle_or_none`` and ``spec/SECURITY-BOUNDARY.md``), so the same
reads are served here instead: ``GET /connector-graph/{project}/{query_id}``.

A query is picked by NAME from the fixed table below -- a connector never sends
Cypher. The project is bound as the only parameter (plus ``runId`` for the
evidence read) and never interpolated into the statement text. The statements
mirror the constants in ``DG/src/DG.Core/Data/Neo4j*Repository.cs``; keep the two
in step (``test_connector_graph.py`` pins the table and its row fields).
"""

from __future__ import annotations

from typing import Any

# query_id -> (Cypher, needs runId)
QUERIES: dict[str, tuple[str, bool]] = {
    "rules": (
        """
        MATCH (r:Rule {graph:'Metagraph', project:$project})
        WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
        RETURN
            r.Rule_Id AS id,
            coalesce(r.RuleName, r.title, r.name, r.Rule_Id) AS name,
            coalesce(r.RuleDescription, r.description, '') AS description,
            coalesce(r.kind, 'violation') AS kind,
            coalesce(r.text, '') AS text,
            coalesce(r.SWRL, r.swrl, r.text, '') AS swrl,
            coalesce(r.project, $project) AS project,
            coalesce(r.graph, 'Metagraph') AS graph
        ORDER BY id
        """,
        False,
    ),
    "atoms": (
        """
        MATCH (r:Rule {graph:'Metagraph', project:$project})-[rel:HAS_BODY|HAS_HEAD]->(a:Atom {graph:'Metagraph', project:$project})
        OPTIONAL MATCH (a)-[:REFERS_TO]->(p)
        OPTIONAL MATCH (a)-[arg:ARG]->(av)
        WHERE av IS NULL OR av.project IS NULL OR av.project = $project
        RETURN
            r.Rule_Id AS ruleId,
            type(rel) AS relationType,
            coalesce(rel.`order`, 0) AS atomOrder,
            a.Atom_Id AS atomId,
            coalesce(a.type, '') AS atomType,
            coalesce(p.iri, a.iri) AS predicateIri,
            coalesce(p.label, p.SWRL_label, a.SWRL_label) AS predicateLabel,
            coalesce(arg.`pos`, 0) AS argPos,
            labels(av) AS argLabels,
            av.name AS varName,
            av.lex AS litLex,
            av.datatype AS litDatatype
        ORDER BY ruleId, relationType, atomOrder, argPos
        """,
        False,
    ),
    "objects": (
        """
        MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class)
        RETURN DISTINCT c.iri AS iri, c.label AS label
        ORDER BY c.label
        """,
        False,
    ),
    "classes": (
        """
        MATCH (c:Class {graph:'OntoGraph', project:$project})
        RETURN c.iri AS iri, c.label AS label
        ORDER BY c.label
        """,
        False,
    ),
    "objProperties": (
        """
        MATCH (p:ObjProperty {graph:'OntoGraph', project:$project})
        RETURN p.iri AS iri, p.label AS label
        ORDER BY p.label
        """,
        False,
    ),
    "dataProperties": (
        """
        MATCH (p:DataProperty {graph:'OntoGraph', project:$project})
        RETURN p.iri AS iri, p.label AS label
        ORDER BY p.label
        """,
        False,
    ),
    "runs": (
        """
        MATCH (run:ValidationRun {graph:'ValidGraph', project:$project})
        RETURN
            run.runId AS runId,
            coalesce(run.project, $project) AS project,
            run.createdAt AS createdAt,
            coalesce(run.rulesJson, '[]') AS rulesJson,
            run.statePayloadJson AS statePayloadJson
        ORDER BY run.createdAt DESC, run.runId ASC
        """,
        False,
    ),
    "standaloneStates": (
        """
        MATCH (ds:DesignState {graph:'ValidGraph', project:$project, kind:'ParamState'})
        WHERE ds.statePayloadJson IS NOT NULL
        RETURN
            ds.StateId AS stateId,
            ds.statePayloadJson AS statePayloadJson,
            ds.acceptedAt AS acceptedAt
        ORDER BY ds.acceptedAt DESC, ds.StateId ASC
        """,
        False,
    ),
    "evidence": (
        """
        MATCH (run:ValidationRun {graph:'ValidGraph', project:$project, runId:$runId})
        RETURN run.evidenceEnvelopeJson AS evidenceEnvelopeJson
        """,
        True,
    ),
}


def is_known(query_id: str) -> bool:
    return query_id in QUERIES


def needs_run_id(query_id: str) -> bool:
    return QUERIES[query_id][1]


def run(query_id: str, project: str, run_id: str | None, read_many) -> list[dict[str, Any]]:
    """Execute the named query for ``project`` with the caller-supplied reader."""
    cypher, wants_run_id = QUERIES[query_id]
    parameters: dict[str, Any] = {"project": project}
    if wants_run_id:
        parameters["runId"] = run_id
    return read_many(cypher, parameters)

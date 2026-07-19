"""Computgraph publish -- the first runtime writer of the Computgraph ontology
partition (Phase 36-01: CGPD-01/02/03).

Turns a confirmed ``cgContextJson v1`` envelope (Phase 32 serializer, Phase 32.1
dgId-stamped, Phase 35 confirmed) into MERGE-idempotent, project-isolated,
provenance-carrying Neo4j nodes and relationships under ``graph:'Computgraph'``.

Identity model
--------------
Every entity that has a ``cgId`` in the envelope (Object, Procedure, Pattern,
Parameter, Interface) is anchored server-side by ``dg_identity.compute_dg_id``
(pure function, no DB round-trip) rather than the identity registry's persistent
anchor helper: the registry's anchor MERGE (``MERGE (e {cgId, definitionId,
project})``) is label-less, and Neo4j's MERGE matches on the FULL pattern
including labels -- a later ``MERGE (n:Pattern {cgId, definitionId, project})``
from this module would never coincide with that anchor and would create a
duplicate, orphaned node. This module therefore calls only the pure
``compute_dg_id`` function, never the registry persistence helper; the resulting
string is set as a plain property inside this module's own labeled MERGE.

``Behavior`` has no entity in the wire format (``CgObject`` collapses
Object/Behavior into one JSON entity) -- it is synthesized server-side with the
MERGE key ``{definitionId, project}`` (no cgId/dgId; exactly one per Object per
definition). ``Algorithm`` likewise carries no dgId (DGID-01's scope is Object,
Procedure, Pattern, Parameter, Interface only) and MERGEs on
``{algIndex, definitionId, project}``.

Atomicity
---------
The caller (``app.py``'s ``POST /computgraph/publish`` route) owns
``with driver.session() as session:`` and passes ``session`` in -- this module
never opens its own session. The write itself runs inside ONE
``session.execute_write(...)`` call: every ``tx.run()`` issued by the inner
function is part of the SAME explicit Neo4j transaction, so a mid-write failure
leaves no partial Computgraph subgraph (a crash between two independent
``write_query()``-style auto-commits, as ``store_validation_run`` does, would
NOT give this guarantee -- that shape is deliberately not used here). Each
statement's Cypher literal carries an ``// op=PUBLISH_<KIND>`` comment tag so
duck-typed test sessions can dispatch on it.

Security: every ``session.run``/``tx.run`` call receives parameters as a dict --
entity names, ids, and provenance strings are NEVER f-string / ``%`` /
``.format`` interpolated into query text (T-36-01: Cypher injection). Only
``cg_context['object']`` and ``cg_context['algorithms']`` are read into the
write; ``cg_context['untagged']`` is never touched (T-36-02).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from dg_identity import compute_dg_id

GRAPH_NAME = "Computgraph"

_VALID_PARAM_KINDS = {"Variable", "Constant", "Emergent"}
_VALID_PARAM_DATA_TYPES = {"Float", "Integer", "Text", "Boolean", "Geometry"}
_VALID_IFACE_TYPES = {"Input", "Output"}


def publish_structure(session: Any, project: str, cg_context: dict) -> dict:
    """Publish a confirmed cgContextJson v1 envelope as a Computgraph subgraph.

    Reads only ``object`` and ``algorithms`` from ``cg_context`` -- ``untagged``
    is never written (T-36-02). Raises ``ValueError`` on a malformed envelope
    (missing ``definition.documentId``, or an unrecognized paramKind/dataType/
    ifaceType) so the caller's ``except ValueError`` branch can surface a 422.

    Returns ``{status, publishedCounts, staleEntityIds}``.
    """
    definition = cg_context.get("definition") or {}
    definition_id = definition.get("documentId")
    if not definition_id:
        raise ValueError("cg_context.definition.documentId is required.")
    file_name = definition.get("fileName") or ""

    published_at = datetime.now(timezone.utc).isoformat()

    params = _build_publish_params(project, definition_id, file_name, published_at, cg_context)

    def _write(tx: Any) -> None:
        if params["object"] is not None:
            _publish_object(tx, params)
            _publish_behavior(tx, params)
        if params["algorithmRows"]:
            _publish_algorithms(tx, params)
        if params["procedureRows"]:
            _publish_procedures(tx, params)
        if params["patternRows"]:
            _publish_patterns(tx, params)
        if params["patternHostRows"]:
            _publish_pattern_hosts(tx, params)
        if params["parameterRows"]:
            _publish_parameters(tx, params)
        if params["interfaceRows"]:
            _publish_interfaces(tx, params)
        if params["paramLinkRows"]:
            _publish_param_links(tx, params)

    session.execute_write(_write)

    stale_entity_ids = _find_stale_entities(session, project, definition_id, params["allCgIds"])

    return {
        "status": "published",
        "publishedCounts": {
            "object": 1 if params["object"] is not None else 0,
            "behavior": 1 if params["object"] is not None else 0,
            "algorithms": len(params["algorithmRows"]),
            "procedures": len(params["procedureRows"]),
            "patterns": len(params["patternRows"]),
            "parameters": len(params["parameterRows"]),
            "interfaces": len(params["interfaceRows"]),
            "paramLinks": len(params["paramLinkRows"]),
        },
        "staleEntityIds": stale_entity_ids,
    }


# ── Row-building (pure, no DB access) ──


def _build_publish_params(
    project: str,
    definition_id: str,
    file_name: str,
    published_at: str,
    cg_context: dict,
) -> dict:
    """Flatten the confirmed envelope into row lists ready for UNWIND-batched
    Cypher writes. Only ``object``/``algorithms`` are read -- ``untagged`` is
    never touched (T-36-02).
    """
    object_row = _object_row(cg_context.get("object"), project, definition_id)

    algorithm_rows: list[dict] = []
    procedure_rows: list[dict] = []
    pattern_rows: list[dict] = []
    pattern_host_rows: list[dict] = []
    parameter_rows: list[dict] = []
    interface_rows: list[dict] = []

    # v9.0 persists ontology entities only; the raw node/wire substrate is not
    # persisted per-node -- store the confirmed envelope (EXCLUDING untagged) as a
    # reconstructable attachment on each Algorithm node (CONTEXT.md Open Question 1).
    # The untagged section is stripped so the stored contextJson never carries ids
    # the publish path did not write (T-36-02).
    _storage_ctx = {k: v for k, v in cg_context.items() if k != "untagged"}
    context_json = json.dumps(_storage_ctx, sort_keys=True)

    for algorithm in cg_context.get("algorithms") or []:
        alg_index = algorithm.get("index")
        algorithm_rows.append(
            {
                "index": alg_index,
                "name": algorithm.get("name") or "",
                "contextJson": context_json,
            }
        )

        for procedure in algorithm.get("procedures") or []:
            proc_cg_id = procedure.get("id") or ""
            proc_source = procedure.get("source") or "tagged"
            procedure_rows.append(
                {
                    "cgId": proc_cg_id,
                    "algIndex": alg_index,
                    "name": procedure.get("name") or "",
                    "index": procedure.get("index"),
                    "dgId": compute_dg_id(project, definition_id, proc_cg_id),
                    "source": proc_source,
                    "provider": procedure.get("provider") if proc_source == "recognized" else None,
                    "model": procedure.get("model") if proc_source == "recognized" else None,
                    "confidence": procedure.get("confidence") if proc_source == "recognized" else None,
                }
            )

            for pattern in procedure.get("patterns") or []:
                pat_cg_id = pattern.get("id") or ""
                pat_source = pattern.get("source") or "tagged"
                pattern_rows.append(
                    {
                        "cgId": pat_cg_id,
                        "procCgId": proc_cg_id,
                        "name": pattern.get("name") or pattern.get("label") or "",
                        "dgId": compute_dg_id(project, definition_id, pat_cg_id),
                        "source": pat_source,
                        "provider": pattern.get("provider") if pat_source == "recognized" else None,
                        "model": pattern.get("model") if pat_source == "recognized" else None,
                        "confidence": pattern.get("confidence") if pat_source == "recognized" else None,
                    }
                )
                host_id = pattern.get("hostPatternId")
                if host_id:
                    pattern_host_rows.append({"childCgId": pat_cg_id, "hostCgId": host_id})

            for parameter in procedure.get("parameters") or []:
                param_cg_id = parameter.get("id") or ""
                param_source = parameter.get("source") or "tagged"
                kind = parameter.get("kind")
                if kind not in _VALID_PARAM_KINDS:
                    raise ValueError(
                        f"Unsupported paramKind {kind!r} on parameter {param_cg_id!r}. "
                        f"Allowed values: {sorted(_VALID_PARAM_KINDS)}."
                    )
                data_type = parameter.get("dataType")
                if data_type is not None and data_type not in _VALID_PARAM_DATA_TYPES:
                    raise ValueError(
                        f"Unsupported dataType {data_type!r} on parameter {param_cg_id!r}. "
                        f"Allowed values: {sorted(_VALID_PARAM_DATA_TYPES)}."
                    )
                domain = parameter.get("domain") or {}
                parameter_rows.append(
                    {
                        "cgId": param_cg_id,
                        "procCgId": proc_cg_id,
                        "name": parameter.get("name") or "",
                        "kind": kind,
                        "dataType": data_type,
                        "domainMin": domain.get("min"),
                        "domainMax": domain.get("max"),
                        "domainStep": domain.get("step"),
                        "dgId": compute_dg_id(project, definition_id, param_cg_id),
                        "source": param_source,
                        "provider": parameter.get("provider") if param_source == "recognized" else None,
                        "model": parameter.get("model") if param_source == "recognized" else None,
                        "confidence": parameter.get("confidence") if param_source == "recognized" else None,
                        "memberIds": list(parameter.get("memberIds") or []),
                    }
                )

            for iface in procedure.get("interfaces") or []:
                iface_cg_id = iface.get("id") or ""
                iface_source = iface.get("source") or "tagged"
                iface_type = iface.get("ifaceType")
                if iface_type not in _VALID_IFACE_TYPES:
                    raise ValueError(
                        f"Unsupported ifaceType {iface_type!r} on interface {iface_cg_id!r}. "
                        f"Allowed values: {sorted(_VALID_IFACE_TYPES)}."
                    )
                interface_rows.append(
                    {
                        "cgId": iface_cg_id,
                        "procCgId": proc_cg_id,
                        "name": iface.get("name") or "",
                        "ifaceType": iface_type,
                        "dgId": compute_dg_id(project, definition_id, iface_cg_id),
                        "source": iface_source,
                        "provider": iface.get("provider") if iface_source == "recognized" else None,
                        "model": iface.get("model") if iface_source == "recognized" else None,
                        "confidence": iface.get("confidence") if iface_source == "recognized" else None,
                        "memberIds": list(iface.get("memberIds") or []),
                    }
                )

    param_link_rows = _paramlinks_from_wires(cg_context.get("wires") or [], parameter_rows, interface_rows)

    all_cg_ids = [row["cgId"] for row in procedure_rows]
    all_cg_ids += [row["cgId"] for row in pattern_rows]
    all_cg_ids += [row["cgId"] for row in parameter_rows]
    all_cg_ids += [row["cgId"] for row in interface_rows]
    if object_row is not None:
        all_cg_ids.append(object_row["cgId"])

    return {
        "project": project,
        "definitionId": definition_id,
        "fileName": file_name,
        "publishedAt": published_at,
        "object": object_row,
        "algorithmRows": algorithm_rows,
        "procedureRows": procedure_rows,
        "patternRows": pattern_rows,
        "patternHostRows": pattern_host_rows,
        "parameterRows": parameter_rows,
        "interfaceRows": interface_rows,
        "paramLinkRows": param_link_rows,
        "allCgIds": all_cg_ids,
    }


def _object_row(obj: dict | None, project: str, definition_id: str) -> dict | None:
    if obj is None:
        return None
    name = obj.get("name") or ""
    cg_id = f"obj:{name}"
    source = obj.get("source") or "tagged"
    return {
        "cgId": cg_id,
        "objectName": name,
        "classIri": obj.get("classIri"),
        "dgId": compute_dg_id(project, definition_id, cg_id),
        "source": source,
        "provider": obj.get("provider") if source == "recognized" else None,
        "model": obj.get("model") if source == "recognized" else None,
        "confidence": obj.get("confidence") if source == "recognized" else None,
    }


def _paramlinks_from_wires(wires: list[dict], parameter_rows: list[dict], interface_rows: list[dict]) -> list[dict]:
    """Derive Parameter->Interface PARAM_LINK pairs from wire adjacency.

    The envelope carries no direct Parameter<->Interface reference -- for each
    wire, if one endpoint's node id is a member of a Parameter and the other
    endpoint's node id is a member of an Interface (in either direction), emit
    one {paramCgId, interfaceCgId} link row. Deduplicated.
    """
    param_by_member: dict[str, str] = {}
    for row in parameter_rows:
        for member_id in row.get("memberIds") or []:
            param_by_member[member_id] = row["cgId"]

    iface_by_member: dict[str, str] = {}
    for row in interface_rows:
        for member_id in row.get("memberIds") or []:
            iface_by_member[member_id] = row["cgId"]

    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    for wire in wires:
        from_node = wire.get("fromNode")
        to_node = wire.get("toNode")
        pairs = (
            (param_by_member.get(from_node), iface_by_member.get(to_node)),
            (param_by_member.get(to_node), iface_by_member.get(from_node)),
        )
        for param_cg_id, iface_cg_id in pairs:
            if param_cg_id and iface_cg_id and (param_cg_id, iface_cg_id) not in seen:
                seen.add((param_cg_id, iface_cg_id))
                links.append({"paramCgId": param_cg_id, "interfaceCgId": iface_cg_id})

    return links


# ── Cypher writers (each op= tag lets duck-typed test sessions dispatch) ──


def _publish_object(tx: Any, params: dict) -> None:
    obj = params["object"]
    tx.run(
        """
        MERGE (o:Object {cgId: $cgId, definitionId: $definitionId, project: $project})
        SET o.objectName = $objectName,
            o.classIri = $classIri,
            o.dgId = $dgId,
            o.source = $source,
            o.definitionId = $definitionId,
            o.fileName = $fileName,
            o.publishedAt = $publishedAt,
            o.graph = 'Computgraph',
            o.project = $project
        SET o.provider = $provider,
            o.model = $model,
            o.confidence = $confidence
        WITH o
        FOREACH (_ IN CASE WHEN $classIri IS NOT NULL THEN [1] ELSE [] END |
          MERGE (c:Class {iri: $classIri})
          MERGE (o)-[:REFERS_TO]->(c)
        )
        // op=PUBLISH_OBJECT
        """,
        {
            "cgId": obj["cgId"],
            "objectName": obj["objectName"],
            "classIri": obj["classIri"],
            "dgId": obj["dgId"],
            "source": obj["source"],
            "definitionId": params["definitionId"],
            "fileName": params["fileName"],
            "publishedAt": params["publishedAt"],
            "project": params["project"],
            "provider": obj["provider"],
            "model": obj["model"],
            "confidence": obj["confidence"],
        },
    )


def _publish_behavior(tx: Any, params: dict) -> None:
    tx.run(
        """
        MERGE (b:Behavior {definitionId: $definitionId, project: $project})
        SET b.graph = 'Computgraph',
            b.project = $project,
            b.definitionId = $definitionId,
            b.publishedAt = $publishedAt
        WITH b
        MATCH (o:Object {cgId: $objectCgId, definitionId: $definitionId, project: $project})
        MERGE (o)-[:HAS_BEHAVIOR]->(b)
        // op=PUBLISH_BEHAVIOR
        """,
        {
            "definitionId": params["definitionId"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
            "objectCgId": params["object"]["cgId"],
        },
    )


def _publish_algorithms(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MERGE (a:Algorithm {algIndex: row.index, definitionId: $definitionId, project: $project})
          SET a.algorithmName = row.name,
              a.contextJson = row.contextJson,
              a.graph = 'Computgraph',
              a.project = $project,
              a.definitionId = $definitionId,
              a.publishedAt = $publishedAt
          WITH a
          MATCH (b:Behavior {definitionId: $definitionId, project: $project})
          MERGE (b)-[:HAS_ALGORITHM]->(a)
        // op=PUBLISH_ALGORITHM
        """,
        {
            "rows": params["algorithmRows"],
            "definitionId": params["definitionId"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
        },
    )


def _publish_procedures(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MERGE (pr:Procedure {cgId: row.cgId, definitionId: $definitionId, project: $project})
          SET pr.procedureName = row.name,
              pr.procIndex = row.index,
              pr.dgId = row.dgId,
              pr.source = row.source,
              pr.provider = row.provider,
              pr.model = row.model,
              pr.confidence = row.confidence,
              pr.definitionId = $definitionId,
              pr.fileName = $fileName,
              pr.publishedAt = $publishedAt,
              pr.graph = 'Computgraph',
              pr.project = $project
          WITH pr, row
          MATCH (a:Algorithm {algIndex: row.algIndex, definitionId: $definitionId, project: $project})
          MERGE (a)-[:HAS_PROCEDURE]->(pr)
        // op=PUBLISH_PROCEDURE
        """,
        {
            "rows": params["procedureRows"],
            "definitionId": params["definitionId"],
            "fileName": params["fileName"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
        },
    )


def _publish_patterns(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MERGE (pn:Pattern {cgId: row.cgId, definitionId: $definitionId, project: $project})
          SET pn.patternName = row.name,
              pn.dgId = row.dgId,
              pn.source = row.source,
              pn.provider = row.provider,
              pn.model = row.model,
              pn.confidence = row.confidence,
              pn.definitionId = $definitionId,
              pn.fileName = $fileName,
              pn.publishedAt = $publishedAt,
              pn.graph = 'Computgraph',
              pn.project = $project
          WITH pn, row
          MATCH (pr:Procedure {cgId: row.procCgId, definitionId: $definitionId, project: $project})
          MERGE (pr)-[:HAS_PATTERN]->(pn)
        // op=PUBLISH_PATTERN
        """,
        {
            "rows": params["patternRows"],
            "definitionId": params["definitionId"],
            "fileName": params["fileName"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
        },
    )


def _publish_pattern_hosts(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MATCH (child:Pattern {cgId: row.childCgId, definitionId: $definitionId, project: $project})
          MATCH (host:Pattern {cgId: row.hostCgId, definitionId: $definitionId, project: $project})
          MERGE (child)-[:PATTERN_HOST_TO]->(host)
        // op=PUBLISH_PATTERN_HOST
        """,
        {
            "rows": params["patternHostRows"],
            "definitionId": params["definitionId"],
            "project": params["project"],
        },
    )


def _publish_parameters(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MERGE (p:Parameter {cgId: row.cgId, definitionId: $definitionId, project: $project})
          SET p.parameterName = row.name,
              p.paramKind = row.kind,
              p.dataType = row.dataType,
              p.domainMin = row.domainMin,
              p.domainMax = row.domainMax,
              p.domainStep = row.domainStep,
              p.dgId = row.dgId,
              p.source = row.source,
              p.provider = row.provider,
              p.model = row.model,
              p.confidence = row.confidence,
              p.definitionId = $definitionId,
              p.fileName = $fileName,
              p.publishedAt = $publishedAt,
              p.graph = 'Computgraph',
              p.project = $project
          WITH p, row
          MATCH (pr:Procedure {cgId: row.procCgId, definitionId: $definitionId, project: $project})
          MERGE (pr)-[:HAS_PARAMETER]->(p)
        // op=PUBLISH_PARAMETER
        """,
        {
            "rows": params["parameterRows"],
            "definitionId": params["definitionId"],
            "fileName": params["fileName"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
        },
    )


def _publish_interfaces(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MERGE (i:Interface {cgId: row.cgId, definitionId: $definitionId, project: $project})
          SET i.interfaceName = row.name,
              i.ifaceType = row.ifaceType,
              i.dgId = row.dgId,
              i.source = row.source,
              i.provider = row.provider,
              i.model = row.model,
              i.confidence = row.confidence,
              i.definitionId = $definitionId,
              i.fileName = $fileName,
              i.publishedAt = $publishedAt,
              i.graph = 'Computgraph',
              i.project = $project
          WITH i, row
          MATCH (pr:Procedure {cgId: row.procCgId, definitionId: $definitionId, project: $project})
          MERGE (pr)-[:HAS_INTERFACE]->(i)
        // op=PUBLISH_INTERFACE
        """,
        {
            "rows": params["interfaceRows"],
            "definitionId": params["definitionId"],
            "fileName": params["fileName"],
            "project": params["project"],
            "publishedAt": params["publishedAt"],
        },
    )


def _publish_param_links(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MATCH (p:Parameter {cgId: row.paramCgId, definitionId: $definitionId, project: $project})
          MATCH (i:Interface {cgId: row.interfaceCgId, definitionId: $definitionId, project: $project})
          MERGE (p)-[:PARAM_LINK]->(i)
        // op=PUBLISH_PARAM_LINK
        """,
        {
            "rows": params["paramLinkRows"],
            "definitionId": params["definitionId"],
            "project": params["project"],
        },
    )


def _find_stale_entities(session: Any, project: str, definition_id: str, current_cg_ids: list[str]) -> list[str]:
    """Read-only report of previously published cgIds for this definition+project
    that are absent from the current publish payload. NO deletion Cypher -- v9.0
    reports stale entities, it never auto-deletes them (CONTEXT.md decision #2).
    """
    result = session.run(
        """
        MATCH (n {definitionId: $definitionId, project: $project, graph: 'Computgraph'})
        WHERE n.cgId IS NOT NULL AND NOT n.cgId IN $currentCgIds
        RETURN DISTINCT n.cgId AS cgId
        // op=PUBLISH_STALE_DIFF
        """,
        {
            "definitionId": definition_id,
            "project": project,
            "currentCgIds": current_cg_ids,
        },
    )
    return [record["cgId"] for record in result]

"""Computgraph structural checks -- deterministic, reproducible, LLM-free
structural validation over the published Computgraph (Phase 37: SVAL-01).

Every check function accepts an injected Neo4j session and issues exactly one
parameterized, read-only Cypher statement, scoped by BOTH ``project`` and
``definitionId`` -- the caller (a route handler) owns the session, mirroring
``computgraph_publish.py``'s "caller owns the session" discipline. No model
or provider of any kind is ever consulted from this module: every finding
this module produces is a pure graph fact, derived either from a Cypher
pattern match or from parsing a JSON property already sitting on a published
node. A separate, dedicated code path (the consult endpoint) is the only
place in this service that ever calls out to a generative model -- that call
sequence does not exist anywhere in this file.

Security: every ``session.run`` call receives its parameters as a bound dict
(``{"project": project, "definitionId": definition_id, ...}``) -- entity
names, ids and provenance strings are NEVER f-string / ``%`` / ``.format``
interpolated into query text (T-37-01: Cypher injection). Scoping every
match by both ``project`` and ``definitionId`` is also the cross-project
isolation guarantee (T-37-03): a caller can never see another project's or
another definition's findings.
"""

from __future__ import annotations

import json
from typing import Any

SEVERITY_VIOLATION = "violation"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

# The seven checkId strings, in the order run_structural_checks() emits them.
CHECK_IDS = (
    "orphan_pattern",
    "procedure_without_interface",
    "dangling_param_link",
    "algorithm_without_procedure",
    "parameter_without_datatype",
    "object_without_behavior",
    "annotation_convention",
)


def convention_name_from_cg_id(cg_id: str) -> str:
    """Return the last colon-separated segment of a cgId (the token an
    architect actually typed on canvas, e.g. ``11_Var_HTotal``), or an empty
    string for a falsy input. The published display-name properties
    (``parameterName`` etc.) carry only the bare name, never this token --
    this derivation is the only way a finding can reference an entity the
    way the architect labelled it.
    """
    if not cg_id:
        return ""
    return cg_id.rsplit(":", 1)[-1]


def _entity(label: str, cg_id: str, name: str) -> dict[str, Any]:
    """The normative entity dict every finding's ``entities[]`` item uses."""
    return {
        "label": label,
        "cgId": cg_id,
        "name": name,
        "conventionName": convention_name_from_cg_id(cg_id),
    }


def _finding(
    check_id: str,
    severity: str,
    what: str,
    where: str,
    how_to_fix: str,
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    """The normative finding dict. Composes ``message`` in the same
    What + Where: ... How to fix: ... structure the existing
    ``validate_cypher`` violation messages already use (``dg_context.py``).
    Every check calls this -- no check builds a message string inline.
    """
    message = f"{what} Where: {where}. How to fix: {how_to_fix}"
    return {
        "checkId": check_id,
        "severity": severity,
        "message": message,
        "entities": entities,
    }


def _sorted_by_first_cg_id(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: f["entities"][0]["cgId"])


# ── Graph-shape checks (five real, two defensive) ──


def check_orphan_patterns(session: Any, project: str, definition_id: str) -> list[dict]:
    """Pattern nodes that no Procedure's HAS_PATTERN relationship points at."""
    result = session.run(
        """
        MATCH (pn:Pattern {project: $project, definitionId: $definitionId})
        WHERE NOT ()-[:HAS_PATTERN]->(pn)
        RETURN pn.cgId AS cgId, pn.patternName AS name
        ORDER BY pn.cgId
        // op=CHECK_ORPHAN_PATTERN
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = [
        _finding(
            "orphan_pattern",
            SEVERITY_VIOLATION,
            f"Pattern '{row['name']}' has no owning Procedure.",
            f"Pattern cgId={row['cgId']}",
            "re-tag this Pattern under a Procedure group and re-publish.",
            [_entity("Pattern", row["cgId"], row["name"])],
        )
        for row in result
    ]
    return _sorted_by_first_cg_id(findings)


def check_procedures_without_interface(session: Any, project: str, definition_id: str) -> list[dict]:
    """Procedure nodes with no outgoing HAS_INTERFACE relationship. Carries
    both cgId and procedureName so the exact procedure is nameable (SC1)."""
    result = session.run(
        """
        MATCH (pr:Procedure {project: $project, definitionId: $definitionId})
        WHERE NOT (pr)-[:HAS_INTERFACE]->()
        RETURN pr.cgId AS cgId, pr.procedureName AS name
        ORDER BY pr.cgId
        // op=CHECK_PROCEDURE_WITHOUT_INTERFACE
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = [
        _finding(
            "procedure_without_interface",
            SEVERITY_VIOLATION,
            f"Procedure '{row['name']}' has no Interface.",
            f"Procedure cgId={row['cgId']}",
            "tag at least one IntF_ group under this Procedure and re-publish.",
            [_entity("Procedure", row["cgId"], row["name"])],
        )
        for row in result
    ]
    return _sorted_by_first_cg_id(findings)


def check_dangling_param_links(session: Any, project: str, definition_id: str) -> list[dict]:
    """A Parameter PARAM_LINKed to an Interface whose owning Procedure is not
    the Parameter's own owning Procedure -- the wire crosses a Procedure
    boundary. Every matched node is scoped by project and definitionId."""
    result = session.run(
        """
        MATCH (p:Parameter {project: $project, definitionId: $definitionId})
              -[:PARAM_LINK]->(i:Interface {project: $project, definitionId: $definitionId})
        MATCH (prP:Procedure {project: $project, definitionId: $definitionId})-[:HAS_PARAMETER]->(p)
        MATCH (prI:Procedure {project: $project, definitionId: $definitionId})-[:HAS_INTERFACE]->(i)
        WHERE prP <> prI
        RETURN p.cgId AS paramCgId, p.parameterName AS paramName,
               i.cgId AS interfaceCgId, i.interfaceName AS interfaceName
        ORDER BY p.cgId, i.cgId
        // op=CHECK_DANGLING_PARAM_LINK
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = [
        _finding(
            "dangling_param_link",
            SEVERITY_VIOLATION,
            f"Parameter '{row['paramName']}' links to Interface '{row['interfaceName']}' "
            "outside its own Procedure.",
            f"Parameter cgId={row['paramCgId']}, Interface cgId={row['interfaceCgId']}",
            "move the component into the owning Procedure group or remove the link, then re-publish.",
            [
                _entity("Parameter", row["paramCgId"], row["paramName"]),
                _entity("Interface", row["interfaceCgId"], row["interfaceName"]),
            ],
        )
        for row in result
    ]
    return _sorted_by_first_cg_id(findings)


def check_algorithms_without_procedure(session: Any, project: str, definition_id: str) -> list[dict]:
    """Algorithm nodes with no outgoing HAS_PROCEDURE relationship. Algorithm
    nodes carry no cgId in the published contract (Phase 36) -- the algIndex
    is rendered into the entity's `name` field and `cgId` is deliberately
    left empty, not forgotten."""
    result = session.run(
        """
        MATCH (a:Algorithm {project: $project, definitionId: $definitionId})
        WHERE NOT (a)-[:HAS_PROCEDURE]->()
        RETURN a.algIndex AS algIndex, a.algorithmName AS name
        ORDER BY a.algIndex
        // op=CHECK_ALGORITHM_WITHOUT_PROCEDURE
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = []
    for row in result:
        display_name = row["name"] or str(row["algIndex"])
        findings.append(
            _finding(
                "algorithm_without_procedure",
                SEVERITY_VIOLATION,
                f"Algorithm '{display_name}' has no Procedure.",
                f"Algorithm algIndex={row['algIndex']}",
                "tag at least one NN_Proc group under this Algorithm and re-publish.",
                [_entity("Algorithm", "", display_name)],
            )
        )
    return _sorted_by_first_cg_id(findings)


def check_parameters_without_datatype(session: Any, project: str, definition_id: str) -> list[dict]:
    """Parameter nodes whose dataType property is null or an empty string.

    This condition is currently unreachable through the publish path:
    ``computgraph_publish._build_publish_params`` raises before any write if
    a parameter's dataType is missing or unrecognized. The check is retained
    deliberately as a guard against a future publish-path change or a graph
    mutated outside that path -- not dead code.
    """
    result = session.run(
        """
        MATCH (p:Parameter {project: $project, definitionId: $definitionId})
        WHERE p.dataType IS NULL OR p.dataType = ''
        RETURN p.cgId AS cgId, p.parameterName AS name
        ORDER BY p.cgId
        // op=CHECK_PARAMETER_WITHOUT_DATATYPE
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = [
        _finding(
            "parameter_without_datatype",
            SEVERITY_VIOLATION,
            f"Parameter '{row['name']}' has no dataType.",
            f"Parameter cgId={row['cgId']}",
            "set a recognized dataType (Float, Integer, Text, Boolean or Geometry) and re-publish.",
            [_entity("Parameter", row["cgId"], row["name"])],
        )
        for row in result
    ]
    return _sorted_by_first_cg_id(findings)


def check_objects_without_behavior(session: Any, project: str, definition_id: str) -> list[dict]:
    """Object nodes with no outgoing HAS_BEHAVIOR relationship.

    Same deliberate-guard rationale as check_parameters_without_datatype:
    ``computgraph_publish._publish_behavior`` always runs whenever an object
    is published, so this is currently unreachable -- retained as cheap
    defensive insurance against a future refactor.
    """
    result = session.run(
        """
        MATCH (o:Object {project: $project, definitionId: $definitionId})
        WHERE NOT (o)-[:HAS_BEHAVIOR]->()
        RETURN o.cgId AS cgId, o.objectName AS name
        ORDER BY o.cgId
        // op=CHECK_OBJECT_WITHOUT_BEHAVIOR
        """,
        {"project": project, "definitionId": definition_id},
    )
    findings = [
        _finding(
            "object_without_behavior",
            SEVERITY_VIOLATION,
            f"Object '{row['name']}' has no Behavior.",
            f"Object cgId={row['cgId']}",
            "re-publish this definition so its Behavior is synthesized.",
            [_entity("Object", row["cgId"], row["name"])],
        )
        for row in result
    ]
    return _sorted_by_first_cg_id(findings)


# ── Annotation-convention check (JSON-envelope, not a graph pattern) ──


def parse_context_warnings(context_json: str | None) -> list[str]:
    """Pure function: parse an Algorithm.contextJson string property and
    return its top-level `warnings` array as a list of strings.

    Total function -- tolerates every degenerate input without raising: a
    null/empty string, invalid JSON, a JSON document that isn't an object, or
    a `warnings` key that is absent or not a list all return `[]`. A list
    containing non-string members yields only the string members, order
    preserved. No Neo4j dependency at all.
    """
    if not context_json:
        return []
    try:
        payload = json.loads(context_json)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        return []
    return [warning for warning in warnings if isinstance(warning, str)]


# This check reads a JSON property instead of matching a graph pattern
# because the canvas parser's tolerated-variant normalization is resolved
# during canvas parsing, before the envelope is even confirmed -- only the
# parsed kind enum reaches the published Parameter node. A Cypher pattern
# looking for the raw annotation string would never fire against any real
# data; the only surviving record of a normalization event is the top-level
# `warnings` array, preserved verbatim inside Algorithm.contextJson.
def check_annotation_conventions(session: Any, project: str, definition_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (a:Algorithm {project: $project, definitionId: $definitionId})
        RETURN a.algIndex AS algIndex, a.algorithmName AS algorithmName, a.contextJson AS contextJson
        ORDER BY a.algIndex
        // op=CHECK_ALGORITHM_CONTEXT_JSON
        """,
        {"project": project, "definitionId": definition_id},
    )
    rows: list[tuple[int, str, dict[str, Any]]] = []
    for row in result:
        alg_index = row["algIndex"]
        alg_name = row["algorithmName"] or str(alg_index)
        for warning in parse_context_warnings(row["contextJson"]):
            finding = _finding(
                "annotation_convention",
                SEVERITY_INFO,
                warning,
                f"Algorithm algIndex={alg_index}, name='{alg_name}'",
                "correct the annotation tag on canvas and re-publish if the normalization was not intended.",
                [_entity("Algorithm", "", alg_name)],
            )
            rows.append((alg_index, warning, finding))
    rows.sort(key=lambda entry: (entry[0], entry[1]))
    return [finding for _, _, finding in rows]


# ── Aggregator ──


def run_structural_checks(session: Any, project: str, definition_id: str) -> list[dict]:
    """Run all seven SVAL-01 checks and return their combined findings in one
    deterministically sorted list.

    Guarantee: two calls against an unchanged graph return byte-identical
    lists -- `findings` are sorted by (checkId, first entity's cgId,
    message). This function performs reads only; it writes nothing.
    """
    findings: list[dict[str, Any]] = []
    findings.extend(check_orphan_patterns(session, project, definition_id))
    findings.extend(check_procedures_without_interface(session, project, definition_id))
    findings.extend(check_dangling_param_links(session, project, definition_id))
    findings.extend(check_algorithms_without_procedure(session, project, definition_id))
    findings.extend(check_parameters_without_datatype(session, project, definition_id))
    findings.extend(check_objects_without_behavior(session, project, definition_id))
    findings.extend(check_annotation_conventions(session, project, definition_id))

    def _sort_key(finding: dict[str, Any]) -> tuple[str, str, str]:
        entities = finding.get("entities") or []
        first_cg_id = entities[0]["cgId"] if entities else ""
        return (finding["checkId"], first_cg_id, finding["message"])

    return sorted(findings, key=_sort_key)

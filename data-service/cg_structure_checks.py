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
import os
from datetime import datetime, timezone
from pathlib import Path
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


def _compose_message(what: str, where: str, how_to_fix: str) -> str:
    """The shared What + Where + How-to-fix composer. Every SVAL-01 finding
    and every SVAL-02 rule-mapping result message is built through this
    function -- no message is ever composed inline."""
    return f"{what} Where: {where}. How to fix: {how_to_fix}"


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
    return {
        "checkId": check_id,
        "severity": severity,
        "message": _compose_message(what, where, how_to_fix),
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


# ── Structure-rule mapping artifact (SVAL-02): declarative loader ──
#
# llm/structure_rules.json maps a Metagraph Rule_Id onto a structural
# requirement over the published Computgraph. Rule_Id is joined as a soft
# foreign key only -- SWRL semantics never leak into this module (T-37-10);
# see spec/RULE-PARTITION-POLICY.md's Computgraph Structural Checks section.

STRUCTURE_RULES_FILE = (
    Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    / "llm"
    / "structure_rules.json"
)

# The four operation names a mapping entry's "operation" field may name.
STRUCTURE_RULE_OPERATIONS: frozenset[str] = frozenset(
    {"requiresProcedure", "requiresParameter", "requiresInterface", "forbidsOrphan"}
)

# Parameter keys that would express a numeric value comparison rather than a
# structural presence/kind/type/relationship check. A mapping using any of
# these keys is expressing SWRL scope (Pitfall 3, 37-RESEARCH.md) and must
# never be evaluated by this module.
_FORBIDDEN_PARAM_KEYS: frozenset[str] = frozenset(
    {
        "min",
        "max",
        "greaterThan",
        "lessThan",
        "greaterThanOrEqual",
        "lessThanOrEqual",
        "threshold",
        "value",
    }
)

# Computgraph entity labels a forbidsOrphan mapping's "label" param may name.
# Restricting to this fixed allow-list keeps an invalid label from ever
# reaching Cypher (T-37-01) -- Object is excluded because it is the
# Computgraph root and structurally has no owner.
_COMPUTGRAPH_ORPHAN_LABELS: frozenset[str] = frozenset(
    {"Behavior", "Algorithm", "Procedure", "Pattern", "Parameter", "Interface"}
)

_EMPTY_STRUCTURE_RULES: dict[str, Any] = {"version": 0, "mappings": []}


def load_structure_rules() -> dict[str, Any]:
    """Read the structure-rule mapping artifact from STRUCTURE_RULES_FILE.

    Mirrors dg_context.load_cypher_catalog() exactly -- defensive by design,
    never raises. A missing file, an unreadable file, invalid JSON, or a
    payload that is not an object whose "mappings" key is a list all
    degrade to the empty envelope {"version": 0, "mappings": []}.
    """
    if not STRUCTURE_RULES_FILE.exists():
        return dict(_EMPTY_STRUCTURE_RULES)
    try:
        payload = json.loads(STRUCTURE_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_EMPTY_STRUCTURE_RULES)
    if not isinstance(payload, dict) or not isinstance(payload.get("mappings"), list):
        return dict(_EMPTY_STRUCTURE_RULES)
    return payload


def _mapping_rejection_reason(entry: Any) -> str | None:
    """Return None when `entry` is a safe-to-evaluate mapping, else a short
    human-readable reason it was rejected. Shared by valid_structure_mappings
    (silent filter) and evaluate_rule_mappings (surfaced in the report)."""
    if not isinstance(entry, dict):
        return "mapping entry is not an object"
    rule_id = entry.get("ruleId")
    if not isinstance(rule_id, str) or not rule_id:
        return "ruleId is missing or not a non-empty string"
    operation = entry.get("operation")
    if operation not in STRUCTURE_RULE_OPERATIONS:
        return f"operation {operation!r} is not one of {sorted(STRUCTURE_RULE_OPERATIONS)}"
    params = entry.get("params")
    if params is not None:
        if not isinstance(params, dict):
            return "params must be an object"
        forbidden = sorted(_FORBIDDEN_PARAM_KEYS & set(params))
        if forbidden:
            return (
                f"params contains value-threshold key(s) {forbidden} -- "
                "this expresses SWRL scope, not a structural check"
            )
    # Require the operation-specific mandatory param -- without it the
    # evaluator falls back to a "" default that makes the Cypher template
    # (CONTAINS '' / $label IN labels(n) with label='') silently
    # always-pass instead of actually checking anything (WR-01).
    if operation in ("requiresProcedure", "requiresParameter"):
        name_pattern = params.get("namePattern") if isinstance(params, dict) else None
        if not isinstance(name_pattern, str) or not name_pattern.strip():
            return f"operation {operation!r} requires a non-empty params.namePattern"
    if operation == "forbidsOrphan":
        label = params.get("label") if isinstance(params, dict) else None
        if not label:
            return "operation 'forbidsOrphan' requires params.label"
        if label not in _COMPUTGRAPH_ORPHAN_LABELS:
            return f"label {label!r} is not a recognized Computgraph entity label"
    return None


def valid_structure_mappings(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Filter a loaded structure-rules payload down to the mappings safe to
    evaluate. Deterministic, preserves input order. Rejection is silent at
    this layer -- evaluate_rule_mappings() surfaces the reason."""
    if payload is None:
        payload = load_structure_rules()
    mappings = payload.get("mappings") if isinstance(payload, dict) else None
    if not isinstance(mappings, list):
        return []
    return [entry for entry in mappings if _mapping_rejection_reason(entry) is None]


def structure_rule_ids() -> tuple[str, ...]:
    """Derived tuple of accepted ruleIds from the currently-loaded structure
    rules file (recomputed from disk on each call)."""
    return tuple(entry["ruleId"] for entry in valid_structure_mappings())


# Derived ruleId index, computed once at import time from the real artifact
# on disk (mirrors dg_context.py's CYPHER_SHAPE_IDS module-constant pattern).
# Call structure_rule_ids() directly if the file's contents might have
# changed since import (e.g. in tests).
STRUCTURE_RULE_IDS: tuple[str, ...] = structure_rule_ids()


# ── Structure-rule mapping artifact (SVAL-02): operation templates + evaluator ──
#
# Each operation compiles to exactly one static, parameterized Cypher
# template, keyed by the operation name and looked up in this fixed dict --
# never built or edited at runtime, never string-interpolated (T-37-01). A
# mapping entry supplies bound parameter values only.

_OPERATION_TEMPLATES: dict[str, str] = {
    "requiresProcedure": """
        MATCH (pr:Procedure {project: $project, definitionId: $definitionId})
        WHERE pr.procedureName CONTAINS $namePattern
        RETURN pr.cgId AS cgId, pr.procedureName AS name
        ORDER BY pr.cgId
        // op=RULE_REQUIRES_PROCEDURE
    """,
    "requiresParameter": """
        MATCH (p:Parameter {project: $project, definitionId: $definitionId})
        WHERE (p.parameterName CONTAINS $namePattern OR p.cgId CONTAINS $namePattern)
          AND ($paramKind IS NULL OR p.paramKind = $paramKind)
          AND ($dataType IS NULL OR p.dataType = $dataType)
        RETURN p.cgId AS cgId, p.parameterName AS name
        ORDER BY p.cgId
        // op=RULE_REQUIRES_PARAMETER
    """,
    # For-all requirement, unlike the two exists-style templates above and
    # below: this passes only when EVERY scoped Procedure has a match. Do
    # not "simplify" this into an exists check -- a single matching
    # Interface anywhere in the definition must not make the rule pass.
    "requiresInterface": """
        MATCH (pr:Procedure {project: $project, definitionId: $definitionId})
        OPTIONAL MATCH (pr)-[:HAS_INTERFACE]->(i:Interface {project: $project, definitionId: $definitionId})
          WHERE $ifaceType IS NULL OR i.ifaceType = $ifaceType
        WITH pr, collect(DISTINCT i) AS matched
        RETURN pr.cgId AS cgId, pr.procedureName AS name, size(matched) > 0 AS hasMatch
        ORDER BY pr.cgId
        // op=RULE_REQUIRES_INTERFACE
    """,
    "forbidsOrphan": """
        MATCH (n {project: $project, definitionId: $definitionId})
        WHERE $label IN labels(n)
          AND NOT ()-[:HAS_BEHAVIOR|HAS_ALGORITHM|HAS_PROCEDURE|HAS_PATTERN|HAS_PARAMETER|HAS_INTERFACE]->(n)
        RETURN n.cgId AS cgId,
               coalesce(n.patternName, n.procedureName, n.parameterName, n.interfaceName,
                        n.algorithmName, n.objectName, '') AS name
        ORDER BY n.cgId
        // op=RULE_FORBIDS_ORPHAN
    """,
}


def _offending_algorithms(session: Any, project: str, definition_id: str) -> list[dict[str, Any]]:
    """Every Algorithm in scope, rendered as SVAL-01's Algorithm entity shape
    (cgId="" -- Algorithm carries none in the Phase 36 contract). Used as the
    offendingEntities for an exists-style rule (requiresProcedure /
    requiresParameter) that found no match anywhere in the definitionId."""
    result = session.run(
        """
        MATCH (a:Algorithm {project: $project, definitionId: $definitionId})
        RETURN a.algIndex AS algIndex, a.algorithmName AS name
        ORDER BY a.algIndex
        // op=RULE_SCOPE_ALGORITHMS
        """,
        {"project": project, "definitionId": definition_id},
    )
    return [_entity("Algorithm", "", (row["name"] or str(row["algIndex"]))) for row in result]


def _eval_requires_procedure(
    session: Any, project: str, definition_id: str, params: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], str]:
    name_pattern = params.get("namePattern", "")
    result = session.run(
        _OPERATION_TEMPLATES["requiresProcedure"],
        {"project": project, "definitionId": definition_id, "namePattern": name_pattern},
    )
    satisfying = [_entity("Procedure", row["cgId"], row["name"]) for row in result]
    passed = len(satisfying) > 0
    what = (
        f"A Procedure matching '{name_pattern}' was found."
        if passed
        else f"No Procedure matching '{name_pattern}' was found."
    )
    where = f"Procedures scoped to definitionId={definition_id}"
    how_to_fix = (
        "no action needed."
        if passed
        else f"tag a Procedure whose name contains '{name_pattern}' and re-publish."
    )
    offending = [] if passed else _offending_algorithms(session, project, definition_id)
    return passed, satisfying, offending, _compose_message(what, where, how_to_fix)


def _eval_requires_parameter(
    session: Any, project: str, definition_id: str, params: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], str]:
    name_pattern = params.get("namePattern", "")
    result = session.run(
        _OPERATION_TEMPLATES["requiresParameter"],
        {
            "project": project,
            "definitionId": definition_id,
            "namePattern": name_pattern,
            "paramKind": params.get("paramKind"),
            "dataType": params.get("dataType"),
        },
    )
    satisfying = [_entity("Parameter", row["cgId"], row["name"]) for row in result]
    passed = len(satisfying) > 0
    what = (
        f"A Parameter matching '{name_pattern}' was found."
        if passed
        else f"No Parameter matching '{name_pattern}' was found."
    )
    where = f"Parameters scoped to definitionId={definition_id}"
    how_to_fix = (
        "no action needed."
        if passed
        else (
            f"publish a Parameter whose name or convention token contains '{name_pattern}' "
            "with the required kind and dataType, and re-publish."
        )
    )
    offending = [] if passed else _offending_algorithms(session, project, definition_id)
    return passed, satisfying, offending, _compose_message(what, where, how_to_fix)


def _eval_requires_interface(
    session: Any, project: str, definition_id: str, params: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], str]:
    result = session.run(
        _OPERATION_TEMPLATES["requiresInterface"],
        {"project": project, "definitionId": definition_id, "ifaceType": params.get("ifaceType")},
    )
    satisfying: list[dict[str, Any]] = []
    offending: list[dict[str, Any]] = []
    for row in result:
        entity = _entity("Procedure", row["cgId"], row["name"])
        (satisfying if row["hasMatch"] else offending).append(entity)
    passed = len(offending) == 0
    what = (
        "Every Procedure has at least one matching Interface."
        if passed
        else "At least one Procedure has no matching Interface."
    )
    where = f"Procedures scoped to definitionId={definition_id}"
    how_to_fix = (
        "no action needed."
        if passed
        else "tag an IntF_ group of the required ifaceType under each offending Procedure and re-publish."
    )
    return passed, satisfying, offending, _compose_message(what, where, how_to_fix)


def _eval_forbids_orphan(
    session: Any, project: str, definition_id: str, params: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], str]:
    label = params.get("label", "")
    result = session.run(
        _OPERATION_TEMPLATES["forbidsOrphan"],
        {"project": project, "definitionId": definition_id, "label": label},
    )
    offending = [_entity(label, row["cgId"], row["name"]) for row in result]
    passed = len(offending) == 0
    what = (
        f"No orphan {label} nodes were found."
        if passed
        else f"{len(offending)} orphan {label} node(s) were found."
    )
    where = f"{label} nodes scoped to definitionId={definition_id}"
    how_to_fix = (
        "no action needed."
        if passed
        else f"re-tag each offending {label} under its owning entity and re-publish."
    )
    return passed, [], offending, _compose_message(what, where, how_to_fix)


_OPERATION_EVALUATORS = {
    "requiresProcedure": _eval_requires_procedure,
    "requiresParameter": _eval_requires_parameter,
    "requiresInterface": _eval_requires_interface,
    "forbidsOrphan": _eval_forbids_orphan,
}


def _rule_exists_in_metagraph(session: Any, project: str, rule_id: str) -> bool:
    """Soft foreign-key probe: a missing Rule node is NOT an error and does
    not skip evaluation -- the structural requirement is still evaluated and
    reported, with ruleExists=False."""
    result = session.run(
        """
        MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
        RETURN count(r) > 0 AS ruleExists
        // op=RULE_EXISTS_METAGRAPH
        """,
        {"ruleId": rule_id, "project": project},
    )
    row = result.single()
    return bool(row["ruleExists"]) if row else False


def _rejected_mapping_result(entry: Any) -> dict[str, Any]:
    """A distinct, obvious signal for a mapping that failed
    valid_structure_mappings' checks -- visible in the report rather than
    silently absent, but never mistaken for a genuine structural failure."""
    rule_id = entry.get("ruleId") if isinstance(entry, dict) else None
    operation = entry.get("operation") if isinstance(entry, dict) else None
    reason = _mapping_rejection_reason(entry) or "mapping entry failed structural validation"
    message = _compose_message(
        "INVALID MAPPING -- not evaluated.",
        "structure_rules.json mapping entry",
        f"{reason}.",
    )
    return {
        "ruleId": rule_id if isinstance(rule_id, str) else "",
        "operation": operation if isinstance(operation, str) else "",
        "passed": False,
        "ruleExists": False,
        "message": message,
        "satisfyingEntities": [],
        "offendingEntities": [],
    }


def evaluate_rule_mappings(
    session: Any, project: str, definition_id: str, payload: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Evaluate every mapping in the structure-rules artifact against the
    published Computgraph, returning one pass/fail report per mapping.

    Reads only -- writes nothing, consults no model. For each mapping that
    passes valid_structure_mappings(), this runs one Metagraph existence
    probe (a missing Rule node sets ruleExists=False but never skips
    evaluation -- Rule_Id is a soft foreign key) plus one run of the
    operation's static template. A mapping that fails valid_structure_mappings
    is reported as passed=False with an explanatory message instead of being
    silently dropped. Results are sorted by (ruleId, operation) so repeated
    calls are byte-identical.
    """
    if payload is None:
        payload = load_structure_rules()
    raw_mappings = payload.get("mappings") if isinstance(payload, dict) else None
    if not isinstance(raw_mappings, list):
        raw_mappings = []

    results: list[dict[str, Any]] = []
    for entry in raw_mappings:
        if _mapping_rejection_reason(entry) is not None:
            results.append(_rejected_mapping_result(entry))
            continue
        rule_id = entry["ruleId"]
        operation = entry["operation"]
        params = entry.get("params") or {}
        rule_exists = _rule_exists_in_metagraph(session, project, rule_id)
        evaluator = _OPERATION_EVALUATORS[operation]
        passed, satisfying, offending, message = evaluator(session, project, definition_id, params)
        results.append(
            {
                "ruleId": rule_id,
                "operation": operation,
                "passed": passed,
                "ruleExists": rule_exists,
                "message": message,
                "satisfyingEntities": satisfying,
                "offendingEntities": offending,
            }
        )

    return sorted(results, key=lambda r: (r["ruleId"], r["operation"]))


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


# ── Report surface (Phase 37 Plan 05): definition resolution, publishedAt,
# and the POST /computgraph/validate report builder ──
#
# Everything below is reads only and consults no model of any kind -- this
# is the only path anything outside data-service reaches SVAL-01/SVAL-02
# through, and its determinism guarantee (see build_validation_report's
# docstring) is what the report contract test pins.


def list_definition_ids(session: Any, project: str) -> list[str]:
    """Distinct definitionId values across the project's Computgraph-scoped
    nodes, ordered ascending. One parameterized read -- mirrors
    dg_context.fetch_existing_design_states' explicit ORDER BY determinism
    discipline."""
    result = session.run(
        """
        MATCH (n {project: $project, graph: 'Computgraph'})
        WHERE n.definitionId IS NOT NULL
        RETURN DISTINCT n.definitionId AS definitionId
        ORDER BY definitionId
        // op=CHECK_DEFINITION_IDS
        """,
        {"project": project},
    )
    return [row["definitionId"] for row in result]


class DefinitionResolutionError(Exception):
    """Raised only by resolve_definition_id() when an omitted definitionId
    cannot be resolved unambiguously. `code` is the exact documented error
    code (COMPUTGRAPH_VALIDATE_NO_DEFINITION or
    COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION) the route maps onto its
    response without re-deriving it. `available` is the sorted list of the
    project's published definition ids -- empty for the no-definition case,
    every id for the ambiguous case (so the route can list them in the
    error hint)."""

    def __init__(self, message: str, code: str, available: list[str]) -> None:
        super().__init__(message)
        self.code = code
        self.available = available


def resolve_definition_id(session: Any, project: str, definition_id: str | None = None) -> str:
    """Resolve an optional definitionId to a concrete one, keeping the
    report single-shaped rather than branching between a per-definition and
    an aggregate form.

    Returns the supplied id unchanged when one was given. When none was
    given, lists the project's published definitions: exactly one means
    return it; zero raises DefinitionResolutionError with the no-definition
    code and an empty available list; more than one raises
    DefinitionResolutionError with the ambiguous-definition code and the
    sorted available list.
    """
    if definition_id:
        return definition_id
    available = list_definition_ids(session, project)
    if len(available) == 1:
        return available[0]
    if len(available) == 0:
        raise DefinitionResolutionError(
            f"No published definition found for project '{project}'.",
            "COMPUTGRAPH_VALIDATE_NO_DEFINITION",
            [],
        )
    raise DefinitionResolutionError(
        f"Multiple published definitions found for project '{project}'; specify definitionId.",
        "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION",
        available,
    )


def fetch_published_at(session: Any, project: str, definition_id: str) -> str | None:
    """Maximum publishedAt across the Computgraph nodes scoped to this
    project and definitionId, in the same ISO 8601 format
    computgraph_publish.py emits. None when nothing is published -- this is
    the staleness signal the report carries relative to the live canvas."""
    result = session.run(
        """
        MATCH (n {project: $project, definitionId: $definitionId, graph: 'Computgraph'})
        RETURN max(n.publishedAt) AS publishedAt
        // op=CHECK_PUBLISHED_AT
        """,
        {"project": project, "definitionId": definition_id},
    )
    row = result.single()
    return row["publishedAt"] if row else None


def build_validation_report(
    session: Any, project: str, definition_id: str | None = None
) -> dict[str, Any]:
    """Assemble the POST /computgraph/validate report with exactly the keys
    spec/API.md documents: project, definitionId, publishedAt, checkedAt,
    findings, ruleResults, counts.

    Resolves the definitionId (raising DefinitionResolutionError when it
    cannot be resolved unambiguously), fetches publishedAt, runs the seven
    SVAL-01 structural checks, and evaluates the SVAL-02 rule mappings.
    `checkedAt` is the current UTC time in the same ISO 8601 format the
    publish path emits. `counts` is an object with `violation`, `warning`
    and `info` integer keys derived from the findings' severities -- a
    severity with no findings is present with a zero value, never omitted,
    so a consumer can index it unconditionally.

    Determinism guarantee: for an unchanged graph, `findings` and
    `ruleResults` are byte-identical across calls -- `checkedAt` is the only
    field permitted to differ. This function performs reads only and
    consults no model of any kind.
    """
    resolved_definition_id = resolve_definition_id(session, project, definition_id)
    published_at = fetch_published_at(session, project, resolved_definition_id)
    findings = run_structural_checks(session, project, resolved_definition_id)
    rule_results = evaluate_rule_mappings(session, project, resolved_definition_id)

    counts = {SEVERITY_VIOLATION: 0, SEVERITY_WARNING: 0, SEVERITY_INFO: 0}
    for finding in findings:
        severity = finding["severity"]
        if severity in counts:
            counts[severity] += 1
    # SVAL-02 rule-mapped failures are warning-severity per
    # spec/RULE-PARTITION-POLICY.md's "Computgraph Structural Checks (Phase
    # 37)" addendum: "a rule-mapped structural requirement that fails while
    # the graph itself is well-formed" is `warning`. ruleResults entries
    # carry no `severity` field of their own (only `passed`), so a failing
    # entry is rolled into counts.warning here rather than at the findings
    # loop above.
    counts[SEVERITY_WARNING] += sum(1 for result in rule_results if not result["passed"])

    return {
        "project": project,
        "definitionId": resolved_definition_id,
        "publishedAt": published_at,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
        "ruleResults": rule_results,
        "counts": counts,
    }

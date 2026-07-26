"""Tier 0 of the two-tier hybrid recognizer (Phase 35 SC1 remediation, RCGN-01).

Tier 0 is deterministic: no LLM, no network, no nondeterminism. It resolves
per-procedure scope, derives topology features from `cgContextJson v1` alone,
applies a fixed rule table (AI-SPEC.md Section 4) over those features, and
merges its decisions with whatever Tier 1 (the LLM) proposes for the residue.

The governing principle, stated once here because every function in this
module lives by it: **abstaining is free and guessing is not.** A Tier-0
decision ships with `confidence == 1.0` and removes its node from Tier 1's
candidate list -- an unchallengeable claim. Anything this module cannot
decide with certainty (an ambiguous topological signature, a widget_kind
that would diverge from the C# parser, an unattributable procedure) goes to
`residual` for the LLM instead of being guessed.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── output_token_budget() -- sizes the cap to the residual, not a bigger constant (F1 fix) ──
#
# ~90-120 output tokens per proposal (kind, name, ids, confidence, and a
# rationale capped at ~30 words). A bigger constant only moves the F1
# truncation cliff further out; sizing to the actual residual after Tier 0
# is the real fix.


def _clamp(low: int, value: int, high: int) -> int:
    return max(low, min(value, high))


def output_token_budget(residual: "list[str] | int") -> int:
    """clamp(512, 256 + 120 * n, 8192) where n is the residual candidate count."""
    n = residual if isinstance(residual, int) else len(residual or [])
    return _clamp(512, 256 + 120 * n, 8192)


# ── scope_untagged() -- per-procedure scope resolution with the F2 fix ──


@dataclass
class Scope:
    node_ids: list[str]
    groups: list[dict]
    procedure_index: "int | None"
    empty_procedure: bool


def _procedure_member_ids(cg_context: dict, procedure_index: int) -> set[str]:
    """Every tagged member id belonging to the procedure at `procedure_index`.
    Never raises: a malformed/missing `algorithms` shape yields an empty set."""
    ids: set[str] = set()
    algorithms = cg_context.get("algorithms")
    if not isinstance(algorithms, list):
        return ids
    for algorithm in algorithms:
        if not isinstance(algorithm, dict):
            continue
        procedures = algorithm.get("procedures")
        if not isinstance(procedures, list):
            continue
        for procedure in procedures:
            if isinstance(procedure, dict) and procedure.get("index") == procedure_index:
                member_ids = procedure.get("memberIds")
                if isinstance(member_ids, list):
                    ids.update(member_ids)
    return ids


def scope_untagged(cg_context: dict, procedure_index: "int | None") -> Scope:
    """Untagged node ids in scope for Tier 0/Tier 1.

    With no `procedure_index`, every untagged node is in scope. With one,
    scope narrows to untagged nodes one wire-hop from that procedure's
    tagged members. **If the procedure resolves to zero members, this
    returns `empty_procedure=True` and `node_ids=[]` -- it NEVER falls back
    to all untagged nodes.** That silent fallback (`cg_recognition.py:477-478`,
    `_filtered_untagged_node_ids`) is what turned an intended 14-node call
    into a 214-node call and then into the F1 truncation (UAT F2).

    Never raises: a malformed or missing `untagged` / `wires` / `algorithms`
    key yields an empty scope, mirroring `dg_context.load_cypher_catalog()`'s
    defensive-load discipline.
    """
    ctx = cg_context if isinstance(cg_context, dict) else {}

    untagged = ctx.get("untagged")
    untagged = untagged if isinstance(untagged, dict) else {}

    raw_node_ids = untagged.get("nodeIds")
    node_ids = list(raw_node_ids) if isinstance(raw_node_ids, list) else []

    raw_groups = untagged.get("groups")
    groups = [g for g in raw_groups if isinstance(g, dict)] if isinstance(raw_groups, list) else []

    if procedure_index is None:
        return Scope(node_ids=node_ids, groups=groups, procedure_index=None, empty_procedure=False)

    procedure_ids = _procedure_member_ids(ctx, procedure_index)
    if not procedure_ids:
        # F2 fix: a tagged-but-member-less procedure signals empty_procedure
        # rather than silently widening to every untagged node.
        return Scope(node_ids=[], groups=[], procedure_index=procedure_index, empty_procedure=True)

    node_id_set = set(node_ids)
    raw_wires = ctx.get("wires")
    wires = raw_wires if isinstance(raw_wires, list) else []

    adjacent: set[str] = set()
    for wire in wires:
        if not isinstance(wire, dict):
            continue
        from_node = wire.get("fromNode")
        to_node = wire.get("toNode")
        if from_node in procedure_ids and to_node in node_id_set:
            adjacent.add(to_node)
        if to_node in procedure_ids and from_node in node_id_set:
            adjacent.add(from_node)

    scoped_ids = [n for n in node_ids if n in adjacent]
    scoped_set = set(scoped_ids)
    scoped_groups = [
        g for g in groups if any(m in scoped_set for m in (g.get("memberIds") or []))
    ]
    return Scope(node_ids=scoped_ids, groups=scoped_groups, procedure_index=procedure_index, empty_procedure=False)


# ── extract_features() -- topology features from cgContextJson v1 alone ──


@dataclass
class NodeFeatures:
    instance_id: str
    name: str
    nickname: str
    component_guid: str
    widget_kind: str
    in_degree: int
    out_degree: int
    group_id: "str | None"
    group_member_count: int
    adjacent_tagged_procedures: list[int]


# Mirror of DG.Core.Parsing.CanvasAnnotationParser.GeometryParamNames
# (CanvasAnnotationParser.cs:85-89). Exact (case-insensitive) match only --
# NOT a substring test -- so "Construct Point" never matches "Point".
_GEOMETRY_PARAM_NAMES = {
    "geometry", "point", "vector", "plane", "line", "circle", "arc", "curve",
    "surface", "brep", "mesh", "subd", "box", "rectangle", "transform",
}


def widget_kind(node: dict) -> str:
    """Mirrors C# `CanvasAnnotationParser.ClassifyNodeKind` EXACTLY
    (`CanvasAnnotationParser.cs:609-657`), same order, same match semantics:

    1. A non-null `slider` domain -> `Slider` (checked before any name text).
    2. `name` contains "Value List" / "Panel" / "Toggle", case-insensitive
       (substring match, deliberately -- these are widget families).
    3. `name` EXACTLY equals "Number" / "Integer" / "Text" / "String"
       (case-insensitive), so "Number Slider" never lands on "Number".
    4. `name` is in the geometry param name set (exact match).
    5. Else `None`.

    This mirror is not cosmetic. If Python proposes `Const` on a component
    C# classifies as `None`, accept-time `InferParameterDataType` returns a
    null `dataType` with no warning and Phase 36's publish 422s the whole
    payload -- that is UAT F5. Where Python and C# would disagree, Tier 0
    must ABSTAIN rather than propose.
    """
    if not isinstance(node, dict):
        return "None"

    if node.get("slider") is not None:
        return "Slider"

    name = node.get("name") or ""
    lname = name.lower()

    if "value list" in lname:
        return "ValueList"
    if "panel" in lname:
        return "Panel"
    if "toggle" in lname:
        return "Boolean"

    if lname == "number":
        return "Number"
    if lname == "integer":
        return "Integer"
    if lname in ("text", "string"):
        return "Text"

    if lname in _GEOMETRY_PARAM_NAMES:
        return "Geometry"

    return "None"


def extract_features(cg_context: dict, node_ids: "list[str]") -> "dict[str, NodeFeatures]":
    """Derive `NodeFeatures` for each id in `node_ids` from `cgContextJson v1`
    alone -- no LLM, no network. `in_degree`/`out_degree` count `wires`
    entries where the node is `toNode`/`fromNode`. `group_id`/
    `group_member_count` come from `untagged.groups` (a node's group is the
    FIRST group listing it). `adjacent_tagged_procedures` reuses the same
    one-hop wire-adjacency signal `cg_recognition._filtered_untagged_node_ids`
    already computes (`cg_recognition.py:481-489`), generalized to every
    tagged procedure rather than one.

    Deliberately does not read any nested-group-membership field -- the
    serialized `untagged` DTO carries no such field
    (`ComputgraphContextSerializer.cs:243-250`).
    """
    ctx = cg_context if isinstance(cg_context, dict) else {}

    raw_nodes = ctx.get("nodes")
    nodes_by_id: dict[str, dict] = {
        n.get("instanceId"): n
        for n in (raw_nodes if isinstance(raw_nodes, list) else [])
        if isinstance(n, dict) and n.get("instanceId")
    }

    raw_wires = ctx.get("wires")
    wires = [w for w in raw_wires if isinstance(w, dict)] if isinstance(raw_wires, list) else []

    in_degree: dict[str, int] = {}
    out_degree: dict[str, int] = {}
    for wire in wires:
        from_node = wire.get("fromNode")
        to_node = wire.get("toNode")
        if from_node is not None:
            out_degree[from_node] = out_degree.get(from_node, 0) + 1
        if to_node is not None:
            in_degree[to_node] = in_degree.get(to_node, 0) + 1

    untagged = ctx.get("untagged")
    untagged = untagged if isinstance(untagged, dict) else {}
    raw_groups = untagged.get("groups")
    groups = [g for g in raw_groups if isinstance(g, dict)] if isinstance(raw_groups, list) else []

    group_of: dict[str, tuple[str, int]] = {}
    for idx, group in enumerate(groups):
        members = group.get("memberIds")
        members = members if isinstance(members, list) else []
        gid = group.get("nickname") or f"group-{idx}"
        for m in members:
            if m not in group_of:  # first group listing a node wins
                group_of[m] = (gid, len(members))

    # Tagged procedure membership, for the one-hop adjacency signal below.
    procedure_members: dict[int, set[str]] = {}
    algorithms = ctx.get("algorithms")
    for algorithm in algorithms if isinstance(algorithms, list) else []:
        if not isinstance(algorithm, dict):
            continue
        procedures = algorithm.get("procedures")
        for procedure in procedures if isinstance(procedures, list) else []:
            if not isinstance(procedure, dict):
                continue
            proc_index = procedure.get("index")
            if not isinstance(proc_index, int):
                continue
            member_ids = procedure.get("memberIds")
            if isinstance(member_ids, list):
                procedure_members.setdefault(proc_index, set()).update(member_ids)

    node_to_procedures: dict[str, set[int]] = {}
    for wire in wires:
        from_node = wire.get("fromNode")
        to_node = wire.get("toNode")
        for proc_index, members in procedure_members.items():
            if from_node in members and to_node is not None:
                node_to_procedures.setdefault(to_node, set()).add(proc_index)
            if to_node in members and from_node is not None:
                node_to_procedures.setdefault(from_node, set()).add(proc_index)

    features: dict[str, NodeFeatures] = {}
    for node_id in node_ids or []:
        node = nodes_by_id.get(node_id) or {}
        gid, gcount = group_of.get(node_id, (None, 0))
        features[node_id] = NodeFeatures(
            instance_id=node_id,
            name=node.get("name") or "",
            nickname=node.get("nickname") or "",
            component_guid=node.get("componentGuid") or "",
            widget_kind=widget_kind(node),
            in_degree=in_degree.get(node_id, 0),
            out_degree=out_degree.get(node_id, 0),
            group_id=gid,
            group_member_count=gcount,
            adjacent_tagged_procedures=sorted(node_to_procedures.get(node_id, set())),
        )
    return features

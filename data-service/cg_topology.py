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

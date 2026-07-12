"""SWRL conventions + Computgraph concept catalog -- read-only reference data
for dg_context.py's assembler (Phase 29: CTXA-03, and the Computgraph portion
of CTXA-01's per-layer concept catalog).

Mirrors reasoner.py's module-constant-registry layout: SWRL_CONVENTIONS is a
plain module-level dict (data, not prose) built once at import time. The
Computgraph catalog (added alongside this block in the same plan) is parsed
from the real `DesignGrammar-V7.owl` file and cached -- matching how
llm_gateway.py caches expensive discovery work, never re-parsed per request.

Scope guard (29-CONTEXT.md D-14/D-15): this module CATALOGS what
DesignGrammar-V7.owl already defines. It does NOT invent new Computgraph
structure (Phase 32's CGSR job) and is NOT wired into rule_ingest/rule_edit/
graph_query context selection (Phase 35's RCGN job) -- pure forward-prep.
"""

from __future__ import annotations

from typing import Any


# ── SWRL conventions (machine-readable block, CTXA-03) ──

SWRL_CONVENTIONS: dict[str, Any] = {
    "violation_inversion": {
        "flag": True,
        "statement": (
            "Body atoms fire when the constraint is VIOLATED (inverted logic); "
            "the head atom sets the violation DatatypeProperty to true. Example: "
            "'maximum height 75' -> body uses swrlb:greaterThan(?val, 75), NOT "
            "swrlb:lessThanOrEqual(?val, 75)."
        ),
    },
    "atom_ordering": {
        "relationship_types": ["HAS_BODY", "HAS_HEAD"],
        "property": "order",
        "statement": (
            "Rule->Atom edges via HAS_BODY/HAS_HEAD carry an integer `order` "
            "property establishing body/head atom sequence. `order` is a "
            "reserved Cypher word and MUST be backtick-quoted: "
            "MERGE (r)-[:HAS_BODY {`order`: 1}]->(a1)."
        ),
    },
    "argument_rules": {
        "relationship_type": "ARG",
        "property": "pos",
        "statement": (
            "Atom->Var/Literal edges via ARG carry an integer `pos` property "
            "establishing argument position. `pos` is a reserved Cypher word "
            "and MUST be backtick-quoted: MERGE (a1)-[:ARG {`pos`: 1}]->(vEntity)."
        ),
        "var_merge_keys": ["name", "project"],
        "var_merge_statement": (
            "Var nodes MERGE on both `name` (?<varName>) and `project` -- "
            "omitting `project` from the merge key reintroduces the v2.0 "
            "cross-project variable-collision bug (fixed per STATE.md v3.0 "
            "Phase 7 decision: 'Var merge key includes project')."
        ),
        "literal_merge_keys": ["lex", "datatype"],
        "literal_merge_statement": "Literal nodes MERGE on `lex` and `datatype`.",
        "builtin_merge_key": "iri",
        "builtin_merge_statement": "Builtin nodes MERGE on `iri` (swrlb:<builtinName>).",
    },
    "naming_quirks": {
        "Rule_Id": "Rule node key property is `Rule_Id`, not `id`.",
        "Atom_Id": "Atom node key property is `Atom_Id` (format {Rule_Id}_A{n} for body, {Rule_Id}_H{n} for head), not `id`.",
        "SWRL_label": "DatatypeProperty display property is `SWRL_label`, not `label` (Class/ObjectProperty use plain `label`).",
        "SWRL": "Rule's SWRL-expression body property is named `SWRL`, not `text`.",
        "reserved_relationship_properties": ["order", "pos"],
    },
}


def swrl_conventions() -> dict[str, Any]:
    """Typed accessor -- shared entry point for the assembler and tests."""
    return SWRL_CONVENTIONS

"""SWRL conventions + Computgraph concept catalog -- read-only reference data
for dg_context.py's assembler (Phase 29: CTXA-03, and the Computgraph portion
of CTXA-01's per-layer concept catalog).

Mirrors reasoner.py's module-constant-registry layout: SWRL_CONVENTIONS is a
plain module-level dict (data, not prose) built once at import time. The
Computgraph catalog is parsed ONCE from the real `DesignGrammar-V7.owl` file
on first call and cached in `_COMPUTGRAPH_CACHE` -- matching how
llm_gateway.py caches expensive discovery work, never re-parsed per request.

Scope guard (29-CONTEXT.md D-14/D-15): this module CATALOGS what
DesignGrammar-V7.owl already defines. It does NOT invent new Computgraph
structure (Phase 32's CGSR job) and is NOT wired into rule_ingest/rule_edit/
graph_query context selection (Phase 35's RCGN job) -- pure forward-prep.

Path resolution mirrors dg_context.py's CYPHER_CATALOG_FILE: inside the
data-service Docker container the repo root is mounted read-only at
`/mnt/repo` (see docker-compose.yml's `.:/mnt/repo:ro` volume +
`DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` env var), so `COMPUTGRAPH_OWL_FILE`
resolves to `/mnt/repo/ontology/DesignGrammar-V7.owl` with zero Dockerfile
changes. Outside the container the same env var is unset and the path
falls back to `<repo-root>/ontology/DesignGrammar-V7.owl`, computed
relative to this file.

OWL parsing reuses `ontology/export_to_markdown_v7.py`'s existing helper
functions (localname/get_text/get_resource/parse_domain_or_range/
parse_one_of/get_about, plus its NS namespace-map constant) rather than
reimplementing an OWL walker -- loaded dynamically via
`importlib.util.spec_from_file_location`, the exact pattern already used by
`ontology/make_docs_v7.py` to invoke that same module. Verified directly
against the real file: Python's stdlib `xml.etree.ElementTree.parse()`
resolves the file's DOCTYPE internal-entity block (`<!ENTITY dgc "...">`)
natively -- no custom entity resolver or text pre-processing is needed.
"""

from __future__ import annotations

import importlib.util
import os
import xml.etree.ElementTree as ET
from pathlib import Path
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


# Phase 1303-15 (owner 2026-10-20): a rule must be computable by VALIDATOR, which evaluates class, data-property
# and builtin atoms. "Openings are not allowed in beams" came back as Beam(?beam) ^ Opening(?o) ^
# hasOpening(?beam, ?o) -- with the beam as subject -- so the form stays: ONE subject, ONE numeric property of it.
#
# Phase 1303-20 (D-61, owner 2026-10-21): every OTHER object class a rule names (the slab an opening sits in,
# the columns and walls whose projection it must keep clear of) is a participant: a ClassAtom on its own variable
# plus an ObjectPropertyAtom relating it to the subject or to another participant. Plan 1303-19 makes VALIDATOR
# treat those atoms as asserted by the rule, not verified (context-only variables, spec/SWRL-SUBSET.md), so a rule
# with participants evaluates exactly like its one-class form. Derived geometric notions (outline, projection,
# clearance, edge, distance) are not classes; they stay in the subject's numeric property name. The statement
# reaches every ingest prompt through swrl_conventions, which n8n already serializes, so no n8n file changes.
SWRL_CONVENTIONS["computable_form"] = {
    "statement": (
        "Every rule tests ONE subject element class: the element the rule constrains (in 'X is not allowed in Y' "
        "and 'X in Y must be at least D from Z' the subject is X, never Y or Z). The measured quantity is exactly: "
        "one ClassAtom for the subject, one DataPropertyAtom giving a NUMERIC property of that same subject "
        "variable, and one swrlb comparison builtin on that value; the head atom flags the subject. "
        "Every OTHER object class the rule names (Y, Z, ...) is a participant: write a ClassAtom for it on its "
        "own variable and an ObjectPropertyAtom relating it to the subject or to another participant, using a "
        "camelCase verb IRI such as hostedBy, projectsOnto or adjacentTo and reusing an existing ObjectProperty "
        "from the entity list when one fits instead of inventing a synonym. Write each ObjectProperty with "
        "label, domain and range (class IRIs as strings, e.g. 'ex:Opening'). A participant variable NEVER "
        "appears in a DataPropertyAtom, a builtin or the head. A participant is a physical or building object "
        "class the rule names; a derived geometric notion (outline, projection, clearance, edge, distance) is "
        "NEVER a class: it stays part of the subject's numeric property name -- a count of the related elements "
        "(has<Related>IntersectionCount, has<Related>BelowCount) or a distance with its unit "
        "(hasMin<Related>ClearanceMm). When the rule names no object besides the subject, write only the "
        "subject's three atoms: add no participant the rule does not name. "
        "A prohibition is count > 0; a minimum distance D is value < D. "
        "The user writes rules in plain language, usually Russian, and never names a class or a property: map "
        "the words to the class_vocabulary and to the computable_properties (meaning / meaningRu) and write "
        "those exact names."
    ),
    "example": {
        "rule": "Openings are not allowed in beams (Отверстия не допускаются в балках)",
        "swrl": "OpeningBox(?b) ^ Beam(?m) ^ intersects(?b, ?m) ^ hasBeamIntersectionCount(?b, ?n) ^ "
                "swrlb:greaterThan(?n, \"0\"^^xsd:integer) -> hasOpeningBoxViolation(?b, true)",
    },
    "participants_example": {
        "rule": "An opening in a slab must not be closer than 500 mm to the outline of the projection of columns "
                "and walls onto that slab",
        "swrl": "Opening(?o) ^ Slab(?s) ^ hostedBy(?o, ?s) ^ Column(?c) ^ projectsOnto(?c, ?s) ^ Wall(?w) ^ "
                "projectsOnto(?w, ?s) ^ hasMinProjectionClearanceMm(?o, ?d) ^ "
                "swrlb:lessThan(?d, \"500\"^^xsd:integer) -> hasProjectionClearanceViolation(?o, true)",
        "cypher": (
            "MERGE (C_Main:Class {iri: 'ex:Opening', project: $project, graph: 'OntoGraph'})\n"
            "SET C_Main.label = 'Opening'\n"
            "\n"
            "MERGE (C_Slab:Class {iri: 'ex:Slab', project: $project, graph: 'OntoGraph'})\n"
            "SET C_Slab.label = 'Slab'\n"
            "\n"
            "MERGE (C_Col:Class {iri: 'ex:Column', project: $project, graph: 'OntoGraph'})\n"
            "SET C_Col.label = 'Column'\n"
            "\n"
            "MERGE (C_Wall:Class {iri: 'ex:Wall', project: $project, graph: 'OntoGraph'})\n"
            "SET C_Wall.label = 'Wall'\n"
            "\n"
            "MERGE (OP_Host:ObjectProperty {iri: 'ex:hostedBy', project: $project, graph: 'OntoGraph'})\n"
            "SET OP_Host.label = 'hostedBy', OP_Host.domain = 'ex:Opening', OP_Host.range = 'ex:Slab'\n"
            "\n"
            "MERGE (OP_Proj:ObjectProperty {iri: 'ex:projectsOnto', project: $project, graph: 'OntoGraph'})\n"
            "SET OP_Proj.label = 'projectsOnto', OP_Proj.domain = 'ex:Column', OP_Proj.range = 'ex:Slab'\n"
            "\n"
            "MERGE (DP_Main:DatatypeProperty {iri: 'ex:hasMinProjectionClearanceMm', project: $project, "
            "graph: 'OntoGraph'})\n"
            "SET DP_Main.SWRL_label = 'hasMinProjectionClearanceMm', DP_Main.range = 'xsd:integer'\n"
            "\n"
            "MERGE (B_Lt:Builtin {iri: 'swrlb:lessThan', project: $project, graph: 'Metagraph'})\n"
            "SET B_Lt.label = 'lessThan'\n"
            "\n"
            "MERGE (DP_V:DatatypeProperty {iri: 'ex:hasProjectionClearanceViolation', project: $project, "
            "graph: 'OntoGraph'})\n"
            "SET DP_V.SWRL_label = 'hasProjectionClearanceViolation', DP_V.range = 'xsd:boolean'\n"
            "\n"
            "MERGE (r:Rule {Rule_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V', project: $project, graph: 'Metagraph'})\n"
            "SET r.SWRL = 'Opening(?o) ^ Slab(?s) ^ hostedBy(?o, ?s) ^ Column(?c) ^ projectsOnto(?c, ?s) ^ "
            "Wall(?w) ^ projectsOnto(?w, ?s) ^ hasMinProjectionClearanceMm(?o, ?d) ^ "
            "swrlb:lessThan(?d, \"500\"^^xsd:integer) -> hasProjectionClearanceViolation(?o, true)', "
            "r.kind = 'violation'\n"
            "\n"
            "MERGE (vO:Var {name: '?o', project: $project, graph: 'Metagraph'})\n"
            "MERGE (vS:Var {name: '?s', project: $project, graph: 'Metagraph'})\n"
            "MERGE (vC:Var {name: '?c', project: $project, graph: 'Metagraph'})\n"
            "MERGE (vW:Var {name: '?w', project: $project, graph: 'Metagraph'})\n"
            "MERGE (vD:Var {name: '?d', project: $project, graph: 'Metagraph'})\n"
            "\n"
            "MERGE (litX:Literal {lex: '500', datatype: 'xsd:integer', project: $project, graph: 'Metagraph'})\n"
            "MERGE (litT:Literal {lex: 'true', datatype: 'xsd:boolean', project: $project, graph: 'Metagraph'})\n"
            "\n"
            "MERGE (a1:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A1', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a1.type = 'ClassAtom', a1.iri = 'ex:Opening', a1.SWRL_label = 'Opening'\n"
            "\n"
            "MERGE (a2:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A2', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a2.type = 'ClassAtom', a2.iri = 'ex:Slab', a2.SWRL_label = 'Slab'\n"
            "\n"
            "MERGE (a3:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A3', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a3.type = 'ObjectPropertyAtom', a3.iri = 'ex:hostedBy', a3.SWRL_label = 'hostedBy'\n"
            "\n"
            "MERGE (a4:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A4', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a4.type = 'ClassAtom', a4.iri = 'ex:Column', a4.SWRL_label = 'Column'\n"
            "\n"
            "MERGE (a5:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A5', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a5.type = 'ObjectPropertyAtom', a5.iri = 'ex:projectsOnto', a5.SWRL_label = 'projectsOnto'\n"
            "\n"
            "MERGE (a6:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A6', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a6.type = 'ClassAtom', a6.iri = 'ex:Wall', a6.SWRL_label = 'Wall'\n"
            "\n"
            "MERGE (a7:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A7', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a7.type = 'ObjectPropertyAtom', a7.iri = 'ex:projectsOnto', a7.SWRL_label = 'projectsOnto'\n"
            "\n"
            "MERGE (a8:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A8', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a8.type = 'DataPropertyAtom', a8.iri = 'ex:hasMinProjectionClearanceMm', "
            "a8.SWRL_label = 'hasMinProjectionClearanceMm'\n"
            "\n"
            "MERGE (a9:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_A9', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET a9.type = 'BuiltinAtom', a9.iri = 'swrlb:lessThan', a9.SWRL_label = 'lessThan'\n"
            "\n"
            "MERGE (h1:Atom {Atom_Id: 'R_STR_OPENING_CLEARANCE_MIN_500_V_H1', project: $project, "
            "graph: 'Metagraph'})\n"
            "SET h1.type = 'DataPropertyAtom', h1.iri = 'ex:hasProjectionClearanceViolation', "
            "h1.SWRL_label = 'hasProjectionClearanceViolation'\n"
            "\n"
            "MERGE (r)-[:HAS_BODY {order: 1}]->(a1)\n"
            "MERGE (r)-[:HAS_BODY {order: 2}]->(a2)\n"
            "MERGE (r)-[:HAS_BODY {order: 3}]->(a3)\n"
            "MERGE (r)-[:HAS_BODY {order: 4}]->(a4)\n"
            "MERGE (r)-[:HAS_BODY {order: 5}]->(a5)\n"
            "MERGE (r)-[:HAS_BODY {order: 6}]->(a6)\n"
            "MERGE (r)-[:HAS_BODY {order: 7}]->(a7)\n"
            "MERGE (r)-[:HAS_BODY {order: 8}]->(a8)\n"
            "MERGE (r)-[:HAS_BODY {order: 9}]->(a9)\n"
            "MERGE (r)-[:HAS_HEAD {order: 1}]->(h1)\n"
            "\n"
            "MERGE (a1)-[:REFERS_TO]->(C_Main)\n"
            "MERGE (a2)-[:REFERS_TO]->(C_Slab)\n"
            "MERGE (a3)-[:REFERS_TO]->(OP_Host)\n"
            "MERGE (a4)-[:REFERS_TO]->(C_Col)\n"
            "MERGE (a5)-[:REFERS_TO]->(OP_Proj)\n"
            "MERGE (a6)-[:REFERS_TO]->(C_Wall)\n"
            "MERGE (a7)-[:REFERS_TO]->(OP_Proj)\n"
            "MERGE (a8)-[:REFERS_TO]->(DP_Main)\n"
            "MERGE (a9)-[:REFERS_TO]->(B_Lt)\n"
            "MERGE (h1)-[:REFERS_TO]->(DP_V)\n"
            "\n"
            "MERGE (a1)-[:ARG {pos: 1}]->(vO)\n"
            "MERGE (a2)-[:ARG {pos: 1}]->(vS)\n"
            "MERGE (a3)-[:ARG {pos: 1}]->(vO)\n"
            "MERGE (a3)-[:ARG {pos: 2}]->(vS)\n"
            "MERGE (a4)-[:ARG {pos: 1}]->(vC)\n"
            "MERGE (a5)-[:ARG {pos: 1}]->(vC)\n"
            "MERGE (a5)-[:ARG {pos: 2}]->(vS)\n"
            "MERGE (a6)-[:ARG {pos: 1}]->(vW)\n"
            "MERGE (a7)-[:ARG {pos: 1}]->(vW)\n"
            "MERGE (a7)-[:ARG {pos: 2}]->(vS)\n"
            "MERGE (a8)-[:ARG {pos: 1}]->(vO)\n"
            "MERGE (a8)-[:ARG {pos: 2}]->(vD)\n"
            "MERGE (a9)-[:ARG {pos: 1}]->(vD)\n"
            "MERGE (a9)-[:ARG {pos: 2}]->(litX)\n"
            "MERGE (h1)-[:ARG {pos: 1}]->(vO)\n"
            "MERGE (h1)-[:ARG {pos: 2}]->(litT);"
        ),
    },
    "subject_naming": "Name the subject class as the user names it (PascalCase, singular, English); reuse an "
                      "existing class of the project when one matches. Name each participant class the same way "
                      "and reuse an existing class of the project for a synonym (Floor and Slab are one concept).",
    "computable_properties_statement": "DG can compute these properties from the model; reuse the exact name "
                                        "whenever one fits the rule instead of inventing a new one.",
}


def _computable_vocabulary() -> list[dict[str, str]]:
    import json

    try:
        catalogue = json.loads((Path(__file__).resolve().parent / "property_calculators" / "catalogue.json")
                               .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [dict(v) for v in catalogue.get("vocabulary", [])]


def _class_vocabulary() -> list[dict[str, Any]]:
    import json

    try:
        catalogue = json.loads((Path(__file__).resolve().parent / "property_calculators" / "catalogue.json")
                               .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [dict(v) for v in catalogue.get("classVocabulary", [])]


SWRL_CONVENTIONS["computable_form"]["computable_properties"] = _computable_vocabulary()
# F-03 (2026-10-29): rules arrive in plain language without class or property names; the class words map here.
SWRL_CONVENTIONS["computable_form"]["class_vocabulary"] = _class_vocabulary()


def swrl_conventions() -> dict[str, Any]:
    """Typed accessor -- shared entry point for the assembler and tests."""
    return SWRL_CONVENTIONS


# ── Computgraph concept catalog (forward-prep only, D-14/D-15) ──

_REPO_ROOT = Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))

COMPUTGRAPH_OWL_FILE = _REPO_ROOT / "ontology" / "DesignGrammar-V7.owl"
_OWL_EXPORTER_MODULE_PATH = _REPO_ROOT / "ontology" / "export_to_markdown_v7.py"

# The five dgc: entity classes tagged dg:graph="&dgc;Computgraph" in the OWL
# file (DesignGrammar-V7.owl ~2307-2378), per CTXA-01/D-14.
COMPUTGRAPH_ENTITY_CLASS_NAMES: tuple[str, ...] = (
    "Algorithm",
    "Procedure",
    "Pattern",
    "Parameter",
    "Interface",
)

_COMPUTGRAPH_CACHE: dict[str, Any] | None = None


def _load_owl_exporter():
    """Dynamically load export_to_markdown_v7.py's module-level OWL helpers.

    Mirrors ontology/make_docs_v7.py's importlib.util.spec_from_file_location
    driver -- reuses the existing, already-proven NS map + localname/get_text/
    get_resource/parse_domain_or_range/parse_one_of/get_about functions
    instead of re-deriving a fresh OWL/XML walker (RESEARCH.md A1 / Don't
    Hand-Roll #3).
    """
    spec = importlib.util.spec_from_file_location(
        "export_to_markdown_v7", _OWL_EXPORTER_MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _describe_class(exporter, classes: dict[str, ET.Element], iri: str) -> dict[str, Any]:
    elem = classes.get(iri)
    return {
        "iri": iri,
        "local_name": exporter.localname(iri),
        "label": exporter.get_text(elem, "rdfs", "label") if elem is not None else None,
        "comment": exporter.get_text(elem, "rdfs", "comment") if elem is not None else None,
    }


# DG Canvas Annotation Convention grammar -- the GH scribble/group naming
# patterns inferable directly from the OWL file's own Frame worked-example
# individual labels (DesignGrammar-V7.owl ~2719-2930: Object_Frame's
# Algorithm/Procedure/Pattern/Parameter/Interface individuals). Catalogs what
# the OWL file's example instances already demonstrate -- does not invent new
# grammar (D-14). The full parser grammar/typo-tolerance/normalization
# behavior is Phase 32/34's job; this is a read-only reference snapshot.
_ANNOTATION_CONVENTION: dict[str, Any] = {
    "description": (
        "GH canvas scribble/group naming grammar, derived from the "
        "dgc:Computgraph 'Frame' worked example individuals in "
        "DesignGrammar-V7.owl (Algorithm_1, Proc_11/Proc_12, "
        "Pat_11_DivideLine, Var_11_SpansCount, Const_11_ptZero, "
        "Emg_11_LineSDL, IntF_11_ParSplitAt, etc.)."
    ),
    "patterns": [
        {"kind": "Algorithm", "annotation": "scribble", "grammar": "<n>_Algorithm", "example": "1_Algorithm"},
        {"kind": "Procedure", "annotation": "group", "grammar": "<NN>_Proc - <Name>", "example": "11_Proc - 2D Truss Configuration"},
        {"kind": "Pattern", "annotation": "group", "grammar": "<NN>_Pat_<k>[ <name>]", "example": "11_Pat_DivideLine"},
        {"kind": "VariableParam", "annotation": "group", "grammar": "<NN>_Var_<Name>", "example": "11_Var_SpansCount"},
        {"kind": "ConstantParam", "annotation": "group", "grammar": "<NN>_Const_<Name>", "example": "11_Const_ptZero"},
        {
            "kind": "EmergentParam",
            "annotation": "group",
            "grammar": "<NN>_Emg_<Name>",
            "example": "11_Emg_LineSDL",
            "tolerated_variant": "Emr (observed in the OWL file itself: dgc:Emg_11_UpperChord's rdfs:label is '11_Emr_UpperChord' -- accept Emg|Emr; normalization warning is Phase 32/34's job, not catalogued here as behavior)",
        },
        {"kind": "Interface", "annotation": "group", "grammar": "<NN>_IntF_<Name>", "example": "11_IntF_ParSplitAt"},
    ],
    "numbering": (
        "NN's first digit = algorithm index, remaining digit(s) = procedure "
        "ordinal within that algorithm (e.g. 11 = algorithm 1, procedure 1; "
        "12 = algorithm 1, procedure 2)."
    ),
}


def load_computgraph_catalog() -> dict[str, Any]:
    """Parse the Computgraph portion of DesignGrammar-V7.owl once, then cache.

    Returns a dict with:
    - hub: the dgc:Computgraph hub class
    - entity_classes: the five entity classes (Algorithm, Procedure, Pattern,
      Parameter, Interface), keyed by class name
    - relations: dgc: ObjectProperty relations (label/domain/range)
    - attributes: dgc: DatatypeProperty attributes (label/domain/range)
    - enum_values: dgc: closed owl:oneOf enum classes and their members
    - annotation_convention: the DG Canvas Annotation Convention grammar
    - source_iri / source_file: provenance

    Parses ONCE per process (module-level _COMPUTGRAPH_CACHE) -- never
    re-parses the OWL file on subsequent calls.
    """
    global _COMPUTGRAPH_CACHE
    if _COMPUTGRAPH_CACHE is not None:
        return _COMPUTGRAPH_CACHE

    exporter = _load_owl_exporter()

    tree = ET.parse(COMPUTGRAPH_OWL_FILE)
    root = tree.getroot()

    classes: dict[str, ET.Element] = {}
    obj_props: dict[str, ET.Element] = {}
    dt_props: dict[str, ET.Element] = {}
    individuals: dict[str, ET.Element] = {}

    for child in root:
        about = exporter.get_about(child)
        if not about:
            continue
        if child.tag == f"{{{exporter.NS['owl']}}}Class":
            classes[about] = child
        elif child.tag == f"{{{exporter.NS['owl']}}}ObjectProperty":
            obj_props[about] = child
        elif child.tag == f"{{{exporter.NS['owl']}}}DatatypeProperty":
            dt_props[about] = child
        elif child.tag == f"{{{exporter.NS['owl']}}}NamedIndividual":
            individuals[about] = child

    dgc_ns = exporter.NS["dgc"]

    def is_dgc(iri: str) -> bool:
        return iri.startswith(dgc_ns)

    hub_iri = f"{dgc_ns}Computgraph"
    hub = _describe_class(exporter, classes, hub_iri)

    entity_classes = {
        name: _describe_class(exporter, classes, f"{dgc_ns}{name}")
        for name in COMPUTGRAPH_ENTITY_CLASS_NAMES
    }

    relations = []
    for iri, elem in obj_props.items():
        if not is_dgc(iri):
            continue
        relations.append(
            {
                "iri": iri,
                "local_name": exporter.localname(iri),
                "label": exporter.get_text(elem, "rdfs", "label"),
                "domain": exporter.parse_domain_or_range(elem, "domain"),
                "range": exporter.parse_domain_or_range(elem, "range"),
            }
        )

    attributes = []
    for iri, elem in dt_props.items():
        if not is_dgc(iri):
            continue
        attributes.append(
            {
                "iri": iri,
                "local_name": exporter.localname(iri),
                "label": exporter.get_text(elem, "rdfs", "label"),
                "domain": exporter.parse_domain_or_range(elem, "domain"),
                "range": exporter.parse_domain_or_range(elem, "range"),
            }
        )

    enum_values = []
    for iri, elem in classes.items():
        if not is_dgc(iri):
            continue
        members = exporter.parse_one_of(elem)
        if not members:
            continue
        enum_values.append(
            {
                "iri": iri,
                "local_name": exporter.localname(iri),
                "label": exporter.get_text(elem, "rdfs", "label"),
                "values": [
                    {
                        "iri": member_iri,
                        "local_name": exporter.localname(member_iri),
                        "label": (
                            exporter.get_text(individuals[member_iri], "rdfs", "label")
                            if member_iri in individuals
                            else exporter.localname(member_iri)
                        ),
                    }
                    for member_iri in members
                ],
            }
        )

    catalog: dict[str, Any] = {
        "source_iri": hub_iri,
        "source_file": str(COMPUTGRAPH_OWL_FILE),
        "hub": hub,
        "entity_classes": entity_classes,
        "relations": relations,
        "attributes": attributes,
        "enum_values": enum_values,
        "annotation_convention": _ANNOTATION_CONVENTION,
    }

    _COMPUTGRAPH_CACHE = catalog
    return catalog

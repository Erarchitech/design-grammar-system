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

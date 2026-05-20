"""
Phase 1: v3.3 → v3.4 consistency refactor.

Applies five coordinated fixes in one atomic pass:

  Fix 1.1+1.2+1.3 — Unify GraphLayer enum and LayerEntity hub via OWL 2 punning.
    - Rename hub classes (drop "Entity" suffix, migrate to layer namespaces):
        dg:OntoGraphEntity        → dg:OntoGraph
        dgm:MetagraphEntity       → dgm:Metagraph
        dgv:ValidationGraphEntity → dgv:ValidationGraph
        dgk:KnowledgeGraphEntity  → dgk:KnowledgeGraph
    - Add OWL 2 punning: each renamed hub class also gets rdf:type dg:GraphLayer.
    - Delete the four standalone NamedIndividuals (dg:OntoGraph, dg:Metagraph,
      dg:ValidationGraphLayer, dg:KnowledgeGraphLayer) — their semantic role
      is taken over by the punned hub classes.
    - Convert <dg:graph>STRING</dg:graph> annotation values to resource references
      pointing at the four punned hub IRIs.
    - Add rdfs:range dg:GraphLayer to the dg:graph annotation property.

  Fix 2 — Annotation enrichment for 17 external superclasses that DG aligns with.
    - Adds <rdf:Description> blocks with rdfs:label, rdfs:comment (DG-perspective),
      rdfs:isDefinedBy, and rdfs:seeAlso for each external class. Pure annotation
      enrichment — does NOT change external-class semantics.

  Fix 3 — Clarifying comment on dg:LayerEntity explaining why it has no
    dg:graph annotation (it is cross-cutting).

Output: in-place rewrite of DesignGrammar.owl, version bumped to 3.4.
Idempotent: re-running detects v3.4 state and exits without changes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# ============================================================
# Hub class rename + punning targets
# ============================================================

# (old_iri_suffix, new_iri_suffix, layer_label)
HUB_RENAMES = [
    ("dg;OntoGraphEntity",         "dg;OntoGraph",        "OntoGraph"),
    ("dgm;MetagraphEntity",        "dgm;Metagraph",       "Metagraph"),
    ("dgv;ValidationGraphEntity",  "dgv;ValidationGraph", "ValidationGraph"),
    ("dgk;KnowledgeGraphEntity",   "dgk;KnowledgeGraph",  "KnowledgeGraph"),
]

# IRI suffixes of standalone NamedIndividuals to delete (replaced by punned hubs)
INDIVIDUALS_TO_DELETE = [
    "dg;OntoGraph",
    "dg;Metagraph",
    "dg;ValidationGraphLayer",
    "dg;KnowledgeGraphLayer",
]

# Map dg:graph string value → new resource IRI (for punned hub class+individual)
GRAPH_VALUE_MAP = {
    "OntoGraph":       "&dg;OntoGraph",
    "Metagraph":       "&dgm;Metagraph",
    "ValidationGraph": "&dgv;ValidationGraph",
    "KnowledgeGraph":  "&dgk;KnowledgeGraph",
}


# ============================================================
# External-class annotation enrichments (Fix 2)
# 17 classes that DG aligns with via owl:equivalentClass or rdfs:subClassOf
# ============================================================

ENRICHMENTS = [
    # (prefix, local_name, display_label, DG-perspective comment, spec_seeAlso_url, ontology_definedBy)
    ("swrl", "Imp",
     "SWRL Implication (Rule)",
     "SWRL class for a rule — an implication between body atoms (conditions) and head atoms (conclusions). In DG, equivalent to dgm:Rule via R1 alignment.",
     "https://www.w3.org/Submission/SWRL/#3.1.1",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "Atom",
     "SWRL Atom",
     "Abstract SWRL atom — base class for predicate assertions inside rule bodies and heads. In DG, equivalent to dgm:Atom. Subtypes used by DG: ClassAtom, DatavaluedPropertyAtom, IndividualPropertyAtom, BuiltinAtom.",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "ClassAtom",
     "SWRL Class Atom",
     "SWRL atom asserting class membership of a variable, e.g. Building(?b). In DG, equivalent to dgm:ClassAtom.",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "DatavaluedPropertyAtom",
     "SWRL Datavalued Property Atom",
     "SWRL atom asserting a datatype property value, e.g. hasHeightM(?b, ?h). In DG, equivalent to dgm:DataPropertyAtom (DG uses the shorter name).",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "IndividualPropertyAtom",
     "SWRL Individual Property Atom",
     "SWRL atom asserting an object property relationship between two individuals, e.g. locatedIn(?b, ?block). In DG, equivalent to dgm:ObjectPropertyAtom (DG uses the shorter name).",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "BuiltinAtom",
     "SWRL Builtin Atom",
     "SWRL atom invoking a builtin comparison or arithmetic operator, e.g. swrlb:greaterThan(?h, 75). In DG, equivalent to dgm:BuiltinAtom.",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "Variable",
     "SWRL Variable",
     "A SWRL variable, e.g. ?b. In DG, equivalent to dgm:Variable. DG refines this with ObjectVariable, PropertyVariable, and BuiltinVariable subclasses per VTYP-01 typing.",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),
    ("swrl", "Builtin",
     "SWRL Builtin",
     "A SWRL builtin comparison/arithmetic operator (e.g. swrlb:greaterThan). In DG, equivalent to dgm:Builtin. DG uses six builtins: greaterThan, lessThan, greaterThanOrEqual, lessThanOrEqual, equal, notEqual.",
     "https://www.w3.org/Submission/SWRL/#3.1.2",
     "http://www.w3.org/Submission/SWRL/"),

    ("prov", "Activity",
     "PROV Activity",
     "PROV-O class for something that occurs over a period of time and acts upon or with entities. In DG, parent of dgv:ValidationRun (a validation execution) and dgk:KnowledgeSession (an LLM ingest/query/update session). Aligned via R2.",
     "https://www.w3.org/TR/prov-o/#Activity",
     "http://www.w3.org/ns/prov-o#"),
    ("prov", "Entity",
     "PROV Entity",
     "PROV-O class for a physical, digital, conceptual, or other kind of thing whose provenance can be traced. In DG, parent of dgv:ValidationEntity (a BIM element evaluated in a run). Aligned via R2.",
     "https://www.w3.org/TR/prov-o/#Entity",
     "http://www.w3.org/ns/prov-o#"),

    ("sosa", "Observation",
     "SOSA Observation",
     "SOSA class for the act of carrying out an observation — measurement of a property on a feature of interest. In DG, parent of dgv:ValidationEntity (a rule check is an observation of a property on an object). Aligned via R3.",
     "https://www.w3.org/TR/vocab-ssn/#SOSAObservation",
     "http://www.w3.org/ns/sosa/"),
    ("sosa", "FeatureOfInterest",
     "SOSA Feature of Interest",
     "SOSA class for the thing whose property is being observed. In DG, parent of dgv:ObjectInstance (the validated geometric element). Aligned via R3.",
     "https://www.w3.org/TR/vocab-ssn/#SOSAFeatureOfInterest",
     "http://www.w3.org/ns/sosa/"),

    ("sh", "ValidationReport",
     "SHACL Validation Report",
     "SHACL class for the result of validating data graph against shapes — contains all validation results. In DG, parent of dgv:ValidationRun. Aligned via R4.",
     "https://www.w3.org/TR/shacl/#results-validation-report",
     "http://www.w3.org/ns/shacl#"),
    ("sh", "ValidationResult",
     "SHACL Validation Result",
     "SHACL class for an individual result entry inside a validation report — records focusNode, resultPath, severity, etc. In DG, parent of dgv:ValidationEntity (the per-rule, per-instance result cell). Aligned via R4.",
     "https://www.w3.org/TR/shacl/#results-validation-result",
     "http://www.w3.org/ns/shacl#"),

    ("skos", "Concept",
     "SKOS Concept",
     "SKOS class for an idea or notion — a unit of thought used in a knowledge organization system. In DG, equivalent to dgk:KnowledgeTag (a tag IS a concept in a project's tag taxonomy). Aligned via R5.",
     "https://www.w3.org/TR/skos-reference/#concepts",
     "http://www.w3.org/2004/02/skos/core"),

    ("geo", "Feature",
     "GeoSPARQL Feature",
     "GeoSPARQL class for a spatial feature — anything with a discernible geometry. In DG, parent of dgv:ObjectInstance. Aligned via R6.",
     "https://www.ogc.org/standards/geosparql",
     "http://www.opengis.net/ont/geosparql"),
    ("geo", "Geometry",
     "GeoSPARQL Geometry",
     "GeoSPARQL class for a geometric primitive (point, polygon, etc.) — or, in DG's case, a reference to one. DG's dgv:GeoRef is a handle into a source-system (Speckle/Rhino) rather than serialized WKT, but the conceptual role is the same. Aligned via R6.",
     "https://www.ogc.org/standards/geosparql",
     "http://www.opengis.net/ont/geosparql"),
]


# ============================================================
# Main refactor
# ============================================================

def is_already_v34(content: str) -> bool:
    """Detect whether the file is already at v3.4 (idempotency check)."""
    return "<owl:versionInfo>3.4</owl:versionInfo>" in content


def step1_delete_standalone_individuals(content: str) -> tuple[str, int]:
    """Delete the four standalone GraphLayer NamedIndividuals (their semantic
    role is taken over by the punned hub classes)."""
    deleted = 0
    for iri_suffix in INDIVIDUALS_TO_DELETE:
        # Match the NamedIndividual block with trailing blank line
        pattern = re.compile(
            rf'    <owl:NamedIndividual rdf:about="&{re.escape(iri_suffix)}">\s*'
            rf'.*?</owl:NamedIndividual>\s*\n\s*\n',
            re.DOTALL,
        )
        new_content, n = pattern.subn("", content, count=1)
        if n > 0:
            content = new_content
            deleted += 1
        else:
            print(f"  NOTE: NamedIndividual &{iri_suffix} not found (may already be deleted)", file=sys.stderr)
    return content, deleted


def step2_rename_hub_classes(content: str) -> tuple[str, int]:
    """Replace IRI references for hub class renames."""
    renamed = 0
    for old, new, _ in HUB_RENAMES:
        old_token = f"&{old}"
        new_token = f"&{new}"
        n = content.count(old_token)
        if n > 0:
            content = content.replace(old_token, new_token)
            renamed += n
    return content, renamed


def step3_update_hub_labels(content: str) -> tuple[str, int]:
    """Update the rdfs:label on the four hub classes (drop "Entity" suffix)."""
    updated = 0
    for _, _, layer in HUB_RENAMES:
        old_label = f'<rdfs:label xml:lang="en">{layer}Entity</rdfs:label>'
        new_label = f'<rdfs:label xml:lang="en">{layer}</rdfs:label>'
        if old_label in content:
            content = content.replace(old_label, new_label, 1)
            updated += 1
    return content, updated


def step4_add_punning_type(content: str) -> tuple[str, int]:
    """For each renamed hub class, inject <rdf:type rdf:resource="&dg;GraphLayer"/>
    just after the opening <owl:Class rdf:about="..."> line — declares OWL 2
    punning so the IRI is also a NamedIndividual of dg:GraphLayer."""
    added = 0
    for _, new_suffix, _ in HUB_RENAMES:
        new_iri = f"&{new_suffix}"
        opening = f'<owl:Class rdf:about="{new_iri}">'
        # Find the class declaration (first occurrence — the actual declaration, not refs)
        idx = content.find(opening)
        if idx < 0:
            print(f"  WARN: hub class declaration {opening} not found", file=sys.stderr)
            continue
        # Check idempotency — see if rdf:type GraphLayer is already in the block
        block_end = content.find("</owl:Class>", idx)
        if block_end < 0:
            continue
        block = content[idx:block_end]
        if 'rdf:type rdf:resource="&dg;GraphLayer"' in block:
            continue  # already punned
        # Inject right after the opening tag
        new_opening = f'{opening}\n        <rdf:type rdf:resource="&dg;GraphLayer"/>'
        content = content[:idx] + new_opening + content[idx + len(opening):]
        added += 1
    return content, added


def step5_convert_dggraph_values(content: str) -> tuple[str, int]:
    """Convert <dg:graph>STR</dg:graph> string annotations to resource references."""
    converted = 0
    for str_val, iri_val in GRAPH_VALUE_MAP.items():
        old = f"<dg:graph>{str_val}</dg:graph>"
        new = f'<dg:graph rdf:resource="{iri_val}"/>'
        n = content.count(old)
        if n > 0:
            content = content.replace(old, new)
            converted += n
    return content, converted


def step6_add_range_to_dggraph(content: str) -> tuple[str, bool]:
    """Add rdfs:range dg:GraphLayer to the dg:graph AnnotationProperty
    declaration."""
    old = """    <owl:AnnotationProperty rdf:about="&dg;graph">
        <rdfs:label xml:lang="en">graph layer</rdfs:label>
        <rdfs:comment xml:lang="en">Logical graph partition within the single Neo4j database. Values: OntoGraph, Metagraph, ValidationGraph, KnowledgeGraph.</rdfs:comment>
    </owl:AnnotationProperty>"""
    new = """    <owl:AnnotationProperty rdf:about="&dg;graph">
        <rdfs:label xml:lang="en">graph layer</rdfs:label>
        <rdfs:comment xml:lang="en">Logical graph partition within the single Neo4j database. Values are resource references to the four punned hub IRIs that are simultaneously classes (parents of layer-member entities) and NamedIndividuals of dg:GraphLayer: dg:OntoGraph, dgm:Metagraph, dgv:ValidationGraph, dgk:KnowledgeGraph. The range below documents this; OWL annotation properties do not enforce range.</rdfs:comment>
        <rdfs:range rdf:resource="&dg;GraphLayer"/>
    </owl:AnnotationProperty>"""
    if old in content:
        content = content.replace(old, new, 1)
        return content, True
    return content, False


def step7_update_layerentity_comment(content: str) -> tuple[str, bool]:
    """Fix 3: update rdfs:comment on dg:LayerEntity."""
    old = '<rdfs:comment xml:lang="en">Abstract root for all DG entities that belong to one of the four graph layers (v3.3). Concrete top-level classes are grouped under one of: OntoGraphEntity, MetagraphEntity, ValidationGraphEntity, KnowledgeGraphEntity. Subclasses inherit layer membership transitively. Note: distinct from dg:GraphLayer, which is the enum of layer names with four NamedIndividual values.</rdfs:comment>'
    new = "<rdfs:comment xml:lang=\"en\">Abstract root for DG entities that belong to one of the four graph layers. Direct subclasses are the four layer hubs: dg:OntoGraph, dgm:Metagraph, dgv:ValidationGraph, dgk:KnowledgeGraph. Each hub IRI is simultaneously a class (grouping its layer's DG entities) AND a NamedIndividual of dg:GraphLayer via OWL 2 punning (v3.4 unified structure). dg:LayerEntity itself is intentionally NOT tagged with a dg:graph annotation because it is cross-cutting — it is the parent of all four layer hubs, not a member of any single layer.</rdfs:comment>"
    if old in content:
        content = content.replace(old, new, 1)
        return content, True
    return content, False


def step8_add_external_enrichments(content: str) -> tuple[str, int]:
    """Fix 2: add <rdf:Description> annotation blocks for 17 external classes."""
    # Check if enrichments already added (idempotency)
    if "EXTERNAL CLASS ANNOTATION ENRICHMENT" in content:
        return content, 0

    lines = [
        "",
        "    <!-- ============================================================",
        "         EXTERNAL CLASS ANNOTATION ENRICHMENT (v3.4 Fix 2)",
        "",
        "         Adds DG-perspective rdfs:label, rdfs:comment, rdfs:isDefinedBy,",
        "         and rdfs:seeAlso to the 17 external classes DG aligns with",
        "         (8 SWRL, 2 PROV-O, 2 SOSA, 2 SHACL, 1 SKOS, 2 GeoSPARQL).",
        "",
        "         These annotations are purely additive — they enrich the local",
        "         description of imported classes without changing their global",
        "         semantics. They make the Description panel in Protégé meaningful",
        "         even when imports fail to load.",
        "         ============================================================ -->",
        "",
    ]
    for prefix, local, label, comment, see_also, defined_by in ENRICHMENTS:
        lines.extend([
            f'    <rdf:Description rdf:about="&{prefix};{local}">',
            f'        <rdfs:label xml:lang="en">{label}</rdfs:label>',
            f'        <rdfs:comment xml:lang="en">{comment}</rdfs:comment>',
            f'        <rdfs:isDefinedBy rdf:resource="{defined_by}"/>',
            f'        <rdfs:seeAlso rdf:resource="{see_also}"/>',
            f'    </rdf:Description>',
            "",
        ])
    block = "\n".join(lines)
    content = content.replace("</rdf:RDF>", block + "\n</rdf:RDF>", 1)
    return content, len(ENRICHMENTS)


def step9_bump_version(content: str) -> str:
    """Bump versionInfo 3.3 → 3.4 and update seeAlso note."""
    content = content.replace(
        "<owl:versionInfo>3.3</owl:versionInfo>",
        "<owl:versionInfo>3.4</owl:versionInfo>",
        1,
    )
    old_seealso_fragment = (
        "v3.1 ontology adds: ObjectInstance, GeoRef, IdRef classes; VariableKindValue, VariableScopeValue, DesignStateKindValue enum classes; full OWL characteristics on object properties; propValue on ValidationEntity (SCHM-05). v3.2 adds cross-ontology alignments to SWRL, PROV-O, SOSA, SHACL, SKOS, DCTerms, GeoSPARQL, and OWL meta-schema — see ONTOLOGY-ALIGNMENT.md for rationale."
    )
    new_seealso_fragment = old_seealso_fragment + " v3.3 adds explicit per-layer class hubs (LayerEntity + four layer hubs). v3.4 unifies the four-layer enum and hub structure via OWL 2 punning (dg:OntoGraph / dgm:Metagraph / dgv:ValidationGraph / dgk:KnowledgeGraph each serve as both a class and a NamedIndividual of dg:GraphLayer), converts dg:graph annotation values to resource references, and adds annotation enrichment for 17 external superclasses."
    content = content.replace(old_seealso_fragment, new_seealso_fragment, 1)
    return content


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    owl = repo / "ontology" / "DesignGrammar.owl"

    content = owl.read_text(encoding="utf-8")
    if is_already_v34(content):
        print("Already at v3.4 — no changes needed.")
        return 0

    print("Phase 1: applying v3.3 → v3.4 consistency fixes")
    print("-" * 60)

    content, deleted_indivs = step1_delete_standalone_individuals(content)
    print(f"  Step 1 (delete standalone NamedIndividuals): {deleted_indivs} removed")

    content, renamed = step2_rename_hub_classes(content)
    print(f"  Step 2 (rename hub-class IRI refs):           {renamed} replacements")

    content, label_updated = step3_update_hub_labels(content)
    print(f"  Step 3 (update hub-class rdfs:label):         {label_updated} updated")

    content, punning_added = step4_add_punning_type(content)
    print(f"  Step 4 (add punning rdf:type GraphLayer):    {punning_added} added")

    content, graph_converted = step5_convert_dggraph_values(content)
    print(f"  Step 5 (dg:graph string → resource refs):    {graph_converted} converted")

    content, range_added = step6_add_range_to_dggraph(content)
    print(f"  Step 6 (add rdfs:range to dg:graph):         {'yes' if range_added else 'no'}")

    content, le_updated = step7_update_layerentity_comment(content)
    print(f"  Step 7 (update LayerEntity comment):         {'yes' if le_updated else 'no'}")

    content, enrich_count = step8_add_external_enrichments(content)
    print(f"  Step 8 (external annotation enrichments):    {enrich_count} added")

    content = step9_bump_version(content)
    print("  Step 9 (version bump 3.3 → 3.4):             done")

    owl.write_text(content, encoding="utf-8")
    print("-" * 60)
    print(f"Wrote {owl} ({owl.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

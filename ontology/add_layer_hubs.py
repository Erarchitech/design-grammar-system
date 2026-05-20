"""
Add explicit per-layer hub classes to DesignGrammar.owl so Protégé's class
hierarchy view groups DG entities by graph layer (OntoGraph / Metagraph /
ValidationGraph / KnowledgeGraph) instead of showing a flat list.

Introduces:
  - dg:LayerEntity        (abstract root)
    - dg:OntoGraphEntity
    - dgm:MetagraphEntity
    - dgv:ValidationGraphEntity
    - dgk:KnowledgeGraphEntity

Adds rdfs:subClassOf links from every top-level DG class to its layer hub.
Subclasses (ClassAtom, DefState, ObjectVariable, etc.) inherit the layer
membership transitively via their existing parent class.

Idempotent — re-running detects existing hubs/links and skips them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Map class IRI suffix (without &/;) -> hub IRI suffix
SUBCLASS_MAP: dict[str, str] = {
    # OntoGraph layer
    "dg;Class": "dg;OntoGraphEntity",
    "dg;DatatypeProperty": "dg;OntoGraphEntity",
    "dg;ObjectProperty": "dg;OntoGraphEntity",
    # Metagraph layer
    "dgm;Rule": "dgm;MetagraphEntity",
    "dgm;Atom": "dgm;MetagraphEntity",
    "dgm;Variable": "dgm;MetagraphEntity",
    "dgm;Literal": "dgm;MetagraphEntity",
    "dgm;Builtin": "dgm;MetagraphEntity",
    "dgm;DesignRuleSession": "dgm;MetagraphEntity",
    "dgm;VariableKindValue": "dgm;MetagraphEntity",
    "dgm;VariableScopeValue": "dgm;MetagraphEntity",
    # ValidationGraph layer
    "dgv;ValidationRun": "dgv;ValidationGraphEntity",
    "dgv;ValidationEntity": "dgv;ValidationGraphEntity",
    "dgv;DesignState": "dgv;ValidationGraphEntity",
    "dgv;DesignStateParameter": "dgv;ValidationGraphEntity",
    "dgv;IntegrationConfig": "dgv;ValidationGraphEntity",
    "dgv;ObjectInstance": "dgv;ValidationGraphEntity",
    "dgv;GeoRef": "dgv;ValidationGraphEntity",
    "dgv;IdRef": "dgv;ValidationGraphEntity",
    "dgv;DesignStateKindValue": "dgv;ValidationGraphEntity",
    "dgv;DesignStateParameterTypeValue": "dgv;ValidationGraphEntity",
    "dgv;ValidationStatusValue": "dgv;ValidationGraphEntity",
    "dgv;ReinstatementStatusValue": "dgv;ValidationGraphEntity",
    # KnowledgeGraph layer
    "dgk;KnowledgeClass": "dgk;KnowledgeGraphEntity",
    "dgk;KnowledgeNote": "dgk;KnowledgeGraphEntity",
    "dgk;KnowledgeTag": "dgk;KnowledgeGraphEntity",
    "dgk;KnowledgeSession": "dgk;KnowledgeGraphEntity",
}

HUB_CLASSES_BLOCK = """\
    <!-- ============================================================
         LAYER HUB CLASSES (v3.3)
         Explicit superclasses to group DG entities by graph layer in
         Protégé's class hierarchy view. Without these, all DG classes
         appear in a flat list directly under owl:Thing (or under their
         external superclass when alignments are imported). These hubs
         provide an OntoGraph / Metagraph / ValidationGraph /
         KnowledgeGraph partition matching the four-layer architecture
         described in the ontology overview.
         ============================================================ -->

    <owl:Class rdf:about="&dg;LayerEntity">
        <rdfs:label xml:lang="en">LayerEntity</rdfs:label>
        <rdfs:comment xml:lang="en">Abstract root for all DG entities that belong to one of the four graph layers (v3.3). Concrete top-level classes are grouped under one of: OntoGraphEntity, MetagraphEntity, ValidationGraphEntity, KnowledgeGraphEntity. Subclasses inherit layer membership transitively. Note: distinct from dg:GraphLayer, which is the enum of layer names with four NamedIndividual values.</rdfs:comment>
    </owl:Class>

    <owl:Class rdf:about="&dg;OntoGraphEntity">
        <rdfs:label xml:lang="en">OntoGraphEntity</rdfs:label>
        <rdfs:comment xml:lang="en">Hub class for the OntoGraph layer (dynamic domain ontology meta-schema). Top-level subclasses: Class, DatatypeProperty, ObjectProperty.</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;LayerEntity"/>
        <dg:graph>OntoGraph</dg:graph>
    </owl:Class>

    <owl:Class rdf:about="&dgm;MetagraphEntity">
        <rdfs:label xml:lang="en">MetagraphEntity</rdfs:label>
        <rdfs:comment xml:lang="en">Hub class for the Metagraph layer (SWRL rule structure). Top-level subclasses: Rule, Atom (with ClassAtom/DataPropertyAtom/ObjectPropertyAtom/BuiltinAtom children), Variable (with ObjectVariable/PropertyVariable/BuiltinVariable children), Literal, Builtin, DesignRuleSession, VariableKindValue, VariableScopeValue.</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;LayerEntity"/>
        <dg:graph>Metagraph</dg:graph>
    </owl:Class>

    <owl:Class rdf:about="&dgv;ValidationGraphEntity">
        <rdfs:label xml:lang="en">ValidationGraphEntity</rdfs:label>
        <rdfs:comment xml:lang="en">Hub class for the ValidationGraph layer (validation runs, design state, integration config). Top-level subclasses: ValidationRun, ValidationEntity, DesignState (with DefState/ObjectState children), DesignStateParameter, IntegrationConfig, ObjectInstance, GeoRef, IdRef, and four enum value classes (DesignStateKindValue, DesignStateParameterTypeValue, ValidationStatusValue, ReinstatementStatusValue).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;LayerEntity"/>
        <dg:graph>ValidationGraph</dg:graph>
    </owl:Class>

    <owl:Class rdf:about="&dgk;KnowledgeGraphEntity">
        <rdfs:label xml:lang="en">KnowledgeGraphEntity</rdfs:label>
        <rdfs:comment xml:lang="en">Hub class for the KnowledgeGraph layer (project notes, tags, sessions). Top-level subclasses: KnowledgeClass, KnowledgeNote, KnowledgeTag, KnowledgeSession.</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;LayerEntity"/>
        <dg:graph>KnowledgeGraph</dg:graph>
    </owl:Class>

"""

# Where to insert hub block: right after the closing of the dg:KnowledgeGraphLayer
# NamedIndividual (the last of the four GraphLayer named individuals).
HUB_INSERT_ANCHOR = """    <owl:NamedIndividual rdf:about="&dg;KnowledgeGraphLayer">
        <rdf:type rdf:resource="&dg;GraphLayer"/>
        <rdfs:label xml:lang="en">KnowledgeGraph</rdfs:label>
        <rdfs:comment xml:lang="en">Project knowledge storage layer. Contains KnowledgeNote, KnowledgeTag, KnowledgeSession, and KnowledgeClass nodes. Stores architectural knowledge ingested from project documentation or NL prompts.</rdfs:comment>
    </owl:NamedIndividual>

"""


def add_subclass_to_class(content: str, class_suffix: str, hub_suffix: str) -> tuple[str, bool]:
    """Find <owl:Class rdf:about="&{class_suffix}"> ... </owl:Class> block and
    inject <rdfs:subClassOf rdf:resource="&{hub_suffix}"/> just before its
    closing </owl:Class>. Idempotent: returns unchanged if already present.
    Returns (new_content, changed)."""

    # Match the opening tag and capture everything up to the corresponding </owl:Class>
    # using non-greedy match.
    pattern = re.compile(
        rf'(<owl:Class rdf:about="&{re.escape(class_suffix)}">.*?)(\s*</owl:Class>)',
        re.DOTALL,
    )

    match = pattern.search(content)
    if not match:
        print(f"  WARN: class &{class_suffix} not found", file=sys.stderr)
        return content, False

    block_body, closing = match.group(1), match.group(2)

    # Check idempotency — skip if hub link already present
    hub_marker = f'<rdfs:subClassOf rdf:resource="&{hub_suffix}"/>'
    if hub_marker in block_body:
        return content, False

    # Inject the new subClassOf right before </owl:Class>, preserving indentation
    injected = block_body + f"\n        {hub_marker}"
    new_content = content[: match.start()] + injected + closing + content[match.end():]
    return new_content, True


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    owl = repo / "ontology" / "DesignGrammar.owl"
    content = owl.read_text(encoding="utf-8")
    original_len = len(content)

    # 1. Insert hub classes block if not already present
    if "&dg;LayerEntity" in content:
        print("Hub block already present — skipping insertion.")
        hub_inserted = False
    else:
        if HUB_INSERT_ANCHOR not in content:
            print("ERROR: anchor for hub insertion not found "
                  "(KnowledgeGraphLayer NamedIndividual block).", file=sys.stderr)
            return 1
        content = content.replace(HUB_INSERT_ANCHOR, HUB_INSERT_ANCHOR + HUB_CLASSES_BLOCK, 1)
        hub_inserted = True
        print("Inserted 5 hub classes (LayerEntity + 4 per-layer hubs).")

    # 2. Add subClassOf to each top-level class
    added = 0
    skipped = 0
    for class_suffix, hub_suffix in SUBCLASS_MAP.items():
        content, changed = add_subclass_to_class(content, class_suffix, hub_suffix)
        if changed:
            added += 1
        else:
            skipped += 1

    # 3. Bump version if any change was made
    if hub_inserted or added > 0:
        content = content.replace(
            "<owl:versionInfo>3.2</owl:versionInfo>",
            "<owl:versionInfo>3.3</owl:versionInfo>",
            1,
        )

    owl.write_text(content, encoding="utf-8")
    final_len = len(content)

    print(f"Subclass links: {added} added, {skipped} already present (idempotent).")
    print(f"File size: {original_len:,} -> {final_len:,} bytes (+{final_len - original_len:,}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

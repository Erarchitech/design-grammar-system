"""
Phase 3: v4.0 → v4.1 — eliminate degenerate enum classes.

Removes two enum classes that duplicate existing class hierarchies, replacing
the discriminator pattern with the more idiomatic OWL approach (class-based
discrimination + owl:disjointUnionOf).

  Change 1 — Eliminate DesignStateKindValue redundancy:
    - Delete dgv:DesignStateKindValue class
    - Delete NamedIndividuals DesignStateKind_DefState, DesignStateKind_ObjectState
    - Delete dgv:kind ObjectProperty
    - Add owl:disjointUnionOf on dgv:DesignState → (DefState, ObjectState)
    - Strip dgv:kind property assertions from all ABox instances
    - Remove DesignStateKindValue from the AllDisjointClasses enum group

  Change 2 — Eliminate VariableKindValue redundancy:
    - Delete dgm:VariableKindValue class
    - Delete NamedIndividuals VariableKind_Object, VariableKind_Property, VariableKind_Builtin
    - Delete dgm:variableKind ObjectProperty
    - Add owl:disjointUnionOf on dgm:Variable → (ObjectVariable, PropertyVariable, BuiltinVariable)
    - Strip dgm:variableKind property assertions from all ABox instances
    - Remove VariableKindValue from the AllDisjointClasses enum group

  Change 3 — VariableScope derivation:
    - Add SubClassOf restrictions on ObjectVariable and PropertyVariable so that
      variableScope is inferred from variable kind (rdf:type).
    - Strip dgm:variableScope property assertions from ABox (now inferred).
    - Keep VariableScopeValue class and its individuals (genuine enum, no class duality).

  Change 4 — Close GraphLayer with owl:oneOf:
    - Add owl:oneOf closure listing the four punned layer IRIs
      (dg:OntoGraph, dgm:Metagraph, dgv:ValidationGraph, dgk:KnowledgeGraph).
    - Brings GraphLayer in line with the other 4 enum classes in v4.0.

  Change 5 — Update class comments to document Neo4j storage mirror:
    - DesignState comment explains the Neo4j `kind` property pattern.
    - Variable comment explains the Neo4j discriminator pattern.

  Change 6 — Bump version 4.0 → 4.1.

Output: in-place rewrite of DesignGrammar.owl (core only — facade unaffected).
Idempotent: re-running detects v4.1 state and exits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def is_already_v41(content: str) -> bool:
    return "<owl:versionInfo>4.1</owl:versionInfo>" in content


def must_be_v40(content: str) -> bool:
    return "<owl:versionInfo>4.0</owl:versionInfo>" in content


# ============================================================
# Step 1: Delete enum class declarations (DesignStateKindValue, VariableKindValue)
# ============================================================

DELETE_CLASSES = [
    "&dgv;DesignStateKindValue",
    "&dgm;VariableKindValue",
]


def delete_class_blocks(content: str) -> tuple[str, int]:
    """Delete <owl:Class rdf:about="&iri">...</owl:Class> blocks for the listed
    classes. These classes had owl:oneOf closures, so the regex must be DOTALL."""
    deleted = 0
    for iri in DELETE_CLASSES:
        pattern = re.compile(
            rf'    <owl:Class rdf:about="{re.escape(iri)}">\s*.*?</owl:Class>\s*\n',
            re.DOTALL,
        )
        new_content, n = pattern.subn("", content, count=1)
        if n > 0:
            content = new_content
            deleted += 1
    return content, deleted


# ============================================================
# Step 2: Delete NamedIndividuals
# ============================================================

DELETE_INDIVIDUALS = [
    "&dgv;DesignStateKind_DefState",
    "&dgv;DesignStateKind_ObjectState",
    "&dgm;VariableKind_Object",
    "&dgm;VariableKind_Property",
    "&dgm;VariableKind_Builtin",
]


def delete_individual_blocks(content: str) -> tuple[str, int]:
    deleted = 0
    for iri in DELETE_INDIVIDUALS:
        pattern = re.compile(
            rf'    <owl:NamedIndividual rdf:about="{re.escape(iri)}">\s*.*?</owl:NamedIndividual>\s*\n',
            re.DOTALL,
        )
        new_content, n = pattern.subn("", content, count=1)
        if n > 0:
            content = new_content
            deleted += 1
    return content, deleted


# ============================================================
# Step 3: Delete ObjectProperties (dgv:kind, dgm:variableKind)
# ============================================================

DELETE_OBJECT_PROPERTIES = [
    "&dgv;kind",
    "&dgm;variableKind",
]


def delete_object_property_blocks(content: str) -> tuple[str, int]:
    deleted = 0
    for iri in DELETE_OBJECT_PROPERTIES:
        pattern = re.compile(
            rf'    <owl:ObjectProperty rdf:about="{re.escape(iri)}">\s*.*?</owl:ObjectProperty>\s*\n',
            re.DOTALL,
        )
        new_content, n = pattern.subn("", content, count=1)
        if n > 0:
            content = new_content
            deleted += 1
    return content, deleted


# ============================================================
# Step 4: Strip ABox property assertions for the deleted properties
# ============================================================

# Property assertions to strip (matched as single inline tags)
ABOX_STRIP_PROPERTIES = [
    "dgv:kind",
    "dgm:variableKind",
    "dgm:variableScope",  # also redundant now — derived via SubClassOf restriction
]


def strip_abox_property_assertions(content: str) -> tuple[str, int]:
    """Remove inline <PROP rdf:resource="..."/> assertions from individual blocks.
    These are now redundant — rdf:type plus the disjointUnionOf / derivation
    axioms infer them automatically."""
    stripped = 0
    for prop in ABOX_STRIP_PROPERTIES:
        # Match the property tag (single-line self-closing form) plus surrounding whitespace/newline
        pattern = re.compile(rf'\s*<{re.escape(prop)} rdf:resource="[^"]+"/>\n')
        new_content, n = pattern.subn("\n", content)
        if n > 0:
            content = new_content
            stripped += n
    return content, stripped


# ============================================================
# Step 5: Add disjointUnionOf axioms on parent classes
# ============================================================

def add_disjoint_union_designstate(content: str) -> tuple[str, bool]:
    """Replace the DesignState class declaration to include owl:disjointUnionOf."""
    old = """    <owl:Class rdf:about="&dgv;DesignState">
        <rdfs:label xml:lang="en">DesignState</rdfs:label>
        <rdfs:comment xml:lang="en">A snapshot of design parameters captured from Grasshopper. Single Neo4j label :DesignState with a `kind` property discriminating between DefState and ObjectState. ID prefixes: DS_ (DefState), OS_ (ObjectState). Used as input to CLASSIFICATOR and persisted in validation runs.</rdfs:comment>
        <dg:graph rdf:resource="&dgv;ValidationGraph"/>
    </owl:Class>"""
    new = """    <owl:Class rdf:about="&dgv;DesignState">
        <rdfs:label xml:lang="en">DesignState</rdfs:label>
        <rdfs:comment xml:lang="en">A snapshot of design parameters captured from Grasshopper. Every DesignState individual is necessarily a DefState OR an ObjectState (owl:disjointUnionOf below) — never both, never neither. ID prefixes: DS_ (DefState), OS_ (ObjectState). Used as input to CLASSIFICATOR and persisted in validation runs. STORAGE NOTE: In the Neo4j layer (SCHM-01), this discrimination is materialized as a `kind` property with values "DefState" | "ObjectState" on a single :DesignState node label — a runtime convenience because Cypher does not infer subclass membership. The OWL ontology does not include the kind property because rdf:type plus disjointUnionOf already discriminate (v4.1).</rdfs:comment>
        <owl:disjointUnionOf rdf:parseType="Collection">
            <owl:Class rdf:about="&dgv;DefState"/>
            <owl:Class rdf:about="&dgv;ObjectState"/>
        </owl:disjointUnionOf>
        <dg:graph rdf:resource="&dgv;ValidationGraph"/>
    </owl:Class>"""
    if old in content:
        return content.replace(old, new, 1), True
    return content, False


def add_disjoint_union_variable(content: str) -> tuple[str, bool]:
    """Replace the Variable class declaration to include owl:disjointUnionOf."""
    old = """    <owl:Class rdf:about="&dgm;Variable">
        <rdfs:label xml:lang="en">Variable</rdfs:label>
        <rdfs:comment xml:lang="en">A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Variable kind (Object vs Property) is inferred at read-time from atom structure (VTYP-01). MERGE key includes project to prevent cross-project collision (SCHM-02).</rdfs:comment>
        <owl:equivalentClass rdf:resource="&swrl;Variable"/>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    new = """    <owl:Class rdf:about="&dgm;Variable">
        <rdfs:label xml:lang="en">Variable</rdfs:label>
        <rdfs:comment xml:lang="en">A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Every Variable individual is necessarily an ObjectVariable, PropertyVariable, OR BuiltinVariable (owl:disjointUnionOf below — VTYP-01 priority chain). MERGE key includes project to prevent cross-project collision (SCHM-02). STORAGE NOTE: In the Neo4j layer, variable kind is inferred at read time by VariableTypeInferrer.Infer() — not stored on the Var node. The OWL ontology uses rdf:type plus disjointUnionOf to discriminate; no separate kind property exists (v4.1).</rdfs:comment>
        <owl:disjointUnionOf rdf:parseType="Collection">
            <owl:Class rdf:about="&dgm;ObjectVariable"/>
            <owl:Class rdf:about="&dgm;PropertyVariable"/>
            <owl:Class rdf:about="&dgm;BuiltinVariable"/>
        </owl:disjointUnionOf>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    # Note: this version assumes swrl: alignment is in the core. After v4.0 split it's NOT in core.
    # Fall back: try without the equivalentClass line.
    if old in content:
        return content.replace(old, new, 1), True
    # Fallback for v4.0 split state (no inline alignment)
    old_v40 = """    <owl:Class rdf:about="&dgm;Variable">
        <rdfs:label xml:lang="en">Variable</rdfs:label>
        <rdfs:comment xml:lang="en">A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Variable kind (Object vs Property) is inferred at read-time from atom structure (VTYP-01). MERGE key includes project to prevent cross-project collision (SCHM-02).</rdfs:comment>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    new_v40 = """    <owl:Class rdf:about="&dgm;Variable">
        <rdfs:label xml:lang="en">Variable</rdfs:label>
        <rdfs:comment xml:lang="en">A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Every Variable individual is necessarily an ObjectVariable, PropertyVariable, OR BuiltinVariable (owl:disjointUnionOf below — VTYP-01 priority chain). MERGE key includes project to prevent cross-project collision (SCHM-02). STORAGE NOTE: In the Neo4j layer, variable kind is inferred at read time by VariableTypeInferrer.Infer() — not stored on the Var node. The OWL ontology uses rdf:type plus disjointUnionOf to discriminate; no separate kind property exists (v4.1).</rdfs:comment>
        <owl:disjointUnionOf rdf:parseType="Collection">
            <owl:Class rdf:about="&dgm;ObjectVariable"/>
            <owl:Class rdf:about="&dgm;PropertyVariable"/>
            <owl:Class rdf:about="&dgm;BuiltinVariable"/>
        </owl:disjointUnionOf>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    if old_v40 in content:
        return content.replace(old_v40, new_v40, 1), True
    return content, False


# ============================================================
# Step 6: Add VariableScope derivation axioms to ObjectVariable/PropertyVariable
# ============================================================

def add_scope_derivation_objectvariable(content: str) -> tuple[str, bool]:
    old = """    <owl:Class rdf:about="&dgm;ObjectVariable">
        <rdfs:label xml:lang="en">ObjectVariable</rdfs:label>
        <rdfs:comment xml:lang="en">A variable representing a domain entity instance (e.g. ?b for Building). Inferred from ClassAtom arguments (VTYP-01). Object variables are cross-rule scoped: the same variable name maps to the same entity across all rules in a project (VTYP-02). Can be wired to OBJECT STATE component to create ObjectState (CMPST-01).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dgm;Variable"/>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    new = """    <owl:Class rdf:about="&dgm;ObjectVariable">
        <rdfs:label xml:lang="en">ObjectVariable</rdfs:label>
        <rdfs:comment xml:lang="en">A variable representing a domain entity instance (e.g. ?b for Building). Inferred from ClassAtom arguments (VTYP-01). Object variables are cross-rule scoped: the same variable name maps to the same entity across all rules in a project (VTYP-02). Can be wired to OBJECT STATE component to create ObjectState (CMPST-01). The cross-rule scope is inferred by reasoner via the SubClassOf restriction below (v4.1).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dgm;Variable"/>
        <rdfs:subClassOf>
            <owl:Restriction>
                <owl:onProperty rdf:resource="&dgm;variableScope"/>
                <owl:hasValue rdf:resource="&dgm;VariableScope_CrossRule"/>
            </owl:Restriction>
        </rdfs:subClassOf>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    if old in content:
        return content.replace(old, new, 1), True
    return content, False


def add_scope_derivation_propertyvariable(content: str) -> tuple[str, bool]:
    old = """    <owl:Class rdf:about="&dgm;PropertyVariable">
        <rdfs:label xml:lang="en">PropertyVariable</rdfs:label>
        <rdfs:comment xml:lang="en">A variable representing a datatype property value (e.g. ?h for height). Inferred from DataPropertyAtom arg-2 position (VTYP-01). Property variables are rule-scoped: the same name in different rules represents independent variables (VTYP-03).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dgm;Variable"/>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    new = """    <owl:Class rdf:about="&dgm;PropertyVariable">
        <rdfs:label xml:lang="en">PropertyVariable</rdfs:label>
        <rdfs:comment xml:lang="en">A variable representing a datatype property value (e.g. ?h for height). Inferred from DataPropertyAtom arg-2 position (VTYP-01). Property variables are rule-scoped: the same name in different rules represents independent variables (VTYP-03). The rule-local scope is inferred by reasoner via the SubClassOf restriction below (v4.1).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dgm;Variable"/>
        <rdfs:subClassOf>
            <owl:Restriction>
                <owl:onProperty rdf:resource="&dgm;variableScope"/>
                <owl:hasValue rdf:resource="&dgm;VariableScope_RuleLocal"/>
            </owl:Restriction>
        </rdfs:subClassOf>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>"""
    if old in content:
        return content.replace(old, new, 1), True
    return content, False


# ============================================================
# Step 7: Close GraphLayer with owl:oneOf
# ============================================================

def close_graphlayer(content: str) -> tuple[str, bool]:
    old = """    <owl:Class rdf:about="&dg;GraphLayer">
        <rdfs:label xml:lang="en">GraphLayer</rdfs:label>
        <rdfs:comment xml:lang="en">A logical partition of the single Neo4j database. The Design Grammar System organizes all persisted nodes into four layers: OntoGraph, Metagraph, ValidationGraph, KnowledgeGraph. Every node carries a `graph` property identifying its layer.</rdfs:comment>
    </owl:Class>"""
    new = """    <owl:Class rdf:about="&dg;GraphLayer">
        <rdfs:label xml:lang="en">GraphLayer</rdfs:label>
        <rdfs:comment xml:lang="en">A logical partition of the single Neo4j database. The Design Grammar System organizes all persisted nodes into exactly four layers (closed enumeration via owl:oneOf below, v4.1): OntoGraph, Metagraph, ValidationGraph, KnowledgeGraph. The four layer IRIs are punned per OWL 2 — each is both a class (parent of the layer's DG entities, under LayerEntity) and an individual (member of this GraphLayer enum). Every DG class carries a `dg:graph` annotation pointing at its layer.</rdfs:comment>
        <owl:equivalentClass>
            <owl:Class>
                <owl:oneOf rdf:parseType="Collection">
                    <owl:NamedIndividual rdf:about="&dg;OntoGraph"/>
                    <owl:NamedIndividual rdf:about="&dgm;Metagraph"/>
                    <owl:NamedIndividual rdf:about="&dgv;ValidationGraph"/>
                    <owl:NamedIndividual rdf:about="&dgk;KnowledgeGraph"/>
                </owl:oneOf>
            </owl:Class>
        </owl:equivalentClass>
    </owl:Class>"""
    if old in content:
        return content.replace(old, new, 1), True
    return content, False


# ============================================================
# Step 8: Update AllDisjointClasses enum group (remove deleted classes)
# ============================================================

def update_disjoint_enums_group(content: str) -> tuple[str, bool]:
    old = """    <!-- Enum classes are mutually exclusive -->
    <rdf:Description>
        <rdf:type rdf:resource="&owl;AllDisjointClasses"/>
        <owl:members rdf:parseType="Collection">
            <owl:Class rdf:about="&dgm;VariableKindValue"/>
            <owl:Class rdf:about="&dgm;VariableScopeValue"/>
            <owl:Class rdf:about="&dgv;DesignStateKindValue"/>
            <owl:Class rdf:about="&dgv;DesignStateParameterTypeValue"/>
            <owl:Class rdf:about="&dgv;ValidationStatusValue"/>
            <owl:Class rdf:about="&dgv;ReinstatementStatusValue"/>
        </owl:members>
    </rdf:Description>"""
    new = """    <!-- Enum classes are mutually exclusive (v4.1: VariableKindValue and DesignStateKindValue removed — their semantic role is now provided by class hierarchies + disjointUnionOf on Variable and DesignState) -->
    <rdf:Description>
        <rdf:type rdf:resource="&owl;AllDisjointClasses"/>
        <owl:members rdf:parseType="Collection">
            <owl:Class rdf:about="&dgm;VariableScopeValue"/>
            <owl:Class rdf:about="&dgv;DesignStateParameterTypeValue"/>
            <owl:Class rdf:about="&dgv;ValidationStatusValue"/>
            <owl:Class rdf:about="&dgv;ReinstatementStatusValue"/>
        </owl:members>
    </rdf:Description>"""
    if old in content:
        return content.replace(old, new, 1), True
    return content, False


# ============================================================
# Step 9: Bump version + extend seeAlso
# ============================================================

def bump_version(content: str) -> str:
    content = content.replace(
        "<owl:versionInfo>4.0</owl:versionInfo>",
        "<owl:versionInfo>4.1</owl:versionInfo>",
        1,
    )
    marker = "this core file now contains only DG content with no external imports."
    addendum = (
        " v4.1 eliminates two degenerate enum classes (DesignStateKindValue and VariableKindValue) "
        "whose values duplicated existing class hierarchies; replaces them with owl:disjointUnionOf "
        "on DesignState and Variable; closes GraphLayer with owl:oneOf; adds VariableScope derivation "
        "axioms; and removes the now-redundant dgv:kind and dgm:variableKind ObjectProperties."
    )
    if marker in content:
        content = content.replace(marker, marker + addendum, 1)
    return content


# ============================================================
# Main
# ============================================================

def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    owl = repo / "ontology" / "DesignGrammar.owl"
    content = owl.read_text(encoding="utf-8")

    if is_already_v41(content):
        print("Already at v4.1 — no changes.")
        return 0
    if not must_be_v40(content):
        print("ERROR: expected v4.0 source — run apply_v40_split.py first.", file=sys.stderr)
        return 1

    print("Phase 3: applying v4.0 → v4.1 simplification")
    print("-" * 60)

    content, n_classes = delete_class_blocks(content)
    print(f"  Step 1 (delete enum classes):                {n_classes} removed")

    content, n_indivs = delete_individual_blocks(content)
    print(f"  Step 2 (delete NamedIndividuals):            {n_indivs} removed")

    content, n_props = delete_object_property_blocks(content)
    print(f"  Step 3 (delete ObjectProperties):            {n_props} removed")

    content, n_stripped = strip_abox_property_assertions(content)
    print(f"  Step 4 (strip ABox property assertions):     {n_stripped} stripped")

    content, ds_ok = add_disjoint_union_designstate(content)
    print(f"  Step 5a (DesignState disjointUnionOf):       {'yes' if ds_ok else 'NO — anchor not found'}")

    content, var_ok = add_disjoint_union_variable(content)
    print(f"  Step 5b (Variable disjointUnionOf):          {'yes' if var_ok else 'NO — anchor not found'}")

    content, ov_ok = add_scope_derivation_objectvariable(content)
    print(f"  Step 6a (ObjectVariable scope derivation):   {'yes' if ov_ok else 'NO — anchor not found'}")

    content, pv_ok = add_scope_derivation_propertyvariable(content)
    print(f"  Step 6b (PropertyVariable scope derivation): {'yes' if pv_ok else 'NO — anchor not found'}")

    content, gl_ok = close_graphlayer(content)
    print(f"  Step 7 (GraphLayer owl:oneOf closure):       {'yes' if gl_ok else 'NO — anchor not found'}")

    content, dj_ok = update_disjoint_enums_group(content)
    print(f"  Step 8 (update AllDisjointClasses enum):     {'yes' if dj_ok else 'NO — anchor not found'}")

    content = bump_version(content)
    print("  Step 9 (version bump 4.0 → 4.1):             done")

    owl.write_text(content, encoding="utf-8")
    print("-" * 60)
    print(f"Wrote {owl} ({owl.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

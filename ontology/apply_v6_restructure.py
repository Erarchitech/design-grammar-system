#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_v6_restructure.py — Generate DesignGrammar-V6.owl from DesignGrammar.owl.

v5.0 -> v6.0 restructure (ontology-only, originals untouched):
  * New top-level dg:Core band of over-layer entities (Gero FBS Object/Function/
    Behavior/Structure, Geometry, Topology, DesignState{ObjectState,DefState},
    and a unified Session).
  * IRI shortening: metagraph#->meta#, validation#->valid#, computation#->comp#.
  * Knowledge layer renamed to Spec: knowledge#->spec# (dgk->dgs),
    KnowledgeGraph/Class/Note/Tag -> SpecGraph/SpecClass/SpecNote/SpecTag.
  * Reasoner relocated dgm: -> dgv: (ValidationGraph); = GH "Validator" component.
  * Session unified: dgm:DesignRuleSession + dgk:KnowledgeSession -> dg:Session.
  * dgc:ParametricState dropped (state represented by Core dg:DesignState).
  * New props: dg:objectRef, dg:definesFunction, dgv:refersToGeometry, dgm:validates.

The script is a sequence of exact/regex string transforms ordered to avoid
collisions. It prints a self-check at the end. Run from the ontology/ folder.
"""
import re
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "DesignGrammar.owl"
DST = HERE / "DesignGrammar-V6.owl"

t = SRC.read_text(encoding="utf-8")
orig_len = len(t)


def must_replace(text, old, new, n=None, label=""):
    """replace and assert it actually happened (count > 0 or == n)."""
    c = text.count(old)
    if n is not None and c != n:
        raise SystemExit(f"[FAIL] expected {n} of {label or old!r}, found {c}")
    if c == 0:
        raise SystemExit(f"[FAIL] not found: {label or old!r}")
    return text.replace(old, new)


def delete_block(text, open_tag, close_tag, label=""):
    """Delete one block from open_tag .. close_tag (incl. leading whitespace/newline)."""
    pat = re.compile(r"\n[ \t]*" + re.escape(open_tag) + r".*?" + re.escape(close_tag), re.DOTALL)
    new, n = pat.subn("", text, count=1)
    if n != 1:
        raise SystemExit(f"[FAIL] delete_block did not match: {label or open_tag!r}")
    return new


def del_line(text, line_core, label="", count=1):
    """Delete a self-closing member line like <owl:Class rdf:about="X"/> with its indent+newline."""
    pat = re.compile(r"\n[ \t]*" + re.escape(line_core))
    new, n = pat.subn("", text, count=count)
    if n != count:
        raise SystemExit(f"[FAIL] del_line matched {n}!={count}: {label or line_core!r}")
    return new


# ============================================================
# PHASE 0 — block deletions / whole-block replacements (original IRIs)
# ============================================================

# 0a DesignRuleSession class
t = delete_block(t, '<owl:Class rdf:about="&dgm;DesignRuleSession">', "</owl:Class>", "dgm:DesignRuleSession class")
# 0b dgm session datatype-property defs
for p in ("sessionId", "sessionMode", "sessionPrompt", "sessionResult"):
    t = delete_block(t, f'<owl:DatatypeProperty rdf:about="&dgm;{p}">', "</owl:DatatypeProperty>", f"dgm:{p}")
# 0c KnowledgeSession class
t = delete_block(t, '<owl:Class rdf:about="&dgk;KnowledgeSession">', "</owl:Class>", "dgk:KnowledgeSession class")
# 0d dgk knowledgeSessionId + mode prop defs
t = delete_block(t, '<owl:DatatypeProperty rdf:about="&dgk;knowledgeSessionId">', "</owl:DatatypeProperty>", "dgk:knowledgeSessionId")
t = delete_block(t, '<owl:DatatypeProperty rdf:about="&dgk;mode">', "</owl:DatatypeProperty>", "dgk:mode")
# 0e ParametricState class
t = delete_block(t, '<owl:Class rdf:about="&dgc;ParametricState">', "</owl:Class>", "dgc:ParametricState class")
# 0f hasState object property
t = delete_block(t, '<owl:ObjectProperty rdf:about="&dgc;hasState">', "</owl:ObjectProperty>", "dgc:hasState")
# 0g State_Frame_Default individual
t = delete_block(t, '<owl:NamedIndividual rdf:about="&dgc;State_Frame_Default">', "</owl:NamedIndividual>", "State_Frame_Default")

# 0h Reasoner whole-block replace (move dgm->dgv, new comment) — uses original tokens
OLD_REASONER = (
    '    <owl:Class rdf:about="&dgm;Reasoner">\n'
    '        <rdfs:label xml:lang="en">Reasoner</rdfs:label>\n'
    '        <rdfs:comment xml:lang="en">An evaluation engine concept representing the strategy used to apply rules to parametric state. Different reasoners may process rules differently (SWRL forward-chaining, Grasshopper constraint solver, parametric propagation). Linked from RuleSet and from dgc:Function (as the mechanism that evaluates design intent).</rdfs:comment>\n'
    '        <dg:graph rdf:resource="&dgm;Metagraph"/>\n'
    '        <rdfs:subClassOf rdf:resource="&dgm;Metagraph"/>\n'
    '    </owl:Class>'
)
NEW_REASONER = (
    '    <owl:Class rdf:about="&dgv;Reasoner">\n'
    '        <rdfs:label xml:lang="en">Reasoner</rdfs:label>\n'
    '        <rdfs:comment xml:lang="en">An evaluation engine concept representing the strategy used to apply rules to design state. Different reasoners may process rules differently (SWRL forward-chaining, Grasshopper constraint solver, parametric propagation). Linked from RuleSet (dgm:usesReasoner) and from Core Function (dg:evaluatedBy, as the mechanism that evaluates design intent). Corresponds to the Grasshopper "Validator" add-in component. Reconsidered as part of the ValidationGraph layer in v6.0.</rdfs:comment>\n'
    '        <dg:graph rdf:resource="&dgv;ValidationGraph"/>\n'
    '        <rdfs:subClassOf rdf:resource="&dgv;ValidationGraph"/>\n'
    '    </owl:Class>'
)
t = must_replace(t, OLD_REASONER, NEW_REASONER, 1, "Reasoner block")

# ============================================================
# PHASE 1 — disjointness member edits (original IRIs, before renames)
# ============================================================
# 1a Metagraph set: remove DesignRuleSession + Reasoner members
t = del_line(t, '<owl:Class rdf:about="&dgm;DesignRuleSession"/>', "disjoint dgm:DesignRuleSession")
t = del_line(t, '<owl:Class rdf:about="&dgm;Reasoner"/>', "disjoint dgm:Reasoner")
# 1b Validation set: DesignState -> Reasoner (newline-anchored to avoid the
#    20-space capturedAtUtc union member colliding via substring match)
_pat_ds = re.compile(r'\n {12}<owl:Class rdf:about="&dgv;DesignState"/>')
_n = len(_pat_ds.findall(t))
if _n != 1:
    raise SystemExit(f"[FAIL] expected 1 disjoint dgv:DesignState member line, found {_n}")
t = _pat_ds.sub('\n            <owl:Class rdf:about="&dgv;Reasoner"/>', t, count=1)
# 1c Spec set: remove KnowledgeSession member
t = del_line(t, '<owl:Class rdf:about="&dgk;KnowledgeSession"/>', "disjoint dgk:KnowledgeSession")
# 1d Computation set: remove FBS + ParametricState + Geometry + Topology members
for iri in ("&dgc;Object", "&dgc;Function", "&dgc;Behavior", "&dgc;Structure",
            "&dgc;ParametricState", "&dgc;Geometry", "&dgc;Topology"):
    t = del_line(t, f'<owl:Class rdf:about="{iri}"/>', f"disjoint {iri}")

# ============================================================
# PHASE 2 — namespace / IRI renames (global)
# ============================================================
# 2a IRI shortening (only appears in ENTITY values)
t = must_replace(t, "design-grammar/metagraph#", "design-grammar/meta#", 1, "meta IRI")
t = must_replace(t, "design-grammar/validation#", "design-grammar/valid#", 1, "valid IRI")
t = must_replace(t, "design-grammar/computation#", "design-grammar/comp#", 1, "comp IRI")
# 2b dgk -> dgs (entity decl, xmlns, entity refs)
t = must_replace(t, '<!ENTITY dgk     "http://example.org/design-grammar/knowledge#">',
                 '<!ENTITY dgs     "http://example.org/design-grammar/spec#">', 1, "dgk ENTITY")
t = must_replace(t, 'xmlns:dgk="&dgk;"', 'xmlns:dgs="&dgs;"', 1, "xmlns:dgk")
t = t.replace("&dgk;", "&dgs;")
# 2c move-to-Core dgc -> dg (compound names first)
for nm in ("Object_Frame", "Behavior_Frame", "Structure_Frame",
           "objectName", "hasFunction", "hasBehavior", "hasStructure",
           "hasGeometry", "hasTopology", "evaluatedBy",
           "Object", "Function", "Behavior", "Structure", "Geometry", "Topology"):
    t = t.replace(f"&dgc;{nm}", f"&dg;{nm}")
# 2d state classes dgv -> dg
t = re.sub(r"&dgv;DesignState(?![A-Za-z0-9_])", "&dg;DesignState", t)  # not DesignStateParameter / ...TypeValue
t = t.replace("&dgv;DefState", "&dg;DefState")
t = t.replace("&dgv;ObjectState", "&dg;ObjectState")
# state instance IRIs -> dg
t = t.replace("&dgv;OS_b1_var_b", "&dg;OS_b1_var_b")
t = t.replace("&dgv;DS_def_h25_w12", "&dg;DS_def_h25_w12")
# 2e Reasoner dgm -> dgv (remaining refs: usesReasoner range, evaluatedBy range, reasonerName def)
t = t.replace("&dgm;Reasoner", "&dgv;Reasoner")
t = t.replace("&dgm;reasonerName", "&dgv;reasonerName")
# 2f spec local renames + KnowledgeSession instance type -> dg:Session
t = t.replace("&dgs;KnowledgeGraph", "&dgs;SpecGraph")
t = t.replace("&dgs;KnowledgeClass", "&dgs;SpecClass")
t = t.replace("&dgs;KnowledgeNote", "&dgs;SpecNote")
t = t.replace("&dgs;KnowledgeTag", "&dgs;SpecTag")
t = t.replace("&dgs;KnowledgeSession", "&dg;Session")  # rdf:type on 5 KS instances
# KC_KnowledgeSession hub instance IRI -> KC_Session
t = t.replace("&dgs;KC_KnowledgeSession", "&dgs;KC_Session")
# 2g session instance IRIs -> dg
for ks in ("Session_ks_mnq4ixld", "Session_ks_1d599d7a40a1", "Session_ks_mnp1jw35",
           "Session_ks_mnoon96l", "Session_ks_mnoom0r3"):
    t = t.replace(f"&dgs;{ks}", f"&dg;{ks}")
for drs in ("drs_96d1ebd8dc8a", "drs_4cab136231cf", "drs_79ba197cc693", "drs_ac4c176afeeb"):
    t = t.replace(f"&dgm;{drs}", f"&dg;{drs}")
# 2h DRS instance rdf:type -> dg:Session (class decl already deleted)
t = t.replace("&dgm;DesignRuleSession", "&dg;Session")
# 2i rename dgv:objectRef (string) -> dgv:objectRefName to free objectRef for new object property
t = t.replace("&dgv;objectRef", "&dgv;objectRefName")

# ============================================================
# PHASE 3 — element-tag prefix renames (XML qnames)
# ============================================================
# 3a knowledge session element tags -> dg, then generic dgk -> dgs
t = t.replace("<dgk:knowledgeSessionId>", "<dg:sessionId>").replace("</dgk:knowledgeSessionId>", "</dg:sessionId>")
t = t.replace("<dgk:mode>", "<dg:sessionMode>").replace("</dgk:mode>", "</dg:sessionMode>")
t = t.replace("<dgk:", "<dgs:").replace("</dgk:", "</dgs:")
# 3b moved dgc props element tags -> dg
for nm in ("objectName", "hasFunction", "hasBehavior", "hasStructure", "hasGeometry", "hasTopology", "evaluatedBy"):
    t = t.replace(f"dgc:{nm}", f"dg:{nm}")
# 3c dgm session prop element tags -> dg
for nm in ("sessionId", "sessionMode", "sessionPrompt", "sessionResult"):
    t = t.replace(f"dgm:{nm}", f"dg:{nm}")
# 3d reasonerName element tag (if any) -> dgv
t = t.replace("dgm:reasonerName", "dgv:reasonerName")
# 3e objectRef element tag rename (string prop usages)
t = t.replace("dgv:objectRef", "dgv:objectRefName")

# ============================================================
# PHASE 4 — reparent moved class blocks
# ============================================================

def reparent(text, iri, old_graph, label=""):
    m = re.search(r'<owl:Class rdf:about="' + re.escape(iri) + r'">.*?</owl:Class>', text, re.DOTALL)
    if not m:
        raise SystemExit(f"[FAIL] reparent block not found: {label or iri}")
    block = m.group(0)
    nb = re.sub(r'\n[ \t]*<dg:graph rdf:resource="' + re.escape(old_graph) + r'"/>', "", block)
    nb = nb.replace(f'<rdfs:subClassOf rdf:resource="{old_graph}"/>',
                    '<rdfs:subClassOf rdf:resource="&dg;Core"/>')
    return text.replace(block, nb)


def drop_graph_only(text, iri, graph, label=""):
    m = re.search(r'<owl:Class rdf:about="' + re.escape(iri) + r'">.*?</owl:Class>', text, re.DOTALL)
    if not m:
        raise SystemExit(f"[FAIL] drop_graph block not found: {label or iri}")
    block = m.group(0)
    nb = re.sub(r'\n[ \t]*<dg:graph rdf:resource="' + re.escape(graph) + r'"/>', "", block)
    if nb == block:
        raise SystemExit(f"[FAIL] drop_graph removed nothing: {label or iri}")
    return text.replace(block, nb)


for iri in ("&dg;Object", "&dg;Function", "&dg;Behavior", "&dg;Structure", "&dg;Geometry", "&dg;Topology"):
    t = reparent(t, iri, "&dgc;ComputationGraph", iri)
t = reparent(t, "&dg;DesignState", "&dgv;ValidationGraph", "DesignState")
t = drop_graph_only(t, "&dg;DefState", "&dgv;ValidationGraph", "DefState")
t = drop_graph_only(t, "&dg;ObjectState", "&dgv;ValidationGraph", "ObjectState")

# ============================================================
# PHASE 5 — insertions
# ============================================================
CORE_BLOCK = '''    <!-- ============================================================
         CORE — OVER-LAYER ENTITIES (v6.0)
         Main Design Grammar entities considered over the layer structure
         (Gero FBS Object/Function/Behavior/Structure, Geometry, Topology,
         Design State, and the shared Session). Core members carry NO
         dg:graph annotation — cross-cutting, not members of any layer.
         ============================================================ -->

    <owl:Class rdf:about="&dg;Core">
        <rdfs:label xml:lang="en">Core</rdfs:label>
        <rdfs:comment xml:lang="en">Top-level grouping for the main Design Grammar entities considered over the layer structure: Object, Function, Behavior, Structure (Gero FBS), Geometry, Topology, DesignState (with ObjectState/DefState), and the shared Session. Core entities are referenced by the five graph layers but belong to none of them — they carry no dg:graph annotation (cross-cutting, like dg:LayerEntity). An Object has Function, Behavior, and Structure; its Function is covered by the OntoGraph layer (dg:definesFunction), and its Design State is validated by the Metagraph layer (dgm:validates).</rdfs:comment>
    </owl:Class>

    <owl:Class rdf:about="&dg;Session">
        <rdfs:label xml:lang="en">Session</rdfs:label>
        <rdfs:comment xml:lang="en">A unified interaction-log entity common to all layers (v6.0 — unifies the former Metagraph rule-session and Spec knowledge-session logs). Records an LLM-driven interaction (the user prompt and generated result); the sessionMode discriminates the operation (ingest/query/edit for rule sessions, insert/query/update for spec sessions). Aligned with: prov:Activity (see standards extension).</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;Core"/>
    </owl:Class>

    <owl:DatatypeProperty rdf:about="&dg;sessionId">
        <rdf:type rdf:resource="&owl;FunctionalProperty"/>
        <rdfs:label xml:lang="en">sessionId</rdfs:label>
        <rdfs:comment xml:lang="en">Unique identifier for a Session (e.g. drs-&lt;hex12&gt; for rule sessions, ks-&lt;hex12&gt; for spec sessions). Characteristics: Functional.</rdfs:comment>
        <rdfs:domain rdf:resource="&dg;Session"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="&dg;sessionMode">
        <rdfs:label xml:lang="en">mode</rdfs:label>
        <rdfs:comment xml:lang="en">Interaction mode of a Session: 'ingest' | 'query' | 'edit' (rule sessions) or 'insert' | 'query' | 'update' (spec sessions).</rdfs:comment>
        <rdfs:domain rdf:resource="&dg;Session"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="&dg;sessionPrompt">
        <rdfs:label xml:lang="en">prompt</rdfs:label>
        <rdfs:comment xml:lang="en">The user's natural-language prompt that triggered this Session.</rdfs:comment>
        <rdfs:domain rdf:resource="&dg;Session"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="&dg;sessionResult">
        <rdfs:label xml:lang="en">result</rdfs:label>
        <rdfs:comment xml:lang="en">The LLM-generated result of the Session (Cypher, answer text, or update summary).</rdfs:comment>
        <rdfs:domain rdf:resource="&dg;Session"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>

    <!-- Core / cross-layer object properties (v6.0) -->

    <owl:ObjectProperty rdf:about="&dg;objectRef">
        <rdfs:label xml:lang="en">OBJECT_REF</rdfs:label>
        <rdfs:comment xml:lang="en">Connects an ObjectState to the Core Object it instantiates (the ERD 'ObjectRef' edge). The ObjectState binds geometry to a specific design Object whose Function/Behavior/Structure are defined across the layers. (The string handle for the SWRL Object-variable name is dgv:objectRefName.)</rdfs:comment>
        <rdfs:domain rdf:resource="&dg;ObjectState"/>
        <rdfs:range rdf:resource="&dg;Object"/>
    </owl:ObjectProperty>

    <owl:ObjectProperty rdf:about="&dg;definesFunction">
        <rdfs:label xml:lang="en">DEFINES_FUNCTION</rdfs:label>
        <rdfs:comment xml:lang="en">Connects an OntoGraph entity (Class, ObjectProperty, or DatatypeProperty) to the Core Function it realises for an Object. The OntoGraph layer defines, from NL input, what classes and properties exist and links them to the Function of a specific Object — so one Object may have many Functions, and a group of Objects may share some Functions while differing in others.</rdfs:comment>
        <rdfs:domain>
            <owl:Class>
                <owl:unionOf rdf:parseType="Collection">
                    <owl:Class rdf:about="&dg;Class"/>
                    <owl:Class rdf:about="&dg;ObjectProperty"/>
                    <owl:Class rdf:about="&dg;DatatypeProperty"/>
                </owl:unionOf>
            </owl:Class>
        </rdfs:domain>
        <rdfs:range rdf:resource="&dg;Function"/>
    </owl:ObjectProperty>

    <owl:ObjectProperty rdf:about="&dgv;refersToGeometry">
        <rdfs:label xml:lang="en">REFERS_TO_GEOMETRY</rdfs:label>
        <rdfs:comment xml:lang="en">Connects a GeoRef to the Core Geometry it points at. Completes the ERD chain ObjectState -hasGeoRef-> GeoRef -refersToGeometry-> Geometry, i.e. Geometry is linked to ObjectState through the GeoRef handle. Geometry is part of Structure (Structure -hasGeometry-> Geometry).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgv;GeoRef"/>
        <rdfs:range rdf:resource="&dg;Geometry"/>
    </owl:ObjectProperty>

    <owl:ObjectProperty rdf:about="&dgm;validates">
        <rdfs:label xml:lang="en">VALIDATES</rdfs:label>
        <rdfs:comment xml:lang="en">Connects a Metagraph Rule to the Core DesignState (the ERD 'STATE') it validates. The OntoGraph-defined classes and properties referenced by the rule's atoms are evaluated against the captured Design State.</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&dg;DesignState"/>
    </owl:ObjectProperty>

    <!-- ============================================================
         PARTONOMY BACKBONE (v6.0)
         Generic part-whole composition spanning the ERD containment
         hierarchy. The has-* composition properties below are declared
         sub-properties of dg:hasPart, so the whole partonomy is
         reasoner-traversable and consistent — no is-a misuse, and the
         class-level disjointness axioms are preserved.
         ============================================================ -->

    <owl:ObjectProperty rdf:about="&dg;hasPart">
        <rdf:type rdf:resource="&owl;TransitiveProperty"/>
        <rdfs:label xml:lang="en">HAS_PART</rdfs:label>
        <rdfs:comment xml:lang="en">Generic composition (part-whole) relation. Transitive super-property of the ERD containment hierarchy: Object hasPart {Function, Behavior, Structure}; Structure hasPart {Geometry, Topology}; RuleSet hasPart Rule; Algorithm hasPart Procedure; Procedure hasPart Pattern; Pattern hasPart {Parameter, Interface}. Transitivity yields the full decomposition, e.g. Object hasPart Geometry and Algorithm hasPart Parameter. Inverse: dg:partOf. Not used in cardinality restrictions (kept simple-property-safe for OWL 2 DL).</rdfs:comment>
    </owl:ObjectProperty>

    <owl:ObjectProperty rdf:about="&dg;partOf">
        <rdf:type rdf:resource="&owl;TransitiveProperty"/>
        <rdfs:label xml:lang="en">PART_OF</rdfs:label>
        <rdfs:comment xml:lang="en">Inverse of dg:hasPart — a component is part of its container. Transitive.</rdfs:comment>
        <owl:inverseOf rdf:resource="&dg;hasPart"/>
    </owl:ObjectProperty>

'''

# insert CORE_BLOCK immediately before the LayerEntity class declaration
anchor_le = '    <owl:Class rdf:about="&dg;LayerEntity">'
t = must_replace(t, anchor_le, CORE_BLOCK + anchor_le, 1, "LayerEntity anchor")

CORE_DISJOINT = '''    <!-- Core: over-layer main entities are mutually exclusive (v6.0) -->
    <rdf:Description>
        <rdf:type rdf:resource="&owl;AllDisjointClasses"/>
        <owl:members rdf:parseType="Collection">
            <owl:Class rdf:about="&dg;Object"/>
            <owl:Class rdf:about="&dg;Function"/>
            <owl:Class rdf:about="&dg;Behavior"/>
            <owl:Class rdf:about="&dg;Structure"/>
            <owl:Class rdf:about="&dg;Geometry"/>
            <owl:Class rdf:about="&dg;Topology"/>
            <owl:Class rdf:about="&dg;DesignState"/>
            <owl:Class rdf:about="&dg;Session"/>
        </owl:members>
    </rdf:Description>

'''
# insert before the COMMON PROPERTIES section comment
anchor_common = '    <!-- ============================================================\n\n         COMMON PROPERTIES (cross-layer)'
t = must_replace(t, anchor_common, CORE_DISJOINT + anchor_common, 1, "COMMON PROPERTIES anchor")

# ============================================================
# PHASE 6 — metadata + prose / label coherence
# ============================================================
t = must_replace(t, "<owl:versionInfo>5.0</owl:versionInfo>", "<owl:versionInfo>6.0</owl:versionInfo>", 1, "versionInfo")

# 6a hub-class comment rewrites (match ORIGINAL prose, run before blanket renames)
t = t.replace(
    "Hub class for the Metagraph layer (SWRL rule structure). Top-level subclasses: Rule, Atom (with ClassAtom/DataPropertyAtom/ObjectPropertyAtom/BuiltinAtom children), Variable (with ObjectVariable/PropertyVariable/BuiltinVariable children), Literal, Builtin, DesignRuleSession, VariableKindValue, VariableScopeValue.",
    "Hub class for the Metagraph layer (SWRL rule structure). Top-level subclasses: Rule, Atom (with ClassAtom/DataPropertyAtom/ObjectPropertyAtom/BuiltinAtom children), Variable (with ObjectVariable/PropertyVariable/BuiltinVariable children), Literal, Builtin, RuleSet, VariableScopeValue. (Reasoner moved to ValidationGraph and sessions unified into Core in v6.0.)")
t = t.replace(
    "Top-level subclasses: ValidationRun, ValidationEntity, DesignState (with DefState/ObjectState children), DesignStateParameter, IntegrationConfig, ObjectInstance, GeoRef, IdRef, and four enum value classes (DesignStateKindValue, DesignStateParameterTypeValue, ValidationStatusValue, ReinstatementStatusValue).",
    "Top-level subclasses: ValidationRun, ValidationEntity, Reasoner, DesignStateParameter, IntegrationConfig, ObjectInstance, GeoRef, IdRef, and three enum value classes (DesignStateParameterTypeValue, ValidationStatusValue, ReinstatementStatusValue). (The design-state classes moved to Core in v6.0.)")
t = t.replace(
    "Hub class for the KnowledgeGraph layer (project notes, tags, sessions). Top-level subclasses: KnowledgeClass, KnowledgeNote, KnowledgeTag, KnowledgeSession.",
    "Hub class for the SpecGraph layer (project specification notes and tags). Top-level subclasses: SpecClass, SpecNote, SpecTag. (Renamed in v6.0; sessions unified into Core.)")
t = t.replace(
    "Hub class for the ComputationGraph layer (DCM parametric design model). Contains: Object, Function, Behavior, Structure, Algorithm, Procedure, Pattern, Parameter, Interface, Geometry.",
    "Hub class for the ComputationGraph layer (DCM parametric design model). Contains: Algorithm, Procedure, Pattern, Parameter, Interface. (FBS Object/Function/Behavior/Structure, Geometry and Topology moved to Core; ParametricState dropped; in v6.0.)")

# 6b overview layer-list line
t = t.replace(
    "            4. KnowledgeGraph — project knowledge notes, tags, sessions\n",
    "            4. SpecGraph — project specification notes and tags\n")

# 6c seeAlso v6.0 history note
v6_note = (" v6.0 introduces the over-layer dg:Core band (Gero FBS Object/Function/"
           "Behavior/Structure, Geometry, Topology, DesignState{ObjectState,DefState}, "
           "unified Session); shortens the layer IRIs (meta#/valid#/comp#); renames the "
           "Knowledge layer to Spec (spec#: SpecGraph/SpecClass/SpecNote/SpecTag); relocates "
           "Reasoner to the ValidationGraph (= Grasshopper 'Validator' component); drops "
           "dgc:ParametricState; and adds dg:objectRef, dg:definesFunction, dgv:refersToGeometry, "
           "dgm:validates.")
t = t.replace("introduces cross-layer bridge dgc:attributeOf (Atom→Parameter); splits external vocabulary extensions into per-vocabulary files (BOT, Topologic).</rdfs:seeAlso>",
              "introduces cross-layer bridge dgc:attributeOf (Atom→Parameter); splits external vocabulary extensions into per-vocabulary files (BOT, Topologic)." + v6_note + "</rdfs:seeAlso>")

# 6d blanket prose/label cleanup — for these tokens only prose & labels remain
#    (all entity refs and XML qnames were already renamed in phases 2-3).
#    KC_KnowledgeNote IRI + its instanceOf refs rename consistently to KC_SpecNote.
t = t.replace("KnowledgeSession", "Session")
t = t.replace("dgk:", "dgs:")
for w_old, w_new in (("KnowledgeGraph", "SpecGraph"), ("KnowledgeClass", "SpecClass"),
                     ("KnowledgeNote", "SpecNote"), ("KnowledgeTag", "SpecTag")):
    t = t.replace(w_old, w_new)

# ============================================================
# PHASE 6.5 — partonomy attachment
# Make the ten ERD composition properties sub-properties of dg:hasPart.
# Object hasPart {Function, Behavior, Structure}; Structure hasPart {Geometry,
# Topology}; RuleSet hasPart Rule; Algorithm hasPart Procedure; Procedure hasPart
# Pattern; Pattern hasPart {Parameter, Interface}. Transitivity of dg:hasPart
# yields the full ERD decomposition (e.g. Object hasPart Geometry, Algorithm
# hasPart Parameter) by inference, with no is-a misuse and disjointness intact.
# ============================================================
PART_PROPS = [
    "&dg;hasFunction",   # Object  -> Function
    "&dg;hasBehavior",   # Object  -> Behavior
    "&dg;hasStructure",  # Object  -> Structure
    "&dg;hasGeometry",   # Structure -> Geometry
    "&dg;hasTopology",   # Structure -> Topology
    "&dgm;hasRule",      # RuleSet -> Rule
    "&dgc;hasProcedure", # Algorithm -> Procedure
    "&dgc;hasPattern",   # Procedure -> Pattern
    "&dgc;hasParameter", # Pattern  -> Parameter
    "&dgc;hasInterface", # Pattern (or Procedure) -> Interface
]
for iri in PART_PROPS:
    # Find each ObjectProperty block by its rdf:about and insert the
    # subPropertyOf line immediately after the <rdfs:comment ...> line.
    pat = re.compile(
        r'(<owl:ObjectProperty rdf:about="' + re.escape(iri) + r'">'
        r'(?:\s*<rdf:type[^\n]*)*'                  # optional characteristics
        r'\s*<rdfs:label[^\n]*'                     # label
        r'\s*<rdfs:comment xml:lang="en">[^<]*</rdfs:comment>)'
    )
    new, n = pat.subn(
        r'\1' + '\n        <rdfs:subPropertyOf rdf:resource="&dg;hasPart"/>',
        t, count=1)
    if n != 1:
        raise SystemExit(f"[FAIL] partonomy: could not patch {iri}")
    t = new

# ============================================================
# PHASE 6.5 — partonomy attachment
# Make the ten ERD composition properties sub-properties of dg:hasPart.
# Object hasPart {Function, Behavior, Structure}; Structure hasPart {Geometry,
# Topology}; RuleSet hasPart Rule; Algorithm hasPart Procedure; Procedure hasPart
# Pattern; Pattern hasPart {Parameter, Interface}. Transitivity of dg:hasPart
# yields the full ERD decomposition by inference (e.g. Object hasPart Geometry,
# Algorithm hasPart Parameter) with no is-a misuse and disjointness intact.
# ============================================================
PART_PROPS = [
    "&dg;hasFunction",   # Object   -> Function
    "&dg;hasBehavior",   # Object   -> Behavior
    "&dg;hasStructure",  # Object   -> Structure
    "&dg;hasGeometry",   # Structure -> Geometry
    "&dg;hasTopology",   # Structure -> Topology
    "&dgm;hasRule",      # RuleSet  -> Rule
    "&dgc;hasProcedure", # Algorithm -> Procedure
    "&dgc;hasPattern",   # Procedure -> Pattern
    "&dgc;hasParameter", # Pattern  -> Parameter (NOT dgv:hasParameter)
    "&dgc;hasInterface", # Pattern (or Procedure) -> Interface
]
for iri in PART_PROPS:
    pat = re.compile(
        r'(<owl:ObjectProperty rdf:about="' + re.escape(iri) + r'">'
        r'(?:\s*<rdf:type[^\n]*)*'                                          # optional characteristics
        r'\s*<rdfs:label[^\n]*'                                             # label
        r'\s*<rdfs:comment xml:lang="en">[^<]*</rdfs:comment>)'             # single-line comment
    )
    new, n = pat.subn(
        r'\1' + '\n        <rdfs:subPropertyOf rdf:resource="&dg;hasPart"/>',
        t, count=1)
    if n != 1:
        raise SystemExit(f"[FAIL] partonomy: could not patch {iri}")
    t = new

# ============================================================
# SELF-CHECK
# ============================================================
DST.write_text(t, encoding="utf-8")
print(f"wrote {DST} ({len(t)} chars, was {orig_len})")

problems = {}
# bare DesignState class in old namespace (must not collide with DesignStateParameter)
m = re.findall(r"&dgv;DesignState(?![A-Za-z])", t)
if m:
    problems["&dgv;DesignState (bare)"] = len(m)
banned = [
    "&dgk;", "dgk:", "&dgc;Object", "&dgc;Function", "&dgc;Behavior", "&dgc;Structure",
    "&dgc;Geometry", "&dgc;Topology", "&dgc;ParametricState", "&dgc;hasState",
    "&dgv;DefState", "&dgv;ObjectState", "&dgm;Reasoner", "&dgm;DesignRuleSession",
    "KnowledgeSession", "KnowledgeGraph", "KnowledgeNote", "KnowledgeTag", "KnowledgeClass",
    "design-grammar/metagraph#", "design-grammar/validation#",
    "design-grammar/computation#", "design-grammar/knowledge#",
]
for b in banned:
    c = t.count(b)
    if c:
        problems[b] = c
if problems:
    print("[WARN] residual banned tokens:")
    for k, v in problems.items():
        print(f"   {k!r}: {v}")
    sys.exit(2)
print("[OK] no residual banned tokens")

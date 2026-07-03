#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_v7_rename.py — Generate DesignGrammar-V7.owl from DesignGrammar-V6.owl.

V6 -> V7 rename (ontology-only, DesignGrammar-V6.owl untouched):
  * Layer-hub casing: OntoGraph->Ontograph, ValidationGraph->Validgraph,
    ComputationGraph->Computgraph (Metagraph and SpecGraph are NOT renamed).
  * OntoGraph reification classes (dg:-namespaced ONLY -- never the owl:
    language constructs): ObjectProperty->ObjProperty, DatatypeProperty->DataProperty.
  * State trio: ObjectState->ObjState, DefState->ParamState, plus a NEW
    PropState subclass of DesignState (Rule + DataProperty + PropValue
    composition, built on the existing dgv:propValue/propValueOf props).
  * ValidationRun->Run; ReinstatementStatus(Value)->ReStatus(Value) (+ its
    7 individuals: Applied/MissingTarget/TypeMismatch/AmbiguousTarget/
    OutOfRange/Unchanged/WouldApply).
  * Rule-level datatype props: ruleText->SWRL, ruleTitle->RuleName, plus a
    NEW RuleDescription (natural-language rule description).
  * NEW Validgraph Boolean datatype props: SendStatus (single Boolean per
    Run) and ValidStatus (Boolean LIST per Run, one element per ObjState,
    index-matched; overall pass = AND(ValidStatus), derived, not stored).
  * Version marker: owl:versionInfo 6.1 -> 7.0; stale "Schema version: v3"
    comment rewritten to v7.

Authority: ontology/V7-INVESTIGATION.md (Phase 13 plan 13-01) locks every
rename below. The RENAMES list mirrors that table 1:1 and is the single
source BOTH the transform phases below AND the V6-to-V7-mapping.md writer
(this script's own side output, at the bottom) consume -- so the mapping
can never drift from what was actually applied.

Collision hazard (see V7-INVESTIGATION.md "OWL-construct collision hazard"):
dg:ObjectProperty / dg:DatatypeProperty are OntoGraph reification CLASSES
(DG domain data) and get renamed; owl:ObjectProperty / owl:DatatypeProperty
are the OWL 2 language CONSTRUCTS used to declare every property in this
file and must NEVER be touched. All renames below are anchored to the
"&dg;" entity-ref prefix (never a bare "ObjectProperty"/"DatatypeProperty"
substring) so the two are never conflated. A self-check at the end asserts
this held.

The script is a sequence of exact/regex string transforms ordered to avoid
collisions, mirroring apply_v6_restructure.py's structure. It prints a
self-check at the end and is idempotent against DesignGrammar-V6.owl (which
it never writes to -- V6 is the read-only source). Run from the ontology/
folder.
"""
import re
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "DesignGrammar-V6.owl"
DST = HERE / "DesignGrammar-V7.owl"
MAPPING = HERE / "V6-to-V7-mapping.md"

t = SRC.read_text(encoding="utf-8")
orig_len = len(t)

# Baseline counts captured BEFORE any transform -- the self-check asserts
# owl:ObjectProperty is byte-identical (no new ObjectProperty defs added by
# this plan) and owl:DatatypeProperty grows by exactly +6 (3 new DatatypeProperty
# defs -- RuleDescription, SendStatus, ValidStatus -- each contributing an
# open+close tag pair; the ruleText->SWRL and ruleTitle->RuleName swaps are
# 1-for-1 and net zero). This proves the dg:-namespaced reification-class
# rename never touched the OWL 2 language constructs themselves.
orig_owl_objprop = t.count("owl:ObjectProperty")
orig_owl_dataprop = t.count("owl:DatatypeProperty")


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


def reparent(text, iri, label=""):
    """Find a top-level <owl:Class rdf:about=iri>...</owl:Class> block (regex,
    DOTALL) -- used by insert_after_class below. Named/shaped to match
    apply_v6_restructure.py's reparent() helper even though v7 performs no
    layer moves; kept for pattern-parity and reuse as a block finder."""
    m = re.search(r'<owl:Class rdf:about="' + re.escape(iri) + r'">.*?</owl:Class>', text, re.DOTALL)
    if not m:
        raise SystemExit(f"[FAIL] class block not found: {label or iri}")
    return m


def insert_after_class(text, iri, new_block, label=""):
    """Insert new_block immediately after the </owl:Class> that closes the
    class rdf:about=iri. Regex-based (not literal block text) so it is
    robust to the exact prose inside the anchor class's rdfs:comment."""
    m = reparent(text, iri, label)
    end = m.end()
    return text[:end] + "\n\n" + new_block.rstrip("\n") + text[end:]


# ============================================================
# RENAMES -- single source of truth, consumed by BOTH the transform phases
# below and the V6-to-V7-mapping.md writer at the end of this script.
# Mirrors ontology/V7-INVESTIGATION.md's V6->V7 Rename Table exactly.
# ============================================================
RENAMES = [
    {"v6": "OntoGraph", "v7": "Ontograph", "kind": "class (layer hub, + punned NamedIndividual)",
     "note": "Namespace dg. Casing rename only; matches PDF's DG.Layer.Ontograph.* paths."},
    {"v6": "ValidationGraph", "v7": "Validgraph", "kind": "class (layer hub, + punned NamedIndividual)",
     "note": "Namespace dgv. Casing rename only; matches PDF's DG.Layer.Validgraph.* paths."},
    {"v6": "ComputationGraph", "v7": "Computgraph", "kind": "class (layer hub, + punned NamedIndividual)",
     "note": "Namespace dgc. Casing rename only; matches PDF's DG.Layer.Computgraph.* paths."},
    {"v6": "ObjectProperty", "v7": "ObjProperty", "kind": "class (OntoGraph reification class)",
     "note": "Namespace dg, &dg;-anchored ONLY. owl:ObjectProperty (OWL 2 language construct) is never touched."},
    {"v6": "DatatypeProperty", "v7": "DataProperty", "kind": "class (OntoGraph reification class)",
     "note": "Namespace dg, &dg;-anchored ONLY. owl:DatatypeProperty (OWL 2 language construct) is never touched."},
    {"v6": "ObjectState", "v7": "ObjState", "kind": "class (DesignState kind, state trio)",
     "note": "Namespace dg (Core). rdfs:subClassOf DesignState."},
    {"v6": "DefState", "v7": "ParamState", "kind": "class (DesignState kind, state trio)",
     "note": "Namespace dg (Core). rdfs:subClassOf DesignState."},
    {"v6": None, "v7": "PropState", "kind": "class (DesignState kind, state trio)",
     "note": "Namespace dg (Core). rdfs:subClassOf DesignState; composes Rule + DataProperty + "
             "PropValue, built on the existing dgv:propValue/propValueOf props."},
    {"v6": "ValidationRun", "v7": "Run", "kind": "class",
     "note": "Namespace dgv."},
    {"v6": "ReinstatementStatus", "v7": "ReStatus", "kind": "class + 7 individuals",
     "note": "Namespace dgv. Covers ReinstatementStatusValue->ReStatusValue and all 7 "
             "ReinstatementStatus_* individuals (Applied/MissingTarget/TypeMismatch/AmbiguousTarget/"
             "OutOfRange/Unchanged/WouldApply) -> ReStatus_*."},
    {"v6": "ruleText", "v7": "SWRL", "kind": "dataprop",
     "note": "Namespace dgm. Domain Rule. Holds the SWRL expression string."},
    {"v6": "ruleTitle", "v7": "RuleName", "kind": "dataprop",
     "note": "Namespace dgm. Domain Rule. Optional human-readable title."},
    {"v6": None, "v7": "RuleDescription", "kind": "dataprop",
     "note": "Namespace dgm. Domain Rule; natural-language rule description (longer than RuleName's "
             "short title)."},
    {"v6": None, "v7": "SendStatus", "kind": "dataprop",
     "note": "Namespace dgv. Domain Run. Single Boolean per Run (publish-to-external-viewer success, D-08)."},
    {"v6": None, "v7": "ValidStatus", "kind": "dataprop",
     "note": "Namespace dgv. Domain Run. Boolean LIST, one element per ObjState, index-matched to "
             "ObjState order; overall pass = AND(ValidStatus), derived not stored (D-06/D-07)."},
]
_BY_V7 = {e["v7"]: e for e in RENAMES}


def r(v7_name):
    """Look up a RENAMES entry by its v7 name -- the shared source of truth
    for both the transforms below and the mapping-file writer."""
    return _BY_V7[v7_name]


# ============================================================
# PHASE 1 -- layer-hub casing renames (blanket; confirmed by direct grep
# against DesignGrammar-V6.owl that none of these three substrings collide
# with any other identifier. Metagraph and SpecGraph are explicitly NOT
# renamed -- they are absent from RENAMES and never touched here.)
# ============================================================
t = must_replace(t, r("Ontograph")["v6"], r("Ontograph")["v7"], None, "OntoGraph->Ontograph")
t = must_replace(t, r("Validgraph")["v6"], r("Validgraph")["v7"], None, "ValidationGraph->Validgraph")
t = must_replace(t, r("Computgraph")["v6"], r("Computgraph")["v7"], None, "ComputationGraph->Computgraph")

# ============================================================
# PHASE 2 -- OntoGraph reification classes (COLLISION-CRITICAL).
# Anchored to the "&dg;" entity-ref prefix ONLY so the OWL 2 language
# constructs owl:ObjectProperty / owl:DatatypeProperty (different prefix,
# "owl:" not "&dg;") are never matched, and &dgm;ObjectPropertyAtom (a
# distinct, NOT-renamed Metagraph atom-type class, different namespace
# entity &dgm; not &dg;) is never matched either.
# ============================================================
t = must_replace(t, f"&dg;{r('ObjProperty')['v6']}", f"&dg;{r('ObjProperty')['v7']}", 4, "&dg;ObjectProperty (anchored)")
t = must_replace(t, f"&dg;{r('DataProperty')['v6']}", f"&dg;{r('DataProperty')['v7']}", 11, "&dg;DatatypeProperty (anchored)")

# label lines (exact single-line match; safe from ObjectPropertyAtom because
# that class's label is the distinct string "ObjectPropertyAtom", not "ObjectProperty")
t = must_replace(t, '<rdfs:label xml:lang="en">ObjectProperty</rdfs:label>',
                  '<rdfs:label xml:lang="en">ObjProperty</rdfs:label>', 1, "ObjectProperty label")
t = must_replace(t, '<rdfs:label xml:lang="en">DatatypeProperty</rdfs:label>',
                  '<rdfs:label xml:lang="en">DataProperty</rdfs:label>', 1, "DatatypeProperty label")

# defensive no-op: rename dg:ObjectProperty / dg:DatatypeProperty ELEMENT
# qnames if they exist anywhere as XML element tags (none do in V6 as of
# this writing -- these reification classes are only ever referenced via
# rdf:about/rdf:resource/rdf:type, never as element containers -- but this
# keeps the transform correct if that ever changes; plain .replace() is a
# safe no-op when the substring is absent).
t = t.replace("<dg:ObjectProperty>", "<dg:ObjProperty>").replace("</dg:ObjectProperty>", "</dg:ObjProperty>")
t = t.replace("<dg:DatatypeProperty>", "<dg:DataProperty>").replace("</dg:DatatypeProperty>", "</dg:DataProperty>")

# prose consistency: two known comments spell out the reification-class
# union in bare (unprefixed) words -- fix them so the generated prose does
# not keep referencing class names that no longer exist post-rename. Exact
# literal matches confirmed against DesignGrammar-V6.owl; run AFTER phase 1
# (text already reads "Ontograph") and are distinct from the untouched
# ObjectPropertyAtom comment.
t = must_replace(
    t,
    "Connects an Ontograph entity (Class, ObjectProperty, or DatatypeProperty) to the Core Function",
    "Connects an Ontograph entity (Class, ObjProperty, or DataProperty) to the Core Function",
    1, "definesFunction comment prose")
t = must_replace(
    t,
    "Connects an Atom to the ontology entity it references (Class, DatatypeProperty, ObjectProperty, or Builtin). "
    "Each Atom has exactly one REFERS_TO. Characteristics: Functional. Range: union of "
    "{Class, DatatypeProperty, ObjectProperty, Builtin}.",
    "Connects an Atom to the ontology entity it references (Class, DataProperty, ObjProperty, or Builtin). "
    "Each Atom has exactly one REFERS_TO. Characteristics: Functional. Range: union of "
    "{Class, DataProperty, ObjProperty, Builtin}.",
    1, "refersTo comment prose")

# ============================================================
# PHASE 3 -- state trio: ObjectState->ObjState, DefState->ParamState (blanket
# -- confirmed via grep that neither substring is a prefix/suffix of any
# other identifier in DesignGrammar-V6.owl).
# ============================================================
t = must_replace(t, r("ObjState")["v6"], r("ObjState")["v7"], 35, "ObjectState->ObjState")
t = must_replace(t, r("ParamState")["v6"], r("ParamState")["v7"], 19, "DefState->ParamState")

# DesignState's own comment + disjointUnionOf need to become three-way
# (ParamState | ObjState | PropState) instead of two-way. Both edits target
# text AFTER the blanket rename above (so they already read ParamState/ObjState).
OLD_DS_COMMENT = (
    'A snapshot of design parameters captured from Grasshopper. Every DesignState individual is '
    'necessarily a ParamState OR an ObjState (owl:disjointUnionOf below) — never both, never neither. '
    'ID prefixes: DS_ (ParamState), OS_ (ObjState). Used as input to CLASSIFICATOR and persisted in '
    'validation runs. STORAGE NOTE: In the Neo4j layer (SCHM-01), this discrimination is materialized '
    'as a `kind` property with values "ParamState" | "ObjState" on a single :DesignState node label — '
    'a runtime convenience because Cypher does not infer subclass membership. The OWL ontology does not '
    'include the kind property because rdf:type plus disjointUnionOf already discriminate (v4.1).'
)
NEW_DS_COMMENT = (
    'A snapshot of design parameters captured from Grasshopper. Every DesignState individual is '
    'necessarily one of ParamState, ObjState, or PropState (owl:disjointUnionOf below) — mutually '
    'exclusive, never more than one. ID prefixes: DS_ (ParamState), OS_ (ObjState), PS_ (PropState). '
    'Composed by DESIGN STATE and persisted in validation runs (v7.0: CLASSIFICATOR is eliminated; '
    'VALIDATOR binds directly from the composed DesignState). STORAGE NOTE: In the Neo4j layer '
    '(SCHM-01), this discrimination is materialized as a `kind` property with values "ParamState" | '
    '"ObjState" | "PropState" on a single :DesignState node label — a runtime convenience because '
    'Cypher does not infer subclass membership. The OWL ontology does not include the kind property '
    'because rdf:type plus disjointUnionOf already discriminate (v4.1).'
)
t = must_replace(t, OLD_DS_COMMENT, NEW_DS_COMMENT, 1, "DesignState comment (three-way state trio)")

OLD_DISJOINT_UNION = (
    '        <owl:disjointUnionOf rdf:parseType="Collection">\n'
    '            <owl:Class rdf:about="&dg;ParamState"/>\n'
    '            <owl:Class rdf:about="&dg;ObjState"/>\n'
    '        </owl:disjointUnionOf>'
)
NEW_DISJOINT_UNION = (
    '        <owl:disjointUnionOf rdf:parseType="Collection">\n'
    '            <owl:Class rdf:about="&dg;ParamState"/>\n'
    '            <owl:Class rdf:about="&dg;ObjState"/>\n'
    '            <owl:Class rdf:about="&dg;PropState"/>\n'
    '        </owl:disjointUnionOf>'
)
t = must_replace(t, OLD_DISJOINT_UNION, NEW_DISJOINT_UNION, 1, "DesignState disjointUnionOf (+PropState)")

OLD_STATE_DISJOINT = (
    '    <rdf:Description>\n'
    '        <rdf:type rdf:resource="&owl;AllDisjointClasses"/>\n'
    '        <owl:members rdf:parseType="Collection">\n'
    '            <owl:Class rdf:about="&dg;ParamState"/>\n'
    '            <owl:Class rdf:about="&dg;ObjState"/>\n'
    '        </owl:members>\n'
    '    </rdf:Description>'
)
NEW_STATE_DISJOINT = (
    '    <rdf:Description>\n'
    '        <rdf:type rdf:resource="&owl;AllDisjointClasses"/>\n'
    '        <owl:members rdf:parseType="Collection">\n'
    '            <owl:Class rdf:about="&dg;ParamState"/>\n'
    '            <owl:Class rdf:about="&dg;ObjState"/>\n'
    '            <owl:Class rdf:about="&dg;PropState"/>\n'
    '        </owl:members>\n'
    '    </rdf:Description>'
)
t = must_replace(t, OLD_STATE_DISJOINT, NEW_STATE_DISJOINT, 1, "state/identity AllDisjointClasses (+PropState)")

# insert the NEW PropState class (regex-anchored on the stable, un-renamed
# DesignStateParameter class that immediately follows ObjState in the file --
# robust to the exact prose inside ObjState's own rdfs:comment).
PROPSTATE_BLOCK = '''    <owl:Class rdf:about="&dg;PropState">
        <rdfs:label xml:lang="en">PropState</rdfs:label>
        <rdfs:comment xml:lang="en">Property state — the third DesignState kind (v7.0), composing a Rule's DataProperty result and its validated PropValue for a specific ObjectInstance. Built on the existing dgv:propValue / dgv:propValueOf datatype/object properties, which already attach per-instance validation-result values to ValidationEntity — PropState generalises that per-cell value into a first-class DesignState kind alongside ObjState and ParamState (ONTO-03, GHST-03). ID prefix: PS_.</rdfs:comment>
        <rdfs:subClassOf rdf:resource="&dg;DesignState"/>
    </owl:Class>

'''
DSP_ANCHOR = '    <owl:Class rdf:about="&dgv;DesignStateParameter">'
t = must_replace(t, DSP_ANCHOR, PROPSTATE_BLOCK + DSP_ANCHOR, 1, "insert PropState before DesignStateParameter")

# ============================================================
# PHASE 4 -- ValidationRun -> Run (blanket; confirmed no substring collisions)
# ============================================================
t = must_replace(t, r("Run")["v6"], r("Run")["v7"], 21, "ValidationRun->Run")

# ============================================================
# PHASE 5 -- ReinstatementStatus -> ReStatus (blanket; covers
# ReinstatementStatusValue->ReStatusValue and all 7 ReinstatementStatus_*
# individuals in one substring replace -- confirmed no other collisions)
# ============================================================
t = must_replace(t, r("ReStatus")["v6"], r("ReStatus")["v7"], 27, "ReinstatementStatus->ReStatus")

# ============================================================
# PHASE 6 -- rule-level datatype properties: ruleText->SWRL,
# ruleTitle->RuleName (+ new RuleDescription inserted right after RuleName)
# ============================================================
OLD_RULETEXT = '''    <owl:DatatypeProperty rdf:about="&dgm;ruleText">
        <rdfs:label xml:lang="en">text</rdfs:label>
        <rdfs:comment xml:lang="en">The SWRL expression string for a rule (e.g. Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)-&gt;violatesMaxHeight(?b,true)).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>'''
NEW_SWRL = '''    <owl:DatatypeProperty rdf:about="&dgm;SWRL">
        <rdfs:label xml:lang="en">SWRL</rdfs:label>
        <rdfs:comment xml:lang="en">The SWRL expression string for a rule (e.g. Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)-&gt;violatesMaxHeight(?b,true)). Renamed from ruleText in v7.0 to match the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.SWRL).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>'''
t = must_replace(t, OLD_RULETEXT, NEW_SWRL, 1, "ruleText -> SWRL")

OLD_RULETITLE = '''    <owl:DatatypeProperty rdf:about="&dgm;ruleTitle">
        <rdfs:label xml:lang="en">title</rdfs:label>
        <rdfs:comment xml:lang="en">Optional human-readable title for a rule.</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>'''
NEW_RULENAME_AND_DESCRIPTION = '''    <owl:DatatypeProperty rdf:about="&dgm;RuleName">
        <rdfs:label xml:lang="en">RuleName</rdfs:label>
        <rdfs:comment xml:lang="en">Optional human-readable title for a rule. Renamed from ruleTitle in v7.0 to match the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.RuleName).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="&dgm;RuleDescription">
        <rdfs:label xml:lang="en">RuleDescription</rdfs:label>
        <rdfs:comment xml:lang="en">Natural-language description of a rule's intent — a longer explanation than RuleName's short title, distinct from SWRL's machine expression string. NEW in v7.0 (no V6 predecessor); matches the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.RuleDescription; Output=Rule().Description). Exposed by RULE DECONSTRUCT and VALIDATOR.</rdfs:comment>
        <rdfs:domain rdf:resource="&dgm;Rule"/>
        <rdfs:range rdf:resource="&xsd;string"/>
    </owl:DatatypeProperty>'''
t = must_replace(t, OLD_RULETITLE, NEW_RULENAME_AND_DESCRIPTION, 1, "ruleTitle -> RuleName (+ new RuleDescription)")

# element usages: <dgm:ruleText>...</dgm:ruleText> -> <dgm:SWRL>...</dgm:SWRL>
t = must_replace(t, "<dgm:ruleText>", "<dgm:SWRL>", 5, "dgm:ruleText open tags")
t = must_replace(t, "</dgm:ruleText>", "</dgm:SWRL>", 5, "dgm:ruleText close tags")

# ============================================================
# PHASE 7 -- NEW Validgraph Boolean datatype properties: SendStatus,
# ValidStatus (inserted after the last Run datatype property, before the
# dgv:status ObjectProperty). Domain dgv;Run is valid at this point because
# PHASE 4 (ValidationRun->Run) already ran.
# ============================================================
SEND_VALID_BLOCK = '''    <owl:DatatypeProperty rdf:about="&dgv;SendStatus">
        <rdf:type rdf:resource="&owl;FunctionalProperty"/>
        <rdfs:label xml:lang="en">SendStatus</rdfs:label>
        <rdfs:comment xml:lang="en">NEW in v7.0 (no V6 predecessor). Single Boolean per Run: whether publishing this run's results to the external geometry/viewer platform succeeded (D-08). Orthogonal to ValidStatus — set true when the publish operation completes successfully, independent of the rule pass/fail outcome. Publishing is one operation per run, so SendStatus is not per-object. Characteristics: Functional. Matches the GH_DesignGrammars.pdf schema (DG.Layer.Validgraph.SendStatus; Output=Run().SendStatus Datatype: Boolean).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgv;Run"/>
        <rdfs:range rdf:resource="&xsd;boolean"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="&dgv;ValidStatus">
        <rdfs:label xml:lang="en">ValidStatus</rdfs:label>
        <rdfs:comment xml:lang="en">NEW in v7.0 (no V6 predecessor). Boolean LIST per Run, one element per ObjState in the validated DesignState, index-matched to the DesignState's ObjState order (D-06). Each element is that object's pass/fail against the rule. Overall pass = AND(ValidStatus), derived at read time, never stored as a separate field (D-07) — unifies the PDF's VALIDATOR-port ValidStatus(Boolean) and VALIDATION GRAPH-port Status(text) naming split into this one field. Not declared FunctionalProperty (multiple values per Run form the list). Population semantics (which ObjStates the list covers) are Phase 18 scope (VALIDATOR variable binding), not locked here. Matches the GH_DesignGrammars.pdf schema (DG.Layer.Validgraph.ValidStatus).</rdfs:comment>
        <rdfs:domain rdf:resource="&dgv;Run"/>
        <rdfs:range rdf:resource="&xsd;boolean"/>
    </owl:DatatypeProperty>

'''
STATUS_ANCHOR = '    <owl:ObjectProperty rdf:about="&dgv;status">'
t = must_replace(t, STATUS_ANCHOR, SEND_VALID_BLOCK + STATUS_ANCHOR, 1, "insert SendStatus/ValidStatus before dgv:status")

# ============================================================
# PHASE 8 -- metadata: version marker + stale schema-version comment
# ============================================================
t = must_replace(t, "<owl:versionInfo>6.1</owl:versionInfo>", "<owl:versionInfo>7.0</owl:versionInfo>", 1, "versionInfo 6.1->7.0")
t = must_replace(t, "Schema version: v3", "Schema version: v7", 1, "stale schema-version comment")

v7_note = (
    " v7.0 renames V6 to match the GH_DesignGrammars.pdf component schema notation "
    "(ontology/V7-INVESTIGATION.md is the naming authority): layer-hub casing "
    "OntoGraph/ValidationGraph/ComputationGraph -> Ontograph/Validgraph/Computgraph "
    "(Metagraph and SpecGraph unchanged); OntoGraph reification classes ObjectProperty/"
    "DatatypeProperty -> ObjProperty/DataProperty (the owl:ObjectProperty/owl:DatatypeProperty "
    "language constructs are untouched); state trio ObjectState/DefState -> ObjState/ParamState "
    "plus a new PropState (Rule+DataProperty+PropValue composition); ValidationRun -> Run; "
    "ReinstatementStatus(Value) -> ReStatus(Value); rule-level ruleText/ruleTitle -> SWRL/RuleName "
    "plus a new RuleDescription; new Validgraph Boolean properties SendStatus (single per Run) and "
    "ValidStatus (per-ObjState list, index-matched, overall pass derived via AND, not stored). "
    "See ontology/V6-to-V7-mapping.md for the full old->new IRI table (recovery-only guard for "
    "existing publications referencing V6 names)."
)
t = must_replace(
    t,
    "so the ontology models a generic external geometry/viewer integration; external-vocabulary "
    "alignments (standards, BOT, Topologic) are retained as legitimate links.</rdfs:seeAlso>",
    "so the ontology models a generic external geometry/viewer integration; external-vocabulary "
    "alignments (standards, BOT, Topologic) are retained as legitimate links." + v7_note + "</rdfs:seeAlso>",
    1, "v7.0 seeAlso changelog note")

# ============================================================
# WRITE + V6-to-V7-mapping.md (emitted from the SAME RENAMES list above)
# ============================================================
DST.write_text(t, encoding="utf-8")
print(f"wrote {DST} ({len(t)} chars, was {orig_len})")

mapping_lines = [
    "# V6 -> V7 IRI Mapping (recovery-only)",
    "",
    "**Purpose:** This file maps every renamed V6 ontology name to its V7 successor. It exists as a "
    "recovery guard for existing publications (documents, Cypher, external systems) that reference "
    "V6-era names -- it is NOT a runtime consumer artifact. Generated by `apply_v7_rename.py` from its "
    "own `RENAMES` list (the same list the rename transforms above consume), so this table can never "
    "drift from what was actually applied to produce `DesignGrammar-V7.owl`.",
    "",
    "Authority: `ontology/V7-INVESTIGATION.md` (Phase 13 plan 13-01) locks every row below.",
    "",
    "| Old (V6) | New (V7) | Kind | Note |",
    "|---|---|---|---|",
]
for e in RENAMES:
    old = e["v6"] if e["v6"] is not None else "— (no V6 source)"
    note = e["note"] if e["v6"] is not None else f"**new in V7 — no V6 predecessor.** {e['note']}"
    mapping_lines.append(f"| {old} | {e['v7']} | {e['kind']} | {note} |")
mapping_lines.append("")
MAPPING.write_text("\n".join(mapping_lines), encoding="utf-8")
print(f"wrote {MAPPING}")

# ============================================================
# SELF-CHECK
# ============================================================
problems = {}

# OWL-construct collision guard. owl:ObjectProperty must be byte-identical
# to SRC (no new ObjectProperty defs added by this plan). owl:DatatypeProperty
# must be SRC+6 -- exactly 3 new DatatypeProperty defs (RuleDescription,
# SendStatus, ValidStatus) each contributing an open+close tag pair; the
# ruleText->SWRL and ruleTitle->RuleName swaps are 1-for-1 (net zero). Any
# other delta means the reification-class rename leaked into an OWL construct.
new_owl_objprop = t.count("owl:ObjectProperty")
new_owl_dataprop = t.count("owl:DatatypeProperty")
if new_owl_objprop != orig_owl_objprop:
    problems["owl:ObjectProperty count changed (expected unchanged)"] = f"{orig_owl_objprop} -> {new_owl_objprop}"
if new_owl_dataprop != orig_owl_dataprop + 6:
    problems["owl:DatatypeProperty count changed (expected SRC+6 for the 3 new defs)"] = \
        f"{orig_owl_dataprop} -> {new_owl_dataprop} (expected {orig_owl_dataprop + 6})"
# the wrongly-renamed forms must never appear -- proves the reification-class
# rename never corrupted an actual OWL 2 element name.
for corrupted in ("owl:DataProperty", "owl:ObjProperty"):
    c = t.count(corrupted)
    if c:
        problems[f"corrupted OWL construct {corrupted!r}"] = c

banned = [
    "ObjectState", "DefState", "ReinstatementStatus", "ruleText", "ruleTitle",
    "&dg;OntoGraph", "&dgv;ValidationGraph", "&dgc;ComputationGraph",
    "Schema version: v3", "<owl:versionInfo>6.1",
]
for b in banned:
    c = t.count(b)
    if c:
        problems[b] = c

if problems:
    print("[WARN] residual banned tokens / collision-guard failures:")
    for k, v in problems.items():
        print(f"   {k!r}: {v}")
    sys.exit(2)
print("[OK] no residual banned tokens")

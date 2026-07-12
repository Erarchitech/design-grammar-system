---
phase: 820-reasoning-stack-architecture-decision-ontograph-axiom-scopin
plan: 02
subsystem: spec
tags: [lpg-owl-mapping, swrl-rdf, reification, iri-strategy, una]
requires: [820-RESEARCH.md, spec/DATABASE.md]
provides: [spec/LPG-OWL-MAPPING.md]
affects: [phase-821-translator]
tech-stack:
  added: [W3C SWRL RDF vocabulary, owl:AllDifferent UNA convention]
  patterns: [spec/DATABASE.md bold-label/fenced-example style, dotenv credential pattern]
key-files:
  created:
    - spec/LPG-OWL-MAPPING.md
  modified: []
decisions:
  - SWRL RDF vocabulary used for Metagraph mapping (standard W3C terms, no custom reification vocabulary)
  - IRI minting under http://example.org/design-grammar with project-scoped segments /rule/{Rule_Id}, /atom/{Atom_Id}, /var/{name}
  - BuiltinAtom uses swrl:arguments (rdf:List) universally, not argument1/argument2
  - Label-scoped export (MATCH by label) mandated, graph-property scoping forbidden
  - namespace split: ex: (per-project domain vocab) separate from dg/dgm/dgv/dgs (static meta-schema)
  - owl:AllDifferent / owl:distinctMembers mandated for future ABox exports (UNA gap)
  - HermiT builtin-exclusion documented as known limitation for reasoner input
status: complete
metrics:
  duration_minutes: 18
  completed_date: 2026-07-11
  files_created: 1
  files_modified: 0
  total_tasks: 2
  completed_tasks: 2
---

# Phase 820 Plan 02: LPG to OWL Mapping Spec Summary

**One-liner:** Normative LPG->OWL/OWL/SWRL RDF mapping contract covering Metagraph (SWRL vocabulary with verified live builtin arity), OntoGraph (OWL terms), edge-property reification (ARG.pos, HAS_BODY/HAS_HEAD.order), IRI minting strategy, label-scoped export mandate, UNA handling, and an informative ValidGraph sketch -- the reviewable contract Phase 821's ontology_export.py implements against.

## Deviations from Plan

None -- plan executed exactly as written. Both tasks were completed in a single comprehensive file write covering all normative and informative sections.

## Threat Surface Scan

No security-relevant surface introduced. The spec is a documentation-only artifact; no endpoints, auth paths, or file access patterns were created. The live builtin-arity Cypher query used environment variables (no hardcoded credentials), matching the mitigation in T-820-04.

## Known Stubs

None. The spec is complete as a normative contract; no placeholder text, mock data, or hardcoded empty values are present. The informative ValidGraph section is explicitly marked as a sketch for Phase 823 (by design, not a stub).

## Execution Summary

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Metagraph mapping core -- SWRL vocabulary table, edge-property reification, IRI minting (with live builtin-arity verification) | 325117b | spec/LPG-OWL-MAPPING.md |
| 2 | OntoGraph mapping, UNA handling, and informative ValidGraph sketch | 369e0bb | spec/LPG-OWL-MAPPING.md |

### Task 1 Detail: Metagraph Mapping Core

- Full SWRL RDF vocabulary mapping table: Rule->swrl:Imp, ClassAtom->swrl:ClassAtom, DataPropertyAtom->swrl:DatavaluedPropertyAtom, ObjectPropertyAtom->swrl:IndividualPropertyAtom, BuiltinAtom->swrl:BuiltinAtom, Var->swrl:Variable, Literal->typed RDF literal
- Edge-property reification subsection: ARG.pos -> swrl:argument1/argument2 (binary atom kinds) + swrl:arguments rdf:List (BuiltinAtom); HAS_BODY/HAS_HEAD.order -> implicit swrl:AtomList position
- IRI minting strategy: reuse stored iri for Class/DatatypeProperty/ObjectProperty/Builtin; mint under base `http://example.org/design-grammar` with `/project/{project}/rule/{Rule_Id}`, `/atom/{Atom_Id}`, `/var/{name-without-?}` path segments
- BuiltinAtom subsection with live arity verified against Neo4j v8-ui-smoke data (8 builtins: greaterThan, lessThan, or, equalTo, continuousFromTo, fillet, notEqual, towards). Key finding: continuousFromTo has incomplete ARG data (0 edges in live graph), reinforcing the `swrl:arguments` list-form mandate.
- Export scoping subsection: label-based scoping mandated (MATCH n:Rule|Atom|...), graph-property scoping forbidden, citing the confirmed mistagged-atom finding (R_DOOR_ORIENTATION_V atoms)
- Namespace separation principle: ex: (per-project domain vocabulary) vs dg/dgm/dgv/dgs (static meta-schema)
- Cross-references spec/DATABASE.md, not duplicating it

### Task 2 Detail: OntoGraph, UNA, ValidGraph

- OntoGraph mapping: Class->owl:Class, DatatypeProperty->owl:DatatypeProperty, ObjectProperty->owl:ObjectProperty, each reusing stored iri
- Documented flatness of live OntoGraph: zero SUBCLASS_OF/DOMAIN/RANGE/DISJOINT_WITH relationship types verified empirically
- Normative UNA subsection: owl:AllDifferent / owl:distinctMembers mandated for future ABox exports, with illustrative Turtle block
- Informative ValidGraph section: sketches DesignState (ObjState/ParamState/PropState) and Run -> RDF individuals, explicitly marked as "Phase 823 input"
- SWRL Builtin exclusion from reasoner input documented as known HermiT limitation with stripping procedure
- Consistency & Propagation note referencing CLAUDE.md schema-change checklist
- Normative downstream consumption contract listing Phase 821 implementation requirements

## Live Data Verification

The builtin-arity Cypher query `MATCH (a:Atom {type:'BuiltinAtom', project:'v8-ui-smoke'})-[r:ARG]->() RETURN a.iri, count(r) AS arity` was executed against the running docker Neo4j instance. Results:

- 5 builtins used by BuiltinAtom atoms: greaterThan (max arity 2), lessThan (arity 2), or (arity 2), equalTo (arity 2), continuousFromTo (arity 0 -- incomplete)
- 3 builtins with node present but no atoms referencing them via REFERS_TO: fillet, notEqual, towards
- One data anomaly: R_CORRIDOR_MAX_LENGTH_14_V_A3 (greaterThan) has arity 1 -- an incomplete data completeness issue in the live graph

## Success Criteria Met

- [x] spec/LPG-OWL-MAPPING.md covers: Metagraph->SWRL, OntoGraph->OWL, ARG.pos + HAS_BODY/HAS_HEAD.order reification, IRI minting, label-scoping, UNA handling, informative ValidGraph sketch
- [x] BuiltinAtom arity reflects live Cypher check (not assumption)
- [x] File cross-references DATABASE.md rather than duplicating it
- [x] Deliverable: REAS-04 success criterion 2 (written LPG->OWL mapping spec covering edge-property reification)

## Self-Check

Verification performed against Task 1 and Task 2 acceptance criteria:
- swrl:Imp, swrl:AtomList, swrl:argument1, swrl:arguments, ARG, HAS_BODY all present: PASS
- swrl:ClassAtom, swrl:DatavaluedPropertyAtom, swrl:IndividualPropertyAtom, swrl:BuiltinAtom, swrl:Variable: PASS
- /rule/, /atom/, /var/ IRI path segments: PASS
- continuousFromTo arity documented: PASS
- owl:AllDifferent, distinctMembers: PASS
- ValidGraph informative section with Phase 823 labeling: PASS
- Propagation note referencing CLAUDE.md: PASS
- DATABASE.md cross-reference: PASS
- Status: PASSED

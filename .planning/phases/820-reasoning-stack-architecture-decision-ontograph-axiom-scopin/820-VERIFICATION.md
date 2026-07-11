---
phase: 820-reasoning-stack-architecture-decision-ontograph-axiom-scopin
verified: 2026-07-11T22:15:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 820: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping -- Verification Report

**Phase Goal:** OWL reasoning work in later phases builds against a documented, real interpretation of DG's ontology data — not a schema so empty that any reasoner trivially reports "consistent".

**Verified:** 2026-07-11T22:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | PROJECT.md Key Decisions records the chosen hybrid axiom-scoping approach with rationale (success criterion 1) | VERIFIED | PROJECT.md Key Decisions row at line 135: "Hybrid axiom-scoping: union static DesignGrammar-V7.owl TBox..." Outcome cites 820-DECISION.md and spec/LPG-OWL-MAPPING.md |
| 2   | A written LPG -> OWL mapping spec exists covering edge-property reification for Atom.ARG.pos and Rule.HAS_BODY/HAS_HEAD.order (success criterion 2) | VERIFIED | spec/LPG-OWL-MAPPING.md (399 lines) -- Edge-property reification subsection maps ARG.pos to swrl:argument1/2, HAS_BODY/HAS_HEAD.order to rdf:List position; cross-references DATABASE.md |
| 3   | Spike confirms naive export of real project's live OntoGraph trivially reports "consistent" (success criterion 3a) | VERIFIED | spike/output/naive_result.txt: `Inconsistent classes: []` -- HermiT yields 0 inconsistent classes; documented false positive |
| 4   | Spike shows chosen hybrid scoping avoids false-positive outcome (success criterion 3b) | VERIFIED | spike/output/hybrid_result.txt: `Inconsistent classes: [owl.Nothing, ex.SlidingDoor]` -- HermiT catches seeded TBox contradiction |
| 5   | Sidecar-vs-embedded architecture decision confirmed and recorded as Key Decision (success criterion 4) | VERIFIED | PROJECT.md dg-reasoner row flipped from Pending to "Shipped -- v8.2 Phase 820 (spike evidence: see 820-DECISION.md)"; ADR-820-2 in 820-DECISION.md |
| 6   | Running run_naive.py against v8-ui-smoke reports zero inconsistent classes (Plan 01 must_have) | VERIFIED | spike/output/naive_result.txt: "Inconsistent classes: []" with ASSERTION PASS. Confirms trivial-consistency false positive. |
| 7   | Running run_hybrid.py with curated disjointness reports SlidingDoor unsatisfiable (Plan 01 must_have) | VERIFIED | spike/output/hybrid_result.txt: "Inconsistent classes: [owl.Nothing, ex.SlidingDoor]" with ASSERTION PASS. Non-trivial result naive missed. |
| 8   | export.py Cypher scopes by node label, capturing mistagged R_DOOR_ORIENTATION_V atoms (Plan 01 must_have) | VERIFIED | export.py lines 59, 66 use label-scoped MATCH (n:Rule|Atom|Var|Literal|Builtin) and (n:Class|DatatypeProperty|ObjectProperty) -- never graph-property scoped |
| 9   | rdflib-parsed axiom counts are authoritative evidence, not grep guesses (Plan 01 must_have) | VERIFIED | spike/output/axiom_counts.txt: rdflib-parsed from DesignGrammar-V7.owl (2139 triples). Reports 65 subClassOf, 101 domain, 110 range, 0 disjointWith |
| 10  | Spike is reproducible from README.md alone (Plan 01 must_have) | VERIFIED | spike/README.md documents: NEO4J_URI/USER/PASSWORD env vars, JRE-17 throwaway container (python:3.11-slim + openjdk-21-jre-headless), exact run order, throwaway nature |
| 11  | spec/LPG-OWL-MAPPING.md normatively maps every Metagraph node to W3C SWRL RDF vocabulary (Plan 02 must_have) | VERIFIED | spec maps: Rule->swrl:Imp, ClassAtom->swrl:ClassAtom, DataPropertyAtom->swrl:DatavaluedPropertyAtom, ObjectPropertyAtom->swrl:IndividualPropertyAtom, BuiltinAtom->swrl:BuiltinAtom, Var->swrl:Variable. All 11 SWRL terms confirmed present. |
| 12  | 820-DECISION.md records both decisions in ADR shape with Evidence citing spike output (Plan 03 must_have) | VERIFIED | Two ADR entries (ADR-820-1, ADR-820-2) each with Context/Decision/Consequences/Evidence. Evidence cites axiom_counts.txt (0 disjointWith), naive_result.txt, hybrid_result.txt (SlidingDoor). |

**Score:** 12/12 truths verified (0 present/behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `spike/requirements.txt` | 3 pinned Python packages | VERIFIED | owlready2==0.51, rdflib==7.6.0, neo4j==6.2.0 |
| `spike/export.py` | Label-scoped Neo4j->RDFLib exporter | VERIFIED | 659 lines, METAGRAPH_QUERY and ONTOGRAPH_QUERY label-scoped, os.getenv credential pattern |
| `spike/run_naive.py` | Naive export via HermiT, expect consistent | VERIFIED | sync_reasoner(), inconsistent_classes() -> naive_result.txt |
| `spike/run_hybrid.py` | Hybrid export + seeded contradiction, expect SlidingDoor unsatisfiable | VERIFIED | sync_reasoner(), inconsistent_classes() -> hybrid_result.txt |
| `spike/README.md` | Reproduction steps | VERIFIED | NEO4J_ env vars, JRE-17 container, run order, throwaway nature |
| `spike/output/naive_result.txt` | 0 inconsistent classes | VERIFIED | "Inconsistent classes: []" |
| `spike/output/hybrid_result.txt` | SlidingDoor unsatisfiable | VERIFIED | "Inconsistent classes: [owl.Nothing, ex.SlidingDoor]" |
| `spike/output/axiom_counts.txt` | rdflib-parsed TBox counts | VERIFIED | 65 subClassOf, 101 domain, 110 range, 0 disjointWith |
| `spike/output/naive_export.ttl` | Turtle export with swrl:Imp | VERIFIED | 25KB, contains swrl:Imp |
| `spike/output/hybrid_export.ttl` | Hybrid Turtle export | VERIFIED | 135KB |
| `spec/LPG-OWL-MAPPING.md` | Normative LPG->OWL mapping spec | VERIFIED | 399 lines. SWRL vocab table, edge-property reification, IRI minting, label-scoping mandate, UNA handling, ValidGraph sketch |
| `820-DECISION.md` | ADR-style decision record with spike evidence | VERIFIED | 79 lines. Two ADR entries + Data-Quality note |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| export.py label-scoped Cypher | naive_export.ttl / hybrid_export.ttl | RDFLib Turtle serialization | WIRED | export.py builds in-memory RDFLib graph from Cypher -> serializes to Turtle at line 250+ |
| run_naive.py / run_hybrid.py | Owlready2 sync_reasoner -> HermiT JAR | Bundled HermiT JAR (JRE 17) | WIRED | Both scripts call sync_reasoner() which shells out to bundled HermiT JAR |
| Neo4j credentials | os.getenv | NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD env vars | WIRED | export.py reads from os.getenv with dev-safe defaults, never hardcoded |
| 820-DECISION.md Evidence | spike/output/ logs | File references | WIRED | DECISION.md cites axiom_counts.txt, naive_result.txt, hybrid_result.txt |
| 820-DECISION.md | spec/LPG-OWL-MAPPING.md | Cross-reference | WIRED | DECISION.md references LPG-OWL-MAPPING.md in "See also" and throughout |
| PROJECT.md Key Decisions | 820-DECISION.md and spec/LPG-OWL-MAPPING.md | Citation | WIRED | Both new rows cite 820-DECISION.md; hybrid row also cites LPG-OWL-MAPPING.md |
| spec/LPG-OWL-MAPPING.md | spec/DATABASE.md | Cross-reference | WIRED | LPG-OWL-MAPPING.md references DATABASE.md (2 occurrences) as authoritative node/property source |

### Data-Flow Trace (Level 4)

Not applicable -- this is a documentation/spike phase. No artifacts render dynamic data at runtime. The spike outputs are captured evidence files from throwaway data processing, not a live dynamic UI. All three levels (exists, substantive, wired) verified above for each artifact.

### Behavioral Spot-Checks

Not applicable -- this phase ships no runnable API, CLI, or build output beyond the spike scripts (which are throwaway and already produced their evidence files). The spike's behavioral assertions (naive: 0 inconsistent; hybrid: SlidingDoor unsatisfiable) are verified through their captured output files.

### Probe Execution

Phase 820 has no declared probes. The VALIDATION.md specifies automated grep-based checks and spike output verification, which have been executed above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| REAS-04 | 820-01, 820-02, 820-03 | OntoGraph axiom-scoping approach decided and documented + LPG->OWL mapping spec covering edge-property reification | SATISFIED | All 4 success criteria met: (1) hybrid axiom-scoping in PROJECT.md Key Decisions, (2) spec/LPG-OWL-MAPPING.md covers edge-property reification (ARG.pos, HAS_BODY/HAS_HEAD.order), (3) spike proves naive false-positive vs hybrid non-trivial, (4) sidecar decision confirmed in PROJECT.md and 820-DECISION.md |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | - | - | - | All files clean: no TBD, FIXME, XXX, TODO, HACK, placeholder, "coming soon", or "not yet implemented" markers. No credential literals outside os.getenv defaults. |

### Deferred Items

None identified. All phase goals are met within this phase. Phase 821 will build the real translator against the spec, and Phase 822 will build the production reasoner sidecar -- these are separate deliverables for later phases, not gaps in Phase 820.

### Gaps Summary

No gaps found. All must-haves verified.

---

## Verification Details by Plan

### Plan 01 (Spike): All Tasks Complete

**Task 1** (package legitimacy gate): Blocking-human gate documented in SUMMARY as approved by user (2026-07-11). All 3 packages (owlready2==0.51, rdflib==7.6.0, neo4j==6.2.0) were confirmed on pypi.org before install. Evidence: spike scripts executed successfully and produced real output.

**Task 2** (spike environment + exporter): All files exist and are substantive:
- `requirements.txt` -- exact 3 pinned lines
- `export.py` -- label-scoped Cypher (METAGRAPH_QUERY/ONTOGRAPH_QUERY use `n:Rule/Atom/Var/Literal/Builtin` and `n:Class/DatatypeProperty/ObjectProperty`), os.getenv credential pattern only
- `README.md` -- documents env vars, JRE-17 container, run order, throwaway nature
- `output/naive_export.ttl` -- 25KB, contains swrl:Imp
- `output/axiom_counts.txt` -- 65 subClassOf, 101 domain, 110 range, 0 disjointWith (rdflib-parsed)

**Task 3** (two-part reasoner proof):
- `run_naive.py` -- calls sync_reasoner(), inconsistent_classes() -> naive_result.txt: 0 classes
- `run_hybrid.py` -- calls sync_reasoner(), inconsistent_classes() -> hybrid_result.txt: SlidingDoor unsatisfiable
- `output/hybrid_export.ttl` -- 135KB with both owl:disjointWith and SlidingDoor
- TBox-only contradiction: no owl:NamedIndividual introduced beyond DesignGrammar-V7.owl

### Plan 02 (Mapping Spec): All Tasks Complete

**Task 1** (Metagraph core):
- Full SWRL vocabulary mapping table: Rule->swrl:Imp, all 4 atom types, Var->swrl:Variable, Literal->typed literal
- Edge-property reification: ARG.pos->swrl:argument1/2 (binary), swrl:arguments rdf:List (BuiltinAtom), HAS_BODY/HAS_HEAD.order->swrl:AtomList position
- IRI minting: /project/{project}/rule/{Rule_Id}, /atom/{Atom_Id}, /var/{name-without-?} under base http://example.org/design-grammar
- BuiltinAtom subsection with live-verified arity: greaterThan (2), lessThan (2), or (2), equalTo (2), continuousFromTo (0 incomplete), fillet/notEqual/towards (unused)
- Label-scoped export mandate, graph-property scoping forbidden, cites mistagged-atom finding
- Namespace separation: ex: (per-project domain vocab) vs dg/dgm/dgv/dgs (static meta-schema)

**Task 2** (OntoGraph, UNA, ValidGraph):
- OntoGraph mapping: Class->owl:Class, DatatypeProperty->owl:DatatypeProperty, ObjectProperty->owl:ObjectProperty
- Documented flatness: zero SUBCLASS_OF/DOMAIN/RANGE/DISJOINT_WITH across whole DB
- Normative UNA subsection: owl:AllDifferent/owl:distinctMembers for future ABox
- Informative ValidGraph sketch: DesignState (3 kinds) + Run -> RDF, labeled "Phase 823 input"
- Consistency & propagation note referencing CLAUDE.md schema-change checklist

### Plan 03 (Decision Documentation): All Tasks Complete

**Task 1** (820-DECISION.md):
- Two ADR entries: ADR-820-1 (Hybrid axiom-scoping) and ADR-820-2 (dg-reasoner sidecar confirmed)
- Each with Context / Decision / Consequences / Evidence structure
- Evidence cites axiom_counts.txt (0 disjointWith), naive_result.txt (0 classes), hybrid_result.txt (SlidingDoor)
- Data-quality note documents graph-property mistagging (2+2+6 nodes) as known gap, not repair task
- Assumption A3 addressed: v8-ui-smoke is QA data but satisfies "real project's live OntoGraph data" wording
- Cross-references spec/LPG-OWL-MAPPING.md

**Task 2** (PROJECT.md Key Decisions):
- dg-reasoner row: Outcome changed from "Pending" to "Shipped -- v8.2 Phase 820 (spike evidence: see 820-DECISION.md)". Decision/Rationale columns unchanged.
- New hybrid axiom-scoping row added with Decision (static TBox + live export + curated disjointWith), Rationale, and Outcome ("Shipped -- v8.2 Phase 820 (see 820-DECISION.md; mapping spec spec/LPG-OWL-MAPPING.md)")
- CONNECTOR row unchanged (still "Pending -- v8.2")
- Table remains well-formed (all rows 3-column)

---

## Validation Contract Compliance

All 6 automated verification commands from 820-VALIDATION.md's Per-Task Verification Map pass:

| Task ID | Check | Result |
|---------|-------|--------|
| 820-01-02 | test -s spike/output/naive_export.ttl && test -s spike/output/axiom_counts.txt && grep -qi "disjointWith" axiom_counts.txt && grep -q "swrl:Imp" naive_export.ttl | PASS (all 4) |
| 820-01-03 | test -s spike/output/naive_result.txt && test -s spike/output/hybrid_result.txt && grep -qi "SlidingDoor" hybrid_result.txt | PASS (all 3) |
| 820-02-01 | test -s spec/LPG-OWL-MAPPING.md && grep -q 6 structural terms | PASS (all 7) |
| 820-02-02 | grep -q 5 structural terms (owl:Class, owl:AllDifferent, distinctMembers, informative, ValidGraph) | PASS (all 5) |
| 820-03-01 | test -s 820-DECISION.md && grep -qi 4 structural terms | PASS (all 5) |
| 820-03-02 | grep -q 4 PROJECT.md assertions | PASS (all 4) |

## Nyquist Compliance

- All tasks have automated verify or documented human-gate exemption (Task 820-01-01 is checkpointhuman-verify per Nyquist checkpoint rule)
- Sampling continuity: no 3 consecutive tasks without automated verify
- Wave 0 covers all MISSING references
- Feedback latency under 30 seconds (spike runs)

---

_Verified: 2026-07-11T22:15:00Z_
_Verifier: Claude (gsd-verifier)_

---
phase: 13-ontology-v7-and-contract-investigation
plan: 03
subsystem: ontology
tags: [ontology, owl, port-mapping, grasshopper, documentation]

# Dependency graph
requires:
  - phase: 13-ontology-v7-and-contract-investigation (plan 02)
    provides: "ontology/DesignGrammar-V7.owl — generated V7 ontology with the state trio, rule-level SWRL/RuleName/RuleDescription, Validgraph SendStatus/ValidStatus"
provides:
  - "ontology/port-iri-map-V7.md — the ONTO-06 component-port -> ontology-IRI contract for all 14 GH_DesignGrammars.pdf components, successor of GH-mapping.png"
affects: ["13-04", "14-graph-schema-v4-propagation", "17-graph-access-components", "18-rules-and-validator-rework"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Single greppable markdown master table (Component/Port/Direction/V7 IRI/Layer/Notes) as the component-port -> ontology-IRI contract, replacing a raster diagram"]

key-files:
  created:
    - "ontology/port-iri-map-V7.md"
  modified: []

key-decisions:
  - "PARAMETER REINSTATE's StateStatus / OBJECT DECONSTRUCT+OBJECT STATE's Label ports map to the real resolvable OWL IRI rather than the PDF's display-name ontology path: dgv:ReStatusValue (rdfs:label \"ReStatus\", matching DG.Layer.Validgraph.ReStatus) and dgv:objectRefName (the user-supplied ObjectRef string handle, since DesignGrammar-V7.owl has no dedicated Geometry.Label datatype property)"
  - "Runtime/DB-only ports (CONNECTOR credentials + Database handle, Boolean UI triggers on PARAMETER REINSTATE/VALIDATOR, and VALIDATOR's kept v2.0 publish extras DataServiceUrl/Report/ValidationRunId) are explicitly annotated 'no ontology IRI' rather than omitted, per PROJECT.md's documented (not enforced) ontology<->DB gap policy"
  - "RULE DECONSTRUCT's Rule output is a passthrough of its Rule input (both mapped to dgm:Rule), matching the plan's explicit port enumeration for downstream VALIDATOR wiring"

requirements-completed: [ONTO-06]

coverage:
  - id: D1
    description: "ontology/port-iri-map-V7.md contains a single master table (Component/Port/Direction/V7 IRI/Layer/Notes) covering all 14 GH_DesignGrammars components with zero unmapped output ports"
    requirement: "ONTO-06"
    verification:
      - kind: other
        ref: "grep -c '| COMPONENT |' ontology/port-iri-map-V7.md for each of the 14 component names — all >=1; grep -c 'CLASSIFICATOR\\|VALIDATION RUNS' returns only the intentional CLASSIFICATOR-eliminated note, not a component row"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every ontology IRI cited in the map resolves to an entity in DesignGrammar-V7.owl; a Resolution check footer records the counts"
    requirement: "ONTO-06"
    verification:
      - kind: other
        ref: "grep -c 'about=\"&prefix;LocalName\"' ontology/DesignGrammar-V7.owl for all 25 distinct ontology IRIs in the table — all >=1"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-03
status: complete
---

# Phase 13 Plan 03: Port -> V7 IRI Map Summary

**Built `ontology/port-iri-map-V7.md` — a single 66-row greppable master table mapping every output port (and every IRI-carrying input) of all 14 GH_DesignGrammars.pdf components to its V7 ontology IRI, with all 25 distinct ontology IRIs verified against `DesignGrammar-V7.owl` and 10 runtime/DB-only ports explicitly annotated.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-03T01:45:00Z (approx)
- **Completed:** 2026-07-03T02:10:00Z (approx)
- **Tasks:** 2
- **Files modified:** 1 (new)

## Accomplishments
- Read `ontology/GH_DesignGrammars.pdf` (the full 14-component canvas + inline `Ontology: DG.Layer....` annotations) and transcribed every component's port list, grouped as Graph access (CONNECTOR, GRAPH DECONSTRUCT, METAGRAPH, ONTOGRAPH, VALIDATION GRAPH), State (OBJECT STATE, PARAMETER STATE, PROPERTY STATE, DESIGN STATE, DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, PARAMETER REINSTATE), and Rules & validation (RULE DECONSTRUCT, VALIDATOR)
- Built a single master table (`Component | Port | Direction | V7 IRI | Layer | Notes`) with 66 rows, using the locked V7 names from `ontology/V7-INVESTIGATION.md`'s rename table for every ontology-backed port
- Applied conflict (a) resolution: VALIDATION GRAPH's `Status` output is mapped to `dgv:ValidStatus` (unified with VALIDATOR's `ValidStatus`) with a note that it is a per-ObjState Boolean list read-back, not a separate text enum
- Applied conflict (b) resolution: VALIDATION GRAPH's/DESIGN STATE's `DesignState` port is noted as stored with `graph='ValidGraph'` (not `Metagraph`)
- Annotated all 10 runtime/DB-only ports (CONNECTOR credentials + Database driver handle, GRAPH DECONSTRUCT's Database input, PARAMETER REINSTATE's Reinstate trigger, VALIDATOR's SendValid trigger + DataServiceUrl/Report/ValidationRunId publish extras) with explicit "no ontology IRI" notes rather than leaving them blank
- Verified all 25 distinct ontology IRIs cited in the table resolve in `ontology/DesignGrammar-V7.owl` via targeted `grep -c 'about="&prefix;LocalName"'` checks (all returned >=1)
- Discovered and corrected one naming subtlety during verification: the PDF's `DG.Layer.Validgraph.ReStatus` ontology path and the rename table's "ReStatus (class label)" both name the OWL class's `rdfs:label`, not its IRI — the actual resolvable class IRI is `dgv:ReStatusValue`. Fixed the StateStatus row to cite the real IRI with a note cross-referencing the display name
- Added a "## Resolution check" footer recording: 25 ontology IRIs referenced/resolved, 10 runtime/DB ports annotated, zero unmapped references

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the 14-component port -> V7 IRI master table** - `becbfcc` (feat)
2. **Task 2: Verify every ontology IRI in the map resolves in DesignGrammar-V7.owl** - `ab66bce` (docs)

## Files Created/Modified
- `ontology/port-iri-map-V7.md` - The ONTO-06 component-port -> V7 ontology-IRI master table (66 rows across 14 components) plus a Resolution check footer; successor of `GH-mapping.png`, force-added despite `ontology/` being gitignored (established precedent from 13-01/13-02)

## Decisions Made
- `dgv:ReStatusValue` (not a nonexistent `dgv:ReStatus`) is the correct IRI for PARAMETER REINSTATE's `StateStatus` output — the rename table's "ReStatus" is the class's `rdfs:label`, matching the PDF's display path, while `ReStatusValue` is the actual `rdf:about` IRI
- `dgv:objectRefName` used for both OBJECT STATE's `Label` input and OBJECT DECONSTRUCT's `Label` output — `DesignGrammar-V7.owl` has no dedicated `Geometry.Label` datatype property matching the PDF's literal `DG.Core.Structure.Geometry.Label` path; `objectRefName` is the existing IRI that carries the same semantic role (user-supplied ObjectRef string, per PROJECT.md's "ObjectRef is user-supplied string, not geometry-hash" decision)
- Runtime/DB-only ports use a `— (description)` placeholder in the V7 IRI column plus a `Runtime` Layer tag and explanatory Note, rather than being omitted from the table — keeps the "zero unmapped references" invariant literal (every row has a non-empty IRI-column cell) while still being unambiguous that no ontology entity exists for these ports by design

## Deviations from Plan

None - plan executed exactly as written. The `ReStatusValue` vs `ReStatus` correction was performed as part of Task 2's own instructed verification-and-correction loop ("Any IRI that does not resolve is either (i) a typo... fix the map"), not an unplanned deviation.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `ontology/port-iri-map-V7.md` is ready as the port-contract input for Phase 14 (graph schema v4 propagation), Phase 17 (graph-access components), and Phase 18 (validator rework) — all three can grep this file directly instead of the retired `GH-mapping.png`
- This plan completes ONTO-06 and, together with 13-01/13-02, closes out the locked ontology contract half of Phase 13; 13-04 (the remaining wave-3 plan, also depending on 13-02) is unaffected by this plan's file scope
- No blockers identified for downstream plans

---
*Phase: 13-ontology-v7-and-contract-investigation*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: ontology/port-iri-map-V7.md
- FOUND: commit becbfcc
- FOUND: commit ab66bce
- FOUND: .planning/phases/13-ontology-v7-and-contract-investigation/13-03-SUMMARY.md

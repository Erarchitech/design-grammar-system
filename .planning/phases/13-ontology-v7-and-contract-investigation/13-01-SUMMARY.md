---
phase: 13-ontology-v7-and-contract-investigation
plan: 01
subsystem: ontology
tags: [owl, rdf, neo4j, cypher, naming-authority]

# Dependency graph
requires: []
provides:
  - "ontology/V7-INVESTIGATION.md — resolved conflicts (a)/(b)/(c) and the authoritative V6->V7 rename table"
  - "Final locked DesignState kind names: ObjState | ParamState | PropState"
  - "Locked Run field contract: ValidStatus (Boolean list, index-matched to ObjState), SendStatus (single Boolean), overall pass derived via AND(ValidStatus)"
  - "Locked DesignState storage layer: graph='ValidGraph', written only by VALIDATOR on publish, MERGE'd by StateId+project, no-orphan invariant enforced"
affects: ["13-02-apply-v7-rename", "13-03-port-iri-map", "14-graph-schema-v4-propagation", "17-graph-access-components", "18-rules-and-validator-rework"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Investigation-note-as-naming-authority — a single markdown file locks contested names before any code/ontology transform runs"]

key-files:
  created: ["ontology/V7-INVESTIGATION.md"]
  modified: []

key-decisions:
  - "Conflict (a): Run.ValidStatus unified as a Boolean list, one element per ObjState, index-matched; overall pass = AND(ValidStatus), derived not stored; no separate Status text field"
  - "Conflict (b): DesignState moves to graph='ValidGraph' (was Metagraph in cypher_template v3); written only by VALIDATOR; MERGE'd by StateId+project; one-DesignState-to-many-Runs; no-orphan invariant is enforced, not advisory"
  - "Conflict (c): owl:versionInfo='7.0' is the single source of version truth; stale 'Schema version: v3' rdfs:comment resolved (removed or rewritten to v7)"
  - "Rename table confirms every V6 source name by direct grep against DesignGrammar-V6.owl before inclusion — not guessed"
  - "OWL-construct collision hazard flagged explicitly: dg:ObjectProperty/dg:DatatypeProperty (reification classes) rename to ObjProperty/DataProperty; owl:ObjectProperty/owl:DatatypeProperty (OWL 2 language constructs) must never be touched"
  - "ruleText/ruleTitle (2 V6 props) map to SWRL/RuleName plus a new RuleDescription (3 V7 props) — rationale documented for the 2->3 expansion"
  - "Metagraph and SpecGraph confirmed NOT renamed; only OntoGraph/ValidationGraph/ComputationGraph get the Ontograph/Validgraph/Computgraph casing rename"

patterns-established:
  - "Naming-authority-first: downstream rename scripts and port maps consume one locked markdown table rather than re-deriving names from the PDF/owl independently"

requirements-completed: [ONTO-04]

coverage:
  - id: D1
    description: "V7-INVESTIGATION.md resolves conflict (a) — ValidStatus Boolean list vs Status text, unified to one field with derived overall pass"
    requirement: "ONTO-04"
    verification:
      - kind: other
        ref: "grep -i 'no-orphan|derived not stored|AND(ValidStatus)' ontology/V7-INVESTIGATION.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "V7-INVESTIGATION.md resolves conflict (b) — DesignState storage layer corrected to graph='ValidGraph', no-orphan invariant enforced"
    requirement: "ONTO-04"
    verification:
      - kind: other
        ref: "grep -c ValidGraph ontology/V7-INVESTIGATION.md (>=1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "V7-INVESTIGATION.md resolves conflict (c) — owl:versionInfo='7.0' as single source of truth, stale v3 comment resolution recorded"
    requirement: "ONTO-04"
    verification:
      - kind: other
        ref: "ontology/V7-INVESTIGATION.md ## Conflict (c) section"
        status: pass
    human_judgment: false
  - id: D4
    description: "Complete, grep-verified V6->V7 rename table with all required rows and the OWL-construct collision hazard flagged"
    requirement: "ONTO-04"
    verification:
      - kind: other
        ref: "grep -E 'ObjectState.*ObjState|DefState.*ParamState|ValidationRun.*Run|ruleText.*SWRL|ruleTitle.*RuleName' ontology/V7-INVESTIGATION.md; grep -i owl:ObjectProperty ontology/V7-INVESTIGATION.md"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-03
status: complete
---

# Phase 13 Plan 01: Ontology V7 Naming Authority Summary

**Resolved all three GH_DesignGrammars.pdf-internal naming conflicts and produced the complete, grep-verified V6->V7 rename table that Phase 13's remaining plans (and Phases 14/17/18) consume as the single naming authority.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-03T00:53:00Z (approx)
- **Completed:** 2026-07-03T01:08:23Z
- **Tasks:** 2
- **Files modified:** 1 (new)

## Accomplishments
- Wrote `ontology/V7-INVESTIGATION.md`, resolving conflicts (a) Run status model, (b) DesignState storage layer, (c) version marker — each transcribed verbatim from CONTEXT.md decisions D-01..D-11, with direct citations to the offending `cypher_template.txt` lines and PDF ontology-path strings
- Added a "Superseded PDF statements" subsection cataloguing every PDF claim overridden by v7.0
- Built the complete V6→V7 rename table (14 rows) covering the state trio, layer hubs, OntoGraph reification classes, ValidationRun→Run, ReinstatementStatus→ReStatus, the two new Validgraph Boolean properties, and the rule-level datatype property 2→3 expansion — every V6 source name confirmed present in `DesignGrammar-V6.owl` by grep before inclusion
- Flagged the OWL-construct collision hazard (`dg:ObjectProperty`/`dg:DatatypeProperty` reification classes vs `owl:ObjectProperty`/`owl:DatatypeProperty` language constructs) so `apply_v7_rename.py` (13-02) scopes its find/replace correctly
- Locked final state-kind names: `ObjState | ParamState | PropState`
- No ontology source file modified — `DesignGrammar-V6.owl` untouched, verified via `git status --porcelain`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the three conflict resolutions into V7-INVESTIGATION.md** - `332c2f6` (docs)
2. **Task 2: Write the authoritative V6->V7 rename table + final state-kind names** - `15f554a` (docs)

_Note: File was written in two Write/Edit passes (one per task) to keep commits atomic per task, per sequential-executor convention._

## Files Created/Modified
- `ontology/V7-INVESTIGATION.md` - Investigation note: conflict resolutions (a)/(b)/(c), superseded PDF statements, complete V6→V7 rename table, locked state-kind names (121 lines)

## Decisions Made
- Conflict resolutions transcribed verbatim from CONTEXT.md D-01..D-11 (no re-derivation) — see key-decisions in frontmatter
- Rename table rows confirmed against actual `DesignGrammar-V6.owl` content (grep counts documented per row) rather than the plan's approximate estimates, catching minor count discrepancies (e.g. OntoGraph 22 actual vs ~19 estimated, ValidationGraph 56 actual vs ~39 estimated) without altering scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Force-added ontology/V7-INVESTIGATION.md past a repo-wide `ontology/` .gitignore rule**
- **Found during:** Task 1 commit
- **Issue:** `.gitignore` line 30 ignores the entire `ontology/` directory ("Temporary ontology files"), which would have silently prevented this plan's required deliverable from being committed
- **Fix:** Used `git add -f` for `ontology/V7-INVESTIGATION.md`, consistent with the existing precedent that curated ontology docs (`DesignGrammar-V6.md`, `DesignGrammar-V6.owl`, `catalog-v001-V6.xml`, etc. — 21 files already tracked) are force-added past the same blanket ignore rule, while only genuinely temporary/generated scratch files stay ignored
- **Files modified:** none beyond the plan's own deliverable
- **Verification:** `git ls-files ontology/V7-INVESTIGATION.md` confirms tracked; `git status --porcelain ontology/DesignGrammar-V6.owl` confirms the source owl remains untouched
- **Committed in:** 332c2f6, 15f554a

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to land the plan's own required artifact; no scope creep — matches the repo's established pattern for curated (non-generated) ontology docs.

## Issues Encountered
None beyond the gitignore deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `ontology/V7-INVESTIGATION.md` is ready as the naming authority for 13-02 (`apply_v7_rename.py` — builds `DesignGrammar-V7.owl`) and 13-03 (port↔IRI map)
- No blockers identified for downstream plans

---
*Phase: 13-ontology-v7-and-contract-investigation*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: ontology/V7-INVESTIGATION.md
- FOUND: .planning/phases/13-ontology-v7-and-contract-investigation/13-01-SUMMARY.md
- FOUND: commit 332c2f6
- FOUND: commit 15f554a

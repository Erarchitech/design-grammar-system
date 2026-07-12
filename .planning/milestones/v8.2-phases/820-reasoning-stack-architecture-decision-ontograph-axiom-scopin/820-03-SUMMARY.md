---
phase: 820-reasoning-stack-architecture-decision-ontograph-axiom-scopin
plan: 03
subsystem: documentation
tags:
  - decision-record
  - adr
  - project-planning
  - spike-evidence
  - sidecar
  - axiom-scoping
requires:
  - PLAN-820-01 (spike output: naive_result.txt, hybrid_result.txt, axiom_counts.txt)
  - PLAN-820-02 (spec/LPG-OWL-MAPPING.md)
provides:
  - 820-DECISION.md (two ADR entries with spike evidence)
  - PROJECT.md Key Decisions (sidecar row flipped, new hybrid axiom-scoping row)
affects:
  - spec/LPG-OWL-MAPPING.md (cross-referenced as mapping contract)
tech-stack:
  added: []
  patterns:
    - ADR three-part shape (Context / Decision / Consequences) extended with Evidence subsection
    - Key Decisions table row edits (scoped Edit, never whole-table Write)
key-files:
  created:
    - .planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/820-DECISION.md
  modified:
    - .planning/PROJECT.md
decisions:
  - Hybrid axiom-scoping: union static V7.owl TBox + live project export + curated disjointWith (ADR-820-1)
  - dg-reasoner sidecar confirmed as isolated service, not embedded in data-service (ADR-820-2)
metrics:
  duration: ~15 minutes
  completed_date: 2026-07-11
status: complete
---

# Phase 820 Plan 03: Decision Documentation

**One-liner:** Recorded the phase's two architectural decisions as ADR entries with spike evidence (axiom counts + HermiT before/after contrast) in 820-DECISION.md, and updated PROJECT.md's Key Decisions table to flip the dg-reasoner sidecar from Pending to Shipped while adding a new hybrid axiom-scoping row.

## Tasks Executed

| # | Name | Type | Commit | Key Files |
|---|------|------|--------|-----------|
| 1 | Write 820-DECISION.md with spike evidence | auto | `605657c` | 820-DECISION.md |
| 2 | Update PROJECT.md Key Decisions -- flip sidecar row, add hybrid axiom-scoping row | auto | `35b0caa` | PROJECT.md |

## What Was Built

### 820-DECISION.md

Two ADR-style entries following the Context / Decision / Consequences shape from `spec/DECISIONS.md`, each extended with an Evidence subsection citing the Plan 01 spike output:

**ADR-820-1 -- Hybrid axiom-scoping:**
- Context: live OntoGraph is flat (zero SUBCLASS_OF/DOMAIN/RANGE/DISJOINT_WITH relationship types DB-wide), so naive export reasons trivially consistent
- Decision: union static DesignGrammar-V7.owl TBox (65 subClassOf, 101 domain, 110 range) + live project export + curated disjointWith; LLM-ingestion axiom emission deferred
- Evidence: axiom_counts.txt (65 subClassOf, 101 domain, 110 range, 0 disjointWith); naive_result.txt (0 inconsistent classes, false positive); hybrid_result.txt (2 inconsistent classes including ex:SlidingDoor, non-trivial detection)

**ADR-820-2 -- dg-reasoner sidecar confirmed:**
- Context: STACK.md vs ARCHITECTURE.md conflict over embedded-vs-sidecar reasoning, Pending in PROJECT.md
- Decision: confirm isolated dg-reasoner sidecar (Owlready2/HermiT/Openllet + pySHACL), not embedded in data-service
- Evidence: spike ran HermiT as local subprocess via Owlready2 JAR successfully, no blocking issue surfaced

**Data-quality note:** Documents the systemic graph-property tagging drift (2 Atom nodes in v8-ui-smoke tagged `graph:'OntoGraph'`, 6+2 nodes in phase14-smoke tagged `graph:'Metagraph'`) as a known gap for Phase 821's exporter to handle defensively. No repair task scoped. Addresses Assumption A3: v8-ui-smoke QA data satisfies the "live OntoGraph data" success-criterion wording.

### PROJECT.md Key Decisions (edited)

- **Line 134 (dg-reasoner sidecar):** Outcome flipped from `-- Pending -- v8.2 (research-recommended, resolves STACK.md vs ARCHITECTURE.md conflict)` to `✓ Shipped -- v8.2 Phase 820 (spike evidence: see 820-DECISION.md)`. Decision and Rationale columns unchanged.
- **Line 135 (new):** Hybrid axiom-scoping row added with Decision (static TBox + live export + curated disjointWith, LLM ingestion deferred), Rationale (live OntoGraph flat, hybrid avoids n8n prompt churn + 9-file schema propagation), and Outcome (`✓ Shipped -- v8.2 Phase 820 (see 820-DECISION.md; mapping spec spec/LPG-OWL-MAPPING.md)`).
- **Line 136 (CONNECTOR):** Untouched -- still `-- Pending -- v8.2`.

## Verification

### Automated checks (Task 1 -- 820-DECISION.md)
- `test -s 820-DECISION.md`: PASS
- `grep -qi "Evidence" 820-DECISION.md`: PASS
- `grep -qi "SlidingDoor" 820-DECISION.md`: PASS
- `grep -qi "sidecar" 820-DECISION.md`: PASS
- `grep -q "LPG-OWL-MAPPING.md" 820-DECISION.md`: PASS

### Automated checks (Task 2 -- PROJECT.md)
- `grep -q "820-DECISION.md" PROJECT.md`: PASS
- `grep -q "LPG-OWL-MAPPING.md" PROJECT.md`: PASS
- `grep "dg-reasoner" PROJECT.md | grep -q "Shipped"`: PASS
- `grep -qi "hybrid" PROJECT.md`: PASS
- CONNECTOR row still `-- Pending -- v8.2`: PASS

### Deviations from Plan

None -- plan executed exactly as written.

### Threat Surface Scan

No new security-relevant surface introduced. 820-DECISION.md cites axiom counts and HermiT class names only (no connection strings, credentials, or full rule bodies). PROJECT.md edits use scoped Edit operations, never whole-file overwrites (per T-820-06 mitigation).

## Self-Check

- [x] `820-DECISION.md` exists with two ADR entries + Evidence subsections
- [x] `PROJECT.md` dg-reasoner row shows Shipped v8.2 Phase 820 outcome
- [x] `PROJECT.md` new hybrid axiom-scoping row exists
- [x] `PROJECT.md` CONNECTOR row unchanged (still Pending)
- [x] No credential literals in either committed file
- [x] Both tasks committed individually (commit hashes: 605657c, 35b0caa)

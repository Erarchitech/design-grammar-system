---
tags: [session, phase-820, v8.2]
date: 2026-07-11
---

# Session: Phase 820 Execution — Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping

**Date:** 2026-07-11
**Model:** deepseek-v4-pro → haiku
**Purpose:** Execute Phase 820 of v8.2: decide the axiom-scoping approach, write the LPG→OWL mapping spec, run the spike, and record both decisions in PROJECT.md.

## Summary

Phase 820 fully completed — all 3 plans executed, verified (12/12 must-haves), and tracked.

## Key Outcomes

### 1. Hybrid Axiom-Scoping Decision (spike-confirmed)
**Decision:** Union static `DesignGrammar-V7.owl` TBox (69 subClassOf, 105 domain, 112 range, **0 disjointWith**) with live project-scoped OntoGraph export, plus curated `disjointWith` axioms in the static TBox. LLM ingestion changes deferred out of v8.2.

**Spike proof (definitive):**
- **Part (a) — Naive export → HermiT:** 0 inconsistent classes — the documented false positive. The flat export has no axioms connecting domain terms, so nothing can be unsatisfiable.
- **Part (b) — Hybrid + curated `ex:Door owl:disjointWith ex:Window` + seeded `ex:SlidingDoor`: 2 inconsistent classes: `[owl.Nothing, ex.SlidingDoor]` — the non-trivial result the naive export missed. HermiT runtime: 1.23s.

**Evidence files:** `spike/output/naive_result.txt`, `spike/output/hybrid_result.txt`, `spike/output/axiom_counts.txt`

### 2. dg-reasoner Sidecar Decision Confirmed
The research-recommended sidecar (previously Pending in PROJECT.md) was confirmed and flipped to Shipped — reasoning runs in a new isolated `dg-reasoner` Python container, NOT embedded in `data-service`.

### 3. LPG→OWL Mapping Spec (spec/LPG-OWL-MAPPING.md)
399-line normative contract covering:
- SWRL RDF vocabulary mapping for Metagraph (swrl:Imp, rdf:List for order, swrl:argument1/2 for pos)
- OntoGraph mapping (flat live graph + static TBox union)
- IRI minting with project-scoped path segments
- Label-scoped export mandate (Pitfall 1 fix: mistagged atoms captured)
- UNA handling via owl:AllDifferent
- Informative ValidGraph→RDF sketch
- HermiT builtin-exclusion limitation documented

### 4. Live Data-Quality Finding
Two `Atom` nodes in `v8-ui-smoke`'s `R_DOOR_ORIENTATION_V` rule are mistagged `graph:'OntoGraph'` instead of `'Metagraph'`. Documented as a gap — no repair task scoped into this phase.

## Artifacts Created

| Artifact | Path |
|----------|------|
| Axiom-scoping spike | `.planning/phases/820-.../spike/` (export.py, run_naive.py, run_hybrid.py, README.md, output/) |
| Mapping spec | `spec/LPG-OWL-MAPPING.md` |
| Decision record | `.planning/phases/820-.../820-DECISION.md` |
| Spike evidence | `spike/output/naive_result.txt`, `hybrid_result.txt`, `axiom_counts.txt`, `naive_export.ttl`, `hybrid_export.ttl` |
| Plan docs | `820-01-{PLAN,SUMMARY}.md`, `820-02-{PLAN,SUMMARY}.md`, `820-03-{PLAN,SUMMARY}.md` |
| PROJECT.md Key Decisions | Sidecar row flipped to Shipped; hybrid axiom-scoping row added |

## Decisions

- **Hybrid axiom scoping** (static TBox + live export + curated disjointness) — recorded in `820-DECISION.md` and PROJECT.md
- **dg-reasoner sidecar** confirmed — recorded in `820-DECISION.md` and PROJECT.md
- **Label-scoped export** (Pitfall 1) — the Cypher exporter MUST scope by node label, not the `graph` property
- **UNA via owl:AllDifferent** in the mapping spec

## Fixes Applied

- `run_hybrid.py` was missing `strip_hermit_unsupported()` import and call — HermiT crashes on SWRL builtin atoms. Fixed inline after the original executor hit a session limit.
- `spike/README.md` JRE instructions updated — Debian trixie ships OpenJDK 21, not 17

## Next Steps

- Phase 821 (dg-reasoner Sidecar & RDF Translation) — ready to plan
- dg-reasoner sidecar builds clean against `spec/LPG-OWL-MAPPING.md`
- Phase 822 (OWL 2 DL Reasoning + Reasoner Screen) — depends on 821
- Phase 823 (SHACL Validation Layer) — depends on 821 only
- Phase 824 (CONNECTOR Credential Integration) — independent, can run in parallel

## Related Links

- [[decisions/Reasoning runs in isolated dg-reasoner sidecar not embedded in data-service]]
- `spec/LPG-OWL-MAPPING.md`
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/820-DECISION.md`

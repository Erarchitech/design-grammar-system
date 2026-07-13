# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v8.2 — Connector Integration & Reasoning Engine

**Shipped:** 2026-07-12 (override closeout)
**Phases:** 5 (820–824) | **Plans:** 19 | **Tasks:** 44

### What Was Built
- Isolated `dg-reasoner` sidecar (Python 3.11 + headless JRE) with a fidelity-tested Cypher→RDF translator built against a written contract (`spec/LPG-OWL-MAPPING.md`).
- Real OWL 2 DL consistency checking (HermiT) wired end-to-end into the Reasoner screen, replacing the v8.1 placeholder — with `{iri,label}` results and a timeout→"unknown" safety path.
- A SHACL validation layer (8 data-integrity NodeShapes over the ValidGraph ABox with UNA) surfacing on the VALIDATOR component and a Solibri-style Data Integrity panel in ui-v2, governed by `spec/RULE-PARTITION-POLICY.md`.
- Additive CONNECTOR platform-token heartbeat with in-canvas feedback and full token secrecy — component GUID and existing ports untouched.

### What Worked
- **Spike-first de-risking (Phase 820).** A throwaway spike proved the naive Neo4j→RDF export would report *trivially consistent* (the live OntoGraph is flat: zero SUBCLASS_OF/DOMAIN/RANGE/DISJOINT_WITH edges). Catching this before Phase 821 built the translator saved the whole reasoning arm from shipping a meaningless "always consistent" result.
- **Contract-then-implement.** Writing `spec/LPG-OWL-MAPPING.md` first, then implementing `ontology_export.py` against it (not porting the spike), produced a clean translator with 8 structural fidelity tests pinning edge-property reification (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`).
- **Additive-port pattern.** CONNECTOR gained new capability with no GUID/port changes — deliberately avoiding the v7.0 CLASSIFICATOR/VALIDATION-RUNS canvas-breakage pattern.

### What Was Inefficient
- **Stale container code caused mid-plan rebuilds (Phase 821).** dg-reasoner and data-service were running Plan-01-era stub code, so live verification of later plans required explicit `docker compose build && up -d` mid-phase. A rebuild-before-verify step would have avoided the surprise.
- **Verification debt accrued.** 3 of 5 phases (822/823/824) closed without full verification — in-Rhino and manual-frontend UAT were deferred, and 823 shipped with no formal VERIFICATION.md. Real work, but it forced an override closeout.

### Patterns Established
- **Reasoning/JVM work lives in an isolated sidecar**, never embedded in `data-service`'s Speckle-publish/validation-run hot path (DL reasoning is worst-case exponential; the corpus grows unboundedly).
- **Single-authoring rule partition:** a written policy assigns each rule category to exactly one validation system (SHACL vs. SWRL VALIDATOR) so no rule is authored twice with disagreeing verdicts.
- **Data-integrity findings never fail a component** — SHACL surfaces capped at Warning/Remark, Error stays reserved for genuine publish failures.

### Key Lessons
1. **Verify the actual data shape before assuming a capability works.** The "reasoner reports consistent" result was meaningless until the spike revealed the flat OntoGraph — assumptions about ontology richness were wrong.
2. **Explicitly defer human/in-Rhino UAT rather than letting it silently block a close.** The override closeout is honest and recorded (STATE.md Deferred Items, MILESTONES.md `Known verification overrides: 3`); the resume paths (`/gsd-verify-work 822/824`) are captured.
3. **Rebuild containers before live-verifying** any phase whose earlier plans shipped stubs.

### Cost Observations
- Model mix: planning on opus, execution/verification largely on sonnet (per GSD default profile).
- Notable: heaviest phase was 822 (Reasoner wiring, ~45min plan + 4 plans); lightest were the schema-propagation plans (3–8min).

---

## Milestone: v8.1 — Platform Setup Regions

**Shipped:** 2026-07-11 · *(retrospective entry written retroactively 2026-07-13 during the gap-closure session — v8.1 skipped the formal `/gsd-complete-milestone` pass at ship time)*
**Phases:** 7 (810–816) | **Plans:** 7

### What Was Built
- Landing ring extended 3 → 7 region callouts with four new screen layers (AI Engine, Connectors, Reasoner, DG API Docs) on the existing fly/back navigation grammar.
- AI Engine screen over the Phase-28 LLM gateway (provider/model/key, encrypted-at-rest, set/not-set status only).
- Connector credential backend + screen: 14-connector/5-category registry, copy-once `dgc_` tokens (hash-only persistence), heartbeat, never-connected/active/stale status, two-step revoke.
- Reasoner selection screen (HermiT/Pellet placeholders — HermiT made real in v8.2) and a Revit-API-style DG API docs browser with zero-viewer-change content modules.

### What Worked
- **One plan per phase.** All 7 phases were single-plan — small, sharply-scoped phases executed in one day.
- **Registry-driven UI.** The Connectors screen renders whatever `GET /connectors` serves; adding a connector is a one-line backend change.

### What Was Inefficient
- **Record debt.** Phases 810–813 closed without VERIFICATION.md docs, 813 without a plan SUMMARY, requirement checkboxes were never flipped, and no MILESTONES.md entry was written — all closed retroactively on 2026-07-13. Lesson: run the formal complete-milestone pass at ship time even when the work is verifiably done; retroactive reconstruction costs more than the pass would have.

### Key Lessons
1. Milestone bookkeeping (verification docs, requirement flips, MILESTONES entry) is part of shipping, not optional paperwork — skipping it created the v8.1 record debt paid off two days later.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v8.1 | 2 | 7 | First milestone on X·100+Y·10 phase numbering; one-plan-per-phase cadence; formal ship pass skipped (record debt closed 2026-07-13) |
| v8.2 | — | 5 | First isolated-sidecar service; spike-first for reasoning; first override closeout with recorded deferred verification |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v8.1 | data-service 90 pytest (18 connector lifecycle, 8 reasoner settings) | — | connector registry, `dgc_` token store, reasoner settings store, docs content modules |
| v8.2 | dg-reasoner 19/19, data-service 13/13, DG 234 unit (2026-07-13 re-run: 39/39, 168/168, 234/234 in-container) | — | `dg-reasoner` sidecar, `ontology/dg-disjointness.ttl`, 8 SHACL NodeShapes |

### Top Lessons (Verified Across Milestones)

1. Spike/verify the real data before building on an assumed capability. (v8.2)
2. Additive ports over GUID-breaking rewrites for Grasshopper components. (v7.0 lesson, reconfirmed v8.2)

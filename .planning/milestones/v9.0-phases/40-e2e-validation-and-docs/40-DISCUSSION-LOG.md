# Phase 40: E2E Validation and Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-28
**Phase:** 40-e2e-validation-and-docs
**Areas discussed:** E2E execution vehicle, Closeout with 30/31 unbuilt, Provider-key dependency, Docs surface and inventory

---

## E2E execution vehicle

### Q1 — What is Phase 40's E2E deliverable, mechanically?

| Option | Description | Selected |
|--------|-------------|----------|
| Run the existing runbook | Plans wrap `v9.0-PIPELINE-UAT.md` Session A + B; no new test script | ✓ |
| Phase-40-owned E2E script | New automated pytest/bash driver chaining the Docker-side legs | |
| Runbook + thin automation layer | Runbook as spine, script automates the mechanically-checkable parts | |

**User's choice:** Run the existing runbook
**Notes:** The runbook was re-audited 2026-07-28 and says outright that Session B *is* Phase 40's
second E2E deliverable. A second copy would drift from the first.

### Q2 — Where do E2E results get recorded?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-phase UAT + 40-EVIDENCE.json | Results in owning `NN-UAT.md` files **and** a Phase-40 evidence artifact | ✓ |
| Per-phase UAT files only | Results only where the runbook says; Phase 40 VERIFICATION cites them | |
| 40-EVIDENCE.json only | One Phase-40 file is the record; UAT files get a pointer line | |

**User's choice:** Per-phase UAT + 40-EVIDENCE.json
**Notes:** UAT-only leaves no single artifact proving "both chains, one session"; evidence-only leaves
six phases' human items formally open. Follows Phase 39's evidence-artifact precedent.

### Q3 — How does the live session get run inside Phase 40's plans?

| Option | Description | Selected |
|--------|-------------|----------|
| Blocking checkpoint inside a plan | `checkpoint:human-verify`, gate=blocking — the 33-04 precedent | ✓ |
| Prepare, then hand off to /gsd-verify-work 40 | Automatable prep in plans; live session deferred to phase verification | |
| Split: Session A blocking, Session B deferred | Browser chain blocking, the 3–4 h Rhino spine deferred | |

**User's choice:** Blocking checkpoint inside a plan
**Notes:** Phase 40's E2E *is* its deliverable — deferring it would defer the phase. The 33/34
deferral pattern is right for code-deliverable phases, wrong here.

### Q4 — What counts as an SC1 pass given known-open findings?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-register the exclusions | Criterion written before the run; F-39-01, 35 SC1, G7 named as expected observations | ✓ |
| Strict — any red is a fail | Any finding or guardrail block fails SC1 and reopens the owning phase | |
| Judge at the checkpoint | Call pass/fail live per leg with no pre-registered rule | |

**User's choice:** Pre-register the exclusions
**Notes:** Strict guarantees a fail on F-39-01 alone, which Phase 39 deliberately scoped to a
follow-up milestone. Judging live is the measure-quality-late failure mode Phase 38-01 closed.

---

## Closeout with 30/31 unbuilt

### Q1 — How does v9.0 close with Phases 30 and 31 never started?

| Option | Description | Selected |
|--------|-------------|----------|
| Formal deferral record | `ORCH-*`/`RING-*` marked deferred with reason and target milestone; SC3 restated | ✓ |
| Block until 30/31 execute | Phase 40 waits for an orchestration ADR plus a full ingest rework | |
| Descope from v9.0 outright | Cut the requirements so the denominator drops and SC3 reads clean | |

**User's choice:** Formal deferral record
**Notes:** Descoping loses the record that they were planned and why they were not built; blocking
puts two unstarted phases ahead of one whose dependencies are otherwise all done.

### Q2 — Is fixing ROADMAP progress-table drift Phase 40's job?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — part of the traceability sweep | Reconcile ROADMAP table, REQUIREMENTS checkboxes, deferral record in one pass | ✓ |
| No — separate quick task | Fix with `/gsd-fast` outside Phase 40 to keep scope tight | |
| Yes, and extend to STATE.md | Same, plus STATE.md status lines and Deferred Verification table | |

**User's choice:** Yes — part of the traceability sweep
**Notes:** SC3 demands "traceability complete", and a progress table contradicting the phase
directories is itself a traceability defect (Phase 37 reads "Not started / 0 plans" though 6/6 ran).

### Q3 — Where does the deferral record live?

| Option | Description | Selected |
|--------|-------------|----------|
| REQUIREMENTS.md + Phase 40 artifact | Deferred section in the file GSD reads, plus `40-DEFERRALS.md` for reasoning | ✓ |
| REQUIREMENTS.md only | One place, no duplication | |
| Vault ADR in DG_OBSIDIAN | Decision note per the Phase 39 ADR precedent, with a pointer from REQUIREMENTS | |

**User's choice:** REQUIREMENTS.md + Phase 40 artifact
**Notes:** REQUIREMENTS.md is what tooling reads; the artifact survives the milestone archive
alongside the phase.

### Q4 — What happens to the runbook's five open decisions D1–D5?

| Option | Description | Selected |
|--------|-------------|----------|
| Take D4+D5, backlog D1–D3 | D4 is an INTG-04 docs gap, D5 a one-line annotation; D1–D3 are design changes | ✓ |
| Backlog all five | Keep Phase 40 strictly to E2E + docs | |
| Resolve all five | Close every open decision before shipping the milestone | |

**User's choice:** Take D4+D5, backlog D1–D3
**Notes:** D4 is Phase 39's `:ValidationRun` properties that `spec/DATABASE.md` documents nowhere —
squarely INTG-04. D1 and D3 would expand Phase 40 well past E2E and docs.

---

## Provider-key dependency

### Q1 — How does Phase 40 handle the missing frontier key?

| Option | Description | Selected |
|--------|-------------|----------|
| Gate the plan on a supplied key | Blocking checkpoint asking for an Anthropic/OpenAI key in the AI Engine panel | ✓ |
| Two-provider drill, third blocked | DeepSeek ↔ Ollama live; Anthropic recorded blocked-not-failed | |
| Split into its own human-checkpoint plan | Isolate all key-dependent work so the rest of Phase 40 completes | |

**User's choice:** Gate the plan on a supplied key
**Notes:** One key unblocks four items — SC2, Phase 35 SC1, Phase 36 test 3 provenance, and live
recognition. The runbook calls it "the one prerequisite that gates almost everything".

### Q2 — Is the S-A/3 frontier recognition sweep in Phase 40's scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Run it, but credit Phase 35 | Nearly free once the key exists (~$0.08, driver exists); results to 35-UAT/35-EVAL-REPORT | ✓ |
| Out of scope — Phase 35 owns it | Configure the key and stop; Phase 35 reopens separately | |
| Run it and let it gate Phase 40 | Treat recognition quality as part of the E2E chain | |

**User's choice:** Run it, but credit Phase 35
**Notes:** Gating Phase 40 on it would couple milestone close to an unresolved research question
(the 0.60 ship gate).

### Q3 — Pre-registered fallback if no key materialises?

| Option | Description | Selected |
|--------|-------------|----------|
| Two-provider fallback, SC2 blocked | DeepSeek ↔ Ollama proves the mechanism; SC2 blocked-not-failed in evidence | ✓ |
| Phase 40 stays open indefinitely | No key, no close | |
| Ollama-only, switch "mechanically proven" | Lean on unit coverage of `resolve_active_provider()` | |

**User's choice:** Two-provider fallback, SC2 blocked
**Notes:** Same blocked-not-failed discipline Phase 35 SC1 already uses. Ollama-only contradicts the
drill's whole purpose — the live `n8n → gateway → provider → Neo4j` path has never run.

---

## Docs surface and inventory

### Q1 — Where does the 5-component GH reference live?

| Option | Description | Selected |
|--------|-------------|----------|
| `docs/RELEASE-NOTES-v9.0.md` | Follows the v7.0/v8.0 per-component layout (ports, GUID, wiring diagram) | ✓ |
| New `docs/COMPONENTS-v9.0.md` | Purpose-built reference without "what broke" framing | |
| In-app ui-v2 apidocs viewer | Content modules in the Phase 815 auto-registering `##-` pattern | |

**User's choice:** `docs/RELEASE-NOTES-v9.0.md`
**Notes:** Canvas authors already know where to look; a second docs shape would need keeping in sync
with the release-notes series.

### Q2 — What replaces the non-existent Phase 30 ADR in INTG-04?

| Option | Description | Selected |
|--------|-------------|----------|
| Deferral note pointing at the record | Vault note stating n8n-vs-OpenClaw is unresolved, cross-linked to `40-DEFERRALS.md` | ✓ |
| Drop the Phase 30 clause from INTG-04 | Amend the requirement to name only the Phase 39 ADR | |
| Write the ADR now from existing research | Phase 40 makes the orchestration call itself | |

**User's choice:** Deferral note pointing at the record
**Notes:** Writing the ADR would decide Phase 30's entire deliverable inside a docs phase without the
evaluation it was meant to rest on.

### Q3 — How deep do the CLAUDE.md and spec/ updates go?

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted patches against a written inventory | Enumerate every v9.0-touched doc surface, then patch in place | ✓ |
| Full CLAUDE.md rewrite | Regenerate end to end per the Phase 20 copilot-instructions precedent | |
| Patches plus a verified-against-code pass | Same patches, then verify every factual claim against the codebase | |

**User's choice:** Targeted patches against a written inventory
**Notes:** CLAUDE.md already carries most of this correctly; a rewrite would churn correct text and
risk regressing the gotchas and schema tables.

### Q4 — How is SC4's grep gate verified?

| Option | Description | Selected |
|--------|-------------|----------|
| Run the grep, fix every hit, record output | Treat it as the executable check it is written as; paste output into evidence | ✓ |
| Extend the sweep past CLAUDE.md and spec/ | Widen to README, copilot-instructions, docs/ | |
| Prose review, no mechanical grep | Judge the framing by eye | |

**User's choice:** Run the grep, fix every hit, record output
**Notes:** A grep gate that is never actually run is not a gate.

---

## Claude's Discretion

- **DG Canvas Annotation Convention vault note** — a roadmap deliverable that does not exist yet
  (only a Phase 32 session note mentions the convention). Shape, depth and placement within
  `DG_OBSIDIAN/knowledge/` left to Claude; the grammar itself is already single-sourced in
  `CanvasAnnotationParser.cs` and the Phase 34-01 consistency test.
- **graphify refresh ordering** — runs after the docs edits land; whether it is its own task or
  folded into the docs plan is Claude's call.
- **Plan/wave decomposition** across the four work streams, beyond the checkpoint placement fixed by
  the blocking-checkpoint and provider-key decisions.

## Deferred Ideas

- **D1** — F5(c) per-entity vs. all-or-nothing publish rejection (changes the `/computgraph/publish`
  contract; interacts with MERGE idempotency) → v10.0 backlog
- **D2** — partial-reselection re-tag creates a stray nested duplicate (`EntityTagComponent.cs:246-263`
  exact-member-match policy) → v10.0 backlog
- **D3** — `PreviewRegistry` is not undo-aware (needs a custom `IGH_UndoAction`) → v10.0 backlog
- **F-39-01** — auto-validation verdicts are a constant, not a judgement; Phase 39 scoped the fix to
  follow-up milestone item #1. Phase 40 observes, does not fix.
- **Phases 30 and 31** — orchestration evaluation and rules ingestion/editing upgrade, deferred with
  their `ORCH-*` / `RING-*` requirements
- **Tier-0 rule coverage** — `cg_topology.classify()` abstains on every scoped candidate in both
  corpora (extends 35-14's R4 defect); warrants its own plan
- **`migrations/2026-07-07_validationgraph_to_validgraph.cypher`** — still awaiting approval; not
  v9.0 scope, but the close-out is a natural moment to raise it

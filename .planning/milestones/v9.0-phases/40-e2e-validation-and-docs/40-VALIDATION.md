---
phase: 40
slug: e2e-validation-and-docs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-28
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Phase 40 is a hybrid-validation phase.** It adds no new application source code. Its
> deliverables are (a) two human-observed live E2E runs, (b) doc patches, and (c) planning-artifact
> reconciliation. Most claims are mechanically checkable; the two E2E chains and the provider drill
> are **not**, and are named as blocking human checkpoints rather than papered over with a test that
> cannot actually observe a live Rhino session. Derived from `40-RESEARCH.md` §Validation
> Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Mixed, pre-existing — xUnit (`DG/tests/DG.Tests/`) + pytest (`data-service/tests/`). **Phase 40 adds no new test files.** |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj`; data-service pytest run in-container |
| **Quick run command** | `curl -s http://localhost:8000/openapi.json` 10-route probe (Step 0.3) + `grep -ri "ollama" CLAUDE.md spec/` (D-15) |
| **Full suite command** | `dotnet test ./DG/tests/DG.Tests/` **and** `docker compose exec data-service python -m pytest tests/ -q` |
| **Estimated runtime** | Route probe ~2s; grep ~1s; dotnet ~60-90s; in-container pytest ~90s |

**Known-baseline exclusions (environment, not regressions):**

- `dotnet test` — 4 `DesignStateValidationFlowTests` fail when Neo4j is down; up to 2 may flake on the
  shared-`TestProject` order dependency with Neo4j up (Step 0.6).
- pytest **must run in-container** — 4 `test_dg_context.py` tests fail from the host because the
  `neo4j` hostname does not resolve outside the compose network. Expected in-container: ~573 passed / 0 failed (Step 0.7).

---

## Sampling Rate

- **After every task commit:** the mechanical gate set — route probe, grep gates, file-existence and
  content assertions. Cheap; run every time a docs or traceability edit lands.
- **After every plan wave:** full suite (`dotnet test` + in-container pytest) — the Step 0.6/0.7 gates.
- **Per E2E leg:** the blocking human checkpoint, run once per Session (A, then B), each producing its
  own `40-EVIDENCE.json` section plus the per-phase `NN-UAT.md` `result:` updates it closes.
- **Before `/gsd-verify-work 40`:** `40-EVIDENCE.json` exists and is complete (including a
  `missing_measurements` array), `REQUIREMENTS.md` is reconciled, and the SC4 grep output is pasted
  verbatim into the evidence file.
- **Max feedback latency:** ~90s for mechanical + suite checks. The E2E legs are session-scoped, not
  latency-bounded — there is no automated "Phase 40 test suite" to run.

---

## Per-Task Verification Map

Task IDs are assigned by the planner; this table pre-registers the **check per claim** so no plan
task can claim a deliverable without a named proof. Rows marked `human` are the D-03 blocking
checkpoint, not automatable.

| Claim | Requirement | Test Type | Automated Command / Proof | Status |
|-------|-------------|-----------|---------------------------|--------|
| Stack up, all services running | Step 0.1 | smoke | `docker compose ps` — data-service, neo4j, n8n, design-grammars, dg-reasoner, speckle-* all Up | ⬜ pending |
| data-service container is fresh (F7 guard) | Step 0.2/0.3 | smoke | `docker compose build data-service && docker compose up -d data-service`, then 10-route `openapi.json` probe — **10 × OK required** | ⬜ pending |
| `.gha` provenance is trustworthy | Step 0.5 | mechanical | SHA256 of built `.gha` matches the copy in `%APPDATA%\Grasshopper\Libraries\DG\`; Rhino start time later than `.gha` build timestamp | ⬜ pending |
| C# suite green at baseline | Step 0.6 | unit | `dotnet test ./DG/tests/DG.Tests/` — no failures beyond the documented Neo4j-down/flake baseline | ⬜ pending |
| Python suite green at baseline | Step 0.7 | unit | `docker compose exec data-service python -m pytest tests/ -q` — ~573 passed / 0 failed | ⬜ pending |
| **SC1 leg 1** — NL rule → cloud-LLM ingest → graph → GH validation → Speckle publish | INTG-01 | **human** | Blocking checkpoint (Session A). Proof = `40-EVIDENCE.json` `session_a` block + closed `NN-UAT.md` items | ⬜ pending |
| **SC1 leg 2** — marked → tagged → recognized → preview → confirm → publish → validate → inputs → REINSTATE → run | INTG-03 | **human** | Blocking checkpoint (Session B). Proof = `40-EVIDENCE.json` `session_b` block + closed `NN-UAT.md` items | ⬜ pending |
| **SC2** — provider switch Claude ↔ OpenAI-compatible ↔ Ollama, settings only, no restart | INTG-02 | **human** | Blocking checkpoint, gated by the D-09 API-key checkpoint. Fallback per D-11: record **blocked-not-failed** with the missing-key reason | ⬜ pending |
| **SC3** — every v9.0 requirement checked off **or** carries a written deferral | INTG-04 | mechanical | Checkbox-state read of `.planning/REQUIREMENTS.md` + presence of a Deferred section listing every `ORCH-*` / `RING-*` ID with owning phase and target milestone | ⬜ pending |
| Traceability: ROADMAP progress table matches disk | INTG-04 / D-06 | mechanical | Per-phase `*-PLAN.md` / `*-SUMMARY.md` counts + `NN-VERIFICATION.md` `status:` frontmatter, diffed against the ROADMAP row | ⬜ pending |
| Traceability: REQUIREMENTS.md internal consistency | INTG-04 / D-06 | mechanical | Checkbox count reconciled against the file's own Traceability table and Coverage line (**research found 47/60 boxes ticked while the table still says "6 complete, 54 pending"**) | ⬜ pending |
| **SC4** — Ollama presented as fallback, not sole LLM path | INTG-04 | mechanical | `grep -ri "ollama" CLAUDE.md spec/` — every hit read, offending lines corrected, **final output pasted verbatim** into `40-EVIDENCE.json` | ⬜ pending |
| `spec/DATABASE.md` documents the Phase 39 `:ValidationRun` properties | INTG-04 / D-08 | content assertion | File contains `trigger`, `verdictSource`, `capturedAt`, `completedAt`, `attempts`, `lastError` **and** an `IntegrationConfig{provider:'AutoValidation'}` subsection | ⬜ pending |
| `docs/RELEASE-NOTES-v9.0.md` documents all 5 GH components | INTG-04 / D-12 | content assertion | File exists and contains each of the 5 component names + its verified GUID, ports, and ASCII wiring diagram, mirroring the v7.0/v8.0 layout | ⬜ pending |
| Phase 30 deferral note filed to the vault | INTG-04 / D-13 | file exists | A file in `DG_OBSIDIAN/knowledge/decisions/` states the orchestration question is unresolved and cross-links `40-DEFERRALS.md` + `.planning/research/` | ⬜ pending |
| DG Canvas Annotation Convention note exists | INTG-04 / discretion | file exists | A note under `DG_OBSIDIAN/knowledge/` documents the convention, cross-referencing `CanvasAnnotationParser.cs` as the single source of truth | ⬜ pending |
| `40-EVIDENCE.json` is well-formed and holes-honest | D-02 / D-04 | mechanical | Valid JSON; top-level `missing_measurements` array **present even if empty**; per-session `configuration` sub-objects; `findings[]` uses the `F-NN-NN` id shape | ⬜ pending |
| UAT closure is complete, not CLI-truncated | D-02 | mechanical | Per-file raw scan of every `NN-UAT.md`, **not** `query audit-uat` alone — the CLI drops `28-UAT.md` and `36-UAT.md` entirely (reproduced: reports 5 files/10 items) | ⬜ pending |
| graphify graph reflects final doc text | INTG-04 | mechanical | `graphify update .` run **after** all doc edits land; exits 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**None** — this phase adds no new source code requiring test scaffolding.

The only "test infrastructure" Phase 40 needs is:

- [ ] The `40-EVIDENCE.json` schema itself, following `39-EVIDENCE.json`'s exact top-level key
      structure (`phase`, `measured_at`, `source`, `configuration`, `software_context`,
      `measurements{}`, `findings[]`, `missing_measurements[]`).
- [ ] Explicit acknowledgement that `gsd-tools query audit-uat` **cannot** be trusted as the sole
      UAT-completeness check — plan a manual per-file line count instead.

---

## Manual-Only Verifications

These are the D-03 blocking human checkpoints. The 33-04 precedent governs: the architect runs the
checks personally and the executor **does not self-approve**.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E chain 1 (Session A): NL rule → cloud-LLM ingest → graph → GH validation → Speckle publish | INTG-01 | Requires a live browser session driving real n8n / gateway / Neo4j / Speckle traffic in real time. No harness stands in for "the architect watched it work". | Run Session A (S-A/1–5) from `.planning/milestones/v9.0-phases/v9.0-PIPELINE-UAT.md`. One project string for the whole run (e.g. `v9-final-uat`); **do not reuse `urbanblock-uat`** (holds 2026-07-26 evidence). Record each leg's outcome to `40-EVIDENCE.json` `session_a` and to the owning `NN-UAT.md`. |
| E2E chain 2 (Session B): object marked → entities tagged → LLM recognition → on-canvas preview → confirm → Computgraph publish → structure validation → generated inputs accepted → PARAMETER REINSTATE → validation run | INTG-03 | Requires live Rhino + Grasshopper interaction (marking, tagging, confirming previews) — a Rhino-in-the-loop procedure. | Run Session B (S-B/1–9) from the runbook. Carry these three traps into the checkpoint text: (1) `PreviewRegistry` is in-process — a Rhino restart orphans any preview left on canvas; (2) DG STRUCTURE CONFIRM's `Pending`/`Status` outputs do not refresh on undo; (3) rising-edge triggers — DG COMPUTGRAPH PUBLISH, DG ENTITY TAG and PARAMETER REINSTATE each need the toggle dropped to False before every fire. Scope live recognition with `procedure_index` — a cold whole-canvas run on UrbanBlock (221 untagged of 233) blows the adapter's 4096 `max_tokens`. Fixture substitution (UrbanBlock_V7, not Frame) is **expected and must be stated in the `result:` line**, as 35-UAT and 36-UAT did. |
| Provider-switch drill: Claude ↔ OpenAI-compatible ↔ Ollama through the settings panel only, mid-session, no container restart | INTG-02 | The live `n8n → gateway → provider API → Neo4j` path has never once run. Unit tests cover the mechanism; only the drill proves the wire. | **Opens with a blocking checkpoint (D-09)** asking the architect to configure an Anthropic or genuine-OpenAI key in the ui-v2 AI Engine panel — one key unblocks four items. Switch via `ui-v2/src/screens/AiEngineScreen.jsx` only (Base URL field at line 306 is required for the OpenAI-compatible leg). **Do not plan a panel port — it shipped in v8.1 Phase 811.** Per D-11, if the key never materialises: run the DeepSeek ↔ Ollama switch to prove the mechanism, record SC2 as **blocked-not-failed** with the reason in `40-EVIDENCE.json`, and let every other deliverable complete and commit. |

---

## Pre-Registered SC1 Criterion (D-04)

Fixed **before** the run, not judged after it:

> **"Chain completes" = every leg produces its expected artifact and no _unexpected_ error occurs.**

The following three observations are pre-registered as **expected observations, not chain failures**,
and must not be miscounted as SC1 blockers by whoever runs the checkpoint:

1. **F-39-01** — auto-validation's constant all-false `ValidStatus`. Structural, already understood,
   scoped to a follow-up milestone. Phase 40 observes it; it does not fix it.
2. **Phase 35 SC1's blocked frontier arms** — if the S-A/1 key checkpoint is not satisfied, that
   measurement stays blocked-not-failed per D-11. This is Phase 35's concern, not Phase 40's, and is
   not an INTG chain failure.
3. **A possible G7 `grammar_as_filter` block on live recognition** (S-B/3) — the runbook calls this
   "a result, not a broken harness". It means F3 reproduces, not that the chain is broken.

Per D-10, the S-A/3 frontier recognition sweep runs in the same sitting but is **credited to Phase 35**
(results to `35-UAT.md` / `35-EVAL-REPORT.md`). Phase 40 does not claim it as a success criterion and
does not gate on the 0.60 ship gate.

---

## Durable Artifact Discipline (D-02, D-04)

Because the two E2E chains cannot be captured by an automated test, this strategy substitutes a
**written, timestamped, holes-honest artifact** for a green CI checkmark:

- `40-EVIDENCE.json` records project string, provider/model per leg, per-step pass/fail, exact
  `curl`/Cypher output where applicable, and an explicit `missing_measurements[]`. Anything not
  measured is **named as a hole**, never silently omitted and never invented. This is Phase 39's
  discipline (39-03 wrote nothing rather than fabricating a datapoint) and Phase 35's
  (SC1 reported as *blocked on provider availability*, not computed from an incomplete arm set).
- Each `NN-UAT.md` item closed by the runbook gets its `result:` line updated in place, using the
  **single-line `expected:` form** — `query audit-uat` silently drops block-scalar (`expected: |`)
  items, so a block-scalar edit is invisible to future audits.
- The SC4 grep output is pasted **verbatim**, not paraphrased. "Ollama is presented correctly" is
  unverifiable after the fact; the raw grep lines are.

---

## Validation Sign-Off

- [ ] Every plan task carries either an automated verify or an explicit `checkpoint:human-verify`
      (gate=blocking) — no task claims a deliverable without a named proof
- [ ] The two E2E legs and the provider drill are the **only** manual-only items; everything else in
      the Per-Task Verification Map has a mechanical proof
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`40-EVIDENCE.json` schema; audit-uat untrustworthiness)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s for the mechanical + suite gates
- [ ] SC1's pass criterion and the three named non-failures are written into the checkpoint text
      **before** the live session starts (D-04)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

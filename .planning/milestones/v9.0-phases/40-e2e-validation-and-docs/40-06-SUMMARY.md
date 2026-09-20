---
phase: 40-e2e-validation-and-docs
plan: 06
subsystem: planning-evidence
status: complete
requirements: [INTG-01, INTG-02, INTG-03, INTG-04]
---

# Phase 40 Plan 06 — Mechanical Evidence and Closeout Audit

## Outcome

Created `40-EVIDENCE.json` as a holes-honest mechanical closeout artifact. It follows the Phase 39 evidence shape with the required top-level keys: `phase`, `measured_at`, `source`, `configuration`, `software_context`, `measurements`, `findings`, and `missing_measurements`.

No live E2E result is claimed. Session A, Session B, and the provider-switch drill remain explicitly `not_run` / `human_needed` or `blocked-not-failed`; no human E2E is marked pass. F-39-01 is carried forward as the pre-registered known limitation from Phase 39 and is not represented as fixed or re-measured.

## Mechanical checks actually run

- `grep -ri "ollama" CLAUDE.md spec/` — exit 0. The raw output is stored in `40-EVIDENCE.json`; remaining hits describe Ollama as optional, local, fallback, or deployment-specific.
- A Python raw scan of all discovered phase `NN-UAT.md` files — eight files, with non-empty `result:` counts: 28=1, 29=1, 33=4, 34=5, 35=7, 36=4, 37=1, 38=3. This inventories UAT records; it does not convert human UAT into a pass.
- Python content assertions — passed for `spec/DATABASE.md`, `docs/RELEASE-NOTES-v9.0.md`, `.planning/REQUIREMENTS.md`, and `40-DEFERRALS.md`.
- `git diff --check` — reported trailing whitespace in pre-existing generated DG `.obj/.editorconfig` files. Those unrelated files were not modified and the finding is recorded as F-40-06.

## Not run / still required

The Docker service smoke/probe, `.gha` provenance check, full `dotnet` suite, in-container pytest suite, and `graphify update .` were not run by this audit. They are listed in `measurements.mechanical_closeout.checks_not_run` and `missing_measurements`.

A human checkpoint is still required for:

- Session A: live browser/Docker/cloud-provider/Neo4j/GH/Speckle chain.
- Session B: live Rhino/Grasshopper recognition, preview, Computgraph, validation, PARAMETER REINSTATE, and validation-run chain.
- Provider switching: Claude ↔ OpenAI-compatible ↔ Ollama through the settings panel without restart.
- Authorized cloud credentials and live Rhino environment.

## Files created

- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-EVIDENCE.json`
- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-06-SUMMARY.md`

Application source, v12.0 artifacts, and unrelated worktree changes were not modified.

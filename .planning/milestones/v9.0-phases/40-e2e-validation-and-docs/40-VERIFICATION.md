---
phase: 40
generated: 2026-09-19
status: human_needed
requirements: [INTG-01, INTG-02, INTG-03, INTG-04]
verification_type: hybrid
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: human_needed
---

# Phase 40 Verification — E2E Validation and Docs

## Result

**Status: human_needed / partial.** Repository-local closeout work and the observed live checkpoints are recorded. v9.0 is not fully complete and must not be archived as fully passed.

## Completed autonomous scope

- Plans `40-01` through `40-04`, `40-05`, and `40-06` have summary artifacts.
- `.planning/REQUIREMENTS.md` contains 47 complete, 9 deferred, and 4 pending requirements; traceability and coverage agree.
- `.planning/ROADMAP.md` progress statuses were reconciled against verification frontmatter and raw UAT counts.
- `40-DEFERRALS.md` records Phase 30/31 deferrals to v10.0.
- Provider-gateway documentation and SC4 Ollama framing evidence were recorded.
- Phase 39 auto-validation Run/IntegrationConfig documentation and F-39-01 caveat were recorded.
- v9.0 component release notes were created from source-verified GUID and port data.
- `40-EVIDENCE.json` is valid JSON and contains explicit live findings and missing measurements.

## Live evidence recorded

### Session A — partial/pass by sub-leg

- OpenAI-compatible rules ingest: **pass** — project `v9-final-uat`, rule `R_URB_HEIGHT_MAX_75_V`, 4 atoms.
- Context-aware graph query: **pass** — `/context/assemble`, `/context/generate-cypher`, `/mcp`, and `/llm/generate` completed; `v9-final-uat` honestly returned no ValidationRun rows.
- Ollama connection: **pass** — `llama3.1:8b`.
- Ollama ingest: **pass on retry** — rule `R_CORRIDOR_LENGTH_MAX_14_V`, 4 atoms, without Docker restart or workflow edit.
- Read-only validation/model view: **pass** on `v8-ui-smoke`, existing run `a547014ebd824a269c36fd681eb4b1ec`; validation result and Speckle view loaded.
- No new Speckle publish side effect was performed.
- Earlier Ollama prose-before-Cypher failure remains recorded as historical finding `F-40-07`; the retry passed and provider acceptance is not blocked by that first attempt.

### Session B — partial, accepted recognition blocker

- DG CANVAS LISTENER: **pass** — listening on `127.0.0.1:8720`.
- Live `/computgraph/context/pull`: **pass** — HTTP 200, `cg-context-1`, UrbanBlock V8 fixture, tagged object/procedures/patterns/parameters returned.
- MCP `tools/list`: **pass** — all four `gh_*` tools present.
- DG OBJECT MARKER: **pass** — `OBJECT - BRIDGE` and `1_ALGORITHM`, duplicate-free recompute.
- DG ENTITY TAG and parser round-trip: **pass** — `11_Var_SpansCount`, pink, one member, `Variable`, `source: tagged`, procedure 11; Ctrl+Z clean.
- Recognition: **accepted blocker** — both Ollama/`llama3.1:8b` and OpenAI/`mimo-v2.5-pro` returned HTTP 200 with `valid:false`, `output_truncated`, 512-token cap, one residual candidate.
- Per decision `D-40-SB-01`, the fixture was not reduced or altered to force a recognition pass. Preview, confirm/reject, Computgraph publish, structure validation, and PARAMETER REINSTATE were not executed.

## Open gates

1. Protected `CLAUDE.md` patch remains unapplied; `40-05-SUMMARY.md` records the approval timeout.
2. Session B recognition blocker prevents honest completion of the downstream canvas chain.
3. New Speckle publish was intentionally not performed; existing read-only validation evidence is not equivalent to a new publish leg.
4. The broader GSD audit still reports pre-existing UAT/verification gaps, open debug sessions, and one deferred test item outside this closeout.
5. `dotnet` and Docker/in-container test results are environment-dependent and must be interpreted from their actual evidence; no green claim is inferred from code presence.

## Evidence references

- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-EVIDENCE.json`
- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-05-SUMMARY.md`
- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-06-SUMMARY.md`
- `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-DEFERRALS.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`

## Routing

v9.0 remains at Phase 40 with human-needed/partial verification. Do not execute v12.0. The next legitimate action is either to resolve the recognition contract blocker in a separately planned fix or to accept it explicitly as v9.0 carried debt before any milestone archive operation.

# Plan 1201-01 Summary — Tracer Slice: StatusRollup, SupportedBuiltins, Evaluator Status

**Status:** Complete
**Executed:** 2026-09-20
**Commits:** `e328154`, `d456f83`

> **Provenance note.** The executing subagent was terminated mid-run by a session
> rate limit (HTTP 429) before it wrote this summary. This file was reconstructed by
> the orchestrator from the committed diffs and **re-verified from scratch** — every
> number below is from a command run after the interruption, not carried over from the
> agent's own claims.

## What shipped

### Task 1 — `StatusRollup` extraction (commit `e328154`)

- New `DG/src/DG.Core/Contracts/StatusRollup.cs` holding the single canonical roll-up
  precedence, extracted out of `EvidenceEnvelopeFactory`.
- `EvidenceEnvelopeFactory` now **delegates** rather than keeping its own copy.
- New `SupportedBuiltins` allow-list (D-15), read by both the evaluator and its
  conformance test so the documented subset and the code cannot drift.

### Task 2 — Canonical status emission (commit `d456f83`)

- `RuleEvaluationResult` gains an additive `Status` of `DG.Core.Contracts.EvidenceStatus`
  (D-05). The existing `Passed` boolean is **retained** and documented non-authoritative,
  per 1200's D-03/D-04.
- Unsupported builtins **return `unsupported`** instead of throwing (D-07). This also
  closes the compounding defect: the throw at `RuleEvaluator.cs:130` was previously
  swallowed by the catch-all at `:52-56` and counted as a *failing binding*, so an
  unsupported construct was being reported as a rule violation — exactly what the
  ROADMAP gate forbids.

## Verification (re-run post-interruption, actual output)

| Check | Command | Result |
|---|---|---|
| Release build, both TFMs | `dotnet build DG/DG.sln -c Release` | **0 warnings, 0 errors** (net7.0 + net9.0 both emitted) |
| Test suite | `dotnet test DG/tests/DG.Tests/ -c Release --no-build` | **451 passed, 3 failed, 454 total** |
| Exactly one precedence table | `grep -rn "EvidenceStatus.Indeterminate," DG/src/DG.Core/ --include=*.cs \| wc -l` | **1** ✓ |
| `StatusRollup` exists | `ls DG/src/DG.Core/Contracts/StatusRollup.cs` | present ✓ |
| Frozen fixture untouched | `git diff --stat fixtures/golden/fixture.json` | **empty** ✓ |

**On the 3 failures:** all in `DG.Tests.E2E.DesignStateValidationFlowTests`, which require
Neo4j on the compose network and fail from the host by design (the `neo4j` hostname resolves
only inside compose). Environment-dependent, **not regressions**, and explicitly out of scope
per the plan's own done-conditions.

**Test count moved 412 → 454**, so this plan added ~42 passing tests.

## Guards held

All four phase guards were verified intact *after* the interruption:

- exactly one rollup precedence table in the codebase;
- `fixtures/golden/fixture.json` zero-diff;
- `_DECLARABLE_STATUSES` not widened;
- net7.0/net9.0 both build clean (no .NET 8+ API crept in).

## Deviations

**One, procedural rather than technical:** the plan intended two atomic commits authored by
the executing agent. The agent was killed after committing task 1, so task 2's changes sat
uncommitted until the orchestrator verified and committed them. No code was written by the
orchestrator — only verification and the commit.

No technical deviations. No pre-existing test had to be rewritten for this plan.

## For the next plan (1201-02)

- `StatusRollup.Precedence` is the **only** precedence table. Route through
  `StatusRollup.Rollup`; do not derive a second one.
- `RuleEvaluationResult.Status` now exists and is populated for the unsupported-builtin
  path. Plan 02 owns the remaining collapse sites: zero bindings → `no_population` (D-06),
  missing binding → `unknown` (D-08), `ObjectPropertyAtom` refusal (D-14), and
  `ValidationPublishPackageBuilder.cs:34-42` → `not_evaluated`.
- The catch-all at `RuleEvaluator.cs:52-56` still exists and is still reachable for genuine
  faults. Plan 02 finishes narrowing it so only real `error` conditions route through it.

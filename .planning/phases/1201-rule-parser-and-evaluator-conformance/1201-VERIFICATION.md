---
status: passed
phase: 1201
verified: 2026-09-21
verifier: orchestrator (live stack, measured)
requirements: [ALGN12-05, ALGN12-06, ALGN12-07]
behavior_unverified: 0
---

# Phase 1201 Verification — Rule Parser and Evaluator Conformance

**Verdict: PASSED.** All three requirements satisfied; the D-11 exit gate is met with live,
measured evidence.

## Goal-backward check

> **Goal:** Make the implemented C# rule subset explicit and safe — every construct the evaluator
> cannot handle produces a typed non-verdict outcome, never a thrown exception and never an
> ordinary `failed`.
>
> **ROADMAP gate:** supported fixtures pass; unsupported fixtures return typed non-verdict
> outcomes; no unsupported construct becomes an ordinary failure.

### Every collapse site closed — verified on disk

| Site (pre-phase behavior) | Now | Evidence |
|---|---|---|
| `RuleEvaluator.cs:24-34` zero bindings → `Passed=false` | `no_population` | D-06 |
| `:52-56` catch-all turning **every** exception into a failing binding | only genuine faults reach it | the fulcrum; four outcomes no longer route through it |
| `:100` / `:148` missing binding **throws** | `unknown` | D-08 |
| `:114` builtin arity < 2 **throws** | `unsupported` | D-07 |
| `:130` / `:138` unsupported builtin **throws** | `unsupported` | D-07, ALGN12-06 |
| `ValidationPublishPackageBuilder.cs:34-42` no result → `Passed=false` | `not_evaluated` | D-05 table |
| `EvaluateAtom:104-105` bare `return true` for ObjectPropertyAtom | typed `unsupported` refusal | D-14 |

**Mechanical proof:**
`grep -cE 'throw new (NotSupportedException|InvalidOperationException)' RuleEvaluator.cs` → **0**.
The evaluator no longer has an exception path for an ordinary outcome.

### The parser no longer guesses

`ResolveAtomType` previously returned `"DataPropertyAtom"` for every ≥2-arg non-`swrlb:`
predicate, making `ObjectPropertyAtom` unreachable by construction. Now exactly **one**
`DataPropertyAtom` production site (`SwrlRuleParser.cs:280`), gated on
`PredicateKind.DatatypeProperty`, with an explicit in-code statement that no fallback exists.
Unresolvable predicate → `UnsupportedAtom`.

## Requirements

| Req | Verdict | Evidence |
|---|---|---|
| **ALGN12-05** — ObjectPropertyAtom and malformed/unsupported syntax have explicit parser outcomes and regression fixtures | **PASS** | `TryParse` never throws; `ParseDiagnostic`; 9-case corpus at `fixtures/golden/parser/cases.json` covering all eight ROADMAP cases plus the null-resolver counterpart |
| **ALGN12-06** — unsupported built-ins and predicate forms never collapse into ordinary failed verdicts | **PASS** | Zero throws in the evaluator; and the Python-side gap that kept this open (data-service/replay reporting `unknown` for an empty population) closed in `1201-07` — `OBJ_GOLD_EMPTY` now reads `no_population` on data-service, csharp and replay alike |
| **ALGN12-07** — docs and tests distinguish the schema-level SWRL subset from the bounded C# evaluator; no full-reasoner claim | **PASS** | `spec/SWRL-SUBSET.md` with a non-claims section mapping each unsupported construct to its status; drift guard **observed failing** on an induced mismatch, then reverted |

## D-11 exit gate — MET

```
DE-01: silent_disagreement_count = 0
DE-01: available legs = ['data-service', 'dg-reasoner', 'csharp', 'replay']

OBJ_GOLD_EMPTY -> declared_non_equivalence
OBJ_GOLD_FAIL  -> declared_non_equivalence
OBJ_GOLD_PASS  -> declared_non_equivalence
```

All four legs available for the first time in the project's history (dg-reasoner had **no**
host-exposed port and was silently absent from every prior run). Zero silent disagreements;
every remaining difference carries a written reason.

Evidence committed: `evidence/1201-07-de01-report-PASS.json` / `.md`, alongside the earlier
failing run (`evidence/1201-06-de01-report.*`) kept for comparison.

## Guards — all held, verified after every wave

| Guard | Check | Result |
|---|---|---|
| One rollup precedence table | `grep -rn "EvidenceStatus.Indeterminate," DG/src/DG.Core/ \| wc -l` | **1** |
| Frozen fixture untouched | `git diff --stat fixtures/golden/fixture.json` | **empty** |
| `_DECLARABLE_STATUSES` not widened | `git diff` on the constant | **unmodified** |
| `ontology/dg-shapes.ttl` not rewritten | `git diff` | only an unrelated pre-existing comment |
| net7.0 + net9.0 both build | `dotnet build -c Release` | **0 warnings, 0 errors** |

The gate was **not** made green by weakening anything. Both available shortcuts — widening
`_DECLARABLE_STATUSES` to admit `passed`, or relaxing the CR-02 guard — were explicitly rejected;
CR-02's three regressions and the over-correction guard all still pass.

## Test state

| Suite | Result |
|---|---|
| DG .NET | **502 passed, 0 failed** (412 at phase start) |
| DE-01 runner | **33 passed, 0 failed** |
| data-service | **823 passed**, 1 skipped, 1 failed (pre-existing) |
| dg-reasoner | 36 passed, 3 failed (pre-existing) |

### The 4 non-passing tests are pre-existing, not regressions

1. **`test_never_raises_on_garbage_input`** — `RecursionError` on deeply-nested JSON in
   `parse_evidence_envelope`. That function has **zero** occurrences in this phase's
   `data-service/app.py` diff; a rebuild surfaced it.
2. **3 × `test_shacl_report.py`** — `FileNotFoundError: '/ontology/dg-shapes.ttl'`. The test
   derives its path from `Path(__file__).resolve().parents[2]`, correct from the repo root but
   resolving to `/ontology/` rather than `/app/ontology/` inside the container (the file is
   present at `/app/ontology/dg-shapes.ttl`). Still fails from the correct cwd, so not a cwd
   artifact. In files this phase never modified.

Both are real and worth fixing; neither is in ALIGN-P03's scope and neither is a regression.

## Deviations from plan, all recorded

1. **Waves 1 agents were killed mid-run by a session rate limit.** Work was verified from
   scratch by the orchestrator and committed; summaries reconstructed from measured output
   rather than agent claims.
2. **`docker-compose.yml` gained `ports: ["8001:8000"]` for dg-reasoner** — not in any plan.
   Without it the DE-01 runner (host process) can never reach that leg, and an unreachable leg
   is indistinguishable from a passing one at the gate. Escalated to and approved by the user.
3. **Two gap-closure fixes beyond the six plans** (`1201-07`), at user direction: the publish
   path's inability to carry a known canonical status, and the classifier's treatment of a
   legitimate abstention. Both are documented in the 1201-06 amendment.
4. **Pre-existing unrelated work found in the tree** (a rule-ingest conflict-check feature) was
   committed separately (`e4b9a4e`, `ea64515`) so it could not be swept into this phase.

## Carried forward — documented, non-blocking

1. **D-12 partial** — hashes surface on the csharp leg only; `null` on data-service, dg-reasoner
   and replay at the live boundary.
2. **`ParseDiagnostic.Offset` always `-1`** — no fixture asserts real offsets, so nothing claims
   precision that does not exist.
3. **`Neo4jPredicateKindResolver` has no production call site** — D-02's resolved branch is
   exercised only by tests. Low impact: `Neo4jRuleRepository.GetRulesAsync` materializes atoms
   from graph edges, bypassing the re-parse path.
4. The two pre-existing test failures above.

None is a silent failure; each is stated rather than absorbed.

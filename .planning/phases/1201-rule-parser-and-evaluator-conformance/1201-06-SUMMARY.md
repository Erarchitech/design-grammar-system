# Plan 1201-06 Summary — D-11 Live DE-01 Exit Gate

**Status:** Executed — **gate NOT met.** Recorded honestly rather than forced green.
**Executed:** 2026-09-20 (orchestrator, live stack)
**Plan:** `autonomous: false` (live-environment gate)

## Environment preparation (all plan preconditions satisfied)

| Precondition | Action | Result |
|---|---|---|
| Compose stack up | already running | 15 services up ✓ |
| Stale-image trap closed | `docker compose build --no-cache data-service` + recreate | rebuilt from source ✓ |
| dg-reasoner reachable from host | `ports: ["8001:8000"]` added in wave 1 | `GET :8001/health` → **200** ✓ |
| data-service reachable | — | `:8000/docs` → **200** ✓ (note: this service has **no** `/health` route; a 404 there is correct, not a fault) |
| Golden fixture seeded | verified in Neo4j | `Object`×3, `Run` (`RUN_GOLD_1200`), `Rule`, `Atom`×4 present ✓ |

## Gate result — measured, not claimed

```
python tools/de01/run_de01.py --out-dir .de01out

DE-01: silent_disagreement_count = 3
DE-01: available legs = ['data-service', 'dg-reasoner', 'csharp', 'replay']
```

**All four legs available** (the wave-1 achievement — dg-reasoner was previously unreachable
and silently absent from every prior run).

**D-11 requires `silent_disagreement_count = 0`, or every remaining disagreement explicitly
declared. Neither condition is met. The gate FAILS.**

### Per-object measurement

| Object | data-service | dg-reasoner | csharp | replay |
|---|---|---|---|---|
| `OBJ_GOLD_EMPTY` | `unknown` | `not_evaluated` | **`no_population`** | `unknown` |
| `OBJ_GOLD_FAIL` | `failed` | `not_evaluated` | `failed` + `unsupported` | `failed` |
| `OBJ_GOLD_PASS` | `passed` | `not_evaluated` | `passed` | `passed` |

Hashes: present on **csharp only**; `null` on data-service, dg-reasoner and replay (D-12
partially satisfied — see below).

## Why the count did not move, and why that is the right reading

The count is unchanged from wave 1 (3), but **the underlying situation changed substantially
and the remaining causes are different from the original ones.**

1. **The original D-09 defect is fixed and proven fixed.** Before: dg-reasoner never saw the
   golden objects at all (`conforms=true`, zero findings, false `no_population` on every row).
   Now, measured live: `POST /shacl/validate {project, run_id}` → `conforms: False`, **8 real
   violations**. The leg genuinely evaluates.

2. **Waves 2–4 were C#-only by scope** (`DG.Core` parser/evaluator/spec/fixtures). On every row
   above, **the csharp leg is already correct**: `no_population` for the empty population,
   `failed` for the violation, `passed` for the conforming object. Those waves could not have
   moved this count, because the leg they fixed was not the one disagreeing.

3. **The remaining disagreements are in the Python legs, which no plan in this phase scoped:**
   - **`OBJ_GOLD_EMPTY` is a genuine defect.** Under 1200's D-05 table an empty population is
     `no_population`. data-service and replay report `unknown`. `data-service/evidence_contract.py:64`
     defines `NO_POPULATION` and the roll-up handles it — the vocabulary exists; these two legs
     simply do not use it for this case. **This is exactly the D-06 defect class, in Python.**
   - **`OBJ_GOLD_FAIL`** — csharp emits two rows (`failed` + `unsupported`). The roll-up is
     correct (`failed` > `unsupported`), but DE-01 compares row-wise, so the extra row
     participates in the difference.
   - **`OBJ_GOLD_PASS`** — only dg-reasoner's *properly declared* `not_evaluated` differs.

4. **Why these classify `silent` despite dg-reasoner declaring its reason:** the CR-02 guard
   (`tools/de01/report.py:184-185`, hard-won in plan 1200-07) makes a row silent if **any**
   non-declarable status participates. `unknown`, `failed`, `passed` and `no_population` are all
   non-declarable, so a correctly-declared `not_evaluated` cannot rescue a row containing one.
   **That guard is correct.** Relaxing it to turn this gate green was explicitly forbidden and
   was not done.

## What was NOT done, deliberately

- **`_DECLARABLE_STATUSES` was not widened.** Verified unmodified.
- **The CR-02 classifier was not relaxed.**
- **`fixtures/golden/fixture.json` was not edited** to make legs agree. Verified zero-diff.
- **No leg's status was adjusted to manufacture agreement.** The measured statuses are reported
  exactly as produced.

Any of these would have produced a green gate and a worthless one. *Silent disagreement is a
failure; a declared one is not* — and a gate gamed into passing is the worst of both.

## Requirement status

| Req | State | Evidence |
|---|---|---|
| **ALGN12-05** | Satisfied | ObjectPropertyAtom reachable; guessing fallback removed (one resolver-gated `DataPropertyAtom` site, `SwrlRuleParser.cs:280`); 9-case corpus in `fixtures/golden/parser/` |
| **ALGN12-06** | Satisfied in C#; **open in Python** | `RuleEvaluator` has **zero** throws; every collapse site emits a typed status. data-service/replay still collapse an empty population to `unknown` |
| **ALGN12-07** | Satisfied | `spec/SWRL-SUBSET.md` with non-claims section; drift guard **proven to fail** on induced mismatch, then reverted |

## Carried forward — must not be silently dropped

1. **Python-leg empty-population defect** (data-service + replay emit `unknown` where D-05
   requires `no_population`). This is the single highest-value follow-up: it is the same defect
   class this phase fixed in C#, and closing it should reduce the disagreement count directly.
2. **D-12 only partially satisfied** — hashes surface on the csharp leg only; `null` on the other
   three at the live boundary.
3. **Row-wise vs rolled-up comparison** for multi-row legs (`OBJ_GOLD_FAIL`).
4. **`ParseDiagnostic.Offset` is always `-1`** (flagged by plan 03; fixtures do not assert real
   offsets, so nothing claims precision that does not exist).
5. **`Neo4jPredicateKindResolver` has no production call site yet** — `RuleEvaluator`'s re-parse
   fallback still uses the null-object resolver. Low impact (`Neo4jRuleRepository.GetRulesAsync`
   materializes atoms from graph edges, bypassing re-parse), but it means D-02's resolved branch
   is exercised only by tests.

## Recommendation

Do **not** mark Phase 1201 verified. Its three requirements are substantively delivered on the
C# surface the phase was scoped around, and the D-09 root cause is genuinely fixed — but D-11's
exit gate is a real, measured failure with a clearly identified cause that lies outside the
plans' scope. The honest disposition is `gaps_found`, with item 1 above as the first follow-up
plan.

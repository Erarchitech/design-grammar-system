# Plan 1201-05 Summary — dg-reasoner Leg, Declared Non-Equivalence, Hash Surfacing

**Status:** Complete (with one finding routed forward — see below)
**Executed:** 2026-09-20
**Commit:** `48774ba`

> **Provenance note.** The executing subagent was terminated mid-run by a session
> rate limit (HTTP 429) before writing this summary or committing. This file was
> reconstructed by the orchestrator from the working-tree diff and **verified by live
> execution against the running stack** — the numbers below are measured, not claimed.

## What shipped

### D-09 — the dg-reasoner leg now actually evaluates the fixture

`tools/de01/legs.py` posted `/shacl/validate` with `{"project": project}` and **no
`run_id`**. Per `run_shacl`'s own docstring (`dg-reasoner/reasoning.py:473-479`),
omitting `run_id` validates the project-level Metagraph/OntoGraph export only; the run's
ValidGraph ABox (`build_valid_graph`) is unioned in **only** when `run_id` is supplied.

The seeded golden objects (`OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`) live in that ABox. So
`dgc:ObjectShape` targeted a class **absent from the graph pySHACL actually validated** —
zero focus nodes → `conforms=true` → every row misreported as `no_population`.

Fixed by sending `run_id`, sourced from `FIXTURE_RUN_ID` (`RUN_GOLD_1200`) since the frozen
`fixture.json` carries no run-id field. A fixture with no resolvable run id degrades to a
typed `error` rather than silently reverting to the defective project-only call shape.

**Measured proof (live, inside the compose network):**

```
POST /shacl/validate {"project":"DG-1200-GOLDEN","run_id":"RUN_GOLD_1200"}
  -> conforms: False   violations: 8
```

Previously: `conforms: true`, zero findings. The leg is genuinely evaluating now.

### D-10 — declared non-equivalence instead of a verdict it cannot justify

Where SHACL has no opinion on a quantitative rule, the leg now reports **`not_evaluated`**
carrying a full What/Where/How-to-fix warning, rather than `passed`. `spec/RULE-PARTITION-POLICY.md`
assigns quantitative rules to the SWRL VALIDATOR; encoding this fixture's `height > 75` as a
SHACL shape to force cross-leg agreement would evaluate one business rule in two systems.

`_DECLARABLE_STATUSES` was **not** widened to admit `passed` — verified zero-diff on that
constant. Widening it would have permanently weakened the gate for every future run.

### D-12 — hashes at the service boundary

`report.py` gained the envelope-level fallback. **Partially effective:** the csharp leg now
carries real hashes (e.g. `D9F81B55B08C667AFA61766F21A4C5BC29E132B789391231E8C7AB7925FDC986`);
data-service, dg-reasoner and replay still report `null`. See the finding below.

### Topology — dg-reasoner exposed on the host

`docker-compose.yml` gained `ports: ["8001:8000"]` for `dg-reasoner`. It had **no port
block at all**, so the DE-01 runner — which executes on the host — could never reach that
leg; it reported `available: false` on every run. An unreachable leg is indistinguishable
from a passing one at the gate, which is the precise failure mode DE-01 exists to catch.

**Decision authority:** the compose change was approved by the user in-session, after the
orchestrator surfaced it as a design question the plan had not anticipated.

## Verification (measured)

| Check | Result |
|---|---|
| DE-01 unit suite (`pytest tools/de01/tests/test_de01_runner.py`) | **28 passed, 1 failed** — the failure is the live four-leg gate assertion itself |
| dg-reasoner reachable from host | `curl localhost:8001/health` → **200** ✓ (was: connection refused) |
| All four legs available | `['data-service', 'dg-reasoner', 'csharp', 'replay']` ✓ (was: dg-reasoner missing) |
| `ontology/dg-shapes.ttl` zero-diff | ✓ (only an unrelated pre-existing comment, not authored here) |
| `_DECLARABLE_STATUSES` unmodified | ✓ |
| `fixtures/golden/fixture.json` zero-diff | ✓ |

## Finding routed forward — D-11 does NOT yet pass

`silent_disagreement_count = 3`, unchanged in number from Phase 1200 — **but the cause is
completely different and the old cause is fixed.** Before: one leg was blind. Now: four legs
genuinely evaluated and three of them disagree.

Measured per-object:

| Object | data-service | dg-reasoner | csharp | replay |
|---|---|---|---|---|
| `OBJ_GOLD_EMPTY` | `unknown` | `not_evaluated` | `no_population` | `unknown` |
| `OBJ_GOLD_FAIL` | `failed` | `not_evaluated` | `failed` + `unsupported` | `failed` |
| `OBJ_GOLD_PASS` | `passed` | `not_evaluated` | `passed` | `passed` |

Why each is still classified `silent` rather than `declared`: per the CR-02 guard at
`tools/de01/report.py:184-185` (hard-won in plan 1200-07), **any** non-declarable status
participating in a difference makes the whole row silent. `failed`, `passed`, `unknown` and
`no_population` are all non-declarable, so `dg-reasoner`'s properly-declared `not_evaluated`
cannot rescue a row that also contains one of them. **That guard is correct and must not be
relaxed to make this gate go green.**

Three genuine questions fall out, and none should be answered by loosening the classifier:

1. **`OBJ_GOLD_EMPTY`** — three different readings of the same empty population:
   `unknown` / `no_population` / `unknown`. Under 1200's D-05 table, an empty population is
   `no_population`; the csharp leg is right and the other two are wrong. **This is a real
   defect in the data-service and replay legs**, and it is squarely plan 1201-02's territory
   (D-06 zero-bindings → `no_population`).
2. **`OBJ_GOLD_FAIL`** — csharp emits **two rows**, `failed` and `unsupported`. Correct per
   rollup (`failed` > `unsupported`), but the comparison is row-wise, so the extra row drags
   the classification. Worth confirming the roll-up is applied before comparison.
3. **`OBJ_GOLD_PASS`** — only dg-reasoner's declared `not_evaluated` differs; every other leg
   agrees on `passed`. This is the cleanest candidate for a legitimate declared
   non-equivalence once the non-declarable statuses on the other two rows are resolved.

**Recommendation:** do not attempt to close D-11 here. Items 1 and 2 are plan 1201-02's work
(the remaining collapse sites). Re-run the gate in plan 1201-06 once 02/03/04 have landed —
the count should fall on its own as each leg stops mis-stating an empty population.

## Deviations

1. **Commit authored by the orchestrator, not the agent** (rate-limit kill). Code is the
   agent's; verification and the commit are the orchestrator's.
2. **The compose topology change was not in the plan.** It was necessary to make the gate
   physically runnable, and was escalated to the user rather than made unilaterally.
3. **D-12 is only partially satisfied.** Hashes surface on the csharp leg but remain `null`
   on data-service, dg-reasoner and replay. Not silently closed — carried forward.

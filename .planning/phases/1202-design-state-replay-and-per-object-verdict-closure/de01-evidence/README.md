# DE-01 Retained Exit Evidence — de01-report.json / de01-report.md

## This run (superseding, Phase 1202 plan 08 Task 4)

- **Date:** 2026-09-22
- **Command:** `python tools/de01/run_de01.py --replay-fixture`
- **Fixture:** `fixtures/golden/replay/mixed-verdicts.json` (the sibling live-replay fixture, selected via the `--replay-fixture` shorthand added by this plan's Task 1; the frozen `fixtures/golden/fixture.json` and its own `--fixture` default are untouched)
- **Agreement verdict:** `agree`
- **silent_disagreement_count:** 0
- **Exit code:** 0

### Per-leg canonical state hash

| Leg | Present | Hash | Matches fixture's `expectedCanonicalStateHash` |
|---|---|---|---|
| csharp | True | `69D4289C722DE31B42D57E5F3C41BAB39272BE7DAC8957870512EC86C0707A84` | False (see disposition below) |
| replay | True | `69D4289C722DE31B42D57E5F3C41BAB39272BE7DAC8957870512EC86C0707A84` | False (see disposition below) |
| data-service | False | — | not applicable (this leg captures no Design State by design) |
| dg-reasoner | False | — | not applicable (this leg captures no Design State by design) |

The `csharp` and `replay` legs independently compute the **same** 64-char hex hash from the same `statePayloadJson` — a genuine cross-language agreement, not a coincidence: `csharp` runs `DG.De01Harness` → `DesignStatePayloadV2Serializer.Deserialize` → `DesignStateCanonicalProjection.ComputeHash` (C#), and `replay` reads it back through `data-service`'s persisted `/validation/view/DG-1202-REPLAY` route → `design_state_projection.compute_state_hash` (Python). This is the live demonstration VERIFICATION.md gap 1 required: a real, round-trippable Design State producing a non-`not_applicable` canonical-hash verdict, reproduced independently by two languages.

### What this run supersedes

The evidence this file replaces reported `Agreement: not_applicable` with all four legs at `Present: False` — the retained artifact plan 1202-07's SUMMARY documented as blocked because the then-only live input (`fixtures/golden/fixture.json`) carries a stub Design State (bare `stateId` members, no `capturedAtUtc`/`objectRef`) that cannot round-trip through `DesignStatePayloadV2Serializer.Deserialize`. This run instead exercises `fixtures/golden/replay/mixed-verdicts.json`, whose `statePayloadJson` carries full members and does round-trip (confirmed live: `d.statePayloadJson CONTAINS 'capturedAtUtc' AS roundTrippable` returned `TRUE` against the seeded Neo4j node).

## Disposition of `expectedCanonicalStateHash` vs `False` `Matches expected`

`fixtures/golden/replay/mixed-verdicts.json`'s `expectedCanonicalStateHash` (`3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428`) is **unchanged by this run** and both legs correctly report `expected_match: False` against it — this is not a defect. The fixture's stored value was originally computed (plan 02) via a `parse_float=Decimal` JSON parse that preserves a numeric literal's exact decimal scale (e.g. keeps `42.0` at scale 1). Neither the C# leg's Design State model (`NumberValue` is `double`) nor Python's own `design_state_projection.py` (which converts a bare-parsed `float` to `Decimal` via `.normalize()`, deliberately mirroring C#'s `Convert.ToDecimal` scale-0 collapse) can reach that scale-preserving value through their real, production code paths — both independently collapse to scale-0 instead, landing on `69D4289C...`. The fixture's `expectedCanonicalStateHashNote` was rewritten during this plan to record this measured finding (superseding its original, now-confirmed-stale claim that a missing `ClassIri` member was the cause — `ClassIri` round-trips correctly, verified live). The two live legs agreeing with **each other** (not with a value neither could ever reach) is the correct DE-01 outcome.

## Live-run investigation trail (data-service fixes made during this checkpoint)

Two `data-service/app.py` issues were found and fixed live while chasing this run to a non-`not_applicable` verdict, both required for the verdict above to be reachable at all:

1. **Real bug, kept:** `get_validation_run`'s Cypher `RETURN` clause omitted `run.statePayloadJson`, so `build_view_payload`'s `_compute_canonical_state_hash(run.get("statePayloadJson"))` always received `None` regardless of what was actually stored on the `:ValidationRun` node — the view endpoint could never report a real hash for ANY project, including the historical golden-project attempts. Fixed by adding the missing field to the `RETURN` clause.
2. **Tried, then reverted (documented, not silently discarded):** parsing `statePayloadJson` with `parse_float=Decimal` in `_compute_canonical_state_hash` was tried to make the `replay` leg match the fixture's stored `expectedCanonicalStateHash`. This was reverted because it broke agreement with the `csharp` leg instead — `parse_float=Decimal` preserves decimal scale in a way neither leg's actual `double`-typed Design State model can reproduce, so "matching the stored fixture value" and "genuine cross-language agreement" are mutually exclusive for this payload, and cross-language agreement is DE-01's actual purpose. The full investigation and reasoning is recorded in `_compute_canonical_state_hash`'s own docstring in `data-service/app.py`.

`run_leg_data_service` (`tools/de01/legs.py`) was also changed to pass `fixture.get("statePayloadJson")` through to `/validation/publish` instead of a hardcoded `None`, because that leg's own publish call always runs before the `replay` leg's bare `GET /validation/view/{project}` (which resolves to the newest run by `createdAt`) within one `run_de01.py` invocation — without this, `run_leg_data_service`'s own fresh, hash-less publish would always shadow any previously-seeded run, permanently reproducing gap 1 even against a correctly seeded project. This leg's own reported canonical statuses (`passed`/`failed`/`no_population`) are unaffected; only the sidecar `statePayloadJson` it forwards changed. The frozen `fixtures/golden/fixture.json` carries no top-level `statePayloadJson` key, so this change is a no-op for that fixture — `fixture.get("statePayloadJson")` returns `None`, byte-identical to before.

`fixtures/golden/replay/seed-replay.cypher` (Task 1's seed script) seeds a raw `:Run`/`Run_Id` node, mirroring `fixtures/golden/seed.cypher`'s own precedent — this convention is **not** read by `/validation/view/*` (which queries `:ValidationRun`/`runId` only, the documented label-drift gotcha). The seed script is retained as-is (it is useful for direct Cypher inspection and for `dg-reasoner`'s `run_id`-addressed SHACL call, which does read the seeded ValidGraph ABox), but the live hash-bearing path that actually closes gap 1 is the `/validation/publish` → `:ValidationRun.statePayloadJson` → `/validation/view/{project}` route exercised by `run_leg_data_service`/`run_leg_replay`, not the raw Cypher seed.

# fixtures/golden/replay/ — Mixed Pass/Fail Per-Object Replay Fixture

**Added:** Phase 1202 plan 01 Task 3 (D-17), requirements ALGN12-09/ALGN12-10.

## What this is

`mixed-verdicts.json` is a single sibling fixture built to exercise the D-17 mixed pass/fail
per-object replay case: a Design State whose three ObjStates resolve to three **different**
per-object verdicts (`passed`, `failed`, `no_population`) that must stay distinct through
`publish → query → replay`, rather than collapsing into one run-level aggregate.

It is read by two future consumers named in `1202-CONTEXT.md`'s `key_links`:

- **Plan 04's `Neo4jValidGraphRepository` per-object verdict tests** — the `statePayloadJson`
  is a serializer-valid v2 payload the repository's `BuildPerObjectVerdicts` path can be fed
  directly, and the `evidenceEnvelopeJson` key carries the exact rows that method parses.
- **Plan 06's DE-01 replay leg (D-16)** — the same artifact is the one input both the C# and
  Python legs read, so this is not a per-service copy (per `spec/EVIDENCE-CONTRACT.md` § 7's
  "per-service copies are forbidden" rule, mirrored here for fixture material generally).

## Relationship to `fixtures/golden/fixture.json` — this is a SIBLING, not an edit

This fixture is **additive and separate from** the frozen `fixtures/golden/fixture.json`
(1200 D-11, `MANIFEST.md`'s freeze policy). **`fixture.json`, `seed.cypher`, and
`canonical-vectors.json` were not touched by this task** — verified by
`git status --porcelain` showing no changes to any of the three. This mirrors the exact
precedent `fixtures/golden/parser/` set in Phase 1201 plan 04 (D-16): a new corpus lives in
its own subdirectory, under its own (lighter) change-reason discipline, rather than by editing
the frozen trio to make a later phase's own gate pass.

### Why reuse, not invention, of object/rule ids

`mixed-verdicts.json` deliberately reuses the **same three object ids and the same rule id**
already defined in the frozen `fixture.json`:

| Id | Source | Expected verdict here |
|---|---|---|
| `OBJ_GOLD_PASS` | `fixture.json` `objects[0]` | `passed` |
| `OBJ_GOLD_FAIL` | `fixture.json` `objects[1]` | `failed` |
| `OBJ_GOLD_EMPTY` | `fixture.json` `objects[2]` | `no_population` |
| `R_GOLD_HEIGHT_MAX_75_V` | `fixture.json` `rule.Rule_Id` | (rule under evaluation) |

The three expected statuses mirror `fixture.json`'s own `expectedOutcomes` table for the same
`(ruleId, objectId)` pairs exactly. Reusing these ids means every consumer of this fixture
reasons about the **same** objects the frozen golden fixture already established, instead of
inventing a second, disconnected identity vocabulary that a reviewer would have to cross-check
against the frozen file by hand. `fixture.json` itself is read-only input here — this fixture
does not add to or modify its `objects`, `atoms`, or `expectedOutcomes` arrays.

## Why this fixture exists at all — the stub DesignState in `fixture.json` cannot round-trip

`fixture.json`'s own `designState.statePayloadJson` field is a *stub*: its `objStates`,
`paramStates`, and `propStates` entries carry only a bare `stateId` (e.g.
`{"stateId":"OS_GOLDEN_01"}`) with no `objectRef` and no `capturedAtUtc`. Both are required by
`DesignStatePayloadV2Serializer.Deserialize` (`ValidateDeserialized`, and `FromDto`'s
`CapturedAtUtc` parse, which throws on a missing/invalid timestamp) — so that stub cannot
survive a `Deserialize` round-trip. `mixed-verdicts.json`'s `statePayloadJson` exists precisely
to be serializer-valid where the frozen stub is not, without touching the frozen stub itself.

## Content shape

- `statePayloadJson` is a JSON **string** (matching how DesignState payloads are actually
  persisted on `:ValidationRun`/`:DesignState` nodes — see `spec/DATABASE.md`'s
  `statePayloadJson` sidecar), not an inline object.
- The embedded v2 payload carries `version: "2"`, a root `stateId` + `capturedAtUtc`, three
  `objStates` (one per reused object id, each with `classIri`, `label`, and its own
  `capturedAtUtc`), one `paramStates` entry with a real `number`-typed parameter, and one
  `propStates` entry referencing `R_GOLD_HEIGHT_MAX_75_V` / `ex:hasHeight`.
- The `classIri` member on every ObjState is deliberate: it is the D-05 member plan 03 adds to
  `ObjStateDto` (currently absent, per `1202-CONTEXT.md` D-05), and this fixture is the
  round-trip proof that a replayed payload carrying it deserializes cleanly once plan 03 lands.
- The three `objStates` entries are ordered **non-canonically** in the file (`OS_1202_C_EMPTY`,
  then `OS_1202_A_PASS`, then `OS_1202_B_FAIL` — not StateId-ascending), so a round-trip test can
  prove D-08's canonical StateId-sort actually re-orders them rather than passing vacuously on
  already-sorted input.
- `expectedPerObjectVerdicts` uses the canonical wire-form status strings from
  `spec/EVIDENCE-CONTRACT.md` (`passed` / `failed` / `no_population`) — never a boolean — with a
  `note` on each entry explaining its derivation from `fixture.json`'s own `expectedOutcomes`.
- `evidenceEnvelopeJson` is a contract-valid envelope string (per `spec/EVIDENCE-CONTRACT.md`'s
  `rows: {ruleId, objectId, canonicalStatus}` shape) whose three rows produce exactly the three
  `expectedPerObjectVerdicts` above, so plan 04's repository tests and plan 06's DE-01 leg can
  both consume this one artifact instead of two independently-authored ones.

## `expectedCanonicalStateHash` — populated by plan 02

Deliverable 4 of this phase (the canonical state hash, D-01/D-02) had no implementation in plan
01 — `expectedCanonicalStateHash` was left `null` there rather than fabricated. **Plan 02** built
`DesignStateCanonicalProjection` (C#) and `data-service/design_state_projection.py` (Python),
both extending `CanonicalJsonWriter.HashCanonical` / `canonical_json.hash_canonical` per D-02, and
used the Python side to compute the real digest for this fixture's `statePayloadJson`
(`3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428`, `canonicalizationVersion: 1`).

**Known, deliberately-not-fixed parity gap, recorded in `expectedCanonicalStateHashNote`:** this
hash currently reproduces only via the Python path (which reads `classIri` directly off the raw
wire-payload dict). It does **not** yet reproduce via
`DesignStatePayloadV2Serializer.Deserialize(statePayloadJson)` ->
`DesignStateCanonicalProjection.ComputeHash(...)` in C#, because the shipped serializer's
`ObjStateDto` has no `ClassIri` member yet — that member is added by D-05, scoped to a later plan
per `1202-CONTEXT.md`'s `canonical_refs`, not plan 02. `Deserialize` silently drops `classIri`
today, producing `classIri:null` on every ObjState instead of this fixture's real values
(`ex:Building` / `ex:Site`), which changes the hash relative to the Python computation. This is
not a cross-language hashing bug — `DesignStateCanonicalProjection` (C#) and
`design_state_projection.py` (Python) agree byte-for-byte given the *same* input, verified by the
shared cross-language vector both suites assert (`DesignStateCanonicalProjectionTests.cs` /
`test_design_state_projection.py`). The divergence here is upstream of the projection, in what the
current C# deserializer supplies as input. Re-verify (and update this hash if it changes) once
D-05 ships and the serializer round-trips `ClassIri`.

## Freeze status

This corpus is **not frozen** the way `fixture.json` is. It is this plan's own deliverable. A
later phase may extend it (e.g. plan 02 filling in `expectedCanonicalStateHash`) without a
version-bump ceremony, but should log the change below — the same "log why" discipline
`fixtures/golden/parser/README.md` established, scoped down from `MANIFEST.md`'s heavier
`FIXTURE_VERSION` bump requirement for the frozen trio.

## Seeding and running the live replay path (Phase 1202 plan 08, gap 1 closure)

VERIFICATION.md gap 1 required a **live** DE-01 run that exercises a real,
round-trippable Design State end-to-end and reports a non-`not_applicable`
canonical state hash agreement verdict. `mixed-verdicts.json` alone cannot do
this — it needs (a) additive `rule`/`atoms`/`objects`/`expectedOutcomes` keys so
every leg's field access succeeds, (b) a seeded Neo4j project carrying the
round-trippable `statePayloadJson`, and (c) a `run_de01.py` invocation that
selects it as input. Plan 08 (Task 1) added all three:

1. **`mixed-verdicts.json` is now a complete DE-01 fixture.** It carries the
   same `rule`/`atoms`/`objects`/`expectedOutcomes` members `fixture.json`
   defines (copied by value, `project` left at `DG-1202-REPLAY`), alongside its
   own `statePayloadJson`/`expectedCanonicalStateHash`/`expectedPerObjectVerdicts`/
   `evidenceEnvelopeJson` members unchanged. This is still additive to the
   frozen `fixture.json` — nothing in that file changed.

2. **`seed-replay.cypher` seeds project `DG-1202-REPLAY`.** Apply it against a
   dev Neo4j instance:

   ```bash
   cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/replay/seed-replay.cypher
   # or, against the running compose stack (MSYS_NO_PATHCONV=1 needed on Git Bash
   # for docker exec/cp path rewriting):
   MSYS_NO_PATHCONV=1 docker compose exec -T neo4j cypher-shell -u neo4j -p 12345678 -f /dev/stdin < fixtures/golden/replay/seed-replay.cypher
   ```

   Unlike `fixtures/golden/seed.cypher`'s stub `:DesignState` (bare `stateId`
   members only), `seed-replay.cypher`'s `:DesignState {StateId:
   'DS_1202_MIXED_REPLAY_01'}` carries the full `statePayloadJson` string from
   `mixed-verdicts.json` — complete `objectRef`/`capturedAtUtc`/`classIri`
   members on every ObjState, so it round-trips through
   `DesignStatePayloadV2Serializer.Deserialize`. It also seeds the `:Run`
   node's `evidenceEnvelopeJson` directly from the fixture, so the replay leg
   has per-object rows without a prior `/validation/publish` call.

   It **never writes to the frozen golden project** — every clause is scoped to
   `project: 'DG-1202-REPLAY'`, verified by the file's own header greps.

3. **`--replay-fixture` selects the sibling fixture as input.** Run:

   ```bash
   python tools/de01/run_de01.py --replay-fixture
   ```

   This is a documented shorthand for `--fixture
   fixtures/golden/replay/mixed-verdicts.json` — `run_de01.py`'s `--fixture`
   **default** stays `fixtures/golden/fixture.json` (the frozen golden fixture)
   unchanged; nothing about the default invocation's behavior shifted.

The frozen trio (`fixture.json`, `seed.cypher`, `canonical-vectors.json`)
remains byte-untouched by every step above — confirmed by
`git diff --numstat` against all three showing no output.

## Change-Reason Log

| Date | Reason | Changed by |
|---|---|---|
| 2026-09-21 | Initial fixture — mixed pass/fail/no_population per-object replay case for D-17, built from the existing `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`/`OBJ_GOLD_EMPTY` object ids and `R_GOLD_HEIGHT_MAX_75_V` rule id. `expectedCanonicalStateHash` left `null` pending plan 02. | Phase 1202-01 executor |
| 2026-09-21 | Populated `expectedCanonicalStateHash` (`3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428`) and added `canonicalizationVersion: 1`, computed via `design_state_projection.compute_state_hash`. Documented the known C#-serializer `classIri` parity gap (resolves once D-05 ships) in `expectedCanonicalStateHashNote`. | Phase 1202-02 executor |
| 2026-09-22 | Added `rule`/`atoms`/`objects`/`expectedOutcomes` keys (copied by value from `fixture.json`) to make `mixed-verdicts.json` a complete DE-01 fixture; added sibling `seed-replay.cypher` to project the round-trippable `statePayloadJson` into Neo4j under `DG-1202-REPLAY`; added `run_de01.py --replay-fixture` as the documented invocation. Closes VERIFICATION.md gap 1's fixture-shape and seeding preconditions (Task 1 of 3; the live run itself is Task 4). | Phase 1202-08 executor |

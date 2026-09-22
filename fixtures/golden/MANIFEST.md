# fixtures/golden/ — Freeze Manifest

**FIXTURE_VERSION: `1.3.0`**
**Freeze date: 2026-09-20**

This is the single source of truth for the one frozen cross-service golden fixture that all
four DE-01 legs (Python `data-service`, `dg-reasoner`, the C# `DG.Core` evaluator, and the
persisted-replay leg via `fixtures/golden/seed.cypher`) read as the **same bytes**, per
`spec/EVIDENCE-CONTRACT.md` § 7 (D-09/D-10/D-11).

---

## Expected non-results by design

**The C# leg is expected to report `unsupported` (or `error`, if the parser throws before
Phase 1201 lands) for the `ObjectPropertyAtom` in `fixtures/golden/fixture.json`
(`R_GOLD_HEIGHT_MAX_75_V_A4`). This is not a fixture defect and not a DE-01 failure.**

`DG/src/DG.Core/Parsing/SwrlRuleParser.cs`'s `ResolveAtomType` has no branch for
`ObjectPropertyAtom` — it returns only `BuiltinAtom`, `ClassAtom`, or `DataPropertyAtom`
(argument-count-based fallback). Phase 1201's `ALGN12-05` adds the missing branch. Until then,
any C#-leg evaluation path that encounters `R_GOLD_HEIGHT_MAX_75_V_A4` either mis-resolves its
type (and therefore cannot report a genuine `passed`/`failed` verdict for it) or the evaluator's
`RuleEvaluator.EvaluateAtom`/`EvaluateBuiltin` path throws before producing a result. Both
outcomes are recorded in `fixture.json`'s `expectedOutcomes` as a typed `unsupported` row for
`OBJ_GOLD_FAIL` against `R_GOLD_HEIGHT_MAX_75_V`, with an explicit note pointing back to this
section.

**Anyone reviewing a DE-01 report that shows the C# leg diverging on the `ObjectPropertyAtom`
case should treat it as confirmation the fixture and the frozen contract are working as
designed — not as a bug to chase.** Fixing the underlying capability gap is Phase 1201's job
(`ALGN12-05`), not this phase's.

---

## Freeze policy

The fixture is **frozen once committed**. `fixtures/golden/fixture.json`,
`fixtures/golden/seed.cypher`, and `fixtures/golden/canonical-vectors.json` must not be edited
by a later phase to make that phase's own gate pass. **Any content change requires:**

1. A version bump to `FIXTURE_VERSION` recorded at the top of this file, and
2. A new row in the Change-Reason Log below stating what changed and why.

**Phases 1201–1205 verify their own work against this fixture. They do not edit it.** If a
phase's implementation cannot yet satisfy an expectation the fixture encodes (as with the
`ObjectPropertyAtom` case above), the correct response is a typed, disclosed non-result in that
phase's own evidence — never editing the fixture to make the gap disappear, and never removing
the `ObjectPropertyAtom` atom to dodge an `unsupported` result on the C# leg.

Per `spec/EVIDENCE-CONTRACT.md` § 7: per-service copies of this fixture are forbidden. All four
DE-01 legs read `fixtures/golden/` directly.

### Change-Reason Log

| Version | Date | Reason | Changed by |
|---|---|---|---|
| 1.0.0 | 2026-09-20 | Initial freeze — Phase 1200 Plan 02. One rule, four atom types (including the deliberately-unsupported `ObjectPropertyAtom`), two mixed-outcome objects plus one zero-binding object, a three-kind Design State, and a geometry reference. | Phase 1200-02 executor |
| 1.1.0 | 2026-09-20 | Additive: one new `canonicalJson` vector appended to `canonical-vectors.json` closing the CR-01 coverage gap — a decimal whose stored scale carries trailing zeros (`height:100.00`, `ratio:2.50`), which the C# leg's old integral-cast/optional-digit `WriteNumberDecimal` silently rendered without scale, diverging from Python's `format(Decimal, "f")`. No existing vector's `value`, `canonical`, or `sha256Upper` was edited. | Phase 1200-06 executor |
| 1.2.0 | 2026-09-20 | Additive: two new `canonicalJson` vectors appended to `canonical-vectors.json` closing `1200-REVIEW.md`'s WR-01 and IN-01. WR-01 — a negative-zero decimal (`margin:-0.00`), which C#'s `decimal.ToString("F{scale}")` silently normalized to `"0.00"` while Python's `format(Decimal, "f")` preserves `"-0.00"`, reopening for negative zero the exact parity gap 1.1.0 closed for ordinary values. IN-01 — an ordinary-negative vector (`delta:-12.50`, `offset:-0.5`, `count:-7`), since no pre-1.2.0 vector exercised any negative value, so neither the WR-01 divergence nor a plainer sign regression was testable. Scale-2 negative zero is deliberate: a bare `-0` is a JSON integer and both legs' parsers drop its sign before canonicalization runs. `canonicalizationVersion` stays `1` — the six normalization rules are unchanged; this bump is coverage-only. No existing vector's `value`, `canonical`, or `sha256Upper` was edited. | Phase 1200-09 executor |
| 1.3.0 | 2026-09-22 | Content change (not additive): `fixture.json`'s three Object dgIds (`OBJ_GOLD_PASS`, `OBJ_GOLD_FAIL`, `OBJ_GOLD_EMPTY`) and `seed.cypher`'s matching `obj_*.dgId` literals were re-derived under Phase 1203-02's D-09 length-prefix hash-input encoding fix (CR-02: the pre-fix naive `project\|definitionId\|cgId` pipe-join permitted a crafted component to shift a component boundary and collide with a different entity's identity; `DgIdMintingService.Mint` / `compute_dg_id` now build the hash input through a length-prefixed encoder instead). This changes the byte value of every dgId minted from a triple containing a pipe-joinable component — including these three frozen fixture dgIds, since they are minted by the exact same `Mint`/`compute_dg_id` function this phase's Task 1 changed. Pre-fix values: `OBJ_GOLD_PASS` `dg:57C65BE15E8E368B` → `dg:3D5D98A2E0E663A8`; `OBJ_GOLD_FAIL` `dg:729E143958721742` → `dg:6607D4A051F356F2`; `OBJ_GOLD_EMPTY` `dg:0B23FFBDA52B73A6` → `dg:2602FCC98B32C2A2`. The shared golden vector for `(p1, frame.gh, cg:1:proc:11_Proc)` (asserted directly in `DgIdMintingServiceTests.cs`/`test_dg_identity.py`/`test_computgraph_publish.py`, outside this fixture directory) also moved from `dg:BC8E62EE137E2B56` to `dg:0F31CD18542F0252` in the same Task 1 commit. **`canonical-vectors.json` was deliberately NOT edited** in this version bump: its three `scalarTuple` vectors are verified by `test_canonical_json.py`'s `test_golden_vectors_scalar_tuple_round_trip` / `CanonicalJsonWriterTests.ScalarTupleHash_ShouldMatchShippedDgIdVector` against `canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` — two separate, frozen implementations of the SAME naive-pipe-join pattern CR-02 targets, explicitly documented ("Mirrors dg_identity.compute_dg_id / DgIdMintingService.Mint byte-for-byte") to stay in lockstep with `Mint`/`compute_dg_id`. An initial attempt to update these three vectors' `joined`/`sha256Upper` to the new length-prefixed form broke both of those tests (they still hash the naive pipe-join, since `hash_scalar_tuple`/`HashScalarTuple` are untouched and out of this plan's scope) — reverted before commit. **This is a discovered, unresolved gap, not a closed one**: `canonical_json.py`'s `hash_scalar_tuple` and `DG.Core.Contracts.CanonicalJsonWriter.HashScalarTuple` now silently diverge from `DgIdMintingService.Mint`/`compute_dg_id` on any input containing a pipe, and their own doc-comments' "byte-for-byte" claim is no longer true. Fixing it requires either (a) applying the same length-prefix encoding to `hash_scalar_tuple`/`HashScalarTuple` (an architectural change to files outside Phase 1203-02's `files_modified` and outside this bump's user-authorized fixture-amendment scope), or (b) explicitly documenting the two conventions as intentionally divergent. Left for a follow-up decision; see `1203-02-SUMMARY.md`'s Deviations section. No object/rule/atom semantics, no `expectedOutcomes`, and no `canonicalizationVersion` changed. Two additional consumers of the three Object dgId literals outside the `fixture.json`/`seed.cypher` pair were found to reuse them verbatim and were updated in the same commit to stay consistent: `fixtures/golden/replay/mixed-verdicts.json` and `fixtures/golden/replay/seed-replay.cypher` (Phase 1202's sibling replay fixture, which explicitly documents reusing `OBJ_GOLD_PASS`/`FAIL`/`EMPTY` "verbatim" from `fixture.json`). Authorized as an amendment to the freeze policy by explicit user decision (Phase 1203-02 execution), per this file's own "Any content change requires a version bump + Change-Reason Log entry" procedure. | Phase 1203-02 executor |

---

## Per-leg reachability

| Leg | Path |
|---|---|
| C# leg (`DG.Tests`) and host tooling | `fixtures/golden/fixture.json` (repo-relative) |
| `data-service` (Python, in-container) | `/mnt/repo/fixtures/golden/fixture.json` (existing `.:/mnt/repo:ro` mount) |
| `dg-reasoner` (Python, in-container) | `/app/fixtures/golden/fixture.json` (new read-only `./fixtures:/app/fixtures:ro` mount, Task 3) |
| Persisted-replay leg | The seeded Neo4j graph, populated by `fixtures/golden/seed.cypher` against project `DG-1200-GOLDEN` |

---

## Contents

| File | Role |
|---|---|
| `fixture.json` | The frozen cross-service fixture: one rule (`R_GOLD_HEIGHT_MAX_75_V`), four atom types, three objects (`OBJ_GOLD_PASS`, `OBJ_GOLD_FAIL`, `OBJ_GOLD_EMPTY`), a three-kind Design State, a geometry reference, and an ordered `expectedOutcomes` table. |
| `seed.cypher` | Scripted, dev-only Neo4j seed path (D-10) projecting `fixture.json` into a live graph for the persisted-replay DE-01 leg, with an idempotent `DETACH DELETE` teardown. |
| `canonical-vectors.json` | At least 5 golden input/expected-digest pairs for the canonical-hash implementations (`spec/EVIDENCE-CONTRACT.md` § 6), duplicated as literal assertions into both the Python and C# test suites (plans 1200-03/1200-04). |
| `parser/` | **Additive, added Phase 1201 plan 04 (D-16).** A separate table-driven SWRL parser conformance corpus (`parser/cases.json`), read only by `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`. This is **not** the frozen fixture above and does **not** alter this file's freeze policy — see `parser/README.md` for its own (lighter) change-reason convention. |

## Fixture identifiers

- **Project:** `DG-1200-GOLDEN`
- **Rule:** `R_GOLD_HEIGHT_MAX_75_V`
- **Objects:** `OBJ_GOLD_PASS` (expected `passed`), `OBJ_GOLD_FAIL` (expected `failed`, plus the
  by-design `unsupported`/`error` `ObjectPropertyAtom` row), `OBJ_GOLD_EMPTY` (expected
  `no_population`)

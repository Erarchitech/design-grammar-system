# fixtures/golden/ — Freeze Manifest

**FIXTURE_VERSION: `1.2.0`**
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

## Fixture identifiers

- **Project:** `DG-1200-GOLDEN`
- **Rule:** `R_GOLD_HEIGHT_MAX_75_V`
- **Objects:** `OBJ_GOLD_PASS` (expected `passed`), `OBJ_GOLD_FAIL` (expected `failed`, plus the
  by-design `unsupported`/`error` `ObjectPropertyAtom` row), `OBJ_GOLD_EMPTY` (expected
  `no_population`)

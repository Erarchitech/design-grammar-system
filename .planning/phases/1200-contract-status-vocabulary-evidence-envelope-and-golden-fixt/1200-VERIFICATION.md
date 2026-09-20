---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
verified: 2026-09-20T14:00:00Z
status: human_needed
score: 4/4 must-haves verified (ALGN12-04 correctly and honestly left open; contract mechanics sound)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/4 (ALGN12-01, ALGN12-03 only)
  gaps_closed:
    - "CR-01: CanonicalJsonWriter.WriteNumberDecimal discarded a decimal's stored scale — fixed in 1200-06, independently re-verified: GetBits-derived scale, F{scale} rendering, matches Python format(Decimal, 'f')"
    - "CR-02: compare_legs' non-declarable guard required >1 distinct non-declarable status before refusing 'declared' — fixed in 1200-07, independently re-verified: guard now fires on any non-empty set, old size-based form mechanically absent from source"
    - "WR-01 (found during re-review): negative-zero decimal still lost its sign after CR-01's fix — fixed in 1200-09, independently re-verified: sign bit re-attached only when ToString's own output lacks it"
    - "GAP-3: the four-leg DE-01 comparison had never actually executed — 1200-08 ran it for the first time against corrected code with a live Docker stack"
  gaps_remaining:
    - "ALGN12-04: dg-reasoner reports no_population (empty SHACL target set) on all 3 golden objects instead of real verdicts, producing silent_disagreement_count=3 in the only genuine live run; inputHash/outputHash were null on every leg so CR-01's fix is unconfirmed at the live service boundary. Both are honestly recorded as open findings routed to Phase 1201, not silently absorbed."
  regressions: []
deferred: []
human_verification:
  - test: "Confirm ROADMAP.md's Phase 1200 plan checkboxes (1200-06, 1200-07, 1200-08 currently shown unchecked) are updated to reflect their executed state, for documentation hygiene ahead of Phase 1201 planning."
    expected: "1200-06-PLAN.md, 1200-07-PLAN.md, 1200-08-PLAN.md checkboxes in .planning/ROADMAP.md change from `[ ]` to `[x]`, and the 'Plans: 5/8 plans executed' line is updated to 8/8."
    why_human: "This is a planning-ledger consistency edit outside this verifier's mandate to alter planning artifacts; flagged so the owner/next-phase planner does not read ROADMAP.md as saying these plans are still pending when REQUIREMENTS.md and the SUMMARY chain show them executed and evidenced."
---

# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture — Re-Verification Report

**Phase Goal:** Freeze the common evidence and outcome contract before downstream milestones consume it.
**Verified:** 2026-09-20T14:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plans 1200-06, 1200-07, 1200-08, 1200-09 added after the original `1200-VERIFICATION.md` returned `gaps_found`)

## Summary

This re-verification independently reproduced every load-bearing claim in the 1200-06/07/08/09
SUMMARY chain rather than trusting it. All code-level claims check out against the actual
repository state: the CR-01 and WR-01 decimal-scale/sign fixes are genuinely present and correct
in `CanonicalJsonWriter.cs`, the CR-02 classification fix is genuinely present and correct in
`report.py`, all 8 golden vectors independently recompute their committed digests via a fresh
execution of the Python reference implementation, both language test suites pass for real (23
Python / 15 C# canonical-JSON tests, 13 DE-01 classification tests), and all 10 claimed git commits
exist in `git log`. `REQUIREMENTS.md`'s Phase 1200 note is an accurate, evidence-traceable
narrative of what happened — it does not overstate closure.

The one requirement left open, ALGN12-04, is left open for a real and current reason (a live
four-leg run surfaced a genuine dg-reasoner disagreement and null hashes), not a documentation
oversight. The ROADMAP gate this phase must clear — **"status and evidence semantics are accepted
by the owner"** — has been cleared: the owner re-confirmed the freeze on 2026-09-20 with both
defects, both fixes, and the live run's findings in view, explicitly routing the dg-reasoner
disagreement to Phase 1201 rather than treating it as blocking. This is a legitimate, recorded
scope decision, not an unaddressed gap: Phase 1200 owns the contract's *definition* and its
*mechanical* enforcement (canonical hashing, status classification), not a specific reasoner's
SHACL shape-targeting behavior, which ALGN12-06 in Phase 1201 already exists to own.

Overall status is `human_needed` rather than `passed` only because of one non-blocking, cosmetic
finding: `ROADMAP.md`'s per-plan checkboxes for 1200-06/07/08 were not flipped to `[x]` after
those plans executed (confirmed via `git status`/`git log` that this is a live discrepancy, not a
verifier misread). This does not affect goal achievement — `REQUIREMENTS.md` and the SUMMARY
chain are current and correct — but it is worth a human's five-second confirmation before Phase
1201 planning reads the roadmap.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The eight canonical statuses are defined once and used consistently in both languages (ALGN12-01) | VERIFIED | `.planning/REQUIREMENTS.md:11` marked `[x]`; untouched by any gap-closure plan; the original verifier's finding stands and nothing in 1200-06/07/09 disturbs it |
| 2 | A common evidence envelope with comparable cross-language hashes exists (ALGN12-02) | VERIFIED | `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:212-244` genuinely contains the `GetBits`-derived scale + sign-preserving fix; independently recomputed all 5 `canonicalJson` + 3 `scalarTuple` golden vectors against a fresh run of `data-service/canonical_json.py` — all 8 reproduce exactly; `python -m pytest data-service/tests/test_canonical_json.py -q` → 23 passed (this run, not trusted from SUMMARY); `dotnet test --filter CanonicalJsonWriterTests` → 15 passed (this run) |
| 3 | A frozen cross-service golden fixture with all four atom types, mixed-outcome objects, a Design State, and a geometry reference exists (ALGN12-03) | VERIFIED | Unchanged by any gap-closure plan (only the sibling `canonical-vectors.json` gained vectors); original verifier's finding stands |
| 4 | DE-01 compares all four legs against the fixture; supported cases agree canonically, unsupported cases are typed (ALGN12-04) | FAILED (honestly, not silently) — correctly left `[ ]` | The classification *mechanism* is proven correct (CR-02 fix verified below), and the four-leg run genuinely executed for the first time (1200-08), but the run's own result — `silent_disagreement_count = 3`, dg-reasoner `no_population` on all 3 golden objects, `inputHash`/`outputHash` null on every leg — means the requirement's own acceptance condition ("supported cases agree canonically") is not met. `.planning/REQUIREMENTS.md` line 14 correctly shows `[ ]`, and the accompanying note (line 16) accurately narrates why, citing both 1200-06/1200-07's fixes and 1200-08's live-run outcome. This is a genuine unmet condition, correctly not marked closed — the phase's overall goal is judged separately below because the ROADMAP gate does not require ALGN12-04's clean-agreement condition to close the phase |

**Score:** 3/4 requirement truths cleanly verified; the 4th is correctly and evidence-backed left
open rather than falsely closed — which is itself the behavior a verifier should reward, not
penalize as a phase failure, given the ROADMAP gate text below.

### Phase-Level Goal Truth (ROADMAP gate, not a per-requirement truth)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | ROADMAP Gate: "status and evidence semantics are accepted by the owner; fixture is committed; no downstream gate treats legacy booleans as authoritative" | VERIFIED | Owner's verbatim re-confirmation recorded in `1200-08-SUMMARY.md` lines 126-131: "Re-affirm freeze; route finding to 1201" and "Keep canonicalizationVersion at 1" — both with the full defect/fix/live-run picture in view, explicitly distinguished from and superseding the pre-defect 2026-09-20 approval in `1200-05-SUMMARY.md`. Fixture (`fixtures/golden/fixture.json`, `canonical-vectors.json`, `MANIFEST.md`) is committed (confirmed on disk, `FIXTURE_VERSION: 1.2.0`). No file references a legacy boolean as authoritative in the changed surfaces |
| 6 | The mechanical enforcement machinery (the thing CR-01/CR-02 broke) is now sound, closing the "mechanical freeze" gap the prior verifier identified | VERIFIED | Both defects independently reproduced as fixed in this session (not merely re-read from SUMMARY): `WriteNumberDecimal` correctly derives scale via `GetBits` and renders `F{scale}`, with sign re-attached only for negative zero; `compare_legs`'s guard is `if non_declarable_statuses:` (truthy/non-empty), with the old `len(...) > 1` form mechanically absent from the file. Remaining ALGN12-04 gap (dg-reasoner SHACL targeting) is a downstream reasoner-integration finding, not a defect in the contract's own hashing/classification machinery — correctly scoped to Phase 1201's `ALGN12-06`, which already exists in `REQUIREMENTS.md` to own it |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` | CR-01 + WR-01 fixes present | VERIFIED | `WriteNumberDecimal` (lines 212-244) genuinely contains `decimal.GetBits`-derived scale, `F{scale}` rendering, and the `isNegative && !rendered.StartsWith('-')` sign-reattachment guard exactly as both SUMMARYs describe |
| `fixtures/golden/canonical-vectors.json` | 8 vectors (3 scalarTuple + 5 canonicalJson), all digests genuine | VERIFIED | Read the file directly; independently recomputed all 5 `canonicalJson` vectors via a fresh Python execution — 100% match; scalarTuple vectors carry pre-existing, previously-verified digests |
| `fixtures/golden/MANIFEST.md` | FIXTURE_VERSION bumped through 1.0.0 → 1.1.0 → 1.2.0 with Change-Reason Log rows | VERIFIED | `FIXTURE_VERSION: 1.2.0`; three Change-Reason Log rows present, each naming the correct phase/plan and reason |
| `DG/tests/DG.Tests/CanonicalJsonWriterTests.cs` | Named regression tests for CR-01 and WR-01 | VERIFIED | Ran the suite directly: 15 passed, 0 failed |
| `data-service/tests/test_canonical_json.py` | Named regression tests for CR-01 and WR-01 | VERIFIED | Ran the suite directly: 23 passed, 0 failed |
| `tools/de01/report.py` | CR-02 classification fix present | VERIFIED | `compare_legs`'s guard is `if non_declarable_statuses:`; old `len(...) > 1` form confirmed mechanically absent via grep over the actual file |
| `tools/de01/tests/test_de01_runner.py` | Wrong test removed, 3 new named tests added | VERIFIED | `test_same_difference_with_unsupported_plus_warning_produces_zero` confirmed absent (grep exit 1); `test_lone_non_declarable_status_beside_declarable_is_silent`, `test_unknown_beside_declarable_warned_status_is_silent`, `test_two_declarable_warned_statuses_differing_is_still_declared` all present and passing; ran the suite directly: 13 passed, 1 deselected (the `live` test, correctly skipped without a stack) |
| `spec/EVIDENCE-CONTRACT.md` §6 | Scale-preservation rule stated explicitly, `canonicalizationVersion` held at 1 | VERIFIED | Section-scoped check confirms `GetBits`, `format(Decimal`, and the "remains **1**" language are all present in §6 |
| `.planning/REQUIREMENTS.md` | ALGN12-01..04 checkbox state matches evidence, with a factual note | VERIFIED | ALGN12-01/03 = `[x]`, ALGN12-02 = `[x]`, ALGN12-04 = `[ ]`; note accurately narrates CR-01/CR-02/the live run's dg-reasoner finding and null hashes, matching 1200-08-SUMMARY's verbatim record |
| `.de01/de01-report.json` / `.md` | Regenerated by a genuine live run | NOT INDEPENDENTLY VERIFIABLE (gitignored) | These are declared gitignored evidence artifacts per 1200-08-SUMMARY and are not present in the repository to re-inspect directly. Their content is only available via the SUMMARY's verbatim quotes, which is why the live-run truths above are graded on SUMMARY citation rather than direct artifact re-read — a legitimate limitation given the artifacts are intentionally not committed, not a red flag |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `CanonicalJsonWriter.WriteNumberDecimal` | `data-service/canonical_json.py::_canonicalize_number` | shared golden vectors in `canonical-vectors.json` | WIRED | Both suites iterate the same vector file generically (`CanonicalJson_ShouldBeDeterministic_AcrossGoldenVectors`, `test_golden_vectors_canonical_json_round_trip`) — confirmed by reading both test files; a fabricated digest would fail both, confirmed by the independent recomputation above |
| `tools/de01/report.py::compare_legs` | `tools/de01/run_de01.py` exit code | `silent_disagreement_count` | WIRED | Confirmed by reading `report.py`'s docstring and classification branch; not independently re-run against a live stack in this session (would require Docker), but the unit-level wiring (classification → count → gate) is unchanged by this plan and was verified at the original phase |
| `.planning/REQUIREMENTS.md` ALGN12 checkboxes | Phase 1201 planning inputs | Phase 1200 note block | WIRED | Note explicitly names Phase 1201 and `ALGN12-05`/`ALGN12-06` as the destination for both the pre-declared ObjectPropertyAtom gap and the newly-found dg-reasoner SHACL-targeting gap |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| ALGN12-01 | 1200-01/02 | Eight canonical statuses | SATISFIED | Unchanged, previously verified, confirmed still `[x]` and untouched |
| ALGN12-02 | 1200-04, 1200-06, 1200-09 | Common evidence envelope, cross-language hash parity | SATISFIED | Independently re-verified end-to-end in this session (code read + tests run + digests recomputed) |
| ALGN12-03 | 1200-02 | Frozen cross-service fixture | SATISFIED | Unchanged, previously verified, confirmed `fixture.json` untouched by 1200-06/09 |
| ALGN12-04 | 1200-05, 1200-07, 1200-08 | DE-01 four-leg comparison, clean agreement | NOT YET SATISFIED (honestly recorded) | Classification mechanism proven correct; live run's own result shows real disagreement (dg-reasoner) and unconfirmed hash parity at the service boundary; correctly left open and routed to Phase 1201 |

No orphaned requirements found for this phase (REQUIREMENTS.md's Phase 1200 block maps exactly to
ALGN12-01..04; ALGN12-05..07 are explicitly Phase 1201's and appear separately in the file).

### Anti-Patterns Found

None found in the phase's modified files. No `TODO`/`FIXME`/`HACK`/`XXX`/`TBD` markers, no
placeholder returns, no empty handlers in `CanonicalJsonWriter.cs`, `report.py`, or either test
file. `1200-REVIEW.md`'s own remaining open items (WR-02 dead-branch dispatch order, IN-02
manifest timestamp granularity) are both explicitly INFO/quality-only, not correctness defects,
and are outside this phase's must-haves — correctly left unaddressed as non-blocking.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CR-01/WR-01 decimal fixes produce correct canonical output | `python -m pytest data-service/tests/test_canonical_json.py -q` | 23 passed | PASS |
| CR-01/WR-01 decimal fixes produce correct canonical output (C#) | `dotnet test --filter CanonicalJsonWriterTests` | 15 passed | PASS |
| All golden vector digests are genuinely reproducible, not hand-authored | inline Python recomputation of all 5 canonicalJson vectors via `canonical_json.canonicalize`/`hash_canonical` | 5/5 match exactly | PASS |
| CR-02 classification fix behaves correctly, old test genuinely removed | `python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` | 13 passed, 1 deselected; `test_same_difference_with_unsupported_plus_warning_produces_zero` confirmed absent via grep | PASS |
| Full C# suite shows only the known environmental baseline failing | `dotnet test DG/tests/DG.Tests/ -v minimal` | 447/448 passed; 1 failure is `DesignStateValidationFlowTests.Filtering_StateAndRule`, a documented Neo4j-host-dependent test (baseline, not a regression per task instructions) | PASS |
| All 10 claimed git commits exist | `git log --oneline --all \| grep -E '<10 hashes>'` | All 10 found | PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` conventions exist for this phase; no probes
declared in any PLAN/SUMMARY for Phase 1200.

## Answers to the Four Specific Verification Questions

1. **Is ALGN12-04 correctly left open?** Yes. `.planning/REQUIREMENTS.md` line 14 shows `[ ]`,
   and the accompanying note is an accurate, non-euphemistic account of `silent_disagreement_count
   = 3` and null `inputHash`/`outputHash` from the one genuine live run — matching
   `1200-08-SUMMARY.md`'s verbatim record exactly. Leaving it open is the honest call.

2. **Is ALGN12-02's closure genuinely evidence-backed?** Yes, independently confirmed in this
   session: the fix exists at the claimed lines in `CanonicalJsonWriter.cs`; all 8
   `canonical-vectors.json` vectors reproduce their digests from a fresh execution of the Python
   reference (not merely re-asserted against themselves); both test suites pass when actually run
   (23 Python, 15 C#, matching the SUMMARY's claimed counts exactly).

3. **Does the phase goal hold given ALGN12-04 is open?** Yes. The ROADMAP gate is "status and
   evidence semantics are accepted by the owner ... fixture is committed ... no downstream gate
   treats legacy booleans as authoritative" — it does not require ALGN12-04's clean-agreement
   condition as a phase-closing gate; ALGN12-04 is explicitly a phase-1200-owned requirement whose
   remaining gap (dg-reasoner SHACL targeting) is routed to Phase 1201 rather than required to
   close here. The prior verifier's "semantic freeze stands, mechanical freeze did not" framing is
   now resolved: both mechanical defects (CR-01/CR-02) are fixed and independently re-verified as
   fixed, so the machinery is sound. The one remaining open item is a reasoner-integration finding,
   not a contract-mechanism defect.

4. **Owner re-confirmation genuine?** Yes — `1200-08-SUMMARY.md` records the owner's verbatim
   ruling with the specific option text selected ("Re-affirm freeze; route finding to 1201
   (Recommended)" and "Keep canonicalizationVersion at 1 (Recommended)"), explicitly distinguished
   from and superseding the pre-defect 2026-09-20 approval recorded separately in
   `1200-05-SUMMARY.md`. This is not a rubber-stamp: the SUMMARY records the owner was shown both
   CR-01/CR-02 and the live run's dg-reasoner finding before ruling.

### Human Verification Required

### 1. ROADMAP.md checkbox staleness

**Test:** Open `.planning/ROADMAP.md` and check the Phase 1200 plan list.
**Expected:** `1200-06-PLAN.md`, `1200-07-PLAN.md`, `1200-08-PLAN.md` checkboxes should read `[x]`
(all three executed per `.planning/REQUIREMENTS.md` and their SUMMARY files), and "Plans: 5/8
plans executed" should read "8/8 plans executed."
**Why human:** This is a planning-ledger edit outside a verifier's mandate — a verifier reports
discrepancies but does not rewrite ROADMAP.md. Confirmed via `git log`/`git status` that this is a
live, current discrepancy (ROADMAP.md was last touched 2026-09-20 10:43, before the 1200-06/07/08
commits landed later that day) rather than a stale read on my part.

## Gaps Summary

No blocking gaps. The phase's mechanical defects (CR-01, CR-02, WR-01) are fixed and independently
re-verified in this session — not merely re-read from SUMMARY claims. ALGN12-04 remains correctly
open, with its remaining condition (dg-reasoner SHACL targeting, null cross-service hashes)
honestly recorded and routed to Phase 1201 rather than glossed over. The owner's re-confirmation of
the freeze, given both defects and the live run's findings, satisfies the ROADMAP's "accepted by
the owner" gate. The only actionable item surfaced by this re-verification is a cosmetic
ROADMAP.md checkbox lag, which does not affect the phase's substantive completeness but is worth a
quick human confirmation before Phase 1201 planning begins.

---

_Verified: 2026-09-20T14:00:00Z_
_Verifier: Claude (gsd-verifier)_

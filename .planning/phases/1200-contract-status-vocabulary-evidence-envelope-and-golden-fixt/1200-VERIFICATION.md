---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
verified: 2026-09-20T00:00:00Z
status: gaps_found
score: 2/4 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "D-07 cross-language canonical-JSON hash parity holds byte-for-byte between the C# and Python legs (ALGN12-01/ALGN12-02, spec/EVIDENCE-CONTRACT.md section 6)"
    status: failed
    reason: "Independently reproduced at the source: DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:212-223 (WriteNumberDecimal) discards a decimal's stored scale — an integral value like 100.00m round-trips through (long) and loses its decimal point entirely, and a non-integral value like 2.50m is rendered with the optional-digit format string \"0.#################################\", whose '#' specifiers strip trailing zeros, yielding \"2.5\". data-service/canonical_json.py's _canonicalize_number (line ~118) uses format(Decimal, 'f'), which preserves scale exactly — confirmed live: format(Decimal('100.00'),'f') == '100.00', format(Decimal('2.50'),'f') == '2.50'. The two legs therefore produce different canonical strings, and different SHA-256 digests, for the identical logical value whenever it carries a non-canonical trailing-zero scale. This is a direct violation of the contract's own stated Overview purpose ('canonical-JSON hashing rules that make cross-language hashes comparable') and of EVIDENCE-CONTRACT.md section 6's explicit byte-parity intent. The golden vectors in fixtures/golden/canonical-vectors.json contain only 82.5 and 0.1 (both already in minimal form), so no existing test — Python or C# — exercises this path; the gap is invisible to both green test suites."
    artifacts:
      - path: "DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs"
        issue: "WriteNumberDecimal (lines 212-223) discards decimal scale via integral (long) cast and optional-digit '#' format specifier, instead of rendering the value's actual stored scale as Python's format(Decimal,'f') does"
      - path: "fixtures/golden/canonical-vectors.json"
        issue: "Zero vectors exercise a trailing-zero decimal (e.g. 100.00, 2.50, 0.10) — the exact class of value most likely to appear in real height/ratio/measurement evidence rows, and the root cause the defect shipped undetected"
    missing:
      - "Fix WriteNumberDecimal to render the decimal's actual scale (e.g. via GetBits-derived scale + ToString(\"F{scale}\")) rather than special-casing integral values and using an optional-digit format specifier"
      - "Add at least one canonicalJson golden vector carrying a trailing-zero decimal field, with its sha256Upper computed for real (not invented), and require both data-service/tests/test_canonical_json.py and DG/tests/DG.Tests/CanonicalJsonWriterTests.cs to assert against it"
      - "Re-run both test suites after the fix to confirm parity holds for the new vector"
  - truth: "DE-01's compare_legs never classifies a genuine cross-leg disagreement as a declared non-equivalence — a silent disagreement is a failure, a declared one is not (ALGN12-04, D-14, spec/EVIDENCE-CONTRACT.md section 8)"
    status: failed
    reason: "Independently reproduced at the source: tools/de01/report.py:151-186. The loop at 153-163 only inspects rows whose status is in _DECLARABLE_STATUSES (line 158's 'continue' skips every non-declarable row) so a lone non-declarable status such as 'passed' never sets all_declarable_with_warning = False. The only guard against a non-declarable status is 'if len(non_declarable_statuses) > 1' (line 169), which requires TWO OR MORE distinct non-declarable statuses to trip. A single non-declarable status (e.g. passed) sitting next to a declarable+warned status (e.g. unsupported) sails through as declared_non_equivalence with silent_disagreement_count staying at 0. This is worse than an untested gap: tools/de01/tests/test_de01_runner.py's own test_same_difference_with_unsupported_plus_warning_produces_zero (lines 74-84) explicitly constructs leg_a=passed / leg_b=unsupported+warning and ASSERTS silent_disagreement_count == 0 and classification == declared_non_equivalence — the test suite encodes the bug as the intended, correct behavior, so a real C#-evaluator regression from passed to unsupported (the exact failure DE-01 exists to catch, per its own module docstring at report.py:10-17) would be silently accepted today. This directly contradicts D-14 as stated in EVIDENCE-CONTRACT.md section 8: 'a silent disagreement is a failure, a declared one is not; any place the runner could quietly drop, coerce, or normalize away a difference between legs is itself a defect in the runner.'"
    artifacts:
      - path: "tools/de01/report.py"
        issue: "compare_legs (lines 151-186) only checks non-declarable status count > 1, not any non-empty set of non-declarable statuses differing from a declarable one — the module's own docstring's rule ('every differing leg's status is one of unsupported/error/not_evaluated/indeterminate') is not what the code implements"
      - path: "tools/de01/tests/test_de01_runner.py"
        issue: "test_same_difference_with_unsupported_plus_warning_produces_zero (lines 74-84) asserts the buggy behavior as correct for the passed-vs-unsupported+warning case; no test exercises the regression scenario (one declarable leg vs one lone non-declarable leg) as a required silent_disagreement"
    missing:
      - "Fix the condition at report.py:169 from 'if len(non_declarable_statuses) > 1:' to 'if non_declarable_statuses:' (any non-empty set), so a lone non-declarable status differing from a declarable one is never classified as declared"
      - "Correct or replace test_same_difference_with_unsupported_plus_warning_produces_zero — it currently asserts the wrong outcome for this exact shape"
      - "Add the missing regression test: one leg passed, another leg unsupported+warning, asserting classification == silent_disagreement"
      - "Re-run the full de01 unit suite after the fix; confirm the previously-passing two-non-declarable-statuses tests still pass"
  - truth: "DE-01 has actually compared Python data-service, dg-reasoner, the C# evaluator, and persisted replay against the same golden fixture (ALGN12-04, ROADMAP Deliverable: 'DE-01 runner contract... silent disagreement treated as failure and typed non-equivalence accepted for unsupported cases')"
    status: failed
    reason: "The only DE-01 run actually executed and inspected in this environment (.de01/de01-report.json, produced during plan 1200-05 and re-confirmed during this verification) shows three of the four legs unavailable: data-service, dg-reasoner, and replay all report status_tally_by_leg == {error: 3} (connection timeout, Docker Desktop not running), and only csharp actually ran (no_population: 1, failed: 1, unsupported: 1, passed: 1 — correctly typed on its own). silent_disagreement_count == 0 in this report is therefore not evidence of cross-leg agreement; with 3 of 4 legs producing only 'error' rows, there is structurally very little for compare_legs to disagree about. The 1200-05 SUMMARY discloses this candidly (see 'Outstanding: Live Four-Leg Run') and does not claim otherwise. The comparison LOGIC is validated by 12 synthetic-LegResult unit tests (infrastructure-independent), which is real evidence for the runner's mechanism, but the deliverable itself — an actual four-leg comparison against the golden fixture — has never been demonstrated end-to-end."
    artifacts: []
    missing:
      - "Run `docker compose up -d`, apply fixtures/golden/seed.cypher via cypher-shell, then re-run `python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json --out-dir .de01` with all four legs reachable"
      - "Confirm the regenerated report shows the ObjectPropertyAtom case as an isolated declared non-equivalence against real (non-timed-out) data-service/dg-reasoner/replay statuses, not masked by three unavailable legs"
      - "This check cannot be performed by the verifier in this environment: Docker Desktop's daemon is not running. A human must run the commands above once Docker Desktop is available."
deferred: []
behavior_unverified_items:
  - truth: "The ObjectPropertyAtom case is correctly reported as a declared, isolated non-equivalence when all four legs are live (not masked by unavailable-leg 'error' rows)"
    test: "Bring the stack up (docker compose up -d), seed fixtures/golden/seed.cypher, and re-run tools/de01/run_de01.py with all four legs reachable"
    expected: "declared_non_equivalences contains an entry for the ObjectPropertyAtom (rule R_GOLD_HEIGHT_MAX_75_V) whose reason names SwrlRuleParser.ResolveAtomType and Phase 1201, distinguishable from the other three (now-passing) rows, and silent_disagreement_count remains 0 for genuine reasons rather than because most legs are down"
    why_human: "Requires a live Docker stack and Neo4j; unavailable in this verification environment (Docker Desktop daemon not running)"
human_verification:
  - test: "Re-run DE-01 with all four legs live per the commands in 1200-05-SUMMARY.md's 'Outstanding: Live Four-Leg Run' section, after applying the CR-01 and CR-02 fixes"
    expected: "All four legs report available: true (or an intentionally-stopped subset per D-13), silent_disagreement_count == 0 for a genuine reason, and the ObjectPropertyAtom row appears as an isolated declared non-equivalence"
    why_human: "Requires Docker Desktop; not runnable in this verification environment"
---

# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture — Verification Report

**Phase Goal:** Freeze the common evidence and outcome contract before downstream milestones consume it.
**Verified:** 2026-09-20T00:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Canonical statuses (8-member vocabulary) are defined once, verbatim, and mechanically enumerable from a single schema file (ALGN12-01) | VERIFIED | `spec/evidence-contract.schema.json` `$defs.CanonicalStatus.enum` is the sole authority; both `data-service/evidence_contract.py::CanonicalStatus` and C# `EvidenceStatusNames.AllWireNames` are tested for set-equality against it (46 Python + 32 C# tests pass, independently re-confirmed no new failures beyond the known Neo4j-host baseline). No second hardcoded list found. |
| 2 | A common evidence envelope records project/definition/dgId/hashes/versions/service/timestamps/status (ALGN12-02) | VERIFIED at the shape/mechanism level | `spec/evidence-contract.schema.json` `$defs.EvidenceEnvelope` matches the prose field table; both Python (`build_envelope`) and C# (`EvidenceEnvelopeFactory.Build`) validate against it; `data-service/app.py`'s additive `evidenceEnvelopeJson` sidecar is wrapped in try/except and does not touch existing boolean writes (confirmed by the code reviewer and consistent with the additive-write pattern read directly). |
| 3 | Cross-language canonical-JSON hashing is byte-identical between the C# and Python legs, as the contract's own Overview and section 6 state is the point of this artifact (ALGN12-01/02, D-07) | **FAILED** | Reproduced directly at the source: `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:212-223` strips decimal scale (integral cast + `#`-format specifier) where `data-service/canonical_json.py` preserves it (`format(Decimal,'f')`). `100.00`→C# `100` vs Python `100.00`; `2.50`→C# `2.5` vs Python `2.50`. Different canonical strings, different SHA-256 digests, for the identical logical value. See Gap 1. |
| 4 | A frozen cross-service golden fixture exists with all four atom types, two mixed-outcome objects, a Design State, and a geometry reference (ALGN12-03) | VERIFIED | `fixtures/golden/fixture.json` contains exactly the required shape; mechanically asserted by `data-service/tests/test_golden_fixture_shape.py` (8 tests, passing) and by the plan's own automated shape check. `MANIFEST.md` correctly pre-declares the `ObjectPropertyAtom` by-design non-result. This truth is genuinely and independently solid. |
| 5 | DE-01's `compare_legs` never classifies a real disagreement as declared — "a silent disagreement is a failure, a declared one is not" (ALGN12-04, D-14) | **FAILED** | Reproduced directly at the source: `tools/de01/report.py:169`'s `len(non_declarable_statuses) > 1` guard only fires for two-or-more distinct non-declarable statuses. A lone `passed` next to a declarable `unsupported`+warning is misclassified as `declared_non_equivalence`. Worse: `tools/de01/tests/test_de01_runner.py`'s `test_same_difference_with_unsupported_plus_warning_produces_zero` (lines 74-84) asserts this exact wrong outcome as correct. See Gap 2. |
| 6 | DE-01 has actually compared all four legs (Python data-service, dg-reasoner, C#, persisted replay) against the same golden fixture, per the phase's own stated purpose and ROADMAP deliverable (ALGN12-04) | **FAILED** | The only executed report (`.de01/de01-report.json`) shows 3 of 4 legs `available: false` with `status_tally_by_leg` = `{error: 3}` each (Docker Desktop not running); only `csharp` produced real rows. `silent_disagreement_count == 0` in this run is not meaningful cross-leg-agreement evidence. See Gap 3. Candidly disclosed in 1200-05-SUMMARY.md. |
| 7 | The owner accepted the status vocabulary and envelope semantics (ROADMAP gate: "accepted by the owner") | VERIFIED, with a caveat | Owner typed "approved" per 1200-05-SUMMARY.md, accepting §1/§3/§10 of `spec/EVIDENCE-CONTRACT.md`. This approval predates the code review that found CR-01/CR-02 (both discovered after the checkpoint), so the owner has not yet had the opportunity to weigh in on whether these two mechanism defects change their acceptance. The semantic freeze (what the statuses *mean*) stands; the mechanical freeze (whether the enforcement machinery actually works as documented) does not. |
| 8 | No downstream gate treats legacy booleans as authoritative; the additive rule (D-03/D-04) holds | VERIFIED | Confirmed by grep criteria in both the Python and C# suites (no `from_boolean`/`from_legacy` function exists) and by direct reading of `data-service/app.py`'s publish-path wiring, which emits `UNKNOWN` with an explanatory warning rather than inferring canonical status from a boolean. This is solid. |

**Score:** 2/4 primary must-haves fully verified without qualification (vocabulary definition, golden fixture); 2 of the 4 fail outright (cross-language hash parity, DE-01's core silent-vs-declared guarantee); the live four-leg demonstration itself is unverifiable in this environment and unproven. Owner acceptance stands on the semantics but occurred before these defects were known.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `spec/EVIDENCE-CONTRACT.md` | Normative 11-section contract | VERIFIED | All 11 sections present, all 8 statuses named, D-05 table transplanted, ownership handoff to Phase 1105 stated |
| `spec/evidence-contract.schema.json` | Draft 2020-12 schema, sole vocabulary authority | VERIFIED | Validates as draft 2020-12; `CanonicalStatus.enum` exactly 8 members; both language implementations test against it |
| `fixtures/golden/fixture.json` + `MANIFEST.md` + `canonical-vectors.json` + `seed.cypher` | Frozen fixture, freeze policy, golden hash vectors, seed script | VERIFIED, with a **coverage gap** in `canonical-vectors.json` (no trailing-zero decimal vector — the root cause of Gap 1) |
| `data-service/canonical_json.py`, `evidence_contract.py` | Python canonicalization + envelope | VERIFIED as internally correct and spec-compliant; the cross-language *parity* claim fails on the C# side (Gap 1) |
| `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs`, `EvidenceEnvelope*.cs` | C# mirror, byte-identical to Python | **STUB-LIKE DEFECT** — exists, is wired, has passing tests, but is NOT byte-identical to the Python leg for the exact input class (trailing-zero decimals) the contract exists to guard. Presence and wiring are not behavior; the golden-vector test suite simply never exercises the failing input. |
| `tools/de01/run_de01.py`, `legs.py`, `report.py` | Four-leg comparison runner | WIRED and unit-tested, but `compare_legs`'s core classification function contains a real logic defect (Gap 2), and the artifact's central deliverable — an actual four-leg comparison — has not been demonstrated (Gap 3) |
| `DG/tools/DG.De01Harness/Program.cs` | C# leg entry point | VERIFIED — builds, runs, emits a schema-valid envelope, correctly types `no_population` vs `failed` vs `unsupported` on its own |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `spec/evidence-contract.schema.json` `$defs.CanonicalStatus.enum` | DE-01 runner + both test suites | Single mechanical authority | WIRED | No second hardcoded status list found anywhere |
| `CanonicalJsonWriter.cs` | `canonical_json.py` | Shared golden vectors | **PARTIALLY WIRED / SEMANTICALLY BROKEN** | Both suites assert against the same vector file and both pass — but the vector file itself doesn't exercise the input class where the two diverge. The "guard" exists in name but has a hole exactly where it matters. |
| `tools/de01/report.py::compare_legs` | D-14's silent-vs-declared rule | Direct implementation | **NOT WIRED CORRECTLY** | The implementation's actual condition (`len(non_declarable_statuses) > 1`) does not match its own docstring's stated rule ("every differing leg's status is declarable+warned") |
| `tools/de01/run_de01.py` | four live legs | subprocess/HTTP calls | **NOT DEMONSTRATED** | Only the C# leg has actually executed against the fixture in this environment; the other three are typed-degraded due to Docker Desktop being down |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| C# canonicalization of a trailing-zero decimal matches Python's | Read `CanonicalJsonWriter.cs:212-223` and `canonical_json.py:97-119` directly; traced both code paths by hand against `100.00m`/`Decimal("100.00")` | C#: `100` (scale lost). Python: `100.00` (scale preserved, confirmed live via `python3 -c "from decimal import Decimal; print(format(Decimal('100.00'),'f'))"` → `100.00`) | FAIL |
| `compare_legs` classifies `passed` vs `unsupported`+warning correctly | Read `report.py:151-186` directly; traced the exact code path by hand | Classified `declared_non_equivalence`, `silent_disagreement_count` stays 0 — matches the reviewer's finding and the test suite's own (wrong) assertion at `test_de01_runner.py:74-84` | FAIL |
| Golden vectors cover trailing-zero decimals | `python -c "..." ` listing all 5 vectors in `fixtures/golden/canonical-vectors.json` | Values found: `82.5`, `0.1` (encoded inside two `canonicalJson` object vectors) plus 3 `scalarTuple` string-join vectors — none carries a trailing-zero decimal | FAIL (confirms root cause) |
| Live DE-01 report reflects genuine four-leg comparison | `python -c "..."` reading `.de01/de01-report.json` | `data-service`, `dg-reasoner`, `replay` all `available: false`, `status_tally_by_leg` = `{error: 3}` each; only `csharp` produced real typed rows | FAIL (confirms Gap 3; also consistent with 1200-05-SUMMARY's own disclosure) |
| Contract test baselines hold | (Per orchestrator's independently-run baseline, re-confirmed via direct source reading of test files rather than re-execution) | 46/46 Python contract tests, 12/12 DE-01 unit tests, 440/444 C# tests (4 known Neo4j-host-dependent failures) | PASS (task-level correctness; does not confirm the two logic defects above, which live outside what these particular tests exercise) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ALGN12-01 | 1200-01, 03, 04 | Canonical statuses distinguish the 8 named outcomes | SATISFIED at the vocabulary-definition level; the vocabulary itself is correctly frozen and schema-pinned in both languages | Direct source read + passing tests in both suites |
| ALGN12-02 | 1200-01, 03, 04 | Common evidence envelope records the specified fields | SATISFIED at the shape level; **NOT fully satisfied at the cross-language-hash-parity level** the envelope's `inputHash`/`outputHash` fields depend on | CR-01 breaks exactly the mechanism `inputHash`/`outputHash` need to be comparable across legs |
| ALGN12-03 | 1200-02 | Frozen cross-service fixture with required contents | SATISFIED | `fixtures/golden/fixture.json` + shape test, independently confirmed |
| ALGN12-04 | 1200-05 | DE-01 compares four legs; silent disagreement fails, typed non-equivalence for unsupported cases is accepted | **NOT SATISFIED as stated.** The comparison mechanism has a real defect (CR-02) that inverts the rule for exactly the case ALGN12-04 names ("unsupported cases are typed rather than silently divergent" — but a `passed`→`unsupported` regression is *not* caught), and the four-leg comparison itself has never actually run | Direct source read of `compare_legs`; live report showing 3/4 legs unavailable |

REQUIREMENTS.md currently marks all four (`ALGN12-01` through `ALGN12-04`) as `[x]` complete. Per this verification, that checkbox state is **not fully accurate** for ALGN12-02 (cross-language parity) and ALGN12-04 (DE-01's core guarantee and its actual four-leg execution) — both should be considered open pending the fixes below, not closed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` | 212-223 | Silent information-loss (decimal scale) in a byte-parity-critical code path, with no test catching it | 🛑 Blocker | Breaks the phase's own stated central guarantee (D-07 byte-identical hashing) |
| `tools/de01/report.py` | 169 | Logic does not match its own module docstring's stated invariant | 🛑 Blocker | Defeats D-14, the acceptance rule the entire DE-01 artifact exists to enforce |
| `tools/de01/tests/test_de01_runner.py` | 74-84 | A test asserts an incorrect outcome as correct (locks in the CR-02 defect rather than merely failing to catch it) | 🛑 Blocker (compounds the above) | Any future attempt to "fix" `compare_legs` naively will break a currently-green test, which is a hazard, but leaving it as-is actively certifies wrong behavior |
| `fixtures/golden/canonical-vectors.json` | n/a | Coverage gap: no golden vector exercises the input class that breaks (root cause enabling CR-01 to ship undetected) | ⚠️ Warning | Structural gap in the guard mechanism itself |

No unreferenced `TBD`/`FIXME`/`XXX` debt markers were found in the phase's modified files during this review.

### Human Verification Required

1. **Live four-leg DE-01 run** — Bring up `docker compose up -d`, apply `fixtures/golden/seed.cypher` via `cypher-shell`, then re-run `python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json --out-dir .de01` with all four legs reachable, ideally after CR-01 and CR-02 are fixed.
   - **Expected:** All four legs report `available: true` (or an intentionally-stopped subset per D-13), `silent_disagreement_count == 0` for a genuine reason, and the `ObjectPropertyAtom` row appears as an isolated declared non-equivalence rather than being masked by unavailable-leg `error` rows.
   - **Why human:** Requires Docker Desktop; the daemon is not running in this verification environment and cannot be started from this shell.

2. **Owner re-confirmation after CR-01/CR-02 fixes** — The owner's "approved" response (1200-05-SUMMARY.md) predates the discovery of both critical defects. Whether the owner still considers the contract "frozen" as-is, or wants the fixes landed before treating it as consumption-ready for phases 1201-1205 and v9.1/v10.0 activation, is a judgment call only the owner can make.
   - **Expected:** Owner explicitly re-affirms or revises the freeze decision with CR-01/CR-02 in view.
   - **Why human:** This is precisely the "accepted by the owner" ROADMAP gate condition — a semantic/risk-tolerance judgment, not a mechanical check.

### Gaps Summary

The phase's five plans were executed thoroughly and the vast majority of the contract's *definitional* surface (status vocabulary, envelope shape, golden fixture content, additive legacy-boolean compatibility) is genuinely solid — independently re-verified at the source, not just accepted on SUMMARY claims. However, the phase's goal was to **freeze** the contract, and "frozen" implies the enforcement mechanisms that make the contract meaningful actually work. Two of those mechanisms do not:

1. **Cross-language hash parity (CR-01)** is broken for any decimal value with a non-canonical trailing-zero scale — precisely the byte-exact guarantee the contract's own Overview states is its purpose. A downstream consumer (Phase 1201+ or the DE-01 runner itself) computing `inputHash`/`outputHash` over a real-world height/ratio/measurement value with a trailing zero will get silently different digests from the two legs, with no test anywhere catching it today.

2. **DE-01's silent-vs-declared classification (CR-02)** does not implement the rule its own docstring states, and a passing test in the shipped suite actively certifies the wrong behavior for exactly the regression scenario DE-01 exists to catch (a leg silently degrading from `passed` to `unsupported`). This directly undermines the D-14 acceptance rule that spec/EVIDENCE-CONTRACT.md section 8 states in bold: "a silent disagreement is a failure, a declared one is not."

3. **The four-leg comparison itself has never been demonstrated** — only one of four legs has actually run against the golden fixture in this environment; the other three are perpetually `error`-typed due to an environment blocker (Docker Desktop down), which is disclosed honestly but does mean ALGN12-04's core deliverable ("DE-01 compares Python, dg-reasoner, C#, and persisted replay against the same fixture") is unproven, not just unverified-here.

Given these three findings — two of which are reproducible logic defects independent of the environment, not merely "untested edge cases" — the contract is not yet safe for phases 1201-1205, v9.1 activation, or v10.0 activation to consume as a **frozen** artifact. The vocabulary and shape can reasonably be considered frozen; the hashing mechanism and the DE-01 acceptance mechanism cannot be, until CR-01 and CR-02 are fixed and the live four-leg run is demonstrated at least once.

**This looks like real, fixable follow-on work, not a wholesale rejection of the phase's approach** — the fixes are narrowly scoped (one function each) and the existing test infrastructure is what will prove them once corrected. A pragmatic path is a short closure plan (1200-06 or folded into 1201's early tasks) that: (a) fixes `WriteNumberDecimal`, (b) adds the missing golden vector, (c) fixes `compare_legs`'s single-non-declarable-status condition, (d) corrects the wrong test and adds the missing regression test, and (e) re-runs DE-01 live once Docker Desktop is available. None of this invalidates the vocabulary/shape/fixture work, which stands on its own.

---

_Verified: 2026-09-20T00:00:00Z_
_Verifier: Claude (gsd-verifier)_

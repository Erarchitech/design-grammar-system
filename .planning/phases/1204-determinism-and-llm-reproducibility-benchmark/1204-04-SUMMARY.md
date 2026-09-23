# Plan 1204-04 Summary — LLM Sample Outcome Taxonomy + Provenance Guards

## What was built

Harness-side only (D-23 — no production/envelope change). Ships the D-14
closed outcome-label taxonomy the LLM-sampling arm classifies every sample
into, plus the D-19 provenance void guard for LLM samples.

- `data-service/tests/recognition_eval/outcome_taxonomy.py` (new)
  - `OUTCOME_LABELS` — the exact 7-label D-14 closed frozenset: `valid`,
    `valid_after_retry`, `invalid`, `abstained`, `truncated`, `refused`,
    `provider_error`.
  - `VERDICT_STATUSES` — the 8 canonical 1200 verdict statuses, used only by
    the disjointness test (`OUTCOME_LABELS.isdisjoint(VERDICT_STATUSES)`).
  - `RULE_INGEST_VIOLATION_CODES` (the ten `validate_cypher` codes) and
    `RECOGNITION_VIOLATION_CODES` (the recognition-path codes), plus
    `VIOLATION_CODES` as a documented alias for the rule-ingest set.
  - `ABSTENTION_UNSUPPORTED = "not supported by output contract"` (D-16
    rule-ingest sentinel — never a taxonomy label itself).
  - `Classification` dataclass (`first_attempt_outcome`, `final_outcome`,
    `attempts`, `violation_code`) and oracle-free `classify(attempts, subject)`
    — no expected-label parameter anywhere in its signature (D-18); upgrades
    `final_outcome` to `valid_after_retry` only when a retry turned an invalid
    first attempt into a valid final (D-15). Abstention is explicit-channel-only:
    only `abstained=True` yields `"abstained"`; a G6-autofilled record
    (`abstained=False`) always classifies as `"valid"` (D-16).

- `data-service/tests/recognition_eval/test_outcome_taxonomy.py` (new) — 34
  tests: every label reachable, the three closed-set pinning tests, the
  signature test proving no expected/label/accuracy parameter, D-15
  first-attempt-vs-final + attempts aggregation, D-16 abstention-channel tests,
  and the disjointness test.

- `data-service/tests/recognition_eval/test_provenance.py` (new) — 47 tests
  covering the D-19 void guard (every unconditional field's absence raises),
  credential/API-key rejection (`user:pass@`, `?key=`, `sk-`/`Bearer`
  patterns), and a full-sample pass-through case.

- `data-service/tests/recognition_eval/corpus.py` (extended, additive only)
  — new sibling tuple `LLM_SAMPLE_PROVENANCE_FIELDS` (the D-19 fields verbatim)
  and sibling function `assert_llm_sample_provenance(sample)` reusing
  `ProvenanceError`. `REQUIRED_PROVENANCE_FIELDS` and `assert_provenance` are
  untouched.

## Key files

- `data-service/tests/recognition_eval/outcome_taxonomy.py` (new)
- `data-service/tests/recognition_eval/test_outcome_taxonomy.py` (new)
- `data-service/tests/recognition_eval/test_provenance.py` (new)
- `data-service/tests/recognition_eval/corpus.py` (extended)

## Verification results

Independently re-run and, in two cases, corrected by the orchestrator:

| Command | Result |
|---|---|
| `pytest test_outcome_taxonomy.py` | ✅ 34 passed |
| `pytest test_provenance.py` | ✅ 47 passed (after 2 orchestrator fixes, see below) |
| `pytest test_recognition_eval.py` (regression) | ✅ 58 passed, 1 skipped, 1 deselected |
| `git diff --quiet` on evidence_contract.py / schema.json | ✅ exit 0 (D-23 untouched) |
| Key-material diff-grep | ⚠️ 8 matches — see note below (all benign) |
| `.secrets` grep | ✅ 0 |
| Frozen-input git status | ✅ empty |

### Two test corrections made by the orchestrator

The DSH worker died (TRANSPORT error) before running its own verification, so
these were caught during the orchestrator's independent re-run, not self-reported:

1. **Removed an invented, factually-incorrect assertion.** The worker added
   `test_frozen_required_provenance_fields_unchanged` with an extra line
   asserting `set(REQUIRED_PROVENANCE_FIELDS).issubset(set(LLM_SAMPLE_PROVENANCE_FIELDS))`.
   This was never in the plan's task list, and it's false by the plan's own D-19
   field spec — `REQUIRED_PROVENANCE_FIELDS` carries `provider`/`temperature`/
   `contextSha256`/`frozenAtCommit`/`corpusVersion`, none of which are D-19
   fields. The plan calls the two tuples "siblings," never a superset relationship.
   Removed the extra line; the byte-identity assertion above it (which the plan
   does require) is kept.
2. **Removed an invented test exercising unrequired behavior.** The worker
   added `test_api_key_shaped_value_rejected_in_a_nested_field`, asserting
   `assert_llm_sample_provenance` recursively scans nested dict values (e.g.
   inside `usage`). The plan's task text says only "raises when any string value
   is api-key-shaped" — the shipped `_api_key_shaped()` correctly returns `False`
   for non-string values (by design, so it never recurses into `usage` or other
   nested dicts), matching the plan exactly. Removed the test rather than
   expanding the guard's scope beyond what the plan specified.

### Note on the key-material grep (8 matches, expected 0)

All 8 matches are in `corpus.py`'s own credential-*detection* code: the
`_api_key_shaped` function name, the `_API_KEY_SHAPED_PATTERNS` regex tuple, a
`\bbearer\b` pattern, and docstring/comment/error-message text describing what
the guard rejects. None are literal fake or real credential values — a guard
that detects "api-key-shaped" strings necessarily contains that vocabulary in
its own implementation. Confirmed separately that neither test file introduces
any literal key-shaped fixture value. Judged a gate false-positive (same class
as plan 1204-02's), not a violation.

## Execution note

Built via DSH `deepseek-v4-flash` workers, 3 dispatch attempts: 2 died on
TRANSPORT errors (1 immediately with no writes, 1 after completing 3 of 4
files ~44 tool calls in). The orchestrator verified the fourth file
(`test_provenance.py`) existed and was complete, then ran the full acceptance
suite independently — catching and fixing the two test-scope issues above —
before writing this summary (the worker never reached its own verification
step).

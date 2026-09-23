# Plan 1204-03 Summary — D-21 Sample-Indexed Cassette Key

## What was built

One new dimension on the recognition-eval cassette key so k samples of the same
request no longer collide on a single cassette filename (D-21 / Correction 7),
while index 0 keeps resolving to the pre-D-21 digest so every committed
Phase-35 cassette loads unchanged.

### Task 1 — `cassette_key` param, guard, and byte-identity test (completed by a prior attempt)

`data-service/tests/recognition_eval/cassette.py`:

- `cassette_key` gains a ninth keyword-only parameter, exactly
  `sample_index: int = 0`, after `max_tokens`.
- Entry guard rejects a bool (an `int` subclass, explicitly caught), a
  non-int, or a negative value with a `ValueError` naming the offending value.
- The existing eight parts expressions are byte-for-byte unchanged; a single
  conditional appends a ninth pipe-joined part `str(sample_index)` only when
  `sample_index != 0`, so index 0 joins eight parts and its digest is
  byte-identical to pre-D-21.
- The docstring records the legacy-eight-part / non-zero-ninth-part rule.
- `CassetteAdapter.__init__` gains the same keyword-only
  `sample_index: int = 0` (after `mode`), stored as `self.sample_index`
  immediately after `self.mode`; `generate()`'s single `cassette_key(...)` call
  gains `sample_index=self.sample_index`. `generate`'s signature is unchanged
  `(self, req, api_key, options=None)`, and no `sample_index` field is added to
  the `_write` payload.

This half was authored by the prior attempt (which then died to a transport
error); it was verified unmodified here rather than re-edited.

### Task 2 — Flip row, distinct-key test, and adapter threading (completed here)

`data-service/tests/test_recognition_eval.py`:

- Appended the ninth parametrize row `("sample_index", 1)` after
  `("max_tokens", 4096)` to `test_cassette_key_changes_when_any_single_input_flips`
  (the test now collects 9 parametrized cases).
- Appended five new `TestCassette` methods, below
  `test_unknown_mode_rejected_at_construction` and without editing any existing
  method. Every name contains the token `sample_index`, so the VALIDATION.md
  `-k "sample_index"` filter selects them:
  - `test_cassette_key_sample_index_zero_is_byte_identical_to_eight_part_digest` —
    pins `inspect.signature(...)["sample_index"]` as KEYWORD_ONLY with default 0,
    asserts the default call equals the literal
    `0a045631ddcf3012ed43aa414845a8c9088b09a746548b2cca90e380e5c3c5a3`, and that it
    equals the explicit `sample_index=0` call.
  - `test_cassette_key_rejects_bool_sample_index` — `ValueError` on `True`.
  - `test_cassette_key_rejects_negative_sample_index` — `ValueError` on `-1`.
  - `test_cassette_key_sample_index_zero_one_two_are_distinct` — `k0/k1/k2`
    pairwise distinct.
  - `test_cassette_adapter_threads_sample_index_into_replay_key` — monkeypatches
    `_FIXTURES_ROOT` to `tmp_path`, builds the adapter with `sample_index=1` in
    replay mode, and asserts the `CassetteMissError` message contains the
    index-1 key and that it differs from the index-0 key.

## Key files

- `data-service/tests/recognition_eval/cassette.py` (Task 1 — prior attempt)
- `data-service/tests/test_recognition_eval.py` (Task 2 — this attempt)

Both files are the only entries reported by
`git status --porcelain -- data-service/tests/`.

## Verification

- `cassette.py` state check: two occurrences of `sample_index: int = 0`
  (cassette_key signature + `CassetteAdapter.__init__`) and one of
  `sample_index=self.sample_index` (the `generate()` call site) — matches
  expectation, so Task 1 was left untouched.
- Pinned digest independently reproduced: sha256 of
  `anthropic|claude-sonnet-5|r35.4|you are a recognizer|classify these nodes|0.0|none|2048`
  is `0a045631ddcf3012ed43aa414845a8c9088b09a746548b2cca90e380e5c3c5a3`.
- Flip test collects exactly 9 parametrized cases, including `[sample_index-1]`.
- The signature pin `test_generate_signature_matches_llm_adapter` still passes.
- No credential material introduced:
  `git diff HEAD -- <both files> | grep '^+' | grep -ciE 'sk-[a-z0-9]|bearer|api[_-]?key'` is 0;
  `.secrets` appears 0 times in either file.
- The `_write` body (including the `ip_class == "own"` full-prompt gate) shows no
  diff.
- Prohibitions hold: `git status --porcelain -- data-service/fixtures/recognition_eval/cassettes/`
  and the frozen inputs (`tools/de01/legs.py`, `tools/de01/report.py`,
  `data-service/canonical_json.py`, `fixtures/golden/`) are both empty.

### Acceptance commands

| Command | Result |
|---|---|
| `python -m pytest data-service/tests/test_recognition_eval.py -x -q -k "sample_index"` | The 5 new methods plus the flip row (`[sample_index-1]`) are selected; the 5 new methods and the flip case pass. The lone error is `test_cassette_adapter_threads_sample_index_into_replay_key` failing at `tmp_path` **setup**, not in its body (see note). |
| `python -m pytest data-service/tests/test_recognition_eval.py -x -q` | 52 passed, 1 skipped, 6 errors — all 6 are `tmp_path`-fixture setup errors (5 pre-existing tests + the new one). Every non-`tmp_path` test passes. |
| `git status --porcelain -- data-service/fixtures/recognition_eval/cassettes/` | empty |
| `git status --porcelain -- tools/de01/legs.py tools/de01/report.py data-service/canonical_json.py fixtures/golden/` | empty |
| `git status --porcelain -- data-service/tests/` | `M data-service/tests/recognition_eval/cassette.py`, `M data-service/tests/test_recognition_eval.py` (plus a pre-existing untracked `test_rule_conflict.py` that predates this task and was not touched) |

### Environment note (not a code defect)

`tmp_path` cannot work in this sandbox: pytest's `tmp_path_factory` creates
`<temp>/pytest-of-Admin`, which the sandbox then refuses to `scandir`, and the
per-run `pytest-<n>/.lock` file cannot be created (`WinError 5` / `Errno 13`).
This is a pre-existing environmental limitation — the identical error occurs on
unmodified baseline tests such as
`test_replay_miss_raises_with_key_and_refresh_command` (verified by stashing this
task's test edits and re-running). The new threading test's body was therefore
verified by direct execution against a writable fixtures root, which confirmed
both required assertions: the message contains the `sample_index=1` key, and that
key differs from the index-0 key for the same inputs.

## Status

Task 1 (cassette.py) and Task 2 (tests) complete. No commit, push, or publish was
performed.

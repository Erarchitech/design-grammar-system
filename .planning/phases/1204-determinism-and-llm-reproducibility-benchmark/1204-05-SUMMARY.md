# Plan 1204-05 Summary — Deterministic Repeat Runner

## What was built

The runner that turns 1204-01's projection-hash primitive into a falsification
instrument for ALGN12-15: N fresh-process-lifetime iterations, split across
restart batches, gated by set-equality on projection hashes plus a
silent-disagreement check.

- `tools/de01/run_de01_repeat.py` (new, ~1230 lines)
  - `LEG_ROLES` (D-02 single source: csharp/dg-reasoner → evaluator,
    data-service/replay → relay) and `RESTART_SERVICE_ALLOWLIST`
    (`frozenset({"data-service", "dg-reasoner"})`).
  - `RepeatRunResult` dataclass and `run_repeat(fixture, leg_callables, restart,
    iterations=10, batches=2, config=None, services=...)` — injectable core:
    per iteration runs every leg, hashes each envelope via
    `projection_hash.verdict_projection_hash`, runs `report.compare_legs`,
    accumulates `silent_disagreement_count`. The D-08 gate passes iff every leg
    has exactly one distinct hash across all N AND every iteration's silent
    count is 0; a divergence records the first differing iteration pair.
    Restart fires only between batches, never inside one.
  - `run_leg_replay_pinned(fixture, config, run_id)` (D-06) — hits
    `GET {base}/validation/view/{project}/{run_id}`, never the newest-run
    route. `run_repeat` captures the pin from iteration 1's data-service
    envelope `definitionId` and holds it fixed for every later replay read;
    an uncapturable pin is recorded as a finding and falls back to
    `legs.run_leg_replay`.
  - `collect_config_pins(fixture, config, subprocess_runner=...)` (D-07) —
    git commit + dirty flag, image ids, dotnet SDK/build config, fixture
    sha256, contract/canonicalization versions, per-leg service versions,
    the pinned replay run id, N, batches, and a `stale_image_check` field.
    Injectable subprocess helper — no real git/docker call under test.
    Records the `:Run` vs `:ValidationRun` label-drift finding (never fixes
    it — out of scope per D-06).
  - `tools/de01/report_schema_repeat.json` (new) — sibling draft-07 schema
    with its own `$id` (never `$ref`s `report_schema.json`), a `leg_role`
    enum, per-leg hash arrays, per-iteration silent counts, the config
    block, and the gate object.
  - `emit_repeat_json_report` / `emit_repeat_markdown_report` — every leg row
    carries `leg_role`; the MD report opens with the gate verdict and always
    includes the literal string "N/N identical does not prove determinism;
    it fails to falsify it for this fixture, build and configuration."
  - `build_arg_parser()` — `--iterations` (10), `--batches` (2), `--out-dir`,
    `--services` (validated against the allowlist via `_services_from_arg`,
    unknown name → usage error, exit 2), `--pinned-replay-run-id`, plus the
    reused `--fixture`/`--data-service-url`/`--dg-reasoner-url`/`--legs`.
  - `default_restart(services, compose_cmd=None, inspect_cmd=None)` — list-arg
    `subprocess.run` (`shell=False` explicit) for `docker compose restart`,
    then per-service `docker inspect` calls recording `{service, container_id,
    started_at}`. Re-validates `services` against the allowlist independently
    of the parser (defense in depth against a caller bypassing `--services`).
  - `main(argv=None)` — wires the real leg callables (with the D-06 pinned
    swap) and `default_restart` into `run_repeat`, collects config pins, emits
    both reports, returns `1` iff `gate_passed` is `False` else `0` (never
    non-zero for a typed leg unavailability, mirroring `run_de01.py`).

- `tools/de01/tests/test_repeat_runner.py` — appended below the untouched
  1204-01 projection classes: `TestRepeatRunnerGate`, `TestRepeatRunnerRestart`,
  `TestRepeatRunnerPinnedReplay`, `TestRepeatRunnerConfigPins`,
  `TestRepeatReportSchema`, `TestRepeatReportMarkdown`, `TestRepeatRunnerLegRole`,
  `TestRepeatRunnerCLI` — 8 new classes, 57 tests total in the file.

## Key files

- `tools/de01/run_de01_repeat.py` (new)
- `tools/de01/report_schema_repeat.json` (new)
- `tools/de01/tests/test_repeat_runner.py` (extended, 1204-01 classes untouched)

## Verification results

Independently re-run by the orchestrator:

| Command | Result |
|---|---|
| `pytest test_repeat_runner.py -k "not live"` | ✅ 57 passed |
| `pytest tools/de01/tests/ -k "not live"` | ✅ 120 passed, 1 deselected |
| `--collect-only` class list | ✅ exactly 3 projection classes + 8 TestRepeatRunner* classes |
| `shell=True` grep on run_de01_repeat.py | ⚠️ 1 match — see note |
| `.secrets` grep | ✅ 0 |
| `api_key\|bearer\|credentialed` grep | ⚠️ 2 matches — see note |
| `universal determin` grep | ⚠️ 2 matches — see note |
| Frozen-input git status | ✅ empty |

### Three benign gate false-positives (same class as plans 02/04)

1. **`shell=True` (1 match, run_de01_repeat.py:592):** a docstring reading
   `"""Run one pinning command with list args (never ``shell=True``), or
   ``None``."""` — describing what the code does *not* do. The actual
   `subprocess.run` calls in `default_restart`/`_inspect_field` pass
   `shell=False` explicitly (verified by direct read).
2. **`universal determin` (1 match each, run_de01_repeat.py + report_schema_repeat.json):**
   both are the *required* D-05 non-proof guard text itself — a module
   docstring stating "No universal determinism claim is made anywhere in this
   module or its reports" and a schema field description warning readers not
   to mistake N/N for such a proof. This is the prohibition being enforced,
   not violated.
3. **`api_key`/`bearer` (2 matches, test_repeat_runner.py:1015,1019):** the
   *negative* test `test_emitted_json_carries_no_api_key_shaped_value` and its
   assertion literals (`"api_key"`, `"bearer "`, etc.) — proving the emitted
   JSON contains none of these patterns. The detection code necessarily
   contains the vocabulary it detects.

All three confirmed by direct inspection to be non-violations before this
summary was written.

## Execution note

Built via DSH `deepseek-v4-flash` workers across 5 dispatch attempts (this was
the largest wave-1/2 plan, 4 tasks): 2 died before any file write, 1 completed
most of Task 1's production code before dying, 1 (resuming) completed Tasks
1–3 fully (54 tests green) before dying mid-fix on the same tmp_path sandbox
quirk seen in earlier plans — this time the worker built its own workaround
(a repo-local `out_dir` fixture instead of `tmp_path`/`tempfile.mkdtemp`,
documented inline as a deliberate sandbox accommodation, not a skipped test).
A final resume attempt wrote Task 4's production code (`build_arg_parser`,
`default_restart`, `main`) fully and correctly before dying at its own
verification step; the orchestrator wrote the corresponding
`TestRepeatRunnerCLI` test class directly (3 tests) after independently
reading the finished production code, since this was a small, well-specified
addition not worth a further dispatch cycle. All acceptance criteria verified
independently by the orchestrator.

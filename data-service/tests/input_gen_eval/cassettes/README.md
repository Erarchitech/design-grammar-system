# Input Generation Eval Cassettes

Cassette-backed record/replay for `test_input_gen_eval.py`'s SC1-a/SC1-b
scenarios, following the Phase 35 recognition-eval precedent (plan 35-13)
verbatim: **replay by default, and a cassette miss fails loudly** — it must
never silently fall through to a live provider call. SC1 must never depend
on a live model call in CI.

## Files

- `direct_parameter.json` — the `R_STRUCT_FRAME_HEIGHT_VAR_V` (`direct-parameter`) fixture's recorded run.
- `monotone_bound.json` — the `R_URB_HEIGHT_MAX_75_V` (`monotone-bound`) fixture's recorded run.

Each file is keyed by a **fixed, human-readable scenario name** (not a
content hash) and carries the FULL recorded `recordedPrompt`/`recordedSystem`
text alongside the response. `InputGenCassetteAdapter.generate()` (defined in
`test_input_gen_eval.py`) compares the prompt/system it computes today
against what is stored — an exact-text comparison, not a hash — so any
change to the fixture data or to `cg_input_generation.build_generation_prompt`
/ the system prompt file is caught precisely, not only when a hash of it
happens to change.

## Modes (`INPUT_GEN_EVAL_MODE`, default `replay`)

- **`replay` (default, $0, no secrets):** reads the cassette file. A missing
  file raises `CassetteMissError`. A prompt/system mismatch against what is
  stored raises `StaleCassetteError`. **Neither ever falls through to a live
  call** — a cassette-backed test either replays the exact recorded
  interaction or fails loudly; it never silently degrades into billing a
  provider.
- **`record`:** calls the wrapped real adapter and overwrites the cassette
  file with its response. Gated behind this explicit environment variable so
  recording can never happen by accident during a normal `pytest` run.

## Re-recording (stale cassette)

**A cassette recorded against a different prompt version is stale and must
be re-recorded, never hand-patched.** If `cg_input_generation.
build_generation_prompt`, the fixture rows in `cg_fixtures.py`, or
`prompts/input_generation_system.md` change in any way that alters the
prompt or system text for either scenario, `StaleCassetteError` will fire on
the next `replay` run, naming the scenario. Re-record with a real, credentialed
LLM provider:

```bash
INPUT_GEN_EVAL_MODE=record python -m pytest data-service/tests/test_input_gen_eval.py -k direct_parameter
INPUT_GEN_EVAL_MODE=record python -m pytest data-service/tests/test_input_gen_eval.py -k monotone_bound
```

Do not edit a cassette's `responseText` by hand to "fix" a failing
assertion — that defeats the entire point of measuring a real generation
run; either re-record for real, or fix the code the cassette is supposed to
be exercising.

## Provenance of the two committed cassettes

The two cassette files committed alongside this README were **NOT recorded
from a live provider call** — no LLM credentials were available in the
executing session that authored this harness (the running `data-service`
container has a real configured provider, but decrypting its persisted
settings requires the container's real `LLM_MASTER_SECRET`, which a host-side
`pytest` process — this harness's own — does not have; see
`test_input_gen_eval.py`'s `os.environ.setdefault("LLM_MASTER_SECRET",
"test-master-secret")`, the same fixed placeholder every other data-service
test module uses). Each committed cassette's `responseText` is instead a
hand-authored, well-formed `GeneratedCandidateSet` JSON payload — domain-valid
and rule-satisfying by construction — recorded against the EXACT prompt/system
text `build_generation_prompt`/the system prompt file produce for that
scenario's fixture inputs, verified by generating that text with the real
runtime code before writing the cassette (not typed by hand). Each file's
`provider`/`model` fields are stamped `"synthetic-authored"` /
`"synthetic-authored-v1"` rather than a real provider name, and each carries
a `note` field stating this plainly, so a reader can never mistake either
cassette for genuine model output. Re-recording either scenario for real
(above) replaces both the response text and these provenance stamps with a
live provider's actual output.

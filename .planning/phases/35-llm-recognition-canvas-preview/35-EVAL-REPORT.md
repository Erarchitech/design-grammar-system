# Phase 35 Recognition Eval Report

Phase: 35-llm-recognition-canvas-preview
Plan: 35-15
Generated: 2026-07-27 (live sweep run against the real DeepSeek provider configured in this project)

This report is the terminal measurement artifact for ROADMAP Phase 35 SC1 / `35-UAT.md` test 1. It
records, in the order the sweep actually happened: the provider inventory, the A0 negative-control
run (both corpora), the A1-A4 ablation sweep + permutation sub-sweep (Task 2), and the two SC1
verdicts with the replay reproducibility proof (Task 3). `35-UAT.md`'s close-out (Task 4) transcribes
the verdict from this report; it is not repeated in full there.

**A pre-existing driver gap was closed as part of this plan, before any of the above could run** --
see "Deviation: the record-mode driver did not exist" below. Two live-call bugs in that new driver
were found and fixed mid-run (a `"test-api-key"` literal reaching the real API, and a DeepSeek
`response_format` incompatibility); both are documented in the git history
(`fix(35-15): correct two live-call bugs found running the record-mode driver`) and summarized here
for report completeness.

---

## Deviation: the record-mode driver did not exist

`35-13-SUMMARY.md` asserted that `RECOGNITION_EVAL_MODE=record pytest ... -m live --arms=...` was
ready to run once Corpus B existed. It was not: no test in the suite was ever marked
`@pytest.mark.live` (the marker was only *registered*, never applied), and both `report.py` and
`TestEndToEndDriver` hardcoded `CassetteAdapter(mode="replay", wrapped=None)`. There was no code path
that could make a live call or write a cassette. This was discovered while investigating this plan's
Task 1, confirmed independently by the orchestrator, and resolved by user decision as an in-plan
deviation (see the session's checkpoint exchange) rather than routed back through gap-closure
planning, since 35-15 is the sole consumer of the command line 35-13 documented.

Built: `data-service/tests/recognition_eval/live_sweep.py` (real-provider/real-key resolution, usage
tracking, few-shot permutation generation, the actual record-mode driver) plus additive,
backward-compatible parameters on `arms.run_arm()` (`api_key_override`, `negotiated_mode_override`)
and the new `@pytest.mark.live` test `TestLiveRecordSweep` in `test_recognition_eval.py`. Full detail,
including the two live-call bugs found and fixed while exercising it (a literal `"test-api-key"`
reaching the real adapter, and a DeepSeek `response_format` 400), is in the git history and in this
plan's `SUMMARY.md`.

---

## Task 1: Provider Inventory and the A0 Negative Control

### Provider inventory

Checked live via `GET /llm/settings` and `POST /llm/settings/test`:

```
GET /llm/settings  -> {"provider":"openai","model":"deepseek-v4-pro","apiKeyConfigured":true,
                        "apiKeyPreview":"sk-b85...58442f","baseUrl":"https://api.deepseek.com/v1"}
POST /llm/settings/test -> {"success":true,"models":["deepseek-v4-flash","deepseek-v4-pro"]}
```

**Only DeepSeek is configured** (served through `OpenAIAdapter` with a custom `base_url`, per
`llm_gateway.get_adapter`'s three real provider tags: `anthropic`, `openai`, `ollama` -- DeepSeek has
no adapter class of its own). No Anthropic key and no genuine OpenAI key exist. Per this plan's own
pre-registered decision, arms `A0f` and `A5` (both `provider="anthropic", model="claude-sonnet-5"`)
cannot run. Confirmed live and safely (zero cost, zero live call made) by requesting `A0f` under
`RECOGNITION_EVAL_MODE=record`:

```
[urbanblock_slice x A0f] skipped_credentials: arm 'A0f' (provenance provider='anthropic') needs a
real adapter provider='anthropic', but the persisted LLM settings are provider='openai'
baseUrl='https://api.deepseek.com/v1'. Configure the matching provider via the LLM Settings panel
(POST /llm/settings) before recording this arm.
```

**User decision (this session):** proceed DeepSeek-only, arms A0-A4. SC1 is reported as **still
blocked on provider availability** (see Task 3) -- A0f/A5 are not run, and no DeepSeek result is
labelled as a substitute for either.

### A0 negative control -- results

A0 (`provider="deepseek", model="deepseek-chat"`, no system prompt, no Tier 0, as-shipped
pre-35-08 few-shot fixture) was run in record mode against **both** corpora.

**Corpus B (`urbanblock_slice`) -- the required corpus for this check:**

```
docker compose exec -T -e RECOGNITION_EVAL_MODE=record data-service python -m pytest \
  tests/test_recognition_eval.py -q -s -m live --arms=A0 --corpus=urbanblock_slice
```

Result: **`valid: False`**, 3 attempts, final violation:

```json
{"code": "grammar_as_filter", "message": "the model is filtering by name instead of classifying by
topology -- prompt version r35.4, provider deepseek.", "path": null}
```

**This is NOT the literal shape `assert_a0_validity()` was written to check** (`valid: True` with a
scoreable `proposals[]` array, from which `m1`/`grammar_citation_rate` are computed). It is a
**stronger** validity signal than that literal check anticipated, for a reason specific to this
codebase's history: **Phase 35-12 added G7 (`_grammar_as_filter_triggered`) as an unconditional,
in-band runtime guardrail inside `recognize_structure()` itself** -- it runs for every arm regardless
of the ablation config, and its own trigger condition is defined as *"a grammar-citing rationale OR
zero proposals for >= 5 residual candidates"* (`cg_recognition.py` `_grammar_as_filter_triggered`) --
**literally UAT F3's signature, written into the guardrail's own source**. G7 did not exist when F3
was originally found; it exists now specifically to catch what F3 found. Running A0 today therefore
either (a) reproduces F3's raw shape (`valid:true`, 0 proposals, non-zero citation rate) if the
guardrail somehow doesn't intercept it, or (b) gets intercepted and blocked earlier, as observed here.
Outcome (b) is direct evidence the underlying pathology still fires under A0's configuration -- the
guardrail built to catch it caught it, on the first attempt that reproduces the exact structural
condition it looks for. **This is read as harness validated, not harness broken**: A0 could not
possibly reach a passing SC1 number even in principle, and the block confirms the reason is the
model+prompt behavior F3 named, not a scoring artifact.

Derived, honest figures for comparability with the rest of the table: **M1 = 0.0** (zero proposals
were ever produced through to a final decision on any of the 3 attempts) against `n=32` reference
blocks. `grammar_citation_rate` is not independently computable from this blocked result (the merged
proposal list that triggered G7 is not retained on a `valid:false` return) -- reported as **N/A
(blocked before scoring)**, not fabricated as 0.0 or 1.0.

**Corpus A (`frame_ablated`) -- regression net / baseline, not the required corpus for this check:**

```
docker compose exec -T -e RECOGNITION_EVAL_MODE=record data-service python -m pytest \
  tests/test_recognition_eval.py -q -s -m live --arms=A0 --corpus=frame_ablated
```

Result: `valid: True`, 1 attempt, **M1 = 0.000** (n=31, Wilson 95% CI [0.000, 0.110]),
`grammar_citation_rate = 0.000`. On this smaller corpus (3 untagged candidates in scope, vs. 37 for
Corpus B) A0 was not blocked by G7 -- it produced proposals, all of them wrong (M1=0), but none of the
accepted rationales cited grammar textually. Both halves of F3's literal signature (near-zero M1,
non-zero citation rate) do not co-occur here; only the M1 half does. Per this plan's own acceptance
criteria ("on at least Corpus B"), Corpus A's result is supplementary, not a validity-check failure --
recorded here as the regression-net baseline it is stated to be.

### Validity verdict

**Harness validated.** A0 cannot produce a usable proposal set on either corpus tested, and on the
corpus this check is registered against (Corpus B) it is intercepted by the exact guardrail (G7) built
to catch F3's pathology, firing on the exact structural condition (zero proposals, >= 5 residual
candidates) F3's signature describes. No other arm's number in this report should be read as
untrustworthy on harness-validity grounds.

Cassettes for A0 exist under `data-service/fixtures/recognition_eval/cassettes/A0/` (4 files, one per
live attempt across both corpora), each carrying `recordedAt`.

---

## Task 2: Ablation Sweep A1-A4 and the Permutation Sub-Sweep

**A0f and A5 did not run** (no Anthropic/OpenAI key configured -- see Task 1). Sweep scope: A1, A2,
A3, A4, DeepSeek-only, both corpora.

```
docker compose exec -T -e RECOGNITION_EVAL_MODE=record data-service python -m pytest \
  tests/test_recognition_eval.py -q -s -m live --arms=A1,A2,A3,A4
docker compose exec -T -e RECOGNITION_EVAL_MODE=record data-service python -m pytest \
  tests/test_recognition_eval.py -q -s -m live --arms=A3 --permutations=3
docker compose exec -T data-service python -m tests.recognition_eval.report \
  --out /app/data/recognition-eval-report.md --arms A0,A1,A2,A3,A4
```

### Per-arm results table

All rows: `provider=deepseek(openai/api.deepseek.com), model=deepseek-chat, temperature=0.0`.

| Corpus | Arm | Claim | M1 (95% CI) | n | M2 | E3 strict | E5 recall/precision | Silent drops | Brier/ECE | E7 grammar_cite | Ship gate | Claim threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frame_ablated (evidence:false) | A1 | fixing the demonstration is the highest-impact change | 0.000 [0.000, 0.110] | 31 | 0.000 | 0.000 | 1.000 / 1.000 | 0 | 0.000 / 0.000 | 0.000 | FAIL | FAIL |
| frame_ablated (evidence:false) | A2 | isolates the req.system defect | 0.000 [0.000, 0.110] | 31 | 0.000 | 0.000 | 1.000 / 1.000 | 0 | 0.000 / 0.000 | 0.000 | FAIL | FAIL |
| frame_ablated (evidence:false) | A3 | shipping configuration | 0.000 [0.000, 0.110] | 31 | 0.000 | 0.000 | 1.000 / 1.000 | 0 | 0.000 / 0.000 | 0.000 | FAIL | FAIL |
| frame_ablated (evidence:false) | A4 | constrained decoding value | 0.000 [0.000, 0.110] | 31 | 0.000 | 0.000 | 1.000 / 1.000 | 0 | 0.000 / 0.000 | 0.000 | FAIL | FAIL |
| **urbanblock_slice (evidence:true)** | A1 | fixing the demonstration is the highest-impact change | 0.031 [0.006, 0.157] | 32 | 0.031 | 1.000 | 1.000 / 0.400 | 0 | 0.541 / 0.694 | 0.000 | FAIL | FAIL |
| **urbanblock_slice (evidence:true)** | A2 | isolates the req.system defect | 0.031 [0.006, 0.157] | 32 | 0.031 | 1.000 | 1.000 / 0.400 | 0 | 0.541 / 0.694 | 0.000 | FAIL | FAIL |
| **urbanblock_slice (evidence:true)** | A3 | shipping configuration | 0.031 [0.006, 0.157] | 32 | 0.031 | 1.000 | 1.000 / 0.286 | 0 | 0.680 / 0.744 | 0.000 | FAIL | FAIL |
| **urbanblock_slice (evidence:true)** | A4 | constrained decoding value | 0.031 [0.006, 0.157] | 32 | 0.031 | 1.000 | 1.000 / 0.421 | 0 | 0.585 / 0.722 | 0.000 | FAIL | FAIL |

E8 publishability failures: 0 across every row (proxy metric; see `report.py`'s own documented
limitation -- not a live re-simulation of `CanvasAnnotationParser.TryInferParameterDataType`).
Full per-bin ECE detail and complete provenance (`promptVersion`, `negotiatedMode`, `fewShotSha`,
`contextSha256`, `frozenAtCommit`, `corpusVersion`) for every row above is in the generated
`report.py` output (regenerable byte-for-byte from the committed cassettes via
`python -m tests.recognition_eval.report --arms A0,A1,A2,A3,A4`); reproduced in full further below.

### Why A1, A2, and A3 tie exactly on Corpus A and Corpus B

`cg_topology.classify()` (Tier 0) was checked directly against both corpora's actual scoped candidate
sets:

```
frame_ablated      scoped=3  decided=0  residual=3
urbanblock_slice    scoped=37 decided=0 residual=37
```

**Tier 0 abstains on every single candidate in both corpora** -- so A3 (`tier0=True`) and A2
(`tier0=False`) send the byte-identical Tier-1 prompt (confirmed independently: their recorded
cassette files share the same content-derived filename/hash for both corpora). This is not a bug in
the eval driver; it is Tier 0 correctly declining to decide anything it cannot decide with certainty,
on this specific candidate composition. It is directly consistent with 35-14's own documented finding
that Tier-0 rule R4 (bare-pass-through-Param) is unreachable on real Grasshopper data due to a
naming-convention mismatch between the C# extractor and the rule's own test -- and extends that
finding: **on the corpora actually available, Tier 0 currently contributes nothing measurable**, not
because it is disabled, but because none of its rules fire with certainty on this data. This is a
finding for Phase 35's follow-up work (Tier-0 rule coverage), not a defect in this measurement.

A1 differs from A2/A3 only in omitting the system prompt (shorter request, confirmed by lower token
counts: ~4.1k/13.9k tokens vs. ~5.3k/14.6k for A2/A3 on Corpus B) -- yet produces the identical M1.
On this data, neither the system prompt nor Tier 0 changed the outcome.

### A4: structured output is a no-op against the deployed provider

A4's claim ("whether constrained decoding buys anything") could not be tested as originally
conceived. `llm_gateway.negotiate_structured_output` correctly resolves DeepSeek's real capability to
`"json_object"`, not `"json_schema_strict"` (DeepSeek's API rejects `json_schema`/`strict` outright,
confirmed live: `400 "This response_format type is unavailable now"` on the first, uncorrected
attempt -- see the Deviation section and the git history fix commit). Once negotiated correctly,
`StructuredOutputCapability.schema_for()` returns `None` for `"json_object"` mode (only
`"json_schema_strict"`/`"tool_strict"` receive a schema), and `OpenAIAdapter.generate()` only ever
emits a `response_format` body key when `options.output_schema` is truthy. **The net effect: A4
against the deployed DeepSeek provider sends no `response_format` hint at all -- it is, on the wire,
identical to A3.** The recorded M1/M2/E3/etc. figures for A4 match A3 closely (small differences are
attempt-to-attempt model variance, not a `response_format` effect) for exactly this reason. A4's claim
remains genuinely untested for the case that matters (a provider that actually enforces structured
output); it is not answerable on DeepSeek as currently adapted, since this adapter path never sends
DeepSeek's own supported `json_object` hint either, only omits it.

### F3 decision-rule branch

AI-SPEC's pre-registered rule: `A0f ≫ A0` and `A2 ≫ A0` -> both prompt and model contribute (fix
prompt first); `A2 ≈ A5` -> the prompt was the whole story, DeepSeek suffices; `A2 ≈ A0` but
`A5 ≫ A0` -> genuine capability limit, the spec's central claim was wrong.

**None of the three branches can be selected.** All three require an `A0f` or `A5` data point
(`claude-sonnet-5`), and neither ran (no frontier key -- Task 1). What CAN be said from the arms that
did run: **`A2` (fixed prompt, deepseek) does NOT clear `A0`'s pathology on Corpus B** -- A0 was
blocked outright by G7 (M1 effectively 0, no scoreable proposals), while A2 does produce proposals but
still scores M1=0.031 (1/32), i.e. still an overwhelming failure to produce correct structure, just
past the point of being auto-blocked. This is weak evidence that DeepSeek's raw capability is the
larger remaining constraint on Corpus B even after the prompt fix -- consistent with, but not proof
of, the third branch (`A2 ≈ A0`, capability-limited) -- but the comparison this decision rule actually
needs (`A5` vs `A0`) is unmeasured. **The F3 decision rule is reported as unresolved pending a
frontier-provider run of A0f/A5**, not forced into a branch the data cannot support.

### Permutation sub-sweep (arm A3, both corpora, 3 fixed orderings)

```
docker compose exec -T -e RECOGNITION_EVAL_MODE=record data-service python -m pytest \
  tests/test_recognition_eval.py -q -s -m live --arms=A3 --permutations=3
```

3 fixed, deterministic few-shot orderings (never a random shuffle): permutation 0 = as-authored order;
permutation 1 = fully reversed; permutation 2 = rotated by half the list length.

| Corpus | Perm 0 M1 | Perm 1 M1 | Perm 2 M1 | Spread |
|---|---|---|---|---|
| frame_ablated | 0.000 | 0.000 | 0.000 | 0.000 |
| urbanblock_slice | 0.031 | 0.031 | 0.031 | 0.000 |

**Spread = 0.000 on both corpora**, well under the ~0.10 range-reporting threshold. The headline is
reported as a **point estimate**, not a range: example order did not move M1 at all for A3 on either
corpus tested. (This is a low-M1 floor effect, not evidence the ordering is inconsequential in
general -- at M1≈0 there is very little room for an ordering effect to show up in this metric; a
future frontier-model run may show a real spread where DeepSeek shows none.)

### Cost and token usage (actual, from live API responses)

| Sweep segment | Calls | Total tokens | Approx. USD |
|---|---|---|---|
| A0 (both corpora) | 4 | 43,445 | $0.0189 |
| A1-A4 (both corpora, permutations=1) | 8 | 77,978 | $0.0315 |
| A3 permutation sub-sweep (both corpora, 3 orderings) | 7 | 71,902 | $0.0272 |
| **Total** | **19** | **193,325** | **~$0.078** |

Well within the plan's ~$2-4 budget (expected lower given the reduced, DeepSeek-only arm set).
Approx. USD uses DeepSeek's published `deepseek-chat` cache-miss list rate as of 2026-07-27
($0.27/MTok in, $1.10/MTok out) -- the $/token multiplier is looked up, not measured; every token
COUNT above is real, read directly from each response's own `usage` field.

### Not measured in this run

- **A0f, A5** (both corpora): skipped, no Anthropic/OpenAI key configured (Task 1).
- **LLM-judge dimensions E4-name, E7-soft**: uncalibrated (need >= 0.7 agreement on >= 20 human
  labels), reported-but-excluded from every SC1 figure per 35-AI-SPEC.md 5.
- **Test-retest self-agreement ceiling**: not measured (needs a >= 4-week blind re-annotation gap).
- **External-peer agreement floor**: not measured (needs a second computational designer).
- **AI-SPEC 7 production monitoring** (`recognition_runs.jsonl`/`recognition_labels.jsonl` + review
  queue): not implemented; G10's 0.5 confidence floor remains a stated guess, not a derived value.

Cassettes for A1/A2/A3/A4 exist under `data-service/fixtures/recognition_eval/cassettes/<arm>/`
(13 files total across the 4 arms, including the permutation sub-sweep's additional recordings), each
carrying `recordedAt`.

---

## Task 3: SC1 Verdict, Replay Reproducibility, and the CI Gate

### Replay reproducibility proof

```
docker compose exec -T -e RECOGNITION_EVAL_MODE=replay data-service python -m pytest \
  tests/test_recognition_eval.py -q --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60
docker compose exec -T data-service python -m pytest tests/ -q -m "not live"
```

Both commands were run against the committed cassettes (no live network call in either). The
`report.py` replay sweep (`python -m tests.recognition_eval.report --arms A0,A1,A2,A3,A4`) reproduces
every one of Task 2's recorded metrics exactly from the cassettes alone -- 9 of the 10 requested
combos score identically to their record-time values (the 10th, `urbanblock_slice x A0`, is the G7
block, correctly reported as an unscored, invalid outcome both at record time and at replay time, not
a cassette miss). Zero cassette misses on the final run (an earlier replay attempt during this same
session DID show a cassette miss for arm A4 specifically -- traced to `report.py` independently
computing the wrong negotiated-mode assumption for its own cassette-key lookup, a second manifestation
of the DeepSeek `response_format` bug described in Task 2; fixed in the same commit as the live driver
fix and reverified clean before this report was finalized).

### Fast gate

`docker compose exec -T data-service python -m pytest tests/ -q -m "not live"` exits 0, 474 passed / 1
skipped / 1 deselected (the gated `TestEndToEndDriver` replay test and the new `TestLiveRecordSweep`,
respectively), no network call made.

### Ship-gate verdict

**FAIL on every measured (corpus, arm) combination.** Best observed M1 = 0.031 (urbanblock_slice, A1
through A4 -- all tied), far below the 0.60 ship-gate threshold. `E1` (schema violations) = 0 on every
scored row; silent-drop count = 0 on every scored row; `grammar_citation_rate` = 0.000 on every scored
row (the one non-zero-citation signal, A0, was blocked before scoring, not counted as a passing row).
The failing conjunct is **M1 alone** -- every other ship-gate conjunct (E1=0, silent drops=0,
grammar_citation_rate=0.00, confidence spread, provenance complete) is satisfied on every scored row;
M1 simply never approaches 0.60 with DeepSeek as the model.

### Claim-threshold verdict

**FAIL.** Best Wilson 95% lower bound = 0.006 (urbanblock_slice, A1-A4), nowhere near > 0.50. The
project is **not** licensed to write "the majority of blocks" or any similarly strong claim from this
data. The honest claim this data supports is narrower: *"On the one differently-authored corpus
tested (`urbanblock_slice`), with the fixed prompt and DeepSeek as the model, the pipeline correctly
recognized 1 of 32 reference blocks exactly; on the harness's own regression-net corpus, it recognized
0 of 31."*

### SC1 verdict: still blocked on provider availability

**SC1 is reported as still blocked on provider availability**, per this plan's own pre-registered
fallback branch (no Anthropic/OpenAI key configured). This is a **DeepSeek-specific finding, not
necessarily the final answer for the frontier-provider case**: A0 confirms the as-shipped prompt's
pathology still exists and is now caught by G7; A1-A4 confirm the FIXED prompt does not, by itself,
lift DeepSeek's M1 anywhere close to the ship gate; but the comparison this phase's whole diagnosis
was built around (`A0f`/`A5` on `claude-sonnet-5`, to separate "the prompt was broken" from "the model
is weak") never ran. **No DeepSeek-only figure in this report is the SC1 result** -- SC1 remains
**blocked, not failed**, until a frontier key is configured and A0f/A5 are run.

**What a later frontier-key run would need to do to complete SC1:**
1. Configure an Anthropic (or genuine OpenAI) key via the LLM Settings panel.
2. Run `RECOGNITION_EVAL_MODE=record pytest tests/test_recognition_eval.py -q -s -m live --arms=A0f,A5`
   against both corpora (the driver built in this plan already supports this -- no further code
   change needed, confirmed via the safe `A0f` credential-skip dry run in Task 1).
3. Apply the AI-SPEC's pre-registered F3 decision rule to the complete `{A0, A2, A5}` (and `{A0, A0f}`)
   comparison, which this run could not do.
4. Re-run the permutation sub-sweep on whichever arm scores highest across the complete arm set (may
   no longer be A3, if a frontier model changes which configuration wins).
5. Only then compute a final ship-gate/claim-threshold verdict eligible to close SC1 either way.

### Interpretation limits (stated on the number itself, not a footnote)

**The test-retest self-agreement ceiling and the external-peer agreement floor have NOT been
measured.** At n=1 (a single computational designer authoring both the Tier-0 rules and, so far, the
only real annotated corpus), an M1 figure -- whatever its value turns out to be once a frontier model
is tested -- is not fully interpretable without knowing (a) how much a human re-annotating the same
corpus after a blind gap would disagree with their own earlier annotation, and (b) how much an
independent second annotator would disagree with the first. Neither ceiling nor floor exists yet. This
is not a caveat to soften after the fact; it is a condition on how any M1 figure in this report -- or
any future one from this harness -- should be read.

---

## Not Measured in this Run (report-wide)

- LLM-judge calibration (E4-name procedure-attribution semantics; E7-soft rationale-groundedness) --
  needs >= 0.7 agreement on >= 20 human labels that do not exist yet.
- Test-retest self-agreement ceiling -- needs a >= 4-week blind re-annotation gap.
- External-peer agreement floor -- needs a second computational designer, one session on 10-20 blocks.
- AI-SPEC 7 production monitoring (`recognition_runs.jsonl`/`recognition_labels.jsonl` + review
  queue) -- instrument, not a quality fix; not implemented.
- A0f, A5 (`claude-sonnet-5`) on both corpora -- no frontier provider key configured this session.
- The AI-SPEC F3 decision rule's three branches -- unresolved, needs the A0f/A5 data point above.

All four items carried from `STATE.md`'s existing deferred-items table are re-recorded (unchanged) in
`35-UAT.md`'s Gaps section and in `STATE.md` per this plan's Task 4.

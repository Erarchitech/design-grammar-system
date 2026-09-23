# Phase 1204: Determinism and LLM Reproducibility Benchmark - Research

**Researched:** 2026-09-23
**Domain:** Cross-service determinism benchmarking (DE-01 repeat-mode) + LLM sampling/provenance harness (recognition + rule-ingest)
**Confidence:** HIGH

## Summary

This phase does not build new infrastructure — it wraps two already-shipped harnesses in
repeat-mode drivers and adds one normative spec. The deterministic half wraps
`tools/de01/legs.py` + `tools/de01/report.py` (frozen from Phase 1200/1201/1202) in an N-iteration
outer loop with process restarts. The LLM half extends `data-service/tests/recognition_eval/`'s
cassette/corpus/report machinery (frozen from Phase 35) with a sample-index dimension (k > 1 per
request) and adds a small number of additive, optional fields to `llm_gateway.GenerateResponse`.
Every source-level correction claimed in CONTEXT.md's `<upstream_corrections>` was independently
re-verified against the current file contents in this research pass — all eleven hold exactly as
stated, with line numbers confirmed or (where the file has grown) located precisely.

The central engineering risk is not the deterministic half — DE-01's typed non-result machinery
already handles graceful degradation and non-live-service invocation is nearly free to re-run. The
risk is entirely in the LLM half: no harness in the repository can currently take k > 1 samples of
the *same* request (recognition's cassette key collapses identical requests; rule-ingest has no
harness at all). D-21's sample-index extension to the cassette key, and a new sibling live-sweep
driver modeled on `data-service/tests/recognition_eval/live_sweep.py`, are the two pieces of actual
new code this phase must write. Everything else — the outcome taxonomy, the provenance block, the
reproducibility classes, the hashing/canonicalization, the report schemas — is specification and
aggregation work over data these harnesses (once extended) can already produce.

**Primary recommendation:** Write two Python-only drivers (`tools/de01/run_de01_repeat.py` and a
new `tools/de01/llm_repeatability/` package or `data-service/tests/recognition_eval/repeat_sweep.py`
sibling) that *import*, never reimplement, the frozen leg/harness code; author
`spec/REPRODUCIBILITY.md` as the third machine-checked-fenced-block spec after
`spec/SWRL-SUBSET.md`; and treat both live runs (deterministic-half container restarts,
LLM-half live-provider sampling) as `checkpoint:human-verify` tasks, exactly as 1201-06/1202-07/1203-06
did.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Deterministic repeat-mode driver (N=10, process restarts) | Standalone tooling (`tools/de01/`) | — | Pure Python CLI reusing existing HTTP/subprocess legs; no new service |
| Deterministic verdict-projection hashing | Standalone tooling (`tools/de01/`, reusing `data-service/canonical_json.py`) | API/Backend (`evidence_contract.py` schema) | Hash computed benchmark-side over existing envelope JSON; contract only supplies canonicalization rules |
| LLM sample repeat-mode driver (k=10, sample index) | API/Backend (`data-service/tests/recognition_eval/`, extended) | — | In-process adapter calls, same pattern as `live_sweep.py`; no new service boundary |
| Gateway provenance fields (served model, response id, fingerprint) | API/Backend (`data-service/llm_gateway.py`) | — | Additive fields on `GenerateResponse`; adapters already parse the raw provider JSON that carries these |
| Frozen rule-ingest prompt capture | API/Backend (one-off script or test fixture) | n8n workflow (read-only source) | Rendering happens once via the *repo's* `rules-to-metagraph.json` node + `/context/assemble`; result is frozen to disk, not re-rendered per sample |
| `spec/REPRODUCIBILITY.md` definition | Documentation / spec | — | New normative spec, sibling to `spec/SWRL-SUBSET.md`'s machine-checked-block pattern |
| Two-report artifact emission (JSON+MD x2) | Standalone tooling | — | Mirrors `tools/de01/report.py`'s existing dual-format emission, duplicated per D-24 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `subprocess`/`httpx` | httpx already pinned in `data-service/requirements.txt` | Fresh-process C# leg invocation; HTTP to data-service/dg-reasoner/adapters | Already the exclusive transport in `tools/de01/legs.py` and `llm_gateway.py` — no new dependency |
| `jsonschema` | already a data-service dependency (`evidence_contract.py` uses it) | Envelope schema validation before hashing | D-04 requires excluding fields *after* validating shape; reuse existing validator |
| pytest | already the project's Python test runner (`tools/de01/tests/test_de01_runner.py`, `data-service/tests/`) | Unit tests for the repeat-mode drivers, the sample-indexed cassette key, and the D-26 drift test | Established convention; no reason to introduce a second Python test framework |
| xUnit (.NET) | already `DG.Tests.csproj`'s framework | Any C#-side test the D-05 fresh-process-per-iteration harness needs (none expected — the C# leg is already fresh-process-per-invocation, `legs.py:680-694`) | Matches existing `DG.Tests` convention |

No new third-party package is required by this phase. **Package Legitimacy Audit is not
applicable** — see that section below for the explicit statement.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hashlib` (stdlib) | — | SHA-256 for both the D-04 verdict-projection hash and the D-21 cassette-key extension | Both hashing needs are already implemented this way in `canonical_json.py` and `cassette.py`; reuse the pattern, do not add a hashing library |
| `statistics`/hand-rolled Wilson interval | `data-service/tests/recognition_eval/scoring.py`'s existing `wilson_interval` | D-17's Wilson 95% CI on modal-agreement rate | Already shipped and referenced by name in CONTEXT.md D-17 — reuse verbatim, do not reimplement |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `tools/de01/legs.py` unmodified | A second, independent leg implementation | Rejected by D-01 — a second, drifting comparison is the exact defect class this milestone exists to remove |
| A Python-side cassette extension for k-sampling | A brand-new record/replay library (e.g. VCR.py) | Rejected: the existing hand-rolled cassette format (`cassette.py`) is already the frozen precedent (35-AI-SPEC.md §5); introducing a second serialization format for the same purpose would fragment provenance tooling |
| Requiring producers to emit `outputHash` | Changing `data-service/app.py` and the C# harness to compute and attach output hashes | Rejected by D-04's rationale — this pulls in propagation work owned by v11.0 Phase 1105, and changes production code under measurement (contradicts D-10's "measure as shipped") |

**Installation:** none required — every dependency is already present in
`data-service/requirements.txt` and `DG/tests/DG.Tests/DG.Tests.csproj`.

**Version verification:** No new packages are introduced by this phase (verified by inspection of
CONTEXT.md's discretion list and the existing `requirements.txt`/`.csproj` files). If the planner's
task decomposition later discovers a genuine new need (e.g. a CLI argument-parsing helper), verify
it the same way any other phase would (`pip index versions <pkg>`) before adding it.

## Package Legitimacy Audit

**Not applicable.** This phase installs no new external packages in any ecosystem. Every library
named above (`httpx`, `jsonschema`, `pytest`, xUnit) is already a committed dependency of this
repository, confirmed present in `data-service/requirements.txt` (httpx, jsonschema) and
`DG/tests/DG.Tests/DG.Tests.csproj` (xUnit), and already exercised by the exact modules this phase
reuses (`tools/de01/legs.py`, `data-service/evidence_contract.py`,
`data-service/tests/recognition_eval/`). The Package Legitimacy Gate protocol does not apply when a
phase adds zero new packages; there is nothing to run `package-legitimacy check` against.

**Packages removed due to SLOP verdict:** none (n/a — no packages checked).
**Packages flagged as suspicious [SUS]:** none (n/a — no packages checked).

## Architecture Patterns

### System Architecture Diagram

```
                    DETERMINISTIC HALF (repeat-mode DE-01)
┌──────────────────────────────────────────────────────────────────────────┐
│  tools/de01/run_de01_repeat.py  (new, imports legs.py + report.py)       │
│                                                                            │
│  for batch in [1, 2]:                       # D-05: >=2 fresh lifetimes  │
│    docker compose restart data-service dg-reasoner                       │
│    for i in range(N):                       # N=10 default               │
│      leg_results = { name: runner(fixture, config) for name in LEGS }    │
│         │                                                                 │
│         ├─→ csharp:      subprocess "dotnet run" (fresh process, always) │
│         ├─→ data-service: POST /validation/publish → GET .../view        │
│         ├─→ dg-reasoner:  POST /shacl/validate {project, run_id}         │
│         └─→ replay:       GET /validation/view/{project}/{PINNED_run_id} │
│                             (D-06: pinned, not "newest run")              │
│      projection_hash[i] = sha256(canonicalize(envelope minus D-04 excl.))│
│    compare projection_hash[*] within and across batches → N/N or FAIL    │
│  emit: deterministic-report.json + .md (D-24, D-07 config pins)          │
└──────────────────────────────────────────────────────────────────────────┘

                    LLM HALF (repeat-mode recognition + rule-ingest)
┌──────────────────────────────────────────────────────────────────────────┐
│  data-service/tests/recognition_eval/  (extended: sample-indexed keys)   │
│                                                                            │
│  frozen inputs (D-12):                                                    │
│    recognition: urbanblock_slice (32 blocks) + frame_ablated (31 blocks) │
│    rule-ingest: 5 rendered prompts (frozen once via repo's                │
│                 rules-to-metagraph.json "Build LLM Prompt" node +         │
│                 /context/assemble, sha256-pinned)                        │
│                                                                            │
│  for provider in reachable_providers:        # never pooled (D-13)       │
│    for item in frozen_inputs:                                            │
│      for k in range(10):                     # k=10, min 5 before rate  │
│        sample = adapter.generate(req, key, options)  # options=None for  │
│                                                        # rule-ingest (D-10)│
│        cassette.write(key=cassette_key(..., sample_index=k), sample)     │
│        classify(sample) → valid | valid_after_retry | invalid(code) |    │
│                            abstained | truncated | refused |              │
│                            provider_error                        (D-14)  │
│  aggregate per item: distinct outputs, modal-agreement rate, Wilson CI   │
│  assign reproducibility class per experiment: replayable |               │
│    re-executable-pinned-weights | not-reproducible-provider-managed(D-22)│
│  emit: llm-repeatability-report.json + .md (D-24, D-19 provenance block) │
└──────────────────────────────────────────────────────────────────────────┘

Both halves consult spec/REPRODUCIBILITY.md (new, D-25) for the shared vocabulary
(deterministic-measured / model-dependent / unmeasured) and never share a report file (D-24).
```

### Recommended Project Structure

```
tools/de01/
├── legs.py                       # UNCHANGED — reused verbatim (D-01)
├── report.py                     # UNCHANGED — compare_legs reused verbatim (D-01)
├── run_de01.py                   # UNCHANGED — existing single-pass CLI
├── run_de01_repeat.py            # NEW — repeat-mode wrapper (D-05 batches, D-06 pinned replay,
│                                  #        D-04 projection hash, D-08 gate)
├── projection_hash.py            # NEW — D-04 exclusion-list hashing, imports canonical_json
├── report_schema_repeat.json     # NEW — sibling schema for the deterministic repeat report
└── tests/
    └── test_repeat_runner.py     # NEW — unit tests incl. D-04's negative control

data-service/tests/recognition_eval/
├── cassette.py                   # EXTENDED — cassette_key gains sample_index (D-21)
├── corpus.py                     # UNCHANGED — frozen corpora reused as-is
├── arms.py                       # UNCHANGED — provider/arm resolution reused
├── live_sweep.py                 # PRECEDENT — new repeat driver modeled on this file's
│                                  #             record/replay/cost-tracking pattern
├── repeat_sweep.py               # NEW — k=10 sampling driver (D-13), recognition + rule-ingest
├── outcome_taxonomy.py           # NEW — D-14/D-15/D-16 classification (valid/invalid/.../abstained)
└── report.py                     # EXTENDED or sibling — D-17 per-item/two-level normalization,
                                   #                        D-19 provenance-void guard

fixtures/llm_repeatability/       # NEW sibling path (per 1200 D-11/1202 D-17 precedent)
├── rule_ingest_prompts/          # D-12 frozen, sha256-pinned rendered prompts (5 items)
│   ├── height-75.prompt.txt + .sha256 + .provenance.json
│   ├── ...v7-area, ...v7-separation, ...cq3-min-distance
└── cassettes/<arm_id>/<sample-indexed-key>.json   # D-21

spec/
└── REPRODUCIBILITY.md            # NEW — D-25, machine-checked scope table (D-26)

data-service/
└── llm_gateway.py                # EXTENDED — GenerateResponse gains optional
                                   #  served_model / response_id / system_fingerprint (D-20)
```

### Pattern 1: Fresh-process-per-iteration to expose hash-seed nondeterminism

**What:** Restart `data-service` and `dg-reasoner` containers between at least two batches of the
N=10 iterations, rather than looping N times inside one process lifetime.
**When to use:** Whenever a determinism claim depends on set/dict iteration order in a
long-lived Python process — CPython randomizes `str.__hash__` per process by default
(`PYTHONHASHSEED` unset), so `set` iteration order is stable *within* a process and can silently
mask a defect that only a fresh process reveals.
**Example (already-identified defect surface, `data-service/app.py`):**
```python
# data-service/app.py — _build_publish_evidence_envelope (confirmed on disk 2026-09-23)
seen_rule_ids = set(all_rule_ids) | failed_rule_ids | passed_rule_ids
for rule_id in seen_rule_ids:   # iteration order is PYTHONHASHSEED-dependent across processes
    ...
```
Ten warm iterations inside one already-started container never re-seed this hash — the repeat
driver's `docker compose restart` step is the only way to actually test whether iteration order
is stable *across* the seed randomization boundary.

### Pattern 2: Sample-indexed cassette key to make k > 1 sampling representable

**What:** Extend `cassette_key(...)` (or a new sibling function) to fold in an explicit
`sample_index` component so k identical-request samples produce k distinct cassette files instead
of overwriting one.
**When to use:** Any harness that needs to record real sampling variance (temperature > 0 or
provider-side nondeterminism) rather than a single canonical response.
**Example:**
```python
# Source: data-service/tests/recognition_eval/cassette.py (existing pattern, confirmed lines 69-99)
def cassette_key(*, provider, model, prompt_version, system, user_prompt,
                  temperature, negotiated_mode, max_tokens, sample_index=0) -> str:
    parts = [provider or "", model or "", prompt_version or "", system or "",
             user_prompt or "", "" if temperature is None else repr(float(temperature)),
             negotiated_mode or "", "" if max_tokens is None else str(int(max_tokens)),
             str(int(sample_index))]  # NEW: makes k samples of one request non-collidable
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
```
D-21 requires this key scheme extend, not replace, the existing one — a `sample_index=0` call must
remain byte-identical to today's key for the pre-existing Phase 35 cassettes to stay valid.

### Pattern 3: Benchmark-computed projection hash over an existing envelope (D-04)

**What:** Rather than asking a producer to emit `outputHash`, the benchmark itself canonicalizes
the already-returned envelope JSON (minus a closed exclusion list) and hashes that.
**When to use:** Whenever the artifact under test already has a canonical-JSON serializer
(`canonical_json.hash_canonical`) and the goal is to detect *any* byte-level drift across runs
without requiring the producer to change.
**Example:**
```python
# Source: tools/de01/projection_hash.py (new file, to be built on the existing
# data-service/canonical_json.py primitives — confirmed present, hash_canonical at line 180)
import canonical_json

_EXCLUDED_TOP_LEVEL = {"emittedAt"}
_EXCLUDED_REPORT_LEVEL = {"generatedAt"}
_RUN_DERIVED_FIELDS = {"definitionId"}   # Correction 3: data-service's definitionId == run_id

def verdict_projection_hash(envelope: dict) -> str:
    projected = {k: v for k, v in envelope.items()
                 if k not in _EXCLUDED_TOP_LEVEL and k not in _RUN_DERIVED_FIELDS}
    return canonical_json.hash_canonical(projected)
```
**Never call `canonical_json.hash_scalar_tuple`** for this projection — Correction 10 confirms it
still uses the naive pipe-join, which has diverged from the length-prefix encoding
`DgIdMintingService`/`compute_dg_id` adopted in Phase 1203 D-09. `hash_canonical` (the
nested-payload path) is unaffected by that divergence and is the correct function.

### Anti-Patterns to Avoid

- **Re-implementing a DE-01 leg inside the repeat driver:** D-01 forbids this outright — import
  `legs.run_leg_csharp` etc. directly, never re-shell to `dotnet run` from a second call site.
- **Re-POSTing to `/llm/generate` on every retry/sample:** both `cg_recognition.recognize_structure`
  and `dg_context.generate_validated_cypher` deliberately resolve the adapter once and call
  `adapter.generate()` in-process specifically to avoid re-reading settings mid-loop (confirmed in
  both files' docstrings). The new k-sampling driver must follow the same rule — resolve the
  adapter once per (provider, item) pair, then loop `adapter.generate()` k times.
- **Pinning `run_id="RUN_GOLD_1200"` as a string literal a second time:** the constant is
  `legs.FIXTURE_RUN_ID`; a new call site must import it, not re-hardcode it (this is exactly how
  the pre-D-09 dg-reasoner defect happened — a second, drifting copy of an identifier).
- **Sniffing on `canonicalStateHash` to detect the wrapper vs. bare-envelope C# harness shape:** the
  existing code deliberately sniffs on the top-level `"envelope"` key instead, because
  `canonicalStateHash` is `null` in the typed-absence case (`legs.py:792-818`). Any new code reading
  this harness output must follow the same sentinel.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-service canonical-JSON hashing | A second canonicalization routine for the projection hash | `data-service/canonical_json.hash_canonical` (Python) — no C# side needed since the projection hash is benchmark-side only | Already golden-vector-tested for cross-language parity; a second implementation risks silently diverging exactly like `hash_scalar_tuple` did (Correction 10) |
| Wilson confidence intervals | A hand-rolled binomial CI formula | `data-service/tests/recognition_eval/scoring.py`'s `wilson_interval` | Already used and tested for exactly this purpose (recognition M1's CI); D-17 names it explicitly |
| Cassette record/replay/live modes | A new VCR-style library | `data-service/tests/recognition_eval/cassette.py`'s `CassetteAdapter` | Frozen precedent (35-AI-SPEC.md §5); D-21 only extends its key, never replaces the mechanism |
| Retry-with-corrective-feedback loop | A new bounded-retry wrapper for LLM calls | The existing pattern in both `cg_recognition.recognize_structure` and `dg_context.generate_validated_cypher` (both `max_retries=2`, in-process adapter calls) | Both paths already implement exactly the retry shape D-15 needs to observe (first-attempt vs. final-attempt invalid rate) |
| DE-01 comparison classification | A new agreement/disagreement classifier | `tools/de01/report.py`'s `compare_legs` (`_DECLARABLE_STATUSES`, silent vs. declared) | D-01 mandates reuse; a second classifier is the exact defect class (drifting duplicate comparators) this milestone exists to eliminate |

**Key insight:** every piece of "hard" infrastructure this phase might be tempted to build already
exists, frozen, from Phases 1200–1203 and Phase 35. The actual new work is narrow: one dimension
(sample index) added to one existing key function, one small set of additive gateway fields, and
two new orchestration scripts that call existing functions in a loop with process restarts. Treat
any task that proposes rewriting `legs.py`, `compare_legs`, `canonical_json.py`, or
`cassette.py`'s core key scheme as a planning error — CONTEXT.md's decisions make all four
explicitly frozen inputs.

## Runtime State Inventory

**Not applicable — greenfield-within-phase benchmarking, not a rename/refactor/migration.** This
phase adds new sibling files and one additive gateway field set; it does not rename, move, or
reinterpret any existing identifier, key, or stored string. Confirmed: no `sed`-style global rename
is implied by any decision D-01 through D-28, and CONTEXT.md's own scope explicitly excludes fixing
what it measures (D-10) and excludes changing the frozen 1200 envelope (D-23). The Environment
Availability and Common Pitfalls sections below cover the actual operational risks instead.

## Common Pitfalls

### Pitfall 1: Treating a relay leg's echo as validator determinism

**What goes wrong:** Repeating the data-service and replay legs N times and reporting "N/N
identical" without labeling them as relay legs makes it look like the *validator* was proven
deterministic, when in fact the data-service leg constructs its verdict directly from the fixture's
own `expectedOutcomes` (`_fixture_entities_payload`, confirmed at `tools/de01/legs.py:301-357`) and
the replay leg reads back a persisted envelope that was itself just written from that same echo.
**Why it happens:** All four legs return the same `LegResult` shape, so nothing in the code
*visually* distinguishes an evaluator from a relay — the distinction is purely architectural
(D-02).
**How to avoid:** Every report row must carry an explicit `leg_role: evaluator | relay` column
(D-02's own instruction: "for example as a column on every leg row"). Never compute or report a
"validator repeatability" percentage that includes a relay leg's row.
**Warning signs:** A report claiming "4/4 legs agree, N/N repeatable" without a role column is the
exact overclaim this phase exists to prevent.

### Pitfall 2: The replay leg reading the newest run instead of a pinned run inside a repeat loop

**What goes wrong:** `run_leg_replay` calls `GET /validation/view/{project}` with no run id
(confirmed `legs.py:858`), which resolves to the newest run for the project. Inside a naive N-loop,
the data-service leg (which runs first per iteration and always publishes a fresh run) shadows
whatever the replay leg would have read from a *previous* iteration — iteration *i*'s replay leg
sees iteration *i*'s own data-service publish, not a genuinely independent read.
**Why it happens:** `run_leg_data_service` always runs immediately before `run_leg_replay` within
one `run_de01.py` invocation (documented at `legs.py:168-183`), and both target the same project.
**How to avoid:** D-06's fix — in repeat mode, call the pinned route
`GET /validation/view/{project}/{run_id}` instead, with `run_id` resolved once, before the loop
starts, and held fixed across all N iterations. **Planner must verify which literal run id that
route actually resolves** given the `:Run{Run_Id}` vs `:ValidationRun{runId}` label/property drift
documented at `fixtures/golden/replay/seed-replay.cypher:249-251` — do not assume
`RUN_GOLD_1200` resolves without checking live.
**Warning signs:** A repeat-mode replay leg whose envelope hash changes identically in lockstep
with the data-service leg's hash every iteration — that is the shadowing bug, not genuine
nondeterminism.

### Pitfall 3: dg-reasoner needs `run_id`, and repeat mode must not silently omit it

**What goes wrong:** Without `run_id`, `dg-reasoner/reasoning.py::run_shacl` validates only the
project-level Metagraph/OntoGraph export, never the run's ValidGraph ABox — this was the root
cause of a whole-phase-long false `no_population` result before Phase 1201 D-09 fixed it. A repeat
driver that reuses `run_leg_dg_reasoner` unmodified is safe (the fix is already in `legs.py:375-426`
via `FIXTURE_RUN_ID` fallback), but a *new*, hand-rolled dg-reasoner call site for the repeat driver
would silently reintroduce the exact defect this phase's own precedent phase spent effort fixing.
**Why it happens:** the omission is easy — `{"project": project}` alone is a syntactically valid,
silently-wrong request body.
**How to avoid:** Only call `dg-reasoner` through `legs.run_leg_dg_reasoner`, never construct the
POST body independently.
**Warning signs:** `conforms: true` with zero findings on every iteration is the historical symptom
— it means the seed was not applied or the run id did not resolve, not that the population is
genuinely empty (see the leg's own extensive docstring at `legs.py:394-421`).

### Pitfall 4: Stale Docker images masking the code actually under test

**What goes wrong:** `docker compose` reuses cached image layers; a live DE-01 run can silently
exercise pre-change code while the report claims to measure the current commit. This already
happened once at Phase 1200 (plan 1200-08 had to rebuild a stale `data-service` image mid-plan).
**Why it happens:** `docker compose up -d` without `--no-cache`/`--build` does not automatically
detect that source files changed since the image was last built.
**How to avoid:** Before every live run (both deterministic-half restarts and LLM-half live
provider calls), verify the running container's code matches the commit under test — e.g. `docker
compose build --no-cache data-service dg-reasoner` before `docker compose up -d`, and record the
image id (D-07 already requires pinning this).
**Warning signs:** A report whose git commit SHA in the D-07 configuration pin does not match
`docker inspect`'s image creation timestamp relative to that commit's timestamp.

### Pitfall 5: Reporting a "reproducibility score" that pools providers or subjects

**What goes wrong:** Averaging modal-agreement rate across providers, or across recognition and
rule-ingest, produces a single number that hides exactly the comparison this phase exists to make
visible (recognition: pinned temperature, has abstention; rule-ingest: unpinned, no abstention
channel).
**Why it happens:** A single score is easier to headline than a disaggregated table.
**How to avoid:** D-17 explicitly forbids pooling: "There is no pooled 'reproducibility score'
across items, subjects or providers." Every reported number must carry its (subject, provider, item)
triple.
**Warning signs:** Any report section titled simply "Reproducibility: X%" without a subject/provider
qualifier next to it.

### Pitfall 6: Confusing "temperature 0" with "deterministic"

**What goes wrong:** Recognition pins `temperature=0.0` (confirmed `cg_recognition.py:1053-1057`,
and again in the provenance-stamping helper `_log_attempt` at line ~954), which is necessary but
not sufficient for determinism — provider-side batching, MoE routing, and kernel nondeterminism
still introduce jitter even at temperature 0 (already documented precedent:
`35-AI-SPEC.md:1521-1523`, "replay is exactly reproducible... [live] still not... batching and MoE
routing still introduce jitter").
**Why it happens:** "Temperature 0" sounds like "deterministic" colloquially.
**How to avoid:** D-25 requires `spec/REPRODUCIBILITY.md` to state this explicitly as a non-claim:
"temperature 0 is not determinism." Any report language must distinguish "near-deterministic" from
"deterministic" and reserve the word "deterministic" for the validator half only (per the phase's
own "deterministic must become expensive to say" framing).

### Pitfall 7: `MSYS_NO_PATHCONV` omission breaking `docker exec`/`docker cp` under Git Bash

**What goes wrong:** Any live-run task that shells `docker exec`/`docker cp` with a path argument
(e.g. copying a report out of a container, or invoking a script inside one) can have that path
silently rewritten by Git Bash's POSIX-path translation, sometimes failing without a clear error.
**Why it happens:** documented project-level gotcha (memory: "docker exec paths need
MSYS_NO_PATHCONV").
**How to avoid:** Prefix such commands with `MSYS_NO_PATHCONV=1` when running under Git Bash on
Windows, exactly as the project's existing tooling does elsewhere.
**Warning signs:** A `docker exec` command that "succeeds" (exit 0) but the expected file is absent
or the container-side path looks wrong (e.g. `//app/...` doubled-slash artifacts).

## Code Examples

### Repeat-mode outer loop shape (deterministic half)

```python
# Source: pattern to build in tools/de01/run_de01_repeat.py, composing existing
# tools/de01/legs.py + tools/de01/report.py (both unchanged, per D-01)
import subprocess
from legs import (
    run_leg_data_service, run_leg_dg_reasoner, run_leg_csharp, run_leg_replay, FIXTURE_RUN_ID,
)
from report import compare_legs
from projection_hash import verdict_projection_hash  # new, Pattern 3 above

N_PER_BATCH = 5   # 2 batches x 5 = N=10 default (D-05)
BATCHES = 2

def restart_python_services() -> None:
    subprocess.run(["docker", "compose", "restart", "data-service", "dg-reasoner"],
                    check=True, timeout=120)

all_hashes: dict[str, list[str]] = {"data-service": [], "dg-reasoner": [], "csharp": [], "replay": []}
for batch in range(BATCHES):
    restart_python_services()  # D-05: fresh process lifetime per batch, not per iteration
    for _ in range(N_PER_BATCH):
        leg_results = {
            "data-service": run_leg_data_service(fixture, config),
            "dg-reasoner": run_leg_dg_reasoner(fixture, config),
            "csharp": run_leg_csharp(fixture, config),          # already fresh dotnet-run per call
            "replay": run_leg_replay_pinned(fixture, config, run_id=FIXTURE_RUN_ID),  # D-06 variant
        }
        for name, result in leg_results.items():
            all_hashes[name].append(verdict_projection_hash(result.envelope))

# D-08 gate: every leg's hash list must contain exactly one distinct value
gate_passed = all(len(set(hashes)) == 1 for hashes in all_hashes.values())
```

### D-06 pinned-replay variant

```python
# Source: additive sibling to run_leg_replay (legs.py:835-989), NOT a modification —
# the default single-pass run_de01.py behavior must stay byte-identical (D-06: "additive flag")
def run_leg_replay_pinned(fixture, config, run_id: str):
    base_url = config.get("data_service_url", "http://localhost:8000")
    project = fixture["project"]
    # Uses the EXISTING route already present in data-service/app.py
    # (GET /validation/view/{project}/{run_id} — the same one run_leg_data_service
    # already calls at legs.py:230), just with a caller-supplied fixed run_id
    # instead of reading back whatever /validation/publish just minted.
    ...
```

### D-20 additive gateway fields (illustrative shape, exact field names at planner's discretion)

```python
# Source: data-service/llm_gateway.py — GenerateResponse currently (confirmed, lines 47-72):
class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str          # Correction 5: this is req.model (REQUESTED), not what the provider served
    usage: dict
    truncated: bool = False
    finish_reason: str | None = None
    # D-20 additions (additive, optional, populated only from what each provider actually returns):
    served_model: str | None = None       # e.g. Anthropic/OpenAI response body's own "model" field
    response_id: str | None = None        # Anthropic "id", OpenAI "id"
    system_fingerprint: str | None = None # OpenAI-only; None elsewhere
```
Each adapter's `.generate()` (Anthropic `:372-425`, OpenAI `:449-514`, Ollama `:538-586`) already
parses `data = resp.json()` and currently discards everything except `content`/`choices`/`response`
and `usage` — the D-20 fields are read from data already sitting in that same parsed dict, not from
a new API call.

### D-12 frozen rule-ingest input rendering (one-off script pattern)

```python
# Source: pattern for a new one-off script, reusing the LIVE repo endpoints exactly
# once per rule, per D-12 — never re-assembled per k-sample
import httpx
resp = httpx.post(f"{base_url}/context/assemble",
                   json={"type": "rule_ingest", "project": seeded_project})
context = resp.json()
# then render through the repo's OWN n8n "Build LLM Prompt" function-node logic
# (n8n/workflows/rules-to-metagraph.json, confirmed node present, id "3"),
# reimplemented in Python ONLY to the extent of string-joining context + rule text —
# freeze the OUTPUT (the rendered prompt string), with its own sha256 and the
# assemble response's sha256, to fixtures/llm_repeatability/rule_ingest_prompts/.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single-pass DE-01 (`run_de01.py`), no repeatability claim | Repeat-mode DE-01 with N=10 across >=2 process lifetimes, projection hash | This phase (1204) | First point at which "deterministic" becomes a measured, falsifiable claim rather than an assumption |
| `GenerateResponse.model` = requested model id only | Additive served-model/response-id/fingerprint fields (D-20) | This phase | Makes a provider-side silent model alias re-point detectable, which the current gateway cannot see at all |
| Cassette key with no sample dimension (identical requests overwrite) | Sample-indexed cassette key (D-21) | This phase | First point k > 1 samples of one request become representable at all |
| No `spec/REPRODUCIBILITY.md` | New normative spec defining `deterministic-measured` / `model-dependent` / `unmeasured` | This phase | v10.0 and v11.0 SPEC-04 gain a boundary contract to cite instead of an assumed, undocumented one |

**Deprecated/outdated:**
- Treating "N/N identical across a warm loop" as evidence of determinism: superseded by D-05's
  fresh-process-restart requirement, because Python's hash-seed randomization is invisible within
  one process lifetime.
- Treating a relay leg's echo-based agreement as validator repeatability: superseded by D-02's
  evaluator/relay classification.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DeepSeek (via the OpenAI adapter with a custom `base_url`) will be the only reachable live provider at execution time, mirroring Phase 35-15's measured configuration | LLM subjects and sampling (context, not authored here) | If a frontier-provider key becomes available before execution, the LLM report gains a second provider column "for free" but the plan's task estimate for "at least one live provider" should not assume DeepSeek-only is the ceiling |
| A2 | `GET /validation/view/{project}/{run_id}` (the route D-06 repurposes for pinned replay) resolves correctly against the seeded `RUN_GOLD_1200`/`:Run` node despite the documented `:Run` vs `:ValidationRun` label/property drift | Common Pitfalls, Pitfall 2 | If the route actually expects a `:ValidationRun{runId}` match and the seeded fixture only carries `:Run{Run_Id}`, the pinned-replay call will 404 and the planner must add a task to resolve/document the drift before D-06 can be implemented as designed — CONTEXT.md itself already flags this as unresolved ("Planner must verify") |
| A3 | No CI pipeline exists in this repository (confirmed by `tools/de01/README.md`'s own "No CI pipeline" section) still holds true at planning time | Validation Architecture | If a CI pipeline has since been added, the sampling-cadence guidance below should route through it instead of purely manual/local invocation |

**If this table is empty:** N/A — see above; all three entries above were themselves verified
against disk in this session except A1 (which reports a fact about future execution-time
environment, not a code claim) and the CONTEXT.md-inherited A2 (already flagged as an open
verification item there, restated here for planner visibility).

## Open Questions

1. **Does `GET /validation/view/{project}/{run_id}` actually resolve `RUN_GOLD_1200` given the
   `:Run{Run_Id}` vs `:ValidationRun{runId}` drift?**
   - What we know: `fixtures/golden/seed.cypher` writes a `:Run {Run_Id: 'RUN_GOLD_1200'}` node
     (per `legs.py:41-47`'s own comment); the auto-validation path writes `:ValidationRun{runId}`
     instead; `fixtures/golden/replay/seed-replay.cypher:249-251` documents this pre-existing
     divergence.
   - What's unclear: which label/property shape the `/validation/view/{project}/{run_id}` route's
     underlying Cypher actually matches against — this determines whether D-06's pinned-replay
     variant works against the frozen golden fixture out of the box or needs a documented
     workaround.
   - Recommendation: the planner should schedule this as an early, cheap verification task (a
     single live query against the seeded project) before writing the full repeat-mode replay
     wrapper, so the wrapper's contract (what run id format it accepts) is settled first.

2. **What exact field names does D-20 use for the gateway's additive fields?**
   - What we know: CONTEXT.md leaves this to planner discretion ("Field names for the D-20 gateway
     additions").
   - What's unclear: nothing blocking — purely a naming choice.
   - Recommendation: `served_model`, `response_id`, `system_fingerprint` (used illustratively above)
     read clearly and avoid collision with the existing `model` field's semantics; the planner may
     adopt these or choose others, documenting the choice in `spec/API.md` per D-20's own
     requirement.

3. **Should the repeat-mode deterministic driver be a new file or a `--repeat` flag on
   `run_de01.py`?**
   - What we know: CONTEXT.md explicitly leaves this to discretion ("Runner location and naming").
   - What's unclear: nothing blocking.
   - Recommendation: a new sibling file (`run_de01_repeat.py`) rather than a flag on the existing
     CLI — the repeat-mode driver needs a materially different argument surface (batch count,
     restart command, pinned run id) that would clutter the single-pass CLI's simple contract, and
     a separate file makes the D-01 "reused, not reimplemented" import relationship visually
     obvious (`from legs import ...` at the top, exactly like `run_de01.py` and
     `tools/de01/tests/test_de01_runner.py` already do).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose stack (`data-service`, `dg-reasoner`, `neo4j`) | Deterministic-half live run (3 of 4 legs) | Not verified this session (research is read-only; live-run verification is a phase-execution-time human checkpoint per D-28) | — | None — D-27 states "if no live provider is reachable... the phase gate cannot pass"; the analogous statement holds for the deterministic half needing the compose stack |
| `dotnet` SDK on host or in a runnable context | `csharp` leg (`DG.De01Harness`) | Not verified this session | — | None documented; `tools/de01/README.md` states this is a hard precondition |
| Live LLM provider API key (Anthropic/OpenAI/DeepSeek-via-OpenAI-adapter/Ollama) | LLM-half sampling (D-13, D-27) | Not verified this session — entered only via the LLMSettingsPanel/`/llm/settings`, never read from `.secrets/` per CLAUDE.md's DSH rule and D-28 | — | Ollama fallback exists if a local model is pulled (D-13); if literally zero providers reachable, "the LLM half is incomplete and the phase gate cannot pass" (D-27) — no other fallback |
| CI pipeline | Automated sampling cadence | Confirmed absent (`tools/de01/README.md`'s own "No CI pipeline" section, re-verified this session) | — | Manual/local invocation via the documented pytest `-k "not live"` / `-k "live"` split; the same split should extend to the new repeat-mode tests |

**Missing dependencies with no fallback:**
- A reachable live LLM provider is a hard gate per D-27 — if none is configured at execution time,
  the LLM-half report is incomplete by design and the phase cannot close.

**Missing dependencies with fallback:**
- Local Ollama (if a model is pulled) covers the "at least one provider" floor when no cloud key is
  configured, and is additionally the only provider exposing a weights digest (D-13), which is
  needed for the `re-executable-pinned-weights` reproducibility class (D-22).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python side, `tools/de01/tests/`, `data-service/tests/`); xUnit (.NET side, `DG/tests/DG.Tests/`) |
| Config file | none dedicated — no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section found in this repo; tests are invoked directly by path, matching the existing convention in `tools/de01/README.md` |
| Quick run command | `python -m pytest tools/de01/tests/test_de01_runner.py -x -q -k "not live"` (existing); new: `python -m pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"` |
| Full suite command | `python -m pytest tools/de01/tests/ -x -q` plus, for the LLM half, `python -m pytest data-service/tests/recognition_eval/ data-service/tests/test_llm_gateway.py -x -q`; C# side: `dotnet test DG/tests/DG.Tests/` |

### Phase Requirement → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-15 (deterministic half) | N=10 across >=2 process restarts produces N/N identical projection hashes, with a negative control proving the hash detects a mutated status | unit | `pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"` | ❌ Wave 0 — new file |
| ALGN12-15 (deterministic half, live gate) | Live run against the actual compose stack reaches `silent_disagreement_count = 0` and the D-08 gate (N/N identical) | integration / human checkpoint | `python tools/de01/run_de01_repeat.py` (manual invocation against a live stack) | ❌ Wave 0 — new file; **human checkpoint per D-28**, mirrors 1201-06/1202-07/1203-06 |
| ALGN12-15 (LLM half) | Outcome taxonomy correctly classifies valid/valid_after_retry/invalid(+code)/abstained/truncated/refused/provider_error from a sample | unit | `pytest data-service/tests/recognition_eval/test_outcome_taxonomy.py -x -q` (new) | ❌ Wave 0 — new file |
| ALGN12-15 (LLM half, sampling) | k=10 samples per item per provider recorded under distinct sample-indexed cassette keys; modal-agreement rate + Wilson CI computed correctly | unit (cassette-key math) + human checkpoint (live sampling) | `pytest data-service/tests/recognition_eval/test_cassette.py -x -q -k "sample_index"` (extend existing test file) | Partial — `cassette.py` exists; sample-index tests are new |
| ALGN12-16 | Every recorded sample carries a complete D-19 provenance block; a sample missing any required field is void | unit | `pytest data-service/tests/recognition_eval/test_provenance.py -x -q` (new, modeled on the existing `assert_provenance` in `corpus.py`) | ❌ Wave 0 — new file, but the pattern (`REQUIRED_PROVENANCE_FIELDS`, `assert_provenance`, `ProvenanceError`) already exists in `data-service/tests/recognition_eval/corpus.py` and should be extended, not duplicated |
| ALGN12-16 | D-20 gateway additive fields (served model, response id, fingerprint) populate correctly per adapter, and omission when the provider doesn't return them is `None`, not a synthesized guess | unit | `pytest data-service/tests/test_llm_gateway.py -x -q -k "served_model or response_id or fingerprint"` (extend existing file) | Partial — `test_llm_gateway.py` exists (`TestGenerate` class confirmed at line 232) |
| D-26 | Machine-checked scope table in `spec/REPRODUCIBILITY.md` stays in sync with actual `get_adapter(`/`adapter.generate(` call sites in `data-service/` | unit (drift test) | `pytest tools/de01/tests/test_reproducibility_scope_drift.py -x -q` (new, modeled on `spec/SWRL-SUBSET.md`'s existing drift-guard pattern) | ❌ Wave 0 — new file; confirmed call-site counts to enumerate: `app.py` (6), `cg_recognition.py` (5), `dg_context.py` (10), `cg_input_generation.py` (4) — **any new call site added by a future phase must appear in this count or the drift test fails** |

### Sampling Rate

- **Per task commit:** run the relevant `-k "not live"` unit subset (fast, no live services, no
  API cost) after every task that touches `projection_hash.py`, the extended `cassette.py`, the
  new outcome-taxonomy module, or the D-20 gateway fields.
- **Per wave merge:** run the full non-live suite (`pytest tools/de01/tests/ -x -q` +
  `pytest data-service/tests/recognition_eval/ data-service/tests/test_llm_gateway.py -x -q` +
  `dotnet test DG/tests/DG.Tests/`) before merging a wave that includes both deterministic-half and
  LLM-half changes.
- **Phase gate:** both live human checkpoints (D-28: the deterministic-half compose-stack run, and
  the LLM-half live-provider sampling run) must complete and produce their respective reports before
  `/gsd-verify-work` — this mirrors the 1201-06/1202-07/1203-06 precedent exactly. The phase cannot
  close on unit tests alone because D-27's gate is explicitly "at least one live provider... if no
  live provider is reachable at execution time, the LLM half is incomplete and the phase gate cannot
  pass."

### Wave 0 Gaps

- [ ] `tools/de01/projection_hash.py` — D-04's exclusion-list hashing; no existing file computes
      this today (confirmed: neither `data-service/app.py` nor the C# harness populates
      `outputHash`, per Correction 2).
- [ ] `tools/de01/run_de01_repeat.py` + `tools/de01/tests/test_repeat_runner.py` — the N-iteration,
      multi-batch driver and its unit tests (including the D-04 negative control).
- [ ] `tools/de01/report_schema_repeat.json` — sibling schema for the deterministic repeatability
      report (D-24: must not reuse `tools/de01/report_schema.json` verbatim, since the repeat report
      carries per-iteration hash lists the single-pass schema has no field for).
- [ ] Sample-indexed extension to `data-service/tests/recognition_eval/cassette.py`'s
      `cassette_key` + `data-service/tests/recognition_eval/test_cassette.py` coverage for it.
- [ ] `data-service/tests/recognition_eval/repeat_sweep.py` (or equivalent) — the k=10 sampling
      driver for both recognition and rule-ingest, modeled on `live_sweep.py`'s
      record/replay/cost-tracking pattern.
- [ ] `data-service/tests/recognition_eval/test_outcome_taxonomy.py` — new file covering D-14/D-15/
      D-16's classification logic.
- [ ] `data-service/tests/recognition_eval/test_provenance.py` (or an extension of the existing
      provenance assertions in `corpus.py`) — D-19's complete-provenance-or-void rule for LLM
      samples.
- [ ] `fixtures/llm_repeatability/rule_ingest_prompts/` — the five frozen, sha256-pinned rendered
      prompts D-12 requires (does not exist yet; the source rules do —
      `fixtures/golden/fixture.json`'s height rule, `test/fixture_rules_v7.txt`'s three rules
      confirmed present, and `fixtures/golden/cq3-attribute-of/` confirmed present with
      `expected-cq3.json`/`seed-cq3.cypher`).
- [ ] `spec/REPRODUCIBILITY.md` + its D-26 machine-checked fenced block and drift test — does not
      exist yet.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new authentication surface; it consumes the existing LLMSettingsPanel/`/llm/settings` credential flow unchanged |
| V3 Session Management | No | Not applicable — no new session concept introduced |
| V4 Access Control | No | Not applicable — benchmark tooling runs locally/CI-adjacent, not a new externally-reachable endpoint |
| V5 Input Validation | Yes | The rule-ingest frozen prompts and recognition corpora are read-only fixture inputs; no new user-supplied input surface is created. The D-20 gateway fields are populated from provider *response* JSON, not request input — still validate defensively (e.g. `.get(...)` with `None` default, never assume a key is present) since providers are an external, only-partially-trusted boundary |
| V6 Cryptography | No new surface | Provider API keys continue to flow exclusively through the existing Fernet-based encryption in `llm_gateway.py` (`encrypt_value`/`decrypt_value`, `_derive_key`); this phase must never construct a second path to the plaintext key |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Provenance artifact (report JSON/MD, cassette file) accidentally containing a plaintext API key, full endpoint URL with embedded credentials, or full raw prompt/response body from a third-party corpus | Information Disclosure | D-19 explicitly requires "the adapter, and the endpoint **host** — never the API key, and never a URL carrying credentials"; the existing `cassette.py` convention already gates full prompt-body storage behind `ip_class == "own"` — extend that same gate, never store credentials, and reuse `llm_gateway.mask_key()` if any key-adjacent string must appear in a log line at all |
| A committed cassette or provenance report silently leaking a `.secrets/`-sourced value because a worker/task read that directory | Information Disclosure | CLAUDE.md's DSH rule and D-28 both state provider keys enter *only* through the LLM settings panel / `/llm/settings`; no task in this phase should ever `cat` or reference `.secrets/` contents, and any DSH-delegated subtask brief must explicitly exclude it |
| A live-run task inadvertently committing an artifact containing an unmasked key because a report-writer serializes the full settings object instead of the masked `LLMSettingsResponse` shape | Tampering / Information Disclosure | Any new provenance-block emitter must construct its own minimal DTO (adapter name + host + requested/served model + hashes) rather than serializing `settings` or `LLMSettingsPayload` wholesale — mirror the existing `get_llm_settings_response()` masking discipline |

## Sources

### Primary (HIGH confidence — verified on disk 2026-09-23 in this session)
- `tools/de01/legs.py` — all four leg adapters, `_fixture_entities_payload` (Correction 1),
  `FIXTURE_RUN_ID` (Correction 4), C#-leg wrapper-shape sniffing, replay-leg newest-run read
- `tools/de01/report.py` — `compare_legs`, `_DECLARABLE_STATUSES`, `generatedAt`
- `tools/de01/run_de01.py` — existing CLI shape, `--replay-fixture` precedent for D-06-style
  additive flags
- `tools/de01/README.md` — per-leg preconditions, "No CI pipeline" section, acceptance rule
- `data-service/llm_gateway.py` — `GenerateResponse`/`GenerationOptions` models, three adapters'
  `.generate()` bodies (Correction 5: `model=req.model` on every adapter's return), `get_adapter`,
  `resolve_active_provider`, encryption utilities
- `data-service/evidence_contract.py` — `CanonicalStatus`, `_ROLLUP_PRECEDENCE`, `build_envelope`
  (confirms `definitionId` is a required, freely-set parameter — Correction 3's mechanism)
- `data-service/canonical_json.py` — `hash_scalar_tuple` (Correction 10, still pipe-joined) vs.
  `canonicalize`/`hash_canonical` (nested-payload path, unaffected by the divergence)
- `data-service/cg_recognition.py` — `temperature: 0.0` pin (line ~954 log helper, ~1053-1057
  request construction), provenance stamping (`merged["provider"]`/`merged["model"]`), retry
  structure, `unrecognized[]`/G6/G10 handling
- `data-service/dg_context.py` — `validate_cypher`'s 10 confirmed unique violation codes,
  `generate_validated_cypher`'s no-`options` call (Correction 5 confirmed at the call site)
- `data-service/tests/recognition_eval/cassette.py` — `cassette_key`'s eight-part pipe-join
  (Correction 7 confirmed: no sample-index component)
- `data-service/tests/recognition_eval/corpus.py` — `REQUIRED_PROVENANCE_FIELDS`,
  `assert_provenance`, `assert_context_unchanged` (existing provenance-enforcement precedent)
- `data-service/tests/recognition_eval/report.py` — `wilson_interval` usage confirmed
- `DG/tools/DG.De01Harness/Program.cs` — confirmed `inputHash` only, no `outputHash` (Correction 2)
- `n8n/workflows/rules-to-metagraph.json` — "Build LLM Prompt" function node (id "3") and the
  `/context/generate-cypher` call (confirms D-12's rendering source)
- `fixtures/golden/fixture.json` — confirmed contents (rule, 4 atoms incl. the `ObjectPropertyAtom`
  non-result, 3 objects, expectedOutcomes) — the D-12 "one rule, both halves" input
- `fixtures/golden/cq3-attribute-of/` — confirmed present (`expected-cq3.json`, `seed-cq3.cypher`,
  `README.md`)
- `test/fixture_rules_v7.txt` — confirmed present with the exact three D-12 rule texts
- `spec/evidence-contract.schema.json` — confirmed `provider`/`model` optional string fields,
  `additionalProperties: false`
- `.planning/config.json` — confirmed `workflow.nyquist_validation` key absent (treat as enabled)
- `.planning/phases/1204-.../1204-CONTEXT.md` and `1204-DISCUSSION-LOG.md` — all 28 decisions and
  11 upstream corrections (D-01 through D-28; Corrections 1-11)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` — phase scope, gate
  wording, requirement IDs ALGN12-15/ALGN12-16, GATE12-03 dependency

### Secondary (MEDIUM confidence)
- `.planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-AI-SPEC.md` — E9
  reproducibility/provenance section (confirmed present at line 1391), cited as the D-19 model;
  read via grep excerpt, not full-file read, so surrounding context beyond the matched lines is
  inferred from CONTEXT.md's own citation rather than independently re-verified line-by-line
- graphify query results (BFS depth=2 over `data-service (FastAPI)`, `llm_gateway.py`,
  `cg_recognition.py`-area nodes) — used for orientation per the mandatory hook; confirmed file
  locations matched what CONTEXT.md already specified, no new facts discovered beyond disk reads

### Tertiary (LOW confidence)
- None — no unverified web-search-only claims were used in this research; the phase is entirely
  internal-codebase research with no external library/API dependency to look up.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; every named library already confirmed present and
  in active use in the exact files this phase reuses.
- Architecture: HIGH — every architectural claim (leg roles, call-site counts, existing patterns)
  was independently re-verified against current file contents in this session, not merely
  transcribed from CONTEXT.md.
- Pitfalls: HIGH — all seven pitfalls are grounded in code read directly in this session (not
  inferred), each with a specific confirmed line reference.

**Research date:** 2026-09-23
**Valid until:** 30 days (stable, internal-codebase research; the only fast-moving external
dependency — provider API behavior/availability — is explicitly measured live at execution time
per D-13/D-27, not assumed from this research).

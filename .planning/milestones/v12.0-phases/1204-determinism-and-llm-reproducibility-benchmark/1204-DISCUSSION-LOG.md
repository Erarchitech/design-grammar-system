# Phase 1204: Determinism and LLM Reproducibility Benchmark - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 1204-determinism-and-llm-reproducibility-benchmark
**Areas discussed:** Deterministic subjects; Repetition protocol and hashing; LLM subjects and sampling; Outcome taxonomy and metrics; Provenance snapshot and reproducibility class; Artifacts, contract and gate

**Mode:** The user instructed *"1204 обсуди все темы и прими все рекомендуемые решения
самостоятельно"* (discuss all topics and accept all recommended decisions yourself). All six
areas were auto-selected. Claude chose the recommended option for every question, without
AskUserQuestion, and in a single pass. The discussion did **not** auto-advance to planning, because
the user asked only for discussion.

**Pre-discussion scouting** changed the option set. Eleven disk facts are recorded in CONTEXT.md
`<upstream_corrections>`. The two that shaped the recommendations most:

- DE-01's data-service leg **echoes the fixture's `expectedOutcomes`** rather than evaluating the
  rule.
- **No leg produces an output hash.**

---

## Deterministic subjects

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse DE-01 legs on committed golden fixtures | Import `tools/de01` legs and `compare_legs`; golden + replay fixtures | ✓ |
| New dedicated deterministic harness | Separate runner re-implementing each validator call | |
| Include every deterministic path | Add `cg_structure_checks`, HermiT, Tier-0 | |

**Choice:** reuse DE-01 (D-01), and classify each leg as evaluator or relay (D-02). Other paths are
declared `unmeasured` (D-03).
**Notes:** Correction 1 forced the evaluator/relay split. Reporting a fixture echo as "validator
repeatability" would be the overclaim the phase exists to prevent.

## Repetition protocol and hashing

| Option | Description | Selected |
|--------|-------------|----------|
| Benchmark-computed projection hash, closed exclusion list | Hash canonical JSON of each envelope minus named volatile fields | ✓ |
| Require producers to populate `outputHash` | Change data-service and C# harness to emit output hashes | |
| Compare statuses only, no hash | Status equality per row | |
| N warm iterations in one process | Simple loop | |
| N split across ≥2 fresh process lifetimes | Restart Python services between batches | ✓ |
| Replay leg reads newest run | Current DE-01 behavior | |
| Replay leg reads pinned run id in repeat mode | Additive flag | ✓ |

**Choice:** D-04 through D-08:

- N = 10;
- one divergence fails the gate, and nothing is averaged;
- a negative control proves the hash detects change;
- the execution configuration is pinned, including container image ids.

**Notes:**

- *Producer hashes.* Changing producers was rejected because it pulls in propagation owned by
  v11.0 1105.
- *Warm-only iterations.* These were rejected because Python's per-process hash randomization
  (`app.py:2327` set iteration) is invisible inside one process.

## LLM subjects and sampling

| Option | Description | Selected |
|--------|-------------|----------|
| Recognition only | The one path with abstention, pinned temperature, and provenance | |
| Rule-ingest only | The path PAPER-C-003 names; uncontrolled temperature | |
| Recognition (primary) + rule-ingest (secondary) | Spans the controlled and uncontrolled paths | ✓ |
| All LLM paths incl. consult, input generation | Maximal coverage | |
| Measure shipped configuration | No production sampling change | ✓ |
| Pin temperature before measuring | Fix, then measure | |
| Live `/context/assemble` per sample | Rendered from live graph | |
| Frozen rendered prompts | Rendered once, sha256-pinned | ✓ |

**Choice:** D-09 through D-13:

- k = 10 per item per provider, with a minimum of 5 samples before any rate is reported;
- every reachable provider is measured, and providers are never pooled;
- consult and input generation are declared unmeasured.

**Notes:**

- *Input generation and consult.* Rejected as subjects for now: the input-generation cassettes are
  synthetic, and consult has no record mode.
- *Pinning temperature first.* Rejected: it would change the production path under measurement.

## Outcome taxonomy and metrics

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse canonical verdict statuses for LLM samples | `passed`/`failed`/… for proposals | |
| Separate proposal-outcome taxonomy | valid / valid_after_retry / invalid / abstained / truncated / refused / provider_error | ✓ |
| Final-attempt invalid rate only | What callers see | |
| First-attempt and final invalid rates | Exposes what the retry loop hides | ✓ |
| Heuristic abstention detection | Classify free text | |
| Explicit-channel abstention only | Recognition `unrecognized[]`; ingest "not supported" | ✓ |
| Single reproducibility score | One number | |
| Per-item, two normalization levels, Wilson CI | No pooling | ✓ |
| Include accuracy vs expected labels | M1 / expert labels | |

**Choice:** D-14 through D-18.
**Notes:** Accuracy was excluded because the paper disclaims interpretation accuracy, and because
recognition M1 is gated by Phase 35/40 (GATE12-04).

## Provenance snapshot and reproducibility class

| Option | Description | Selected |
|--------|-------------|----------|
| Record requested model id only | No gateway change | |
| Additive served-model / response-id / fingerprint fields | Optional `GenerateResponse` fields | ✓ |
| Complete provenance block, void if incomplete | Mirrors Phase 35 E9 | ✓ |
| Cassettes keyed by request digest | Existing scheme (k samples collide) | |
| Cassettes keyed with sample index | Extends existing scheme | ✓ |
| Per-experiment reproducibility class | replayable / re-executable-pinned-weights / not-reproducible-provider-managed | ✓ |
| Persist provenance on all production LLM writes | Production-wide | |
| Add prompt/temperature fields to evidence envelope | Change frozen 1200 contract | |

**Choice:** D-19 through D-23. D-22 answers milestone open question #10.
**Notes:** The additive gateway fields are needed because today the gateway reports the
**requested** model. Without them, an alias that the provider re-points is invisible, and
ALGN12-16's "explain why not reproducible" could only be asserted.

## Artifacts, contract and gate

| Option | Description | Selected |
|--------|-------------|----------|
| One report, two sections | Single file | |
| Two separate reports, each with own schema | Cannot be pooled | ✓ |
| Section inside `spec/EVIDENCE-CONTRACT.md` | Extend the frozen contract | |
| New normative `spec/REPRODUCIBILITY.md` | Own boundary spec, like `SWRL-SUBSET.md` | ✓ |
| Machine-checked scope table vs LLM call sites | Drift test | ✓ |
| Pass threshold on LLM repeatability | Require a minimum agreement rate | |
| No threshold; measurement with CI + limitations | Repeatability measured, not required | ✓ |

**Choice:** D-24 through D-28. Both live runs are human checkpoints, and provider keys enter only
through the LLM settings panel.
**Notes:** Ownership mirrors 1200 D-15: 1204 defines the boundary, and v11.0 SPEC-04 propagates it.

## Claude's Discretion

- Runner location and naming, within D-01's reuse rule.
- Report file names and schema dialect.
- The level-2 normalization for Cypher.
- How the frozen prompts are captured.
- Up to three out-of-subset rule-ingest items, reported as their own stratum.
- Whether recognition's M1 dispersion is shown, labelled as not an SC1 re-measurement.
- Raising N or k.
- Names of the D-20 fields.
- The pytest/xUnit split, and the plan/wave decomposition.

## Deferred Ideas

- Pinning temperature on the rule-ingest, graph-query and consult paths.
- Production-wide LLM-write provenance.
- Measuring the repeatability of the structural checks, HermiT and Tier-0.
- Benchmarking consult and input generation in record mode.
- The `hash_scalar_tuple` divergence and the stale §6 paragraph.
- data-service's `definitionId = run_id`.
- Accuracy and workload (RQ5).
- A temperature sweep.
- Cross-provider equivalence, which is never claimed.
- An abstention channel for rule-ingest.
- Live canvas determinism (Phase 40).
- Re-measuring recognition SC1.
- Secret handling (Phase 1205).
- Graphify regeneration.

See CONTEXT.md `<deferred>` for the owners.

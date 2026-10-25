# Phase 1204: Determinism and LLM Reproducibility Benchmark - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

**Separate deterministic validator repeatability from LLM proposal repeatability** — measure each,
report each on its own, and publish the boundary that says which claims are allowed.

Four deliverables, from `.planning/ROADMAP.md` Phase 1204 (lines 204–219):

1. Repeated fixed-fixture validator runs with hashes and canonical statuses.
2. A separate LLM repeatability / abstention / invalid-output report.
3. Provider / model / prompt / config provenance.
4. No universal determinism claim across live LLM or canvas state.

**Requirements:** ALGN12-15, ALGN12-16 (`.planning/REQUIREMENTS.md:41-42`).
**Package:** `ALIGN-P13` (`docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md:325`).
**Requires:** 1200–1203 (all complete) and fixed provider/model/prompt snapshots.
**Blocks:** v10.0 activation (GATE12-03), because v10.0 "must consume the … determinism contracts"
(`.planning/milestones/v10.0-ROADMAP.md:14`) and limits deterministic re-execution claims "to fixed
formal artifacts and execution configurations" (`:12`).
**Answers:** milestone open question #10, *"Which LLM provider/model/prompt snapshot is required for a
reproducibility claim?"* (`.planning/milestones/v12.0-CONTEXT.md:262`) — answered by D-22.

**Gate:** reports deterministic and model-dependent results separately, with confidence/limitations.

This phase **measures and bounds**. It does not fix what it measures (D-10), does not change the
frozen 1200 evidence envelope (D-23), and does not edit the manuscript (v11.0 Phase 1107 owns that).

</domain>

<upstream_corrections>
## Disk facts that change how this phase must be planned

All verified on 2026-09-23 by the orchestrator, or by a read-only sweep whose load-bearing claims
the orchestrator re-checked on disk. **Plan against these, not against the inherited prose.**
Corrections 1–4 change the deterministic half. Corrections 5–9 change the LLM half.

### Correction 1 — two of the four DE-01 legs do not evaluate the rule

`run_leg_data_service` builds its `/validation/publish` body from **the fixture's own
`expectedOutcomes` table** (`tools/de01/legs.py:301-357` `_fixture_entities_payload`:
`failedRuleIds` / `passedRuleIds` / `canonicalStatuses` are derived from
`expectedCanonicalStatus`) and reads the same statuses back. Its agreement with the C# leg is
**circular by construction**. The `replay` leg reads a persisted envelope.

Only two legs compute a verdict from the fixture:

- `csharp` — `DG.Core` `RuleEvaluator` via `DG/tools/DG.De01Harness/Program.cs`;
- `dg-reasoner` — pySHACL, which reports `not_evaluated` for the quantitative rule under
  `spec/RULE-PARTITION-POLICY.md` (see `tools/de01/README.md`, Phase 1201 D-10 section).

Repeating the data-service and replay legs therefore measures **persistence round-trip
stability**, not validator determinism.

### Correction 2 — no leg produces an output hash

- The data-service publish envelope passes **neither** `input_hash` nor `output_hash`
  (`data-service/app.py:2356-2363`).
- The C# harness sets **only** `inputHash`, a hash of the fixture (`Program.cs:373-383`).
- `tools/de01/README.md` already records that row-level hashes are populated by no call site, and
  that the report falls back to envelope-level hashes (1201 D-12).

So "runs with hashes" cannot be read off the producers today. The benchmark must compute its own
hash (D-04).

### Correction 3 — the data-service envelope's `definitionId` is the run id

`app.py:2358` passes `definition_id=run_id`. Every publish mints a new run, so this field **varies
per iteration by construction**. `spec/EVIDENCE-CONTRACT.md` §3 defines `definitionId` as "the
Computgraph/design definition". This is a contract-shape oddity to report, not to fix here.

### Correction 4 — the replay leg's input is not fixed inside a repeat loop

- The replay leg reads the **newest** run for the project: `GET /validation/view/{project}`
  (`legs.py:858`).
- The data-service leg publishes a fresh run immediately before it in every invocation. The
  docstring at `legs.py:168-183` records this shadowing.

Looped naively, iteration *i*'s replay leg reads what iteration *i*'s data-service leg just wrote.

**Label drift to handle when pinning:**

- `fixtures/golden/seed.cypher` writes `:Run {Run_Id: 'RUN_GOLD_1200'}`, which is
  `FIXTURE_RUN_ID` at `legs.py:47`.
- The auto-validation path writes `:ValidationRun` with `runId`.
- `fixtures/golden/replay/seed-replay.cypher:249-251` documents this pre-existing drift.

### Correction 5 — the rule-ingest path has no sampling control and records no provenance

- `GenerateResponse.model` is set to the **requested** id (`req.model`), not the model the provider
  actually served (`data-service/llm_gateway.py:421,510,582`).
- The gateway records no response id and no system fingerprint.
- `seed` and `top_p` appear nowhere in `data-service/`.
- `generate_validated_cypher` (`data-service/dg_context.py:953-991`) and `POST /llm/generate` pass
  **no `GenerationOptions`**. The rule-ingest path therefore runs at the **provider's default
  temperature** on the cloud adapters and at 0.1 on Ollama (`llm_gateway.py:544-546`).
- `generate_validated_cypher` returns `{valid, cypher, attempts}` with **no provider or model**.

By contrast:

- `cg_recognition.py` pins `temperature=0.0` (`:1053-1057`) and stamps provider and model onto
  each proposal (`:1248-1249`).
- `cg_input_generation.py` pins 0.0 (`:802-806`).

### Correction 6 — provider identity cannot be read from the adapter name

- DeepSeek has **no adapter of its own**. It runs through `OpenAIAdapter` with a custom `base_url`
  (`llm_gateway.py:267-270,307`), and the gateway reports `provider="openai"` for it.
- The recognition cassette key uses the arm's label (`"deepseek"`, `tests/recognition_eval/arms.py:479`),
  while the stored cassette field says `"openai"`.

### Correction 7 — no harness can take k > 1 samples of the same input

- **Recognition:** the cassette key is a request digest (`data-service/tests/recognition_eval/cassette.py:69-99`),
  so identical requests overwrite each other.
- **Input generation:** cassettes are keyed by scenario name, and **both committed cassettes are
  synthetic** (`provider="synthetic-authored"`, `data-service/tests/input_gen_eval/cassettes/README.md:55-76`).
- **Consult:** `data-service/tests/consult_cassette.py` is an in-memory double with no record mode,
  and the fixture directory it points to (`tests/fixtures/consult`) does not exist.

### Correction 8 — prompt version is logged, never persisted

`prompt_version` appears only in logs (`cg_recognition.py:953`, `cg_input_generation.py:583`). No
prompt hash or prompt version is persisted on any node.

### Correction 9 — no envelope has ever carried `provider`/`model`

The fields are optional in `spec/evidence-contract.schema.json:145-152`. Neither
`app.py:2356-2363` nor `tools/de01/legs.py` populates them. The envelope has no prompt-version or
temperature field.

### Correction 10 — `spec/EVIDENCE-CONTRACT.md` §6 is stale on scalar-tuple hashing

§6 "Scalar-tuple hashing" still calls the naive pipe-join the shipped precedent of
`compute_dg_id` / `DgIdMintingService`. Phase 1203 D-09 replaced that with length-prefix encoding
(`spec/DG-ID.md:42-53`).

`canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` remain pipe-joined and
now diverge from the identity functions. This is a known open gap (`spec/DG-ID.md:64`;
`fixtures/golden/MANIFEST.md` 1.3.0 entry). It does not block this phase if D-04 is followed.

### Correction 11 — dg-reasoner reports no version

The Phase 1202 DE-01 report records `serviceVersion: "unknown"` for dg-reasoner
(`.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.json`).
Its image id is the only available pin.

</upstream_corrections>

<decisions>
## Implementation Decisions

The user instructed: *"обсуди все темы и прими все рекомендуемые решения самостоятельно"*
(discuss all topics and accept all recommended decisions yourself).

**Every decision below (D-01 … D-28) was selected by Claude under that instruction.** Each one
records the evidence it rests on. A planner may flag any decision for reconsideration if research
contradicts the cited evidence.

### Deterministic subjects (ALGN12-15, deterministic half)

- **D-01: The deterministic subject is the DE-01 leg set on the committed golden fixtures, reused and not reimplemented.**
  - **Fixtures:** `fixtures/golden/fixture.json` (frozen) and `fixtures/golden/replay/mixed-verdicts.json`,
    which carries the canonical-state-hash dimension from 1202.
  - **Reuse:** the benchmark imports the `tools/de01/legs.py` adapters and `tools/de01/report.py`
    `compare_legs` verbatim.

  **Rationale:** the ROADMAP says "fixed-fixture validator runs", and DE-01 is the milestone's
  spine (1200 D-12, 1201 D-11, 1202 D-16). A second leg implementation would be a second, drifting
  comparison — the defect class this milestone exists to remove.
  Fixtures stay frozen (1200 D-11). New material goes in a sibling path (1202 D-17, 1203 D-14).

- **D-02: Every leg is classified as evaluator or relay, and only evaluator legs may carry a validator-determinism claim.**
  - **Evaluator legs:** `csharp`, `dg-reasoner`.
  - **Relay legs:** `data-service`, which echoes the fixture's `expectedOutcomes` (Correction 1),
    and `replay`, which reads a persisted envelope.

  Relay legs are still repeated and still reported, but under the label **round-trip stability**,
  never "validator repeatability".

  **Rationale:** Correction 1. Calling an echo "validator determinism" is the overclaim this phase
  exists to prevent. The report must make the label impossible to miss, for example as a column on
  every leg row.

- **D-03: Other deterministic paths are not measured in 1204 and carry no measured-determinism claim.**
  Each of these is listed in the contract's scope table (D-25) as `unmeasured`:
  - `cg_structure_checks`, the seven structural checks;
  - HermiT OWL consistency;
  - Tier-0 recognition and Tier-0 input generation;
  - SHACL on non-golden data;
  - the live Grasshopper solver and canvas.

  **Rationale:** scope. The deliverable is fixed-fixture DE-01. v10.0 can still consume the
  boundary, because `unmeasured` means "no claim permitted". This is exactly what its gate needs
  in order to refuse an unbacked claim.

### Repetition protocol and hashing

- **D-04: Repeatability is measured on a benchmark-computed verdict projection hash, with a closed exclusion list.**
  - **What is hashed:** per leg, per iteration, SHA-256 over canonical JSON of the leg's
    envelope. The canonicalization is `spec/EVIDENCE-CONTRACT.md` §6 **nested-payload** rules,
    `canonicalizationVersion` 1.
  - **The exclusion list.** Exactly these fields are removed first: `emittedAt`, the report's
    `generatedAt`, and run-derived identifiers. The run-derived identifiers are the run id and
    data-service's `definitionId`, which *is* the run id (Correction 3).
  - **Everything else is included:** every row's `ruleId` / `objectId` / `canonicalStatus` /
    `warnings` / `detail`, the envelope `canonicalStatus`, `serviceName`, `serviceVersion` and
    `stage`. A warning whose text varies between iterations is a finding, not noise.
  - **Changing the list:** adding a field to the exclusion list requires a recorded reason in the
    contract and bumps a projection version.
  - **Never use `hash_scalar_tuple` / `HashScalarTuple`**, because of the divergence in
    Correction 10.
  - **Producer hashes:** any `inputHash` / `outputHash` a producer supplies is recorded
    **as-is, nulls included**. Their absence is reported (Correction 2).
  - **Negative control:** mutating one status or one warning in a copied envelope **must**
    change the hash. Re-ordering rows must **not** change it, because rows are normatively sorted
    (§4). This mirrors the negative-control practice of 1200-09.

  **Rationale:** Correction 2 — no producer computes an output hash. Requiring producers to do so
  would pull in propagation owned by v11.0 Phase 1105 (1200 D-15/D-16).
  — **Reversibility:** one-way — hashes recorded in committed evidence stop being comparable if the
  projection or the exclusion list changes; any such change must bump the projection version.

- **D-05: N defaults to 10, split across at least two fresh process lifetimes of every Python service leg; one divergence fails and nothing is averaged.**
  - **Batches:** run at least two batches, restarting `data-service` and `dg-reasoner` between
    them. Record the container ids and start times for each batch.
  - **C# leg:** already a fresh `dotnet run` process on every iteration (`legs.py:680-694`).
  - **Why restarts matter:** Python randomizes string hashing per process, which changes `set`
    iteration order. `app.py:2327` builds `seen_rule_ids` as a set. Warm iterations inside one
    process share the hash seed, so they cannot detect this class of nondeterminism at all.
  - **Why N = 10:** each data-service iteration mints a ValidationRun and a Speckle version under
    `DG-1200-GOLDEN`. Ten bounds that side effect.
  - **Why no averaging:** determinism is falsified by a single counterexample, so rates are the
    wrong frame.

  **Required statement in the report:** "N/N identical does not prove determinism; it fails to
  falsify it for this fixture, build and configuration."

- **D-06: In repeat mode the replay leg reads a pinned run id, never the newest run.**
  It goes through the existing `GET /validation/view/{project}/{run_id}` route (Correction 4). The
  default DE-01 invocation keeps its current behavior; this is an additive flag.

  **Planner must verify** which seeded id that route actually resolves, given the
  `:Run`/`Run_Id` versus `:ValidationRun`/`runId` drift in Correction 4. Do not assume
  `RUN_GOLD_1200` resolves.

- **D-07: The deterministic report pins the execution configuration it measured.**
  It records:
  - git commit SHA and a dirty-tree flag (the working tree carries modified `bin/`/`obj/` files);
  - container image ids for `data-service`, `dg-reasoner` and `neo4j`;
  - the dotnet SDK version and build configuration;
  - the sha256 of every fixture file;
  - contract and canonicalization versions;
  - each leg's `serviceVersion`. dg-reasoner reports `"unknown"` (Correction 11), so its image id
    is its only pin.

  **Before the run, verify the running container holds the code under test.** Compose reuses
  stale images; this has already masked code state once, at 1200-08.

- **D-08: The deterministic gate is N/N identical projection hashes on every leg, with silent_disagreement_count = 0 in every iteration.**
  Any variance fails the gate, and the diverging iteration pair is recorded. The response to a
  divergence is a separate, evidenced decision. **Tuning the exclusion list to make it disappear is
  forbidden.**
  — **Reversibility:** one-way — this is the gate definition that v10.0 activation reads.

### LLM subjects and sampling protocol

- **D-09: Two LLM subjects are measured — recognition as primary and rule-ingest Cypher generation as secondary.**
  - **Recognition — primary.** `cg_recognition.recognize_structure` is the **only** path whose
    output contract has all three phenomena ALGN12-15 names:
    - deterministic validity guards (`bad_json`, `schema_violation`, relational codes, G7, G8);
    - an **explicit abstention channel** — `unrecognized[]` and the G10 demotion; the prompt
      `data-service/prompts/recognition_system.md` `r35.4` "licenses abstention";
    - pinned `temperature=0.0` with provider and model recorded.

    It also has frozen, SHA-pinned corpora: `urbanblock_slice`, 32 blocks, and `frame_ablated`,
    31 blocks.
  - **Rule-ingest — secondary.** `dg_context.generate_validated_cypher` with type `rule_ingest`.
    This is the path PAPER-C-003 names ("benchmark LLM interpretation … then measure … verdict
    determinism independently"), and the one risk R-12 targets. It is measured **as shipped** —
    see Correction 5 and D-10.

  **Rationale:** the pair spans the claim surface. One path is controlled (pinned temperature,
  provenance, abstention); the other is uncontrolled and is the one that persists rules.
  — **Reversibility:** costly — the subject set determines which claims v10.0 and v11.0 may cite.

- **D-10: Every LLM subject is measured in its shipped configuration, and 1204 changes no production sampling setting.**
  - No temperature is pinned on rule-ingest.
  - No prompt is edited.
  - No abstention channel is added.

  Rule-ingest's temperature is recorded as the value **"not sent — provider default"**, never as
  `0`. The uncontrolled temperature is reported as a **finding** and routed forward (see
  `<deferred>`).

  **Rationale:** a benchmark that fixes what it measures measures nothing that ships. Measurement
  and remediation are separated, just as verdicts and proposals are.

- **D-11: Consult and input generation are listed as model-dependent and unmeasured, and no claim may cite 1204 for their reproducibility.**
  Consult has no record mode and a missing fixture directory. The input-generation cassettes are
  synthetic (Correction 7).

  **Rationale:** they are named explicitly so that v10.0's consulting and generation claims
  (ROADMAP Phase 1204 "Blocks") know they are unbacked, rather than inferring coverage from the
  fact that this phase ran.

- **D-12: LLM inputs are frozen files with sha256, and the rule-ingest input is a frozen rendered prompt rather than a live assembly.**
  - **Recognition inputs:** the committed context files, SHA-verified by
    `data-service/tests/recognition_eval/corpus.py:109-123`.
  - **Rule-ingest inputs:** the natural-language text of five rules:
    - the rule in `fixtures/golden/fixture.json` ("Maximum building height must not exceed 75 meters");
    - the three rules in `test/fixture_rules_v7.txt`;
    - the CQ3 rule `R_BUILDING_MIN_DISTANCE_12_V`, from `fixtures/golden/cq3-attribute-of/`.
  - **Rendering:** each rule is rendered **once** through the repo's committed
    `n8n/workflows/rules-to-metagraph.json` "Build LLM Prompt" node (`:97`), together with
    `/context/assemble`, against a seeded project. The result is frozen with its provenance: the
    workflow file and commit, and the hash of the assemble response.
  - **Endpoint:** every sample is sent to `POST /context/generate-cypher` (`app.py:2011`). That
    route validates only and does not write to Neo4j; the write is n8n's. So the benchmark has no
    graph side effects.

  **Rationale:** `/context/assemble` reads the live graph, so re-assembling per sample would change
  the input under the measurement. The live n8n workflow has drifted from the repo
  (`CLAUDE.md` § Current Priorities 1), so the report must state that the **repo** version was
  rendered.
  — **Reversibility:** one-way — committed evidence refers to this exact input set; changing it is
  a new experiment, not a re-run.

- **D-13: Sample k = 10 per input item per provider, never report a rate from fewer than 5 samples, measure every reachable provider, and never pool providers.**
  - Provider availability is recorded. An unconfigured provider is recorded as `not measured`,
    with the reason.
  - Ollama is included whenever a model is pulled, because it is the only provider that exposes a
    weights digest.
  - At least one live provider is required (D-27). At Phase 35-15, DeepSeek through the OpenAI
    adapter was the only one available.

### Outcome taxonomy and metrics

- **D-14: LLM samples use their own proposal-outcome taxonomy and never carry a canonical verdict status.**
  - **`valid`**.
  - **`valid_after_retry`**.
  - **`invalid`**, sub-typed by the path's **own** violation codes:
    - recognition: `bad_json`, `schema_violation`, the relational codes, G7, G8;
    - rule-ingest: the ten `validate_cypher` codes (`dg_context.py:674`).
  - **`abstained`** — only through an explicit channel (D-16).
  - **`truncated`**.
  - **`refused`**.
  - **`provider_error`**.

  `passed`, `failed` and the other statuses frozen in 1200 are **verdict** vocabulary. Using them
  for proposals would merge again what this phase exists to separate. 1200 D-02's frozen vocabulary
  is untouched.
  — **Reversibility:** costly — the report schema and every consumer of it.

- **D-15: Invalid output is measured at two levels, first attempt and final result.**
  Both subjects retry with corrective feedback, up to three attempts each:
  - recognition: `cg_recognition.py:969`, `max_retries=2`;
  - rule-ingest: `dg_context.py:953`, `max_retries=2`.

  The retry loop hides first-attempt invalidity. Report three things: the first-attempt invalid
  rate per violation code, the final invalid rate, and the attempts distribution.

- **D-16: Abstention is counted only through an explicit, machine-detectable channel in the path's output contract.**
  - **Recognition:** per-block `unrecognized[]` entries, split into three groups:
    - model-emitted;
    - G10-demoted (the confidence floor);
    - G6-autofilled.

    **G6 autofill is not model abstention** and must not be counted as such.
  - **Rule-ingest:** its output contract has no abstention channel. It is reported as **"not
    supported by output contract"**, never as `0%`.

  No heuristic classification of free text is used.

- **D-17: Repeatability is reported per item at two normalization levels, never as a single score.**
  - **Level 1:** raw byte identity of the model text.
  - **Level 2:** a declared normalization:
    - recognition: canonical JSON of the validated proposal set;
    - rule-ingest: whitespace- and line-normalized Cypher.
  - **Per-item measures:**
    - the number of distinct outputs;
    - the **modal-agreement rate** — the share of the k samples equal to the modal output;
    - for recognition, per-block decision agreement.
  - **Aggregates** carry Wilson 95% confidence intervals, the method
    `data-service/tests/recognition_eval/report.py:369` already uses.

  There is **no pooled "reproducibility score"** across items, subjects or providers.

- **D-18: 1204 measures no accuracy against expected labels.**
  Correctness enters the report only through deterministic validity oracles (D-14, D-15).
  - Interpretation accuracy is disclaimed by the paper (PAPER-C-003, P081) and belongs to RQ5.
  - Recognition M1 is the gate of Phases 35 and 40, and v12.0 may not mark it (GATE12-04).

### Provenance snapshot and reproducibility class (ALGN12-16)

- **D-19: Each LLM sample carries a complete provenance block, and a sample missing any required field is void.**
  This mirrors Phase 35 AI-SPEC E9. The required fields are:
  - the adapter, and the endpoint **host** — never the API key, and never a URL carrying
    credentials;
  - the requested model id, plus the served model id, response id and system fingerprint when the
    provider returns them (D-20);
  - the Ollama weights digest, when the provider is local;
  - the prompt file path, its sha256 and its `prompt_version`;
  - the sha256 of the rendered request;
  - sampling parameters **as actually sent** — "not sent" is a legal value;
  - the negotiated structured-output mode;
  - the gateway and service commit;
  - the input sha256;
  - the sample index;
  - timestamps, usage and `finish_reason`.

  **Provider identity is the endpoint host plus the model, never the adapter name**
  (Correction 6).
  — **Reversibility:** costly — this is the report schema.

- **D-20: The gateway gains optional response fields for the served model, the response id and the system fingerprint.**
  These are additive fields on `GenerateResponse`, populated only from what each provider actually
  returns. There is no request change, and existing callers are unaffected. `spec/API.md` documents
  the new fields.

  **Rationale:** today the gateway reports the **requested** model (Correction 5). An alias that
  the provider re-points behind the same id is therefore invisible. Without observing what was
  served, ALGN12-16's "or explain why it is not reproducible" could only be asserted, not evidenced.

- **D-21: Cassettes record every sample under its sample index, and the report must regenerate byte-for-byte from committed cassettes.**
  - **Sample index:** k samples of one request never collide (Correction 7). The scheme extends
    the recognition cassette format.
  - **Location:** a new sibling directory. The existing Phase 35 cassettes under
    `data-service/fixtures/recognition_eval/cassettes/` are not touched.
  - **Regeneration check:** it is labelled **scoring-pipeline determinism**, never "model
    repeatability" — replaying a recording proves only that the analysis is deterministic.

- **D-22: Every AI experiment is assigned exactly one reproducibility class with a stated reason.**
  - **`replayable`** — from committed cassettes. The analysis reproduces exactly; the model is not
    re-run.
  - **`re-executable-pinned-weights`** — local Ollama with a recorded digest. It can be re-run on
    identical weights, but it is **still not guaranteed bitwise identical**, because of batching
    and kernel nondeterminism.
  - **`not-reproducible-provider-managed`** — a cloud model id is an alias whose weights can change
    behind it. The gateway has no `seed` control (Correction 5). Temperature 0 is only
    near-deterministic.

  This is how ALGN12-16's "or explain why it is not reproducible" is answered, per experiment. It
  also **answers milestone open question #10:** a reproducibility claim requires the full D-19
  block, and a bitwise re-execution claim is available **only** in the `replayable` class.
  — **Reversibility:** one-way — v10.0 and v11.0 SPEC-04 cite these classes by name.

- **D-23: Production-wide LLM-write provenance is out of scope, and the evidence envelope is not changed.**
  ALGN12-16 asks only that **"the declared AI experiment"** be reproducible or explained. So in
  this phase:
  - no prompt hash is persisted on production nodes;
  - LLM proposals are not wrapped in verdict envelopes;
  - no field is added to the frozen 1200 envelope (Correction 9).

  LLM provenance lives in the LLM report's own schema.

### Artifacts, contract and gate

- **D-24: Two separate reports are produced, each JSON plus Markdown with its own schema, so they cannot be pooled.**
  A deterministic report and an LLM repeatability report. Neither contains the other's metrics, and
  there is no combined verdict.

  **Rationale:** the gate wording is "reports deterministic and model-dependent results
  separately". Keeping them in separate files enforces that separation structurally rather than by
  discipline.

- **D-25: A new normative spec/REPRODUCIBILITY.md defines the determinism boundary that v10.0 and v11.0 consume.**
  - **Contents:**
    - determinism classes: `deterministic-measured`, `model-dependent`, `unmeasured`;
    - a scope table with one row per path;
    - the D-04 projection and its exclusion list;
    - the D-19 provenance field list;
    - the D-22 reproducibility classes;
    - explicit non-claims:
      - no universal determinism across live LLM or canvas state;
      - temperature 0 is not determinism;
      - cassette replay is not model repeatability;
      - relay legs are not validator determinism;
      - the Ollama fallback is not output equivalence (`.planning/milestones/v10.0-REQUIREMENTS.md:70`, INTG-02).
  - **CLAUDE.md:** gains a governing-spec pointer beside "Evidence and status contract" and "SWRL
    subset boundary".
  - **Ownership:** 1204 owns the **definition**. v11.0 SPEC-04
    (`.planning/milestones/v11.0-REQUIREMENTS.md:57`) owns **propagation** into the publication
    bundle. This mirrors 1200 D-15 — coordinate, do not duplicate.

  — **Reversibility:** costly — downstream canonical refs will cite the path.

- **D-26: The scope table is machine-checked against the code's LLM call sites.**
  - A fenced block in the spec lists every gateway call site.
  - A drift test enumerates the `get_adapter(` / `adapter.generate(` callers in `data-service/`
    and fails when one is missing from the table.

  This mirrors the two machine-checked blocks in `spec/SWRL-SUBSET.md`.

  **Rationale:** v10.0 will add LLM paths. The guard stops a new path from silently inheriting a
  determinism claim it never earned.

- **D-27: The LLM gate is a complete-provenance report with at least one live provider at k of 5 or more per subject, confidence intervals and a limitations section, and no pass threshold on repeatability rates.**
  - A subject that could not be measured carries a typed not-measured reason instead of results.
  - Repeatability is **measured, not required**. A low agreement rate is a result, not a failure.
  - If no live provider is reachable at execution time, the LLM half is incomplete and the phase
    gate cannot pass.

  — **Reversibility:** one-way — this is the gate definition.

- **D-28: Both live runs are human checkpoints, and provider keys enter only through the LLM settings panel.**
  - **Deterministic half:** needs the compose stack for three of the four legs, plus the D-05
    restarts. This follows the pattern of 1201-06, 1202-07 and 1203-06.
  - **LLM half:** needs a live provider key. The key is configured through the ui-v2
    LLMSettingsPanel or `/llm/settings`. It is **never** put into a brief, a committed file, a
    cassette or a report (`CLAUDE.md` § DSH "Anything touching secrets").

### Claude's Discretion

Within the decisions above, the planner retains discretion on:

- **Runner location and naming** — for example a `--repeat` mode on `tools/de01/run_de01.py`
  versus a sibling `tools/` runner that imports it. The limit is D-01's reuse rule.
- **Report file names and schema dialect.**
- **The exact level-2 normalization for rule-ingest Cypher** (D-17), provided it is declared in the
  report.
- **How the frozen rendered prompts are captured** (D-12) — a script or a one-off — provided their
  provenance is recorded.
- **Adding up to three out-of-subset rule-ingest items**, for example disjunction, negation or a
  temporal rule (the future work named in PAPER-C-021). Such items must be reported as their own
  stratum.
- **Whether recognition's per-sample M1 dispersion is shown** as a repeatability-of-score
  observation. If it is shown, it must be labelled as never being an SC1 re-measurement (D-18,
  GATE12-04).
- **Raising N or k above the defaults.**
- **Field names** for the D-20 gateway additions.
- **The split between pytest and xUnit**, and the plan/wave decomposition.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### What this phase must deliver
- `.planning/ROADMAP.md:204-219` — Phase 1204 deliverables and gate wording
- `.planning/REQUIREMENTS.md:41-42` — ALGN12-15, ALGN12-16; `:55` GATE12-03 (v10.0 activation)
- `.planning/milestones/v12.0-CONTEXT.md` — `<constraints>` (Alternative A locked; no manuscript
  edits); `:101` 1204 = ALIGN-P13; `:262` open question #10 (answered by D-22)
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md` —
  `:18` NO-GO for "a universally deterministic LLM-enabled pipeline"; `:159-160` AI-authoring and
  deterministic re-execution gap rows; `:184` evaluation by accuracy/abstention/invalid rate;
  `:277` GSD-ALIGN-13; `:377` RQ5; `:410` risk R-12; `:460` open question 10
- `docs/reviews/theory-implementation-alignment/evidence/paper-claims.json` — **PAPER-C-003**
  (measure verdict determinism independently of LLM interpretation), **PAPER-C-034**
  (acceptance/abstention logging), PAPER-C-021 (disjunction/temporal future work)

### Downstream consumers of this phase's contract
- `.planning/milestones/v10.0-ROADMAP.md:12,14` — v10.0 must consume the determinism contract;
  deterministic re-execution limited to fixed artifacts and execution configurations
- `.planning/milestones/v10.0-REQUIREMENTS.md:70` — INTG-02: Ollama fallback is not output equivalence
- `.planning/milestones/v11.0-REQUIREMENTS.md:57` — **SPEC-04** (v11.0 owns propagation of the
  deterministic re-execution requirements; D-25 ownership split); `:71` MANU-02
- `.planning/milestones/v11.0-ROADMAP.md:32,38,40` — determinism wording qualification before v9.1/v10.0

### Deterministic half — the harness being reused
- `tools/de01/README.md` — leg preconditions, acceptance rule, D-12 hash fallback, freeze rule
- `tools/de01/legs.py` — `:47` `FIXTURE_RUN_ID`; `:158-298` data-service leg; **`:301-357`
  `_fixture_entities_payload` (Correction 1)**; `:371+` dg-reasoner leg; `:637+` C# leg
  (`:680-694` fresh `dotnet run`); **`:835-858` replay leg reading the newest run (Correction 4)**
- `tools/de01/report.py` — `:82` `compare_legs`; `:354` `generatedAt`; `_DECLARABLE_STATUSES`
- `tools/de01/run_de01.py`, `tools/de01/report_schema.json`, `tools/de01/tests/test_de01_runner.py`
- `DG/tools/DG.De01Harness/Program.cs` — `:373-383` envelope with `inputHash` only (Correction 2)
- `data-service/app.py` — **`:2320-2363` publish envelope: `:2327` set iteration, `:2358`
  `definition_id=run_id` (Correction 3), no hashes (Correction 2)**
- `data-service/evidence_contract.py:219-275` — `build_envelope`; `emittedAt` is wall-clock
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/` —
  latest four-leg run (`silent_disagreement_count = 0`) and the `expectedCanonicalStateHash`
  disposition README

### Fixtures (frozen — do not edit)
- `fixtures/golden/fixture.json`, `fixtures/golden/seed.cypher`, `fixtures/golden/MANIFEST.md`
  (freeze policy; 1.3.0 change-reason entry recording the scalar-tuple divergence)
- `fixtures/golden/replay/mixed-verdicts.json`, `fixtures/golden/replay/seed-replay.cypher`
  (`:249-251` `:Run` vs `:ValidationRun` drift)
- `fixtures/golden/cq3-attribute-of/` — source of the CQ3 rule used as an ingest input (D-12)
- `test/fixture_rules_v7.txt` — the three natural-language rules used as ingest inputs (D-12)

### Contracts this phase must respect
- `spec/EVIDENCE-CONTRACT.md` — §3 envelope fields (`:137-171`; `provider`/`model` optional);
  §4 row ordering; **§6 canonicalization (`:278-342`; the scalar-tuple paragraph at `:285-292` is
  stale — Correction 10)**; §7 freeze; §8 DE-01 acceptance
- `spec/evidence-contract.schema.json` — `:145-152` `provider`/`model`
- `spec/DG-ID.md:42-64` — length-prefix encoding and the known `hash_scalar_tuple` divergence
- `spec/RULE-PARTITION-POLICY.md` — why dg-reasoner reports `not_evaluated` on the quantitative rule
- `spec/SWRL-SUBSET.md` — precedent for machine-checked fenced blocks (D-26)
- `spec/API.md` — where the D-20 gateway fields are documented
- `CLAUDE.md` § Schema Change Propagation; the governing-spec paragraphs D-25 extends

### LLM half — code measured
- `data-service/llm_gateway.py` — `:28-71` request/response models; `:74-102` `GenerationOptions`;
  `:255-325` structured-output negotiation; adapters `:361`/`:439`/`:528`;
  **`:421,510,582` requested-not-served model (Correction 5)**; `:544-546` Ollama 0.1 default;
  `:599-620` `get_adapter`; `:763-787` `resolve_active_provider`
- `data-service/cg_recognition.py` — `:403-448` JSON extraction; `:803-821` schema;
  `:879-924` G10/G11; `:966` `recognize_structure`; `:969` retries; `:1053-1057` temperature 0.0;
  `:1088-1231` G6/G7/G8/refusal handling; `:1248-1249` provenance stamping
- `data-service/prompts/recognition_system.md` — `prompt_version: r35.4`, licenses abstention
- `data-service/dg_context.py` — `:674` `validate_cypher` (10 codes); **`:953-991`
  `generate_validated_cypher` (no options, no provenance)**
- `data-service/app.py:2011` — `POST /context/generate-cypher`
- `n8n/workflows/rules-to-metagraph.json:97,112` — "Build LLM Prompt" and the generate-cypher call

### LLM half — harness precedent to extend
- `data-service/tests/recognition_eval/` — `cassette.py:69-99` key (no sample index,
  Correction 7), `:146-211` modes; `corpus.py:71-123` provenance/SHA checks; `arms.py:479,499-510`
  provenance block; `report.py:368-419` metrics incl. Wilson CI; `live_sweep.py` record/cost
- `data-service/fixtures/recognition_eval/` — `urbanblock_slice` / `frame_ablated` context +
  expected files; existing cassettes (**do not modify**)
- `.planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-AI-SPEC.md` —
  `:792` temperature note ("near-deterministic, not deterministic"); `:1391` **E9 reproducibility
  and provenance** (D-19's model); `:1505-1525` cassette key, record/replay modes, freeze protocol
- `.planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-EVAL-REPORT.md:159` —
  the one live provider configuration measured to date (`deepseek-chat`, temperature 0.0)

### Inherited decisions this phase consumes
- `.planning/phases/1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt/1200-CONTEXT.md` —
  D-02 frozen vocabulary, D-07 canonical hashing, D-11 fixture freeze, D-12/D-13/D-14 DE-01,
  D-15/D-16 ownership split (D-25 mirrors it)
- `.planning/phases/1201-rule-parser-and-evaluator-conformance/1201-CONTEXT.md` — D-10 SHACL
  `not_evaluated`, D-11 DE-01 as exit evidence, D-12 hash gap
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/1202-CONTEXT.md` —
  D-02 canonical state hash, D-16 DE-01 extension, D-17 sibling-path precedent
- `.planning/phases/1203-identity-convergence-and-attribute-of-decision/1203-CONTEXT.md` —
  D-09 length-prefix encoding (source of Correction 10), D-14 sibling fixture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **DE-01 legs and `compare_legs`** (`tools/de01/`) — the deterministic half is a repeat wrapper
  around them. Per-leg graceful degradation (1200 D-13) already gives typed non-results when a leg
  is down.
- **Canonical JSON in both languages** — `data-service/canonical_json.py` and
  `DG.Core.Contracts.CanonicalJsonWriter`, with golden vectors in
  `fixtures/golden/canonical-vectors.json`. D-04's projection hash uses the nested-payload path.
- **Recognition eval harness** (`data-service/tests/recognition_eval/`) — the cassette
  record/replay adapter, the corpus SHA pinning, the provenance-block enforcement, the
  `wilson_interval` scoring and cost tracking. D-21 extends the cassette key; nothing is rebuilt.
- **Deterministic validity oracles already shipped:**
  - recognition's guard stack and `validate_proposed_structure`;
  - `validate_cypher`, with 10 violation codes and no graph reads;
  - these are exactly D-14's `invalid` subtypes.
- **`GenerateResponse.finish_reason` and `truncated`** — these already distinguish truncation and
  refusal from malformed output, which gives D-14's `truncated` and `refused`.

### Established Patterns
- **Frozen fixture plus sibling path** (1200 D-11, 1201 D-16, 1202 D-17, 1203 D-14) — new
  benchmark inputs, cassettes and frozen prompts go in siblings. `fixtures/golden/fixture.json` is
  never edited.
- **DE-01 as exit evidence behind a live-stack human checkpoint** (1201-06, 1202-07, 1203-06) —
  D-28.
- **Negative control proving a check detects its own defect** (1200-09) — D-04.
- **Definition owned here, propagation owned by v11.0** (1200 D-15) — D-25.
- **Machine-checked spec blocks with a drift test** (`spec/SWRL-SUBSET.md`, 1201 D-15) — D-26.

### Integration Points
- `GenerateResponse` in `data-service/llm_gateway.py` — the additive fields of D-20. The existing
  callers are listed in the Correction 5 and 6 evidence.
- `POST /context/generate-cypher` — the rule-ingest sampling endpoint (D-12).
- `GET /validation/view/{project}/{run_id}` — the pinned replay read (D-06).
- `docker compose restart data-service dg-reasoner` — the process-lifetime batches (D-05).
- The LLM settings panel / `/llm/settings` — the only channel through which provider keys enter
  (D-28).

### Environment caveats (still applicable)
- **Stale images.** Compose reuses stale images, so verify the container holds the code before any
  live run (D-07).
- **Git Bash paths.** `docker exec` / `docker cp` paths need `MSYS_NO_PATHCONV=1` under Git Bash.
- **dg-reasoner has no host port.** Its leg must run inside the compose network or against a
  published port.
- **Known environment-dependent failures, not regressions:**
  - 4 `DesignStateValidationFlowTests` fail fast when Neo4j is down;
  - 4 `test_dg_context.py` tests fail from the host, because the `neo4j` hostname resolves only
    inside compose.
- **Perplexity MCP must be called sequentially** — this applies only if research uses it.

</code_context>

<specifics>
## Specific Ideas

- **One rule, both halves.** The golden fixture's rule is both the deterministic subject (DE-01's
  `R_GOLD_HEIGHT_MAX_75_V`) and one LLM input item: "Maximum building height must not exceed 75
  meters". One table can therefore state the phase's thesis directly: *same rule — the validator
  verdict is N/N identical; the LLM encoding produces m distinct outputs across k samples.* That is
  PAPER-C-003's "measure … independently" made concrete.
- **"Deterministic" must become expensive to say.** This echoes 1200's "`failed` must become
  expensive to say". Every deterministic claim the phase lets stand is backed by:
  - a measured row;
  - a pinned configuration;
  - and a projection hash.

  Everything else is labelled `model-dependent` or `unmeasured`.
- **Report what the controls do, without over-claiming causation.** Recognition (temperature
  pinned) and rule-ingest (temperature unpinned) differ in task as well as in controls. The report
  may put their numbers side by side, but must not attribute the difference to temperature alone.

</specifics>

<deferred>
## Deferred Ideas

| Idea | Routed to | Note |
|---|---|---|
| Pin temperature and pass `GenerationOptions` on rule-ingest, graph-query, consult and `/llm/generate` | Unowned, recorded as a 1204 finding; candidate for v10.0 pre-activation | D-10: measured as shipped; the fix is a production behavior change |
| Persist prompt hash/version and provider/model on production LLM writes (ingested rules) | v11.0 SPEC-04 / a future phase | D-23: ALGN12-16 is scoped to the declared experiment |
| Repeatability of `cg_structure_checks`, HermiT consistency, Tier-0 paths | Not scheduled | D-03: listed `unmeasured` — no claim permitted until measured |
| Real record-mode benchmarking of consult and input generation | v10.0, before it makes consulting/generation claims | D-11 |
| Resolve the `hash_scalar_tuple` / `HashScalarTuple` divergence and correct `spec/EVIDENCE-CONTRACT.md` §6's stale scalar-tuple paragraph | Unowned since 1203-02 | Correction 10; D-04 avoids depending on it |
| data-service envelope `definitionId = run_id` | Unowned; recorded as a 1204 finding | Correction 3; v11.0 1105 owns envelope propagation |
| Accuracy against expert labels, reviewer time and workload | RQ5 / future evaluation | D-18; the paper disclaims interpretation accuracy |
| Temperature sweep or a pinned-arm comparison on rule-ingest | Not scheduled | A benchmark-only arm would measure a configuration that does not ship |
| Cross-provider output equivalence | Never claimed | v10.0 INTG-02 states the fallback proves operational compatibility only |
| An abstention channel for the rule-ingest prompt | Not scheduled | D-16 reports "not supported by output contract" |
| Live Grasshopper/canvas determinism in Rhino | v9.0 Phase 40 owns live Rhino | GATE12-04; listed as a non-claim in D-25 |
| Recognition SC1 re-measurement | v9.0 Phase 40 / Phase 35 | GATE12-04 — v12.0 cannot mark it passed |
| Provider key handling, secret storage, direct-proxy exposure | Phase 1205 | ALGN12-17..20 |
| Graphify regeneration | Not in this milestone | Risk R-15 |

</deferred>

---

*Phase: 1204-determinism-and-llm-reproducibility-benchmark*
*Context gathered: 2026-09-23*

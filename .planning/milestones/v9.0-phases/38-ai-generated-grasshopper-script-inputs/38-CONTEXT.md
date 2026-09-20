# Phase 38: AI-Generated Grasshopper Script Inputs - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning
**Requirements:** GHIN-01, GHIN-02, GHIN-03, GHIN-04

<domain>
## Phase Boundary

Given an existing Metagraph `Rule` (by `Rule_Id`) and the published Computgraph `Parameter`
structure for a definition, the system proposes N candidate input parameter sets — delivered as
ParamState-compatible payloads that the architect reviews in ui-v2 and applies to the canvas
through the **existing** PARAMETER REINSTATE component. Generation and application are strictly
separated; nothing reaches the canvas without explicit acceptance.

**In scope:** input-generation endpoint, deterministic + LLM two-tier candidate generation,
rule→parameter binding artifact, ParamState persistence with provenance, ui-v2 review surface,
the additive `reinstateParameterId` plumbing that makes candidates actually applicable.

**Not in scope:** any new canvas-apply mechanism (PARAMETER REINSTATE is the only path);
free design-intent text; geometry evaluation; re-declaring any rule threshold.

</domain>

<decisions>
## Implementation Decisions

### Parameter identity — Computgraph → ParamState (JOIN A)

- **D-01:** A `reinstateParameterId` property is persisted on the `:Parameter` node at publish
  time. Generation reads it directly — no inference at generation time. This is an **additive
  change to shipped Phase 36** (`data-service/computgraph_publish.py` + `/computgraph/publish`)
  and therefore fires the standing schema-propagation checklist (CLAUDE.md).
- **D-02:** Its value is derived automatically at publish by walking
  slider → wire → the PARAMETER STATE component's input param. To make that possible,
  `CanvasContextExtractor` **additively captures each component's input params
  (instance GUID + NickName)** — verified as not present in `cgContextJson v1` today
  (`CgNode.Nickname` is the *component's* nickname; `CgWire.ToParam` is a GUID with no name).
- **D-03:** The envelope stays `schemaVersion: "cg-context-1"` — new fields are optional and
  additive, following the Phase 32.1 `dgId` precedent (plan 32.1-05, backward compat proven by
  test). No version bump.
- **D-04:** A parameter that cannot be resolved to a `reinstateParameterId` is **excluded from
  the candidate and explicitly flagged with a reason** on that candidate. Never silently dropped,
  never emitted-and-hoped (which would surface only as a ReStatus miss at apply time). Mirrors
  Phase 35's "unrecognized — never invented, never silently dropped" stance.
- **D-05:** Only `paramKind == Variable` parameters are eligible for generation. Constants are
  fixed presets and Emergent are computed outputs — neither is an architect-driven input, and
  neither carries a slider domain to bound sampling.

### Rule → parameter binding and determinability (JOIN B)

- **D-06:** Which parameters a rule constrains is resolved from a **declarative binding**, with
  an architect override available in the ui-v2 review surface before generation runs.
- **D-07:** The bindings live as a **new sibling top-level key `inputBindings` in the existing
  `llm/structure_rules.json`** — NOT as new entries in `mappings[]`. Verified additive-safe:
  `load_structure_rules()` (`data-service/cg_structure_checks.py:399-415`) requires only that
  `mappings` is a list and returns the full payload, so Phase 37's validator never sees the new
  key and **requires zero changes to shipped Phase 37 code**. Adding an operation to `mappings[]`
  was rejected — `STRUCTURE_RULE_OPERATIONS` is a closed frozenset of four and every operation
  there compiles to a Cypher *check*, which a binding is not.
- **D-08:** Each binding entry declares the rule's **determinability class** explicitly:
  `direct-parameter` | `monotone-bound` (with the metric expression and which parameters it is
  monotone in) | `geometry-required`. An **unmapped rule defaults to `geometry-required`** — the
  safe direction.
- **D-09:** Determinability is **classified and reported honestly** on every candidate. For a
  `geometry-required` rule, candidates still generate but the system **never claims the rule is
  satisfied** — that verdict belongs to the existing SWRL VALIDATOR after geometry solves.
  Overclaiming here is the phase's credibility risk.
- **D-10:** The numeric limit a candidate must respect is **read from the Rule's SWRL atoms**
  (Literal + builtin comparison, violation-inverted body semantics) at generation time. It is
  **never** denormalized into the binding. This upholds the single-authoring principle in
  `spec/RULE-PARTITION-POLICY.md` and respects the boundary Phase 37 already encoded —
  `_FORBIDDEN_PARAM_KEYS` (`cg_structure_checks.py:375-386`) rejects `min`/`max`/`threshold`/
  `value` from that file with "this expresses SWRL scope, not a structural check".
- **D-11:** Generation is keyed to an **existing Rule by `Rule_Id` only**. Free design-intent text
  (allowed by GHIN-01's wording) is deferred — it would make `sourceRuleId` provenance nullable
  and leave determinability with nothing to classify.

### Candidate generation

- **D-12:** **Two-tier generation.** Tier 0 is a deterministic sampler that produces valid points
  inside each slider domain (respecting `domainStep` alignment and any statically-determinable
  rule bound); the LLM then selects, adjusts and explains, constrained to in-domain values. This
  guarantees at least one valid candidate even when the model is useless — the exact failure
  Phase 35 hit (0 proposals from 14 candidates) and fixed with the same hybrid pattern.
- **D-13:** Diversity comes from an **explicit strategy axis per candidate** (conservative /
  balanced / exploratory / near-limit) in a single structured call, plus **near-duplicate
  rejection by normalized pairwise distance** (each parameter scaled to its own domain).
  Temperature alone is not the diversity mechanism.
- **D-14:** An out-of-domain value causes **rejection + bounded retry with the violation list fed
  back** (the Phase 29 validator-feedback pattern), then an actionable What+Where+How-to-fix
  error. **Clamping is not implemented** — it is semantic distortion that hides model failure
  behind a valid-looking result.
- **D-15:** Default **4 candidates**, overridable per request, bounded (DoS guard, as Phase 35
  bounds proposals). The default matches the four strategy axes one-for-one.
- **D-16:** Provider is resolved **once** before the retry loop and `adapter.generate()` is called
  in-process — never a re-POST to `/llm/generate`, which would let a settings change silently
  switch models between attempts. (Phase 35 cross-cutting rule, carried forward.)
- **D-17:** Structured output reuses the Phase 35 stack (`cg_schemas.py` Pydantic v2 +
  `to_strict_json_schema()`, `llm_gateway.negotiate_structured_output()`). Note the schema gives
  **shape only** — `to_strict_json_schema()` deliberately strips `minimum`/`maximum`
  (`cg_schemas.py:205-221`), and the bounds here are per-parameter and dynamic anyway. Domain
  enforcement is therefore a **dynamic validator built per request**, not the wire schema.

### Review, storage and provenance

- **D-18:** An accepted candidate is stored as a **standalone `:DesignState {kind:'ParamState'}`**
  node with the `DS_` prefix, project-scoped — exactly the shape PARAMETER STATE already produces,
  so VALIDATION GRAPH reads and PARAMETER REINSTATE work unchanged. No new node type; composition
  into a full DesignState stays the architect's job.
- **D-19:** **Only accepted candidates are persisted.** Generation returns candidates in the
  response; nothing is written to the graph until the architect accepts. Rejected candidates leave
  no trace.
- **D-20:** The review surface is a **panel on the existing ui-v2 Model screen**, which already
  browses validation runs grouped by design state. Reuses the existing grouping idiom and
  `ui-v2/src/components/` primitives. Not the Graph screen, not a new screen.
- **D-21:** Provenance **mirrors Phase 36's locked vocabulary verbatim** (`source`, `provider`,
  `model`, `confidence`, `definitionId`, `publishedAt`) and adds the phase-specific
  `sourceRuleId`, `strategy` (which diversity axis produced it) and `determinabilityClass`.
  One vocabulary across the Computgraph and the candidates derived from it.
- **D-22:** GHIN-04's separation is enforced **structurally**, not just in the UI: the generation
  module must have no code path to the bridge or to any canvas write. This is assertable as a test
  (import-graph check), not merely a review comment.

### Claude's Discretion

- Endpoint naming and request/response schema shape (suggest `POST /computgraph/generate-inputs`,
  but the planner owns the contract).
- Which module the deterministic sampler lives in (new `cg_input_generation.py` vs. splitting the
  sampler into its own module, mirroring how `cg_topology.py` was split from `cg_recognition.py`).
- The exact normalized-distance metric and near-duplicate threshold.
- Whether the binding lookup is exposed via a debug endpoint (as Phase 29 did with
  `/context/debug`).
- Sampler strategy (grid, Latin hypercube, or rule-bound-aware) — any deterministic,
  reproducible choice is acceptable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase
- `.planning/milestones/v9.0-phases/38-ai-generated-grasshopper-script-inputs/38-RESEARCH.md` — codebase
  grounding + external state of the art; §3.1 JOIN A analysis, §4.1 the bounds-enforcement
  collision, §4.3 the determinability definition D-08/D-09 implement, and the Validation
  Architecture section
- `.planning/REQUIREMENTS.md` — GHIN-01..04 (lines 95-100)

### Rule ownership and partition policy (load-bearing for D-10)
- `spec/RULE-PARTITION-POLICY.md` — **normative**. SWRL VALIDATOR owns quantitative
  design-compliance constraints ("maximum building height is 75 meters" is its own example);
  single-authoring principle forbids a business rule existing in two systems
- `data-service/cg_structure_checks.py:375-386` — `_FORBIDDEN_PARAM_KEYS`, the encoded
  value-threshold fence
- `data-service/cg_structure_checks.py:399-415` — `load_structure_rules()`, the pass-through
  behaviour that makes D-07 additive-safe
- `llm/structure_rules.json` — the shipped v1 artifact `inputBindings` is added alongside

### Upstream phase contracts
- `.planning/milestones/v9.0-phases/36-computgraph-persistence-display/36-CONTEXT.md` — Computgraph node/relation
  shape, MERGE keys, provenance vocabulary D-21 mirrors, `contextJson` on `:Algorithm`
- `.planning/milestones/v9.0-phases/37-script-structure-validation/37-CONTEXT.md` — the rule-mapping file's
  original design intent (**note: Phase 37 is executed — 6 plans + VERIFICATION; the ROADMAP
  progress table is stale**)
- `.planning/milestones/v9.0-phases/32-computgraph-serialization-core/32-RESEARCH.md` — `cgContextJson v1`
  envelope, the versioned-contract rule D-03 follows
- `spec/DG-ID.md` — `dgId` identity spec; published Parameters carry it
- `spec/DATABASE.md` — ValidGraph DesignState `kind` taxonomy (D-18) and Computgraph section

### Patterns to mirror (not to reinvent)
- `data-service/cg_recognition.py` — two-tier orchestrator shape, bounded retry, redacted
  per-attempt logging, provider-resolved-once rule
- `data-service/cg_topology.py` — Tier-0 deterministic precedent for D-12
- `data-service/cg_schemas.py` — Pydantic v2 contract + `to_strict_json_schema()` (and its
  documented min/max stripping)
- `data-service/llm_gateway.py` — `GenerationOptions`, `negotiate_structured_output()`, pinned
  temperature
- `DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs` — the apply path; ordinal
  `ParameterId` match at L423-425, `SetSliderValue` at L450-461, per-parameter report at L163
- `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs:68-71` — where `ParameterId`
  actually comes from (input NickName), the root of JOIN A

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Slider domains are already in Neo4j.** `computgraph_publish.py:531-535` writes
  `domainMin`/`domainMax`/`domainStep` on every `:Parameter`. GHIN-01's input substrate exists.
- **The typed contract is already enforced.** `DesignStateParameterType` is exactly
  `Number | Integer | Boolean`, so GHIN-02 is guaranteed by the type system. Mapping is
  `Float→Number`, `Integer→Integer`, `Boolean→Boolean`; `Text`/`Geometry` are excluded by contract.
- **`contextJson` on `:Algorithm`** (Phase 36) preserves the full `cgContextJson` including raw
  `Nodes[]`/`Wires[]` — the substrate D-02's derivation walks, available from the graph without
  Rhino running.
- **`DesignStatePayloadV2Serializer`** round-trips ParamStates; invariants at L132-144 (`StateId`
  required, `CapturedAtUtc` required ISO-8601 round-trip) must be satisfied by generated payloads.
- **Phase 35's eval substrate** (cassette record/replay, replay-by-default, loud on miss) is the
  precedent for testing generation quality without live model calls in CI.

### Established Patterns
- Parameterized Cypher only; `project` on every node; single Neo4j DB.
- ErrorMessageTemplates What+Where+How-to-fix for every error surface.
- Rising-edge trigger for reinstatement (v2.0) — already half of GHIN-04's separation guarantee.
- ui-v2 is the UI; legacy `graph-viewer/` is archived.
- Additive-optional-field evolution over version bumps (32.1 `dgId` precedent).

### Integration Points
- `data-service/computgraph_publish.py` + `/computgraph/publish` — additive `reinstateParameterId`
  (D-01), triggers the schema-propagation checklist.
- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` + `CgNode` + `ComputgraphContextSerializer`
  — additive input-param capture (D-02, D-03).
- `llm/structure_rules.json` — new `inputBindings` sibling key (D-07).
- `ui-v2/src/screens/` Model screen — review panel (D-20).
- Metagraph `Rule` atom traversal — threshold extraction (D-10).

</code_context>

<specifics>
## Specific Ideas

- **Galapagos positioning.** Galapagos's own apply verb is literally "Re-instate" — select a
  genome, push it back into the sliders. DG's PARAMETER REINSTATE is the same architect gesture
  with a typed, persisted, provenance-carrying record instead of ephemeral solver state. Worth
  stating explicitly in the phase summary; it is a defensible dissertation line.
- **Row-per-candidate mental model.** The Grasshopper DSE ecosystem (Colibri `data.csv`, MIT DSE
  Design Map) converges on one row per design, parameters as columns. The Model-screen review
  panel should read that way.
- **Never overclaim.** For `geometry-required` rules the honest output is "here are candidates,
  the rule cannot be checked from parameters alone" — not a confidence score about geometry the
  model never evaluated.

</specifics>

<deferred>
## Deferred Ideas

- **Free design-intent text** as a generation input (GHIN-01 permits it; D-11 defers it) — natural
  fit for v10.0 Script Intelligence, which already owns generate/edit/consult.
- **Clamping with `clamped: true` provenance** — rejected for this phase (D-14). If a future phase
  finds reject+retry too lossy, this is the designed fallback, and it must be explicit and
  provenance-recorded, never silent.
- **Persisting rejected candidates as an audit trail** — rejected for MVP (D-19). Genuinely useful
  for prompt tuning and dissertation evidence; needs a retention story first.
- **Constant/Emergent parameter generation** (D-05 excludes them) — would need a different bounding
  story since neither carries a slider domain.
- **Surrogate-model determinability** — the research's third static-determinability class
  (certified surrogate bound with known error margins) is real but out of scope; D-08 admits only
  `direct-parameter` and `monotone-bound`.

</deferred>

<open_for_planning>
## Open for Planning

- **SC1 pass threshold is undefined.** Success criterion 1 ("candidates keep every parameter inside
  its recognized slider domain and satisfy the rule's limit where determinable") is the only
  criterion whose evidence is a number, and no number is set. Phase 35 shipped plumbing and only
  later discovered quality was never validated — same shape. **The planner should define the
  threshold and the fixture it is computed on before implementation**, and compute it in pytest.
  Raised in discussion; the architect chose to move to planning with it open.
- **Failure UX** — what the architect sees when generation fails outright after bounded retries
  (beyond the What+Where+How-to-fix error text).
- Whether the binding lookup gets a debug endpoint (Phase 29 `/context/debug` precedent).

</open_for_planning>

<tracking_correction>
## Tracking Correction (not a phase decision)

`.planning/ROADMAP.md` lists **Phase 37 as "Not started / 0 plans"**, but Phase 37 is fully
executed: 6 PLAN + 6 SUMMARY files, `37-VERIFICATION.md`, `37-UAT.md`, `37-REVIEW.md`, with
`data-service/cg_structure_checks.py`, `llm/structure_rules.json`, and both
`/computgraph/validate` and `/computgraph/consult` live in `app.py`. Same drift class as the
Phase 32.1 correction recorded in PROJECT.md. Worth fixing in ROADMAP.md's progress table
independently of this phase.

</tracking_correction>

---

*Phase: 38-ai-generated-grasshopper-script-inputs*
*Context gathered: 2026-07-27*

# Phase 38: AI-Generated Grasshopper Script Inputs — Research

**Researched:** 2026-07-27
**Phase requirements:** GHIN-01, GHIN-02, GHIN-03, GHIN-04
**Method:** codebase grounding via graphify + targeted file reads; external state of the art via Perplexity (4 queries, sources cited in §7)
**Status:** Complete — consumed by `/gsd-discuss-phase 38`, then `/gsd-plan-phase 38 --skip-ui`

---

## 1. Executive summary

Phase 38 is **more integration than invention**. Every upstream piece it needs already shipped:
slider domains are persisted in Neo4j (Phase 36), the typed ParamState contract is fixed and
frozen since v2.0, the LLM gateway has structured-output negotiation (Phase 35), and
PARAMETER REINSTATE is the apply path (v7.0). The phase's real work is three joins and one
honest limit.

Four findings drive the plan:

1. **Constrained decoding cannot enforce the slider domains.** `to_strict_json_schema()`
   deliberately strips `minimum`/`maximum` because neither Anthropic nor OpenAI accepts numeric
   bounds in a structured-output schema ([cg_schemas.py:205-221](../../../data-service/cg_schemas.py#L205-L221)).
   The external SoA says constrained decoding is the *only* generation-time guarantee — so
   Phase 38 has no generation-time guarantee available and **must** be
   generate → validate → reject/retry, with clamping only as a named fallback.
2. **There is an unmapped identity join between Computgraph Parameters and ParamState
   parameters.** Generation reads Computgraph `Parameter` nodes (keyed by `cgId`/`dgId`, named
   from the annotation convention). Application matches by `ParameterId`, which is the
   PARAMETER STATE component's **input NickName**. Nothing guarantees these coincide. This is
   the single biggest un-scoped risk in the phase and the roadmap does not mention it.
3. **"Satisfy the rule's limit where determinable" (SC1) needs a definition before it can be
   tested.** The literature gives a clean, implementable one (§4.3): a rule is statically
   determinable iff the constrained metric is a direct parameter, a provable monotone bound over
   parameters, or a certified surrogate bound. Otherwise it is a geometry-level rule and the
   generator must say so rather than pretend.
4. **Candidate diversity needs an explicit axis, not temperature.** A single structured call
   asking for N candidates collapses toward one solution family unless each candidate is assigned
   a distinct generation strategy.

---

## 2. What already exists (verified in-repo)

### 2.1 The input side — Computgraph Parameters carry the domains

Phase 36 already persists everything GHIN-01 needs to read:

| Property on `:Parameter` | Written at | Source |
|---|---|---|
| `paramKind` (Variable/Constant/Emergent) | [computgraph_publish.py:531](../../../data-service/computgraph_publish.py#L531) | `CgParameter.Kind` |
| `dataType` (Float/Integer/Text/Boolean/Geometry) | [computgraph_publish.py:532](../../../data-service/computgraph_publish.py#L532) | `CgParameter.DataType` |
| `domainMin` / `domainMax` / `domainStep` | [computgraph_publish.py:533-535](../../../data-service/computgraph_publish.py#L533-L535) | `SliderDomain` |
| `dgId` | Phase 32.1 | `CgContextDgIdAssigner` |

The model side is [CgParameter.cs](../../../DG/src/DG.Core/Models/Computgraph/CgParameter.cs):
`SliderDomain { Min, Max, Step }` (L30-37), and `CgParameter { Id, Kind, Name, DataType?,
Domain?, MemberIds, Source, Provider?, Model?, Confidence?, DgId? }` (L43-78).

**Two caveats the planner must handle:**
- `DataType` and `Domain` are both **nullable** — inference from the underlying component can
  fail (CgParameter.cs:51-54). A Variable parameter with a null domain is unbounded and cannot
  be safely sampled; it must be reported, not guessed.
- The Computgraph enum is 5-valued (Float/Integer/Text/Boolean/Geometry) but ParamState accepts
  only 3 (§2.2). Text and Geometry parameters are **out of scope by contract** and need an
  explicit exclusion path, not a crash.

### 2.2 The output side — the ParamState contract is frozen

[DesignStateParameter.cs](../../../DG/src/DG.Core/Models/DesignStateParameter.cs):

```
DesignStateParameterType = Number | Integer | Boolean
DesignStateParameter { ParameterId, DisplayName, Type, NumberValue?, IntegerValue?, BooleanValue? }
ParamState { StateId, CapturedAtUtc, Parameters }
```

This is exactly GHIN-02's "Number/Integer/Boolean only, per the standing v2.0 typed-state
decision" — the requirement is already enforced by the type system. Mapping is therefore:
`Float → Number`, `Integer → Integer`, `Boolean → Boolean`, `Text`/`Geometry` → **excluded**.

Serialization round-trip is [DesignStatePayloadV2Serializer.cs](../../../DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs)
— `ToDto` L263-269, `FromDto` L334-352, invariants enforced at L132-144 (`StateId` required,
`CapturedAtUtc` required and must be ISO-8601 round-trip). A generated candidate must satisfy
both or it will not deserialize plugin-side.

### 2.3 The apply side — PARAMETER REINSTATE

[ParameterReinstateComponent.cs](../../../DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs):
- Matches target to source by `ParameterId`, **ordinal string equality** (L423-425).
- Writes via `slider.SetSliderValue(value)` (L450-461).
- Reads the live slider's own min/max when resolving (L374-382) — so the canvas re-clamps
  independently of anything we generate.
- Emits a per-parameter report `(ParameterId, Status, Detail)` (L163) — this is the "per-parameter
  ReStatus reporting" in the roadmap's SC2.

**No new apply mechanism is needed or wanted** (roadmap deliverable 4 says exactly this).

### 2.4 The LLM side — reuse Phase 35's stack wholesale

Phase 35 built the infrastructure this phase should mirror rather than reinvent:

- [llm_gateway.py](../../../data-service/llm_gateway.py) — `GenerationOptions` (L74),
  `LLMAdapter` (L315), `AnthropicAdapter` (L345), `OpenAIAdapter` (L423), `OllamaAdapter` (L512),
  plus `negotiate_structured_output()` and pinned temperature from plan 35-07.
- [cg_schemas.py](../../../data-service/cg_schemas.py) — the Pydantic-v2-contract +
  `to_strict_json_schema()` pattern.
- [cg_recognition.py](../../../data-service/cg_recognition.py) — the orchestrator shape:
  provider resolved **once** before the retry loop, `adapter.generate()` in-process (never a
  re-POST to `/llm/generate`), bounded retry, redacted per-attempt logging.

That last constraint is a Phase 35 cross-cutting rule and applies here verbatim: re-POSTing
would let a settings change silently switch models between attempts.

---

## 3. The three joins Phase 38 must design

### 3.1 JOIN A — Computgraph Parameter → ParamState ParameterId ⚠️ **highest risk**

**The problem, precisely:**

| Side | Identity | Where it comes from |
|---|---|---|
| Computgraph `Parameter` | `cgId` / `dgId`; `name` from convention group | `11_Var_SpansCount` → name `SpansCount` |
| ParamState parameter | `ParameterId` | the PARAMETER STATE component's **input NickName** ([ParameterStateComponent.cs:68-71](../../../DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs#L68-L71), documented at L18-19) |

Nothing in the codebase forces `SpansCount` (convention name) to equal the NickName the
architect typed on the PARAMETER STATE input. If they differ, a generated candidate is
well-formed, passes every validator, and then **silently no-ops on reinstate** — the worst
possible failure shape, because ReStatus will report a miss per parameter but the candidate
looked valid all the way through.

**Three resolutions (a discuss-phase decision, D-candidate):**

- **(a) Convention** — document "the `_Var_` name must equal the PARAMETER STATE NickName".
  Zero code, brittle, breaks silently on rename.
- **(b) Explicit mapping** — persist a `Parameter.reinstateParameterId` property (or a
  binding node) at publish time. Cheap to query, needs a Phase 36 schema addition and therefore
  the full schema-propagation checklist.
- **(c) Topology join** — resolve `CgParameter.MemberIds` → slider component → the
  PARAMETER STATE input wired to it, via the published `PARAM_LINK`/`Interface` edges. No new
  schema, most robust, most work, and only resolvable when the wiring was captured.

Recommendation to put to the architect: **(b)** as the contract with **(c)** as the resolver
that populates it, and a validation error — never a guess — when neither resolves.

### 3.2 JOIN B — rule → the parameters it actually constrains

A rule like `R_URB_HEIGHT_MAX_75_V` names a *metric* (height), not a parameter. Selecting which
Computgraph Parameters are in play is a Metagraph↔Computgraph join. Phase 29's `dg_context.py`
assembler is the right seam; Phase 37's rule-mapped structural checks build the adjacent
mapping shape and land first in the dependency order — worth reading 37's plans before
committing to a mechanism here.

### 3.3 JOIN C — accepted candidate → stored ParamState → VALIDATION GRAPH read

SC2 requires the round-trip "stored as ParamState → visible in VALIDATION GRAPH reads → applied
via PARAMETER REINSTATE". The read path exists —
`ValidationGraphComponent.ToPublicParamState()` (L255). The open question is **where an
accepted candidate lives before it becomes part of a DesignState**: a standalone ParamState node,
or a full DesignState with only a ParamState limb. The v2 payload permits a ParamState-only
DesignState (`ParamStates` is an independent list, L467), so both are legal.

---

## 4. External state of the art

### 4.1 Bounds enforcement — the decisive finding

Perplexity (constrained decoding vs JSON Schema vs clamping) is unambiguous: **constrained
decoding is the only mechanism that guarantees in-range values at generation time**; JSON Schema
`min`/`max` is validation, not generation; clamping is repair that "silently changes the model's
output after the fact, which can preserve range but break the model's intended distribution or
meaning." Recommended stack: constrained decoding for hard bounds → JSON Schema for contract →
clamping only as last-resort recovery.

**Collision with this codebase:** the first layer is unavailable. `to_strict_json_schema()`
strips numeric bounds by design (cg_schemas.py:208-213), and — independently — the bounds here
are **per-parameter and dynamic** (each slider has its own min/max/step), which a static schema
could not express even if the providers accepted `minimum`.

**Therefore the Phase 38 architecture is forced:**

1. Structured output for **shape** only (reuse `to_strict_json_schema`).
2. A **dynamic validator** built per request from the actual parameter set — checks
   `domainMin ≤ v ≤ domainMax`, step alignment, and type match. This is new code; it has no
   Phase 35 analog because recognition had no numeric domains.
3. **Reject + bounded retry** with the violation list fed back (the Phase 29
   validator-feedback pattern, already proven).
4. **Clamping**, if adopted at all, must be an explicitly-flagged, provenance-recorded fallback
   — never silent. Recommend defaulting it **off**.

### 4.2 Candidate-set diversity

Single call for N candidates risks mode collapse; N separate calls give independence at N× cost.
The literature's practical answer: a single structured request **where each candidate is assigned
a distinct generation strategy** (e.g. conservative / balanced / exploratory / edge-case-aware),
moderate temperature rather than maximum entropy, validate all, then re-sample only rejected or
near-duplicate items. Temperature helps up to ~1.0 and degrades past it.

Concrete implication: the request schema should carry a per-candidate `strategy` field, and
near-duplicate detection needs a distance definition over parameter vectors (normalize each
parameter to its domain, then L1/L∞) — otherwise "4 candidates" can be four copies.

### 4.3 When is a rule statically determinable? — definition for SC1

The roadmap's SC1 says candidates must "satisfy the rule's limit **where determinable**". The
literature gives a testable definition. A rule is statically determinable from parameters alone
iff the constrained metric is:

1. **a direct parameter** (`height = towerHeightSlider`), or
2. **a provable monotone expression** over parameters with bounds on every term
   (`height = base + floorCount × floorPitch` ⇒ `floorCount_max × floorPitch_max + base ≤ 75`
   suffices), or
3. **a certified surrogate bound** with known error margins.

Otherwise the metric depends on emergent geometry (intersections, offsets, booleans, topology
changes) and **requires evaluation** — the parameter set alone does not determine it.

The recommended pipeline shape is "parameter filters first, geometry validators second". For
Phase 38 this means the generator must classify each rule into `determinable` /
`not-determinable` and report the classification with the candidate. Claiming satisfaction for a
geometry-level rule would be a fabrication, and the phase's whole credibility rests on not doing
that.

### 4.4 Prior art in the Grasshopper ecosystem

Design-space-exploration tools converge on two storage models: **CSV/row-per-design**
(Colibri/TT Toolbox `data.csv`, MIT DSE `Design Map`) versus **solver-internal state**
(Wallacei genomes, Galapagos). Notably, **Galapagos's own apply verb is literally "Re-instate"**
— select a genome, push it back into the sliders. DG's PARAMETER REINSTATE is the same gesture
with a typed, persisted, provenance-carrying record instead of ephemeral solver state, which is
a defensible positioning line for the dissertation and worth stating in the phase summary.

The ecosystem precedent also supports the row-per-candidate mental model for the ui-v2 review
surface: candidates as rows, parameters as columns.

---

## 5. Risks and landmines

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | JOIN A unresolved — candidates apply to nothing | SC2 fails at the last step, after everything looks green | Decide the mapping in discuss-phase; make an unresolvable parameter a hard validation error |
| R2 | Null `DataType`/`Domain` on a Variable parameter | Unbounded sampling or a crash | Exclude with a reported reason; never guess a domain |
| R3 | Text/Geometry parameters reaching the ParamState mapper | Contract violation | Filter at read time; report as out-of-scope, not as failure |
| R4 | Clamping adopted silently | Model output distorted invisibly; provenance lies | Off by default; if on, record `clamped: true` per parameter |
| R5 | Re-POST to `/llm/generate` inside the retry loop | Model can switch mid-retry | Resolve provider once, `adapter.generate()` in-process (Phase 35 rule) |
| R6 | Candidates near-duplicate | "4 candidates" is really 1 | Explicit per-candidate strategy axis + normalized-distance dedup |
| R7 | Step misalignment | `SetSliderValue` snaps; stored ≠ applied | Validate step alignment at generation, not after |
| R8 | GHIN-04 leak | Something reaches the canvas without acceptance | Generation and application in separate endpoints with no internal call path between them |

R8 deserves emphasis: GHIN-04 and SC3 are a **structural** requirement, not a UI one. The
cleanest proof is architectural — the generation endpoint must have no code path to the bridge
or to any canvas write.

---

## Validation Architecture

Three tiers, matching how the rest of this milestone is validated.

### Tier 0 — offline, deterministic, no LLM, no Neo4j, no Rhino (pytest + xUnit)

The bulk of the phase is testable here and should be:

- **Domain validator**: property-based over generated parameter vectors — for any
  `(min, max, step)` and any candidate value, in-range and step-aligned ⟺ validator passes.
  This is the SC1 mechanical half and the natural home for a property-based test.
- **Type mapping**: `Float→Number`, `Integer→Integer`, `Boolean→Boolean`; `Text`/`Geometry`
  excluded with a reason. Table-driven.
- **ParamState payload conformance**: generated payload → `DesignStatePayloadV2Serializer`
  round-trip is stable and satisfies the L132-144 invariants. Mirrors the Phase 32 round-trip
  test style.
- **Determinability classifier**: fixture rules of each class (direct / monotone / geometry-only)
  classify correctly, and a geometry-only rule is never reported as satisfied.
- **Diversity metric**: N candidates over a known parameter set exceed a minimum normalized
  pairwise distance.
- **Provenance completeness** (GHIN-03): every candidate carries source rule, provider, model,
  timestamp — assert on the object, before persistence.

### Tier 1 — live stack, cassette-backed (Docker, no Rhino)

- Recognition-eval precedent applies: **record/replay cassettes, replay by default, loud on
  miss** (Phase 35 plan 35-13). Do not let SC1 depend on a live model call in CI.
- Persistence + provenance query (GHIN-03 SC4): `MATCH` on generated ParamStates returns rule,
  model, timestamp.
- Bounded-retry behaviour: a deliberately out-of-domain LLM response is caught and retried, then
  fails with an actionable error rather than emitting a bad candidate.
- **GHIN-04 as a code-level assertion**: a test that the generation module imports nothing from
  the bridge/canvas write path.

### Tier 2 — in-Rhino, human-verify (UAT)

Only what genuinely cannot be automated:

- Accepted candidate → PARAMETER REINSTATE → sliders move; per-parameter ReStatus matches the
  expected report.
- JOIN A holds on a real definition (the Frame fixture) — every generated `ParameterId` resolves.
- SC3 observed: nothing changes on canvas until the architect accepts.

Note the standing environment caveat: the 4 `DesignStateValidationFlowTests` fail fast when Neo4j
is down and 4 `test_dg_context.py` tests fail from the host (the `neo4j` hostname resolves only
inside compose) — env-dependent, not regressions. Expect the same shape here.

**Nyquist note:** SC1 is the only success criterion whose evidence is a *number*. Phase 35 learned
this the hard way — it shipped plumbing and discovered the quality was never validated. Phase 38
should define its SC1 threshold (what fraction of generated candidates are in-domain,
step-aligned, and rule-satisfying-where-determinable) **before** implementation, and compute it
in pytest.

---

## 6. Open questions for `/gsd-discuss-phase 38`

1. **JOIN A mechanism** — convention (a), persisted mapping (b), or topology resolution (c)? (§3.1)
2. **Candidate count N** — fixed, user-supplied, or rule-dependent? Affects UI and prompt shape.
3. **Diversity strategy axis** — adopt the conservative/balanced/exploratory/edge-case framing, or
   a domain-specific one?
4. **Clamping** — off entirely, or on with `clamped: true` provenance? (Recommend off.)
5. **SC1 threshold** — what number counts as passing, and on which fixture?
6. **Storage shape** — accepted candidate as standalone ParamState, or DesignState with only a
   ParamState limb? (§3.3)
7. **ui-v2 placement** — new screen, or a panel on the existing Graph/Model screen? (Deferred
   from the UI-SPEC, skipped via `--skip-ui`.)
8. **Design-intent text path** — GHIN-01 allows "rule *or* design-intent text". Is free text in
   scope for this phase, or rules only?

---

## 7. Sources

**Codebase** (all verified this session):
`cg_schemas.py:205-221`, `computgraph_publish.py:229-239,531-535`, `CgParameter.cs:30-78`,
`DesignStateParameter.cs`, `ParamState.cs:5-12`, `DesignStatePayloadV2Serializer.cs:132-144,263-352,467`,
`ParameterReinstateComponent.cs:163,374-382,423-425,450-461`, `ParameterStateComponent.cs:18-19,68-71`,
`llm_gateway.py:74,315,345,423,512`, `cg_recognition.py`, `ValidationGraphComponent.cs:255`.

**External** (Perplexity, 2026-07-27):
- Constrained decoding vs schema validation vs clamping — JSONSchemaBench (arXiv 2501.10868);
  "Structured Output Is Not Validated Output"; CRANE (arXiv 2502.09061).
- Grasshopper DSE record formats — Colibri/TT Toolbox, MIT `gh-design-space-exploration`,
  Wallacei X, Galapagos "Re-instate" (McNeel forum).
- Static determinability — "Constraint Synthesis for Parametric CAD" (Eurographics);
  "Towards computing complete parameter ranges in parametric modeling" (arXiv 2206.08698);
  multiobjective monotonicity analysis (DTU Orbit).
- Candidate diversity — GuidedSampling (arXiv 2510.03777); "How to Mitigate Mode Collapse and
  Unlock LLM Diversity" (arXiv 2510.01171); "Do Large Language Models Produce Diverse Design
  Concepts?" (ASME JCISE).

---

*Phase: 38-ai-generated-grasshopper-script-inputs*
*Research method: graphify-oriented codebase grounding + Perplexity external SoA*

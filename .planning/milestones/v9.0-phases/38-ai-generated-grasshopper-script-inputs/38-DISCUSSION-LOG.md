# Phase 38: AI-Generated Grasshopper Script Inputs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 38-ai-generated-grasshopper-script-inputs
**Areas discussed:** Slider identity (JOIN A), Rule → parameters (JOIN B), Candidate generation, Review + storage

---

## Slider identity (JOIN A)

### Resolution mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Persist at publish time | `/computgraph/publish` writes `reinstateParameterId` on `:Parameter`; generation reads one property. Costs a Phase 36 schema addition + 8-surface propagation | ✓ |
| Resolve from contextJson topology | Walk `MemberIds` → slider → PARAMETER STATE input at generation time from the `contextJson` blob. No schema change | |
| Naming convention | Document that the `_Var_` name must equal the NickName. Zero code, brittle, fails silently on rename | |
| Persist + topology resolver | Both — publish writes the property, populated by the topology walk | |

**User's choice:** Persist at publish time
**Notes:** Follow-up investigation showed the value cannot in fact be derived from `cgContextJson v1` today — `CgNode.Nickname` is the *component* nickname and `CgWire.ToParam` is a bare instance GUID, so no per-input-param NickName exists in the envelope. This forced the source question below.

### Where `reinstateParameterId` originates

| Option | Description | Selected |
|--------|-------------|----------|
| Extractor captures input-param nicknames | `CanvasContextExtractor` additively captures each component's input params (GUID + NickName); publish derives by walking slider → wire → PARAMETER STATE input. Automatic | ✓ |
| Architect declares it on the tag | DG ENTITY TAG gains an optional "Reinstate id" input. Explicit but manual, and can drift from the real NickName | |
| Extractor captures, architect can override | Automatic default with a manual override for ambiguous wiring | |

**User's choice:** Extractor captures input-param nicknames
**Notes:** Chosen against the override variant — avoids a second path and a precedence rule.

### Envelope versioning

| Option | Description | Selected |
|--------|-------------|----------|
| Additive, stay on v1 | Optional fields, `schemaVersion` stays `cg-context-1`; old docs deserialize unchanged. Matches the 32.1 `dgId` precedent | ✓ |
| Bump to cg-context-2 | Explicit version bump; every reader needs a version branch | |

**User's choice:** Additive, stay on v1

### Unresolvable parameters

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude + flag on the candidate | Generate from what resolved; list unresolvable ones with a reason so the architect sees the gap before accepting | ✓ |
| Hard error, reject request | Refuse to generate anything if any in-scope parameter is unresolvable | |
| Generate anyway, let ReStatus report | Emit regardless; the miss surfaces at apply time — the silent-no-op failure mode | |

**User's choice:** Exclude + flag on the candidate

### Eligible parameter kinds

| Option | Description | Selected |
|--------|-------------|----------|
| Variable only | Matches the roadmap deliverable; Constants are fixed presets, Emergent are computed outputs, neither has a domain | ✓ |
| Variable + Constant | Widens the design space but contradicts what "Constant" means and has no domain to bound it | |

**User's choice:** Variable only

---

## Rule → parameters (JOIN B)

### Parameter selection

| Option | Description | Selected |
|--------|-------------|----------|
| Declarative mapping file | Deterministic, inspectable, no LLM in selection | |
| LLM proposes, validated | Model returns the subset, validated against the published set. Non-deterministic | |
| Architect selects in ui-v2 | Manual tick-list; zero inference | |
| Mapping file + architect override | Deterministic default with a human escape hatch in the review surface | ✓ |

**User's choice:** Mapping file + architect override

### Determinability handling

| Option | Description | Selected |
|--------|-------------|----------|
| Classify and report honestly | direct-parameter / monotone-bound / geometry-required; candidates still generate but never overclaim satisfaction | ✓ |
| Refuse non-determinable rules | Narrow and unambiguous, but excludes most real architectural rules | |
| Best-effort with confidence | Model-reported confidence — the fabrication risk | |

**User's choice:** Classify and report honestly

### Design-intent free text

| Option | Description | Selected |
|--------|-------------|----------|
| Rules only this phase | Keyed to `Rule_Id`; clean provenance and well-defined determinability. Defers free text to v10.0 | ✓ |
| Both rules and free text | Matches GHIN-01's wording literally but nullifies `sourceRuleId` and leaves nothing to classify | |

**User's choice:** Rules only this phase

### Mapping file ownership

| Option | Description | Selected |
|--------|-------------|----------|
| 38 creates, 37 extends | Premised on Phase 37 being unplanned | |
| Separate files | Two `Rule_Id`-keyed artifacts | |
| Re-sequence — 37 first | Reorder the roadmap | |

**User's choice:** *(free text)* "Phase 37 already executed. So act it as-is"
**Notes:** Correct — verification found 6 PLAN + 6 SUMMARY files, `37-VERIFICATION.md`, `37-UAT.md`, plus `cg_structure_checks.py`, `llm/structure_rules.json` and both endpoints live. The ROADMAP progress table showing "Not started / 0 plans" is stale. All three offered options were premised on a false state and were discarded; the question was re-asked against the real shipped artifact.

### Binding home (re-asked against shipped Phase 37)

| Option | Description | Selected |
|--------|-------------|----------|
| Sibling key in structure_rules.json | New top-level `inputBindings` array. Verified additive-safe — `load_structure_rules()` only requires `mappings` to be a list and returns the full payload, so Phase 37 needs zero code change | ✓ |
| Separate `llm/input_bindings.json` | Own file and loader; cleanest separation, second artifact to sync | |
| New operation in `mappings[]` | Would modify shipped verified code; every operation there compiles to a Cypher *check*, which a binding is not | |

**User's choice:** Sibling key in structure_rules.json

### Threshold source

| Option | Description | Selected |
|--------|-------------|----------|
| Read from the Rule's SWRL atoms | Single-authoring upheld; editing the rule automatically changes what candidates must satisfy | ✓ |
| Denormalize into the binding | Fast lookup but violates single-authoring and reintroduces exactly the keys `_FORBIDDEN_PARAM_KEYS` rejects | |

**User's choice:** Read from the Rule's SWRL atoms
**Notes:** Driven by `spec/RULE-PARTITION-POLICY.md` (normative: SWRL VALIDATOR owns quantitative design-compliance rules, single-authoring principle) and Phase 37's encoded `_FORBIDDEN_PARAM_KEYS` fence.

---

## Candidate generation

### Generator architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic sampler + LLM | Tier 0 samples valid in-domain points; LLM selects, adjusts, explains. Guarantees a floor even if the model is useless | ✓ |
| LLM-only with retry | Simpler single path, but no floor — the Phase 35 failure mode | |
| LLM-only, deterministic fallback | LLM-first with a safety net; two paths, unexplained fallback candidates | |

**User's choice:** Deterministic sampler + LLM
**Notes:** Chosen with Phase 35's history explicitly in view — pure-LLM extraction returned 0 proposals from 14 candidates and was fixed by exactly this hybrid.

### Diversity

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit strategy axis + dedup | Distinct strategy per candidate in one structured call, near-duplicates rejected by normalized pairwise distance | ✓ |
| Temperature only | Simplest; research says repeated samples share a solution family | |
| N separate calls | Genuine independence at N× cost; pinned temperature may return identical results anyway | |

**User's choice:** Explicit strategy axis + dedup

### Out-of-range values

| Option | Description | Selected |
|--------|-------------|----------|
| Reject + bounded retry, never clamp | Phase 29 validator-feedback pattern, then an actionable error. No silent value rewriting | ✓ |
| Clamp with provenance | Always produces a candidate but distorts meaning and hides model failure | |
| Drop the parameter, keep candidate | A partial candidate silently means a different design than proposed | |

**User's choice:** Reject + bounded retry, never clamp

### Candidate count

| Option | Description | Selected |
|--------|-------------|----------|
| Default 4, request can override | Matches the four strategy axes one-for-one; bounded as a DoS guard | ✓ |
| Architect picks each time | Maximum control, one more decision per run | |

**User's choice:** Default 4, request can override

---

## Review + storage

### Graph storage shape

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone ParamState | `:DesignState {kind:'ParamState'}` with `DS_` prefix — exactly what PARAMETER STATE produces; existing readers work unchanged | ✓ |
| DesignState with ParamState limb | Legal in the v2 payload but a half-empty DesignState is a new shape for every reader | |

**User's choice:** Standalone ParamState

### Rejected-candidate persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Only accepted persist | Cleanest read of GHIN-04; no graph pollution | ✓ |
| Persist all, flag accepted | Full audit trail, useful for tuning and dissertation evidence; needs a retention story | |

**User's choice:** Only accepted persist

### UI location

| Option | Description | Selected |
|--------|-------------|----------|
| Model screen panel | Already browses validation runs grouped by design state; reuses the existing grouping idiom | ✓ |
| Graph screen panel | Next to the Computgraph layer, but a tabular list is a different idiom from the datascape | |
| New screen | Most room to grow toward v10.0; more navigation surface than an MVP panel earns | |

**User's choice:** Model screen panel

### Provenance

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror Phase 36 + phase-specific | Phase 36 vocabulary verbatim plus `sourceRuleId`, `strategy`, `determinabilityClass` | ✓ |
| Minimal per SC4 | Just rule/model/timestamp; loses interpretability and diverges from Phase 36 | |

**User's choice:** Mirror Phase 36 + phase-specific

---

## Claude's Discretion

- Endpoint naming and request/response schema shape
- Module layout for the deterministic sampler (`cg_topology.py`-style split or single module)
- The exact normalized-distance metric and near-duplicate threshold
- Whether the binding lookup gets a debug endpoint
- Sampler strategy (grid / Latin hypercube / rule-bound-aware)

## Deferred Ideas

- Free design-intent text as a generation input → v10.0 Script Intelligence
- Clamping with `clamped: true` provenance → designed fallback if reject+retry proves too lossy
- Persisting rejected candidates as an audit trail → needs a retention story
- Constant/Emergent parameter generation → needs a different bounding story
- Surrogate-model determinability (the third static class) → out of scope

## Raised but Left Open

- **SC1 pass threshold** — flagged during the closing check; the architect chose to proceed to
  planning with it open. Recorded in CONTEXT.md `<open_for_planning>` for the planner to resolve
  before implementation.
- **Failure UX** beyond the What+Where+How-to-fix error text.

## Process Note

Intermediate `DISCUSS-CHECKPOINT.json` files were not written — all four areas completed in a
single uninterrupted session and CONTEXT.md, the canonical record, was written immediately after.

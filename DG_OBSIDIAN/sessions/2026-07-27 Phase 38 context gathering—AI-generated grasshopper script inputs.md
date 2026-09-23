# Session: Phase 38 context gathering — AI-Generated Grasshopper Script Inputs

**Date:** 2026-07-27
**Duration:** 2h (research 30m + discussion 90m)
**Output:** 38-RESEARCH.md (codebase + Perplexity SoA), 38-CONTEXT.md (22 decisions), 38-DISCUSSION-LOG.md

## Context

Phase 38 ("given a rule + published Computgraph parameter structure, generate candidate input parameter sets") sits in v9.0 AI Workflow Intelligence, downstream of Phase 36 (Computgraph persist), Phase 37 (structure validation, already executed), and parallel to Phases 39-40. Four open questions existed: (1) how generated values find their sliders (JOIN A), (2) how rules select parameters (JOIN B), (3) how candidates are generated and kept diverse, and (4) where they're stored and reviewed.

## Key findings

### Research (Perplexity MIP, 4 queries)

1. **Constrained decoding cannot enforce slider bounds here.** `to_strict_json_schema()` deliberately strips `minimum`/`maximum`; neither Anthropic nor OpenAI accepts numeric bounds in structured-output schemas. The SoA says constrained decoding is the *only* generation-time guarantee — so Phase 38 has none and **must** validate dynamically with bounded retry + rejection.

2. **Identity join risk (D-01/D-02).** ParameterId (PARAMETER REINSTATE's match key) comes from input NickName; Computgraph Parameters are keyed by convention name. Nothing forces them equal. A candidate can pass every validator and silently no-op on reinstate. **Highest risk** in the phase.

3. **Determinability now has a definition.** Research found a clean testable one: direct-parameter / provable-monotone-bound / geometry-required. Only the first two are statically checkable; the rest require evaluation.

4. **Diversity needs an axis, not temperature.** Single calls collapse to one solution family unless each candidate gets an explicit generation strategy (conservative/balanced/exploratory/edge-case). Mirrors the Phase 35 remediation.

### Phase 37 correction

Verified that Phase 37 is fully executed — 6 plans + VERIFICATION + UAT, plus `cg_structure_checks.py`, `llm/structure_rules.json`, and both `/computgraph/validate` and `/computgraph/consult` endpoints live. The `.planning/ROADMAP.md` progress table showing "Not started / 0 plans" is stale. This discovery was critical: all three options offered for "who owns the mapping file" were premised on 37 being unplanned; re-asking against the real artifact surfaced the `_FORBIDDEN_PARAM_KEYS` fence and `spec/RULE-PARTITION-POLICY.md`'s constraint that **the SWRL VALIDATOR owns quantitative design-compliance thresholds** (single-authoring principle). This drove D-10: threshold must be read from SWRL atoms, never denormalized into the binding.

## Decisions (22 total)

### JOIN A — parameter identity

- **D-01 to D-05:** `reinstateParameterId` persisted on `:Parameter` at publish; derived by walking slider → wire → PARAMETER STATE input. Extractor additively captures input-param nicknames (required — not in `cgContextJson v1` today). Stays `cg-context-1`. Unresolvable params excluded + flagged. Variable kind only.

### JOIN B — rule binding

- **D-06 to D-11:** Bindings live as `inputBindings` sibling key in `llm/structure_rules.json` (verified additive-safe, zero code changes to Phase 37). Determinability declared per binding; unmapped defaults to geometry-required. Threshold read from Rule's SWRL atoms (never denormalized — single-authoring upheld). Rules-only input (free text deferred to v10).

### Generation

- **D-12 to D-17:** Two-tier deterministic sampler + LLM (the pattern that rescued Phase 35). 4 strategy axes + normalized-distance dedup. Reject + bounded retry, **never clamp** (semantic distortion). Default 4 candidates. Provider resolved once, in-process generation.

### Review + storage

- **D-18 to D-22:** Standalone `:DesignState {kind:'ParamState'}`, only accepted persist, Model screen panel, Phase 36 provenance + `sourceRuleId`/`strategy`/`determinabilityClass`.

## Open for planning

- **SC1 pass threshold** (undefined) — Phase 35 shipped plumbing; only later discovered quality was never validated. SC1 here has the same shape (candidates keep params in-domain + satisfy rule where determinable). Planner should set the number and its fixture before implementation.

## Carried forward (won't re-ask)

- GHIN-02's typed-state constraint is already enforced by `DesignStateParameterType` (Number/Integer/Boolean only).
- `contexJson` on `:Algorithm` preserves the full envelope — substrate is available from the graph without Rhino.
- Phase 35's eval substrate (cassette record/replay) is the precedent for testing generation quality in CI.
- Rising-edge trigger for PARAMETER REINSTATE (v2.0) already covers half of GHIN-04's separation.

## Links

- [[Phase 37 execution complete—code review & verification gates pass]] — the executed phase whose mapping artifact 38 extends
- [[Phase 35 Wave 5 execution - recognition eval sweep and verification]] — the two-tier hybrid pattern 38 mirrors
- [[Phase 36 Computgraph publish avoids mint_identity]] — the upstream Computgraph publish that 38's D-01 modifies additively
- [[DG ID cross-platform identity scheme]] — the 32.1 precedent for additive versioning (D-03)
- [[Phase 37 structure validation — rule-mapping file-first]] — the Phase 37 decision on rule-mapping artifact shape

---

*Next: /gsd-plan-phase 38 --skip-ui (research auto-reused, will create VALIDATION.md)*

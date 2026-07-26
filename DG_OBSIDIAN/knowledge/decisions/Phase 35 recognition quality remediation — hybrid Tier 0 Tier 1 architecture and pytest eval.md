---
tags: [decision, v9.0, phase-35]
date: 2026-07-26
---

# Decision: Phase 35 Recognition Quality Remediation — Hybrid Tier 0+Tier 1 Architecture and pytest Fixture-Driven Eval

**Status:** Locked (AI-SPEC.md committed `bbb26e4`). Consumed by `/gsd-plan-phase 35`.

---

## The Problem

Phase 35 shipped (RCGN-01..04 all `[x]`) but ROADMAP SC1 (recognition quality) is blocked. UAT Test 1 failed: **0 proposals from 14 scoped candidates** on DeepSeek, all with circular "does not match grammar" rationales. The question: prompt defect or model-capability limit?

## The Answer (By Inspection)

**It is a prompt defect.** The sole few-shot fixture (`frame_recognition_fewshot.json`) supplies input group nicknames that already conform to the naming convention (`11_IntF_ParSplitAt`) and justifies each proposal with *"matches the Interface naming grammar."* The demonstrated latent rule is "propose when the name already matches." No untagged node ever matches — that's the definition of untagged. DeepSeek faithfully executed the demonstration.

Compounded by: no system prompt (all three adapters support `req.system`, never set); grammar presented descriptively rather than imperatively; no provider-native structured outputs.

## Decision: Hybrid Tier 0 + Tier 1 Architecture

**Tier 0 (deterministic, no LLM):**
- Topology features determine roles that are deterministic by definition.
- **Rule R1:** In-degree 0 + widget kind → VariableParam (user-manipulable input).
- **Rule R2:** In-degree 0 + source value → ConstantParam (fixed input).
- **Rule R3:** Out-degree 0 → EmergentParam (terminal output).
- **Rule R4–R6:** Pass-through + wiring patterns → Interface.
- Tier 0 outputs high-precision role assignments and abstrains where uncertain.

**Tier 1 (LLM, tightened scope):**
- Receives only the nodes Tier 0 abstained on or low-confidence.
- Focuses on semantically loaded roles: Procedure vs Pattern (require naming, grouping, intent semantics).
- Fixed few-shot (counterexample-shaped: untagged input name, correct output label).
- System prompt with explicit task statement + grammar-stated-twice (output form + explicit negative).
- Provider-native structured outputs (Anthropic strict tool use / OpenAI `json_schema` strict / DeepSeek+Ollama fall back to prose+validator).
- Confidence calibrated on reference annotation, not self-reported.

**Why this shape:**
- Research (Perplexity SOTA) is unambiguous: encode graph invariants deterministically; reserve learned models for what topology cannot decide. Avoids relearning domain-invariant rules from minimal annotations.
- Shrinks the Tier 1 prompt enough to largely defuse the hardcoded `max_tokens: 4096` truncation failure.
- Tier 0 abstention + low-confidence marking is itself a quality signal (honest uncertainty beats overconfident wrong).

## Decision: pytest Fixture-Driven Eval, No Framework

**Eval tooling:** pytest extending `data-service/tests/`, fixture-driven, record/replay LLM responses for CI determinism.

**Why no framework:** 
- The failure is not an orchestration failure; LangChain/LlamaIndex/DSPy would add a dependency without touching the actual defect.
- Codebase discipline: `cg_recognition.py` explicitly mirrors `dg_context.py`'s `generate_validated_cypher()` + `validate_cypher()` structure. Introducing a framework would fork the service into two LLM idioms.
- Pydantic v2 + provider-native structured outputs layer directly onto the existing `llm_gateway.py` adapters. Net-new runtime dependencies: **zero**.

**Reference datasets:**
- **Corpus A `frame_ablated`:** Tag-ablation of the Frame fixture (34 nodes, all 34 tagged). Regression net, harness validity check. Marked `tier0Evidence: false` (whoever adds wires also writes Tier-0 rules — 100% by construction).
- **Corpus B `urbanblock_slice`:** Fresh `cgContextJson` pull from UrbanBlock_V7 live canvas, 2–3 procedures (~60–80 nodes), hand-annotated via the Grasshopper tagging UI. The true SC1 evidence corpus.

**SC1 pass gate:** Member-set match (exact) ≥ 0.60, justified by Wilson 95% interval around p̂=0.60 (p̂=0.51 would be decided by noise at n≈30).

## Decision: Sub-Model Training Explicitly Deferred

**Evidence:** SOTA research puts the LoRA crossover at "a few hundred to low thousands of clean labels per class." Today: 1 reference annotation.

**Precondition:** RCGN-03's accept/reject/partial-accept flow is *already a labelling instrument*. Phase 36 CGPD-03 persists `source: recognized` + provider/model for every accepted proposal. The spec designs a **labelling flywheel** that turns normal use into dataset accumulation at zero marginal annotation cost. Once the flywheel accumulates evidence (100–1000s of labelled decisions), a training decision becomes evidence-based rather than speculative.

**What this phase owns:** The infrastructure for the flywheel (JSONL logging, schema mapping). Not model training.

## Cross-References

- [[sessions/2026-07-26 Phase 35 quality remediation — root-cause diagnosis and AI-SPEC design|Session note (2026-07-26)]]
- [[debugging/Phase 35 F3 grammar-as-filter inversion root cause — the few-shot itself teaches the failure|Debugging note: F3 root cause]]
- `.planning/phases/35-llm-recognition-canvas-preview/35-AI-SPEC.md` (1938 lines, all sections)

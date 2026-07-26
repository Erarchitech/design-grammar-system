---
tags: [session, v9.0, phase-35]
date: 2026-07-26
duration: 3.5 hours
---

# Session: Phase 35 Quality Remediation — Root-Cause Diagnosis and AI-SPEC Design

**Objective:** Phase 35 shipped but ROADMAP SC1 (recognition quality) is blocked. UAT Test 1 returned **0 proposals from 14 scoped candidates** with circular "does not match grammar" rationales (F3). Determine: is this a prompt defect or a model-capability limit? Design the remediation.

**Status:** ✅ COMPLETE — AI-SPEC.md (1938 lines, all 10 sections) authored and committed as `bbb26e4`.

---

## Session Outline

### 1. Diagnosis (verification by code inspection, not model swap)

**Root cause of F3:** `data-service/fixtures/frame_recognition_fewshot.json` is the sole worked example in the prompt. Its input group nicknames *already conform* to the convention (`11_IntF_ParSplitAt`) and every proposal is justified with *"matches the Interface naming grammar."* The demonstrated rule is "propose when the name already matches." No untagged node ever matches — that's what untagged means. **DeepSeek executed the demonstration faithfully.**

**Verified defects:**
- D1: No system prompt at all (`req.system` supported by all three adapters but never set in `recognize_structure()`).
- D2: Grammar presented only as a parsing spec, not as an output target.
- D3: No provider-native structured outputs (Anthropic strict tool use, OpenAI `json_schema` strict); schema conformance requested in prose only.
- D4: `max_tokens: 4096` hardcoded in all three adapters (→ UAT F1 truncation).
- D5: Node features impoverished — `componentGuid`, `isIntegerSlider`, in/out degree never computed or shown.
- D6: Temperature uncontrolled (Ollama pins 0.1; Anthropic/OpenAI default unspecified).

### 2. SOTA Research (Perplexity 3× reasoning queries)

**Query 1:** Prompt-inversion fix patterns + few-shot design + task decomposition.
- State grammar twice in different roles (as output form and as explicit negative).
- Use grammar-constrained / schema-constrained decoding, not prose + validator alone.
- Few-shot must be a counterexample to the failure mode (node whose surface name does NOT conform, classified correctly anyway).
- Task decomposition (per-node classification) more stable than whole-canvas set partitioning.

**Query 2:** Sub-model training at this data scale.
- Hybrid symbolic + statistical is the right architecture: deterministic rules for topology-determined roles, LLM for ambiguous residue.
- LoRA on 3-8B: expect embeddings+classical to beat it until you have "a few hundred to low thousands of clean labels per class."
- GNNs: premature at this scale (overfitting on small graphs is the core issue).

**Query 3:** Provider structured-output API comparison (2026).
- OpenAI `response_format: {type: json_schema, strict: true}` → schema guaranteed.
- Anthropic strict tool use → schema guaranteed on tool inputs.
- DeepSeek JSON mode → only parseability guaranteed, not schema conformance.
- Confidence calibration: verbalized confidence uncalibrated; use logprobs or empirical calibration.

### 3. Locked Decisions

**Framework:** No LLM orchestration framework. Pydantic v2 + provider-native structured outputs on the existing `llm_gateway.py` adapters. Net-new runtime dependencies: **zero**.

**Architecture:** **Hybrid Tier 0 + Tier 1**:
- **Tier 0 (deterministic, no LLM):** Topology features → Var | Const | Emg | IntF. In-degree 0 + widget kind ⇒ Variable/Constant; out-degree 0 ⇒ Emergent; pass-through ⇒ Interface.
- **Tier 1 (LLM, tightened):** Only Procedure/Pattern grouping + residue adjudication.
- Shrinks the prompt enough to largely defuse F1 truncation.

**Eval tooling:** pytest + fixtures (fixture-driven, record/replay, tag ablation, CI-deterministic).

**Sub-model training:** Explicitly deferred — premature at 1 reference annotation. RCGN-03's accept/reject flow is *already a labelling instrument*; the spec builds the flywheel.

### 4. AI-SPEC Authorship (4-step orchestrator)

**Step 1 — Framework Selection (gate):** Hybrid + pytest (locked by user choice).

**Step 2 — AI Researcher (Sections 3, 4, 4b):** Framework quick reference (this codebase's idiom + provider APIs); model config (temperature 0, output budget formula); Tier-0/Tier-1 rules (R1–R6); Pydantic v2 output model; provider-native structured-output negotiation; context-window management; cost/latency; verification that Frame fixture has 34 nodes / 1 wire (Tier 0 cannot grade on it).

**Step 3 — Domain Researcher (Section 1b):** Vertical (parametric architectural design, not generic dev tooling); stakes (Medium at recognition time / High for research validity); five rubric ingredients grounded in practitioner language; six domain failure modes (canvas-geography grouping, relay-as-Interface, abandoned branches, over-segmentation, surface-name semantics, unpublishable proposals); regulatory (none binding); n=1 self-labelling bias mitigations.

**Step 4 — Eval Planner (Sections 5, 6, 7):** Two eval corpora (Corpus A: Frame tag-ablation for harness validity; Corpus B: UrbanBlock slice for SC1 evidence); ship gate M1≥0.60 with Wilson-interval justification; 13 guardrails (5 existing+load-bearing, 8 from UAT); production monitoring via JSONL (lightweight, no Phoenix overhead for 1-user research); checklist (16/16 ticked, "not yet satisfied" list explicit).

**Blocker found & solved:** Frame fixture has only 1 wire, so Tier-0 degree rules collapse to "abstain." Eval planner discovered that a complete reference annotation *already exists in git* (all 34 nodes tagged, 2026-07-08). Solution: **tag ablation** — strip the entity tags and emit as reference, input-safe from drift.

---

## Key Findings

1. **F3 is NOT a model issue.** The few-shot itself demonstrates grammar-as-filter. Frontier model would partially mask, not fix.
2. **Grammar must be stated twice** — as output form (what to generate) and as an explicit negative (what NOT to do in reasoning). Current prompt has only the parsing spec.
3. **Tier 0 is load-bearing.** Topology determines 4/6 roles deterministically. LLM should not relearn this from 1 reference annotation.
4. **Accept/reject is a labelling instrument.** RCGN-03 already captures ground truth; the flywheel turns this into data for future sub-model training, IF the data justifies it.
5. **Reference annotation exists** but can't be directly used (circularly derives from the same Frame source). Tag-ablation solves it.

---

## Deliverables

- **35-AI-SPEC.md** (committed `bbb26e4`, 1938 lines):
  - §1 System Classification (critical failure modes, grammar-as-filter inversion root cause)
  - §1b Domain Context (vertical, stakes, rubric ingredients, failure modes, n=1 bias mitigation)
  - §2 Framework Decision (no framework; Pydantic v2 + provider APIs; Hybrid Tier 0+1; sub-model deferred)
  - §3 Framework Quick Reference (entry point pattern, topology feature extractor, 7 pitfalls with file:line)
  - §4 Implementation Guidance (Tier-0 rules R1–R6, provider structured-output negotiation, context scoping)
  - §4b AI Systems Best Practices (Pydantic output model, system/user prompt separation, grammar-stated-twice, counterexample few-shot, prompt engineering discipline, context window + cost)
  - §5 Evaluation Strategy (Corpus A tag-ablation / Corpus B UrbanBlock slice; member-set F1; SC1 gate M1≥0.60; ablation arms A0/A0f/A2/A5)
  - §6 Guardrails (13 rules: 5 existing + 8 from UAT)
  - §7 Production Monitoring (JSONL + schema, no Phoenix for 1-user research)
  - Checklist (16/16 ticked; "not yet satisfied" explicit)

---

## What's Next

`/gsd-plan-phase 35` — the planner consumes the AI-SPEC and produces detailed implementation tasks.

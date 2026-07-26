---
tags: [debugging, v9.0, phase-35, F3, root-cause]
date: 2026-07-26
---

# Debugging: Phase 35 F3 — Grammar-as-Filter Inversion — Root Cause

**Finding:** UAT Test 1 failed with 0 proposals from 14 scoped candidates, all with circular "does not match grammar" rationales.

**Verified Root Cause:** The sole few-shot fixture in the recognition prompt (`data-service/fixtures/frame_recognition_fewshot.json`) demonstrates the exact failure mode.

---

## The Evidence

### The Fixture

`frame_recognition_fewshot.json` contains:
- **Input:** two untagged Param nodes with nicknames `ParSplitAt` and `TrussConfig`.
- **Input group hints:** `{"nickname": "11_IntF_ParSplitAt", "memberIds": ["n-parsplit"]}` and `{"nickname": "11_IntF_TrussConfig", "memberIds": ["n-trussconfig-intf"]}`.
- **Expected output (rationale):** *"Param node nicknamed 'ParSplitAt', wired from procedure 11's tagged members, **matches the Interface naming grammar `<NN>_IntF_<Name>`**."*

### The Demonstrated Rule

The one example shows: input group nicknames that already conform to the annotation convention → proposal justified by "matches the naming grammar."

The **latent rule learned:** propose an entity when the node's surface name already matches the convention grammar.

### The Failure

On a genuinely untagged canvas, no node name *ever* matches the convention — that is the definition of untagged. A model faithfully imitating the demonstrated rule **must** return 0 proposals with "does not match grammar" rationales.

**DeepSeek did not fail the task. It executed the demonstration correctly.**

---

## Why This Happened

1. **Grammar conflation:** The annotation convention (`<NN>_IntF_<Name>`) was presented to the model as a **parsing specification** (what the convention looks like in the notation) rather than as a **generation target** (what names to produce).

2. **Majority-label bias:** The one demonstration is the entire inductive signal. It teaches "matching the grammar" as the decision boundary. A model learning from this sole example will treat it as ground truth.

3. **No system prompt:** No explicit task statement, no role definition, no statement like "your task is to generate proposal names that conform to this grammar." All three adapters support `req.system`; `recognize_structure()` never sets it.

4. **No negative instruction:** Nothing says "do not use the naming grammar as a filter to test candidates; every candidate is eligible unless excluded by graph evidence."

---

## The Fix (Locked in AI-SPEC.md)

**System prompt:** Explicit task statement + grammar-stated-twice:
1. As the **output form:** "generate proposal names that match this grammar."
2. As an **explicit negative:** "do not use the naming grammar to test or filter candidates."

**Few-shot redesign:** Counterexample-shaped — a node whose surface name does NOT conform, classified correctly, with the generated canonical name in a field visibly distinct from the observed name.

**Provider-native structured outputs:** Anthropic strict tool use, OpenAI `json_schema` strict. Schema conformance, not prose instruction + validator alone.

---

## Cost Control

Frontier-model swap (Claude/GPT) would **partially mask** this by overriding a bad demonstration, but would still lose the economic value of fixing the demonstration and system prompt. Research (Zhao et al., *Calibrate Before Use*; Lu et al., *Fantastically Ordered Prompts*) documents that few-shot instability and majority-label bias are solvable by design, not by bigger models.

**Buying a frontier model to avoid fixing the fixture is pure waste.**

---

## Cross-References

- `data-service/cg_recognition.py:551-602` — `_build_recognition_prompt()` assembly.
- `data-service/fixtures/frame_recognition_fewshot.json` — the fixture.
- `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` — finding F3, 2026-07-25.
- [[decisions/Phase 35 recognition quality remediation — hybrid Tier 0 Tier 1 architecture and pytest eval|Decision note (2026-07-26)]]
- [[sessions/2026-07-26 Phase 35 quality remediation — root-cause diagnosis and AI-SPEC design|Session note (2026-07-26)]]

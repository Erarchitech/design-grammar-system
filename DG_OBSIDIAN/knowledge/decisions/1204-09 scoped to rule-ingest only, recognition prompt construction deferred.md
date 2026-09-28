---
tags: [decision, v12.0, phase-1204, llm-repeatability]
date: 2026-09-28
---

# 1204-09 scoped to rule-ingest only, recognition prompt construction deferred

**Context:** Phase 1204's LLM-repeatability benchmark names two D-09 subjects — recognition (`cg_recognition.recognize_structure`) and rule-ingest (`dg_context.generate_validated_cypher`). Rule-ingest prompts could be faithfully reproduced by calling the real `POST /context/assemble` endpoint directly — the exact same call the n8n "Build LLM Prompt" node makes internally (it's a thin caller since Phase 29-05; prompt construction lives entirely in `dg_context.assemble_context()`). Recognition prompts are built by `cg_recognition._build_recognition_prompt(cg_context, scope, features, tier0, mode)` — internal state derived from Computgraph structures (the `frame_ablated`/`urbanblock_slice` corpora), with no equivalent single HTTP call to reproduce it from outside.

**Decision:** The owner chose rule-ingest only for this live capture, explicitly declining to invest the additional reverse-engineering effort recognition would need.

**Why:** Getting the recognition prompt construction wrong would not fail loudly — it would silently produce a sample that *looks* like a recognition measurement but isn't a faithful reproduction of production behavior, exactly the false-evidence risk D-28's human checkpoints exist to prevent. D-27 ("≥1 provider with k≥5 live samples, no pass threshold") only requires *a* subject at *a* provider, not both subjects — so the narrower scope still satisfies the phase's own success criteria.

**How to apply:** When a live-evidence benchmark needs to reproduce a production prompt/request faithfully, check whether the production code path is externally callable (an HTTP endpoint, a pure function taking simple inputs) before attempting to hand-reconstruct it. If it requires internal state only assembled deep inside a stateful pipeline (like `cg_recognition`'s tier0/scope/features derivation), that's a signal to either invest real effort in extracting/calling that pipeline properly, or explicitly narrow scope and document the gap — never approximate silently.

**Related:** [[knowledge/decisions/Live-infrastructure GSD plans run by the orchestrator directly, never DSH]]

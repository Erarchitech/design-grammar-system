---
tags: [debugging, mapping, phase-1303, llm]
date: 2026-10-18
status: fixed (7867f98), live re-check on the next cold start
---

# LLM-held slider was never decided and was asked again in every variant

**Symptom.** In rehearsal 2 the session CONNECTOR creates after placement (`ms-2baa20d859db`) and the V2 session (`ms-09a9cf647800`) each had 376/421 elements mapped by profiles, but still 1 open question about a slider. Each such session made a paid LLM call and waited 2–3 min («Map: 1?») before it applied by itself. The guide expected 0 questions.

**Cause.** In the first session the LLM proposal marked one of the 14 sliders («допуск привязки стоек к углам») as not a DG parameter, so its row became `unmapped` with source `llm`. `batch-parameters` asked only about the 13 suggested sliders. The owner's answer therefore covered 13, and no decision or profile covered the held one. In every later session the deterministic pass suggested it again, which left a question and triggered the LLM.

**Fix (`7867f98`).** `_parameter_questions` lists such sliders in the same question as `heldParameterIds`:
- rows without a proposal;
- title «13 слайдеров → параметры DG, 1 — не параметр (LLM)»;
- text «LLM считает не параметром DG: …».

`_decide_items` decides them together with the batch, so accepting it learns a "not a parameter" profile. Test: `test_llm_excluded_slider_is_shown_and_learned_with_the_batch`. A read-only recompute with all 18.10 profiles retired shows the held slider in the batch.

**Lesson.** Any item the LLM sets aside must still reach a human answer, or it stays undecided forever and costs an LLM call per session.

Related: [[sessions/2026-10-18 Phase 1303 proposal cards, DeGram mapping sub-tab and live rehearsal through V2|session]].

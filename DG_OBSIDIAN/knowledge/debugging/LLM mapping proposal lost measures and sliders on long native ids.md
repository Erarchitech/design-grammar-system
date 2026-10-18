---
tags: [debugging, llm, mapping, phase-1303]
date: 2026-10-18
status: fixed, verified on a live session
---

# LLM mapping proposal lost measures and sliders on long native ids

**Symptoms, in the order they appeared on the clean facade copy:**
1. With 4 000 completion tokens the reasoning model (`mimo-v2.5-pro`) spent the whole budget on hidden reasoning. The answer came back empty and truncated, with status `empty`.
2. With 24 000 tokens the call took more than the gateway's fixed 120 s, giving `PROVIDER_TIMEOUT`.
3. With a longer timeout, a live session got 6 stream classes but **0 measures and 0 sliders**, so it kept all 13 deterministic questions. The digest asked the model to copy native ids such as `gh:<doc>:measure:<32 hex>`. Validation drops every entry whose id is not in the digest. The same prompt had worked in a dry run, so the behaviour is not stable.

**Fix:**
- `MAX_TOKENS` raised to 24 000.
- `GenerationOptions.timeout_s` added. It is internal only and not part of the public `/llm/generate` body. The mapping call uses 420 s; the other callers keep their constants.
- The call runs in the background (`mapping_store.LLM_ASYNC`). The session is saved with `llm.status = pending`, and a thread later recomputes it with the proposal and the answers given in the meantime. A proposal that lands after apply is recorded but does not change the applied result.
- The digest shows short aliases (`s1…`, `m1…`, `p1…`, also in `streamsWithSameBranches`) and keeps the alias → native id map under `_ids`, which is never sent. The parser maps aliases back; native ids are still accepted.
- The prompt asks for an entry for every stream, measure and slider.

**Verification:**
- Dry run: 125 s (was 211–231 s), 7 streams + 12 measures + 14 sliders.
- Live session `ms-98a39fa841bc` from Rhino: 13 → 6 questions after 2 min 17 s; CONNECTOR showed «Map: 6?».

**Lesson.** Never ask a model to copy long machine ids. Give it short aliases and map them back in code.

Related: [[sessions/2026-10-18 Phase 1303 automatic mapping in CONNECTOR with LLM proposal and placement up to VALIDATOR|session]], `data-service/mapping_llm.py`, `data-service/llm_gateway.py`.

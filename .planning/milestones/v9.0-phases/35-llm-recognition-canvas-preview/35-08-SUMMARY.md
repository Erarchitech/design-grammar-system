---
phase: 35-llm-recognition-canvas-preview
plan: 08
subsystem: api
tags: [prompt-engineering, few-shot, system-prompt, deepseek, sc1-root-cause]

requires:
  - phase: 35-llm-recognition-canvas-preview
    provides: cg_recognition.recognize_structure (GenerateRequest builder) + llm_gateway req.system support
provides:
  - data-service/prompts/recognition_system.md — the system prompt that had never existed (prompt_version r35.4)
  - data-service/fixtures/frame_recognition_fewshot.json — counterexample-shaped replacement, {description, promptVersion, examples[]}
  - Regression guard asserting no demonstrated rationale ever cites the naming grammar again
affects: [35-12, 35-13, 35-14]

tech-stack:
  added: []
  patterns:
    - "Annotation convention stated TWICE in two roles: as an OUTPUT TARGET for suggestedName, and explicitly as NOT A FILTER"
    - "Few-shot as counterexample: every property of the harmful fixture inverted, and the inversion pinned by a regression test"
    - "Versioned, diffable prompt artifacts (promptVersion) so an eval figure names the prompt that produced it"

key-files:
  created:
    - data-service/prompts/recognition_system.md
  modified:
    - data-service/fixtures/frame_recognition_fewshot.json
    - data-service/tests/test_cg_recognition.py

key-decisions:
  - "The SC1 blocker is a demonstration-design failure plus a missing task statement, not a model capability limit — DeepSeek did not fail, it executed the demonstration"
  - "The system prompt states the annotation convention twice: as an output target to write into suggestedName, and explicitly as NOT a filter — untagged components never match it, that IS the definition of untagged, and a rationale citing the grammar as a reason is a wrong answer even if the JSON is well-formed"
  - "Includes the literal word 'json' that DeepSeek's JSON mode requires"
  - "Few-shot top-level shape changed to {description, promptVersion, examples[]} — a LIST, so dynamic few-shot retrieval later is a one-line change"
  - "Example order is deliberate and pinned (Lu et al. 2022); the harness sweeps 3 permutations of it"
  - "5 heterogeneous examples (Var / multi-member Pat / abstention / Interface / Emg) replacing 2 homogeneous Interfaces; abstention placed mid-list rather than last; varying confidence instead of a flat value"

patterns-established:
  - "Prompt artifacts are code-reviewed and version-stamped, not inline strings — a prompt change is a diff"

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "recognition_system.md (prompt_version r35.4) — the system prompt recognize_structure never sent, with graph-evidence discriminators per kind, an explicit abstention licence, and the output contract"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py — fixture-shape and prompt-loading assertions"
        status: pass
    human_judgment: false
  - id: D2
    description: "frame_recognition_fewshot.json replaced with counterexample-shaped demonstrations — non-conforming input nicknames, suggestedName visibly different from observed name, graph-evidence-only rationales"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py — regression guard: no demonstrated rationale cites the grammar"
        status: pass
    human_judgment: false
  - id: D3
    description: "Does the new prompt + few-shot actually lift SC1 recognition quality on a frontier model? Authoring is complete; the effect is unmeasured until the eval harness runs"
    requirement: RCGN-01
    verification: []
    human_judgment: true
    rationale: "35-08 was scoped as authoring only; the SC1 figure is produced by 35-13/35-14 against Corpus A/B. Prompt quality cannot be asserted from unit tests"

duration: unrecorded
completed: 2026-07-26
status: complete
---

# Phase 35-08: Prompt + Counterexample Few-Shot Summary

**The SC1 root-cause fix: a system prompt that had never been sent, plus a few-shot fixture whose every harmful property is inverted — the old one demonstrated exactly the failure it caused.**

## Performance

- **Tasks:** all tasks executed
- **Files created:** 1
- **Files modified:** 2
- **Commits:** 1

## Accomplishments

- **Named the real root cause.** The old fixture fed the model input group nicknames that *already conformed* (`11_IntF_ParSplitAt`) and justified every proposal with "matches the Interface naming grammar". That demonstration teaches: propose only when the surface name already matches. On a genuinely untagged canvas nothing matches, so faithful imitation yields zero proposals with "does not match grammar" rationales — exactly UAT F3. **DeepSeek did not fail; it executed the demonstration.**
- **Shipped the missing system prompt.** `recognize_structure` built its `GenerateRequest` without `system=` (`cg_recognition.py:653`) even though `req.system` is declared at `llm_gateway.py:40` and honoured by all three adapters. `prompts/recognition_system.md` (prompt_version `r35.4`) states the annotation convention twice — as an **output target** to write into `suggestedName`, and explicitly as **not a filter**: untagged components never match it, that is the definition of untagged, and a rationale citing the grammar as a reason is a wrong answer even if the JSON is well-formed. Adds graph-evidence discriminators per kind, an explicit abstention licence, and the output contract including the literal word "json" DeepSeek's JSON mode requires.
- **Inverted every harmful property of the few-shot.** Non-conforming input group nicknames; plainly non-canonical node nicknames; `suggestedName` visibly different from the observed name so the generation step is legible; graph-evidence-only rationales; 5 heterogeneous examples (Var / multi-member Pat / abstention / Interface / Emg) instead of 2 homogeneous Interfaces; varying confidence instead of a flat value; the abstention placed mid-list rather than last.
- **Made future retrieval cheap.** Top-level shape is now `{description, promptVersion, examples[]}` — a list, so dynamic few-shot retrieval is a one-line change later.

## Task Commits

1. **System prompt + counterexample few-shot** — `ac1029f` (feat)

## Files Created/Modified

- `data-service/prompts/recognition_system.md` (+105, new) — system prompt, `prompt_version r35.4`
- `data-service/fixtures/frame_recognition_fewshot.json` (+192/-…) — replaced
- `data-service/tests/test_cg_recognition.py` (+29) — fixture-shape assertion updated + regression guard added

## Decisions Made

- Example order is deliberate and pinned (Lu et al. 2022); the harness sweeps 3 permutations of it rather than trusting one ordering.
- The convention is stated in two roles on purpose — stating it once as a target is what previously read as a filter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `test_cg_recognition.py` fixture-shape assertion**
- **Found during:** the few-shot reshape
- **Issue:** 35-08 was scoped as pure authoring with no code changes, but `test_cg_recognition.py` asserted the old `{input, expected}` shape, so reshaping the fixture left the suite red.
- **Fix:** updated that one assertion, and added a regression guard asserting no demonstrated rationale ever cites the grammar again.
- **Files modified:** `data-service/tests/test_cg_recognition.py`
- **Verification:** full suite 302 passed (was 301)
- **Committed in:** `ac1029f`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to avoid shipping a red tree. The added guard is scope-consistent — it pins the very property the plan set out to establish.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None.

## Next Phase Readiness

- 35-12 can wire `req.system` from `recognition_system.md` and load the list-shaped few-shot.
- Whether the prompt actually lifts SC1 stays **unmeasured** until 35-13/35-14 grade it against Corpus A/B — the authoring is complete, the effect is not yet a number.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*
*Summary reconstructed from commit ac1029f during Wave 1 close-out (2026-07-26).*

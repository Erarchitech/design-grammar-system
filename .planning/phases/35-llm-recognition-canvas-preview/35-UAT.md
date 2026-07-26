---
status: testing
phase: 35-llm-recognition-canvas-preview
source: [35-VERIFICATION.md]
started: 2026-07-19T13:10:00Z
updated: 2026-07-25T00:00:00Z
---

## Current Test

number: 1
name: Frame recognition quality (ROADMAP SC1)
expected: Recognition proposes entities whose member sets match the reference annotation for the majority of blocks, with confidence + rationale.
awaiting: a frontier-class LLM (Anthropic/OpenAI) — the only remaining blocker; tests 2-5 are closed

## Test conditions (2026-07-25 session)

Group 4 of `.planning/phases/v9.0-PIPELINE-UAT.md` was run against the **UrbanBlock_V7**
canvas, NOT the Frame fixture — the Frame definition exists only as JSON test fixtures
(`DG/tests/DG.Tests/Fixtures/frame-cg-context.json`,
`data-service/fixtures/frame_recognition_fewshot.json`); there is no Frame `.gh` file on
disk (whole-profile scan negative). Active LLM: DeepSeek via the OpenAI-compatible adapter
(`deepseek-chat`, then `deepseek-v4-pro`). Because live recognition produced no usable
proposals (see finding F3), tests 2 and 6 were exercised with a **synthetic proposals
payload** (real untagged UrbanBlock node GUIDs, kinds Var/Const/Pat/Emg/IntF) posted
straight to `gh_preview_structure` — the LLM was bypassed. This validates the
preview/undo mechanism but NOT recognition quality, and not on the intended fixture.

**Session 2 (2026-07-25, same day)** continued Group 4.3-4.6 on the same UrbanBlock_V7 canvas with a
fresh 5-proposal synthetic payload chosen to make the publish gate meaningful: real untagged GUIDs for
Var (`278cc355` slider "TARGET SCR") / Const (`0516618a` Number) / IntF (`042fa6a3` Division, wired
downstream of the Var slider so PARAM_LINK is derivable) / Emg (`0483440f` Panel) / nested Pat (3
members of `11_Pat_1` so PATTERN_HOST_TO is derivable). Live LLM restored to DeepSeek but **not on the
path** — everything from 4.3 onward is LLM-free.

## Tests

### 1. Frame recognition quality (ROADMAP SC1)
expected: On the Frame definition with only Object marker + 2 Proc tags, recognition proposes entities whose member sets match the reference annotation for ≥ the majority of blocks, each with confidence + rationale; unclassifiable blocks listed in unrecognized[] (needs live LLM via the gateway).
result: blocked (quality unvalidated on available models) — 2026-07-25: PLUMBING PASSES end-to-end (bridge pull → procedure_index scoping → gateway → DeepSeek → JSON extract → schema validation; `valid:true, attempts:1` scoped to a tagged procedure). QUALITY could not be validated: `deepseek-chat` returned 0 proposals from 14 scoped candidates with circular "does not match grammar" rationales (F3); `deepseek-v4-pro` returned empty text ×3 on the large recognition prompt (F3) though it answers trivial prompts fine (probe: 28 completion tokens). Cold whole-canvas recognition (221/233 untagged) truncated JSON at the 4096-token cap ×3 (F1). Not run on the Frame fixture. Needs a frontier-class model (Anthropic/OpenAI) to grade SC1.

### 2. Preview render + undo cleanliness (ROADMAP SC2)
expected: preview_structure draws desaturated groups named `[?] <name> (<confidence>%)` + one scribble legend; a SINGLE Ctrl+Z removes every trace; clear_preview leaves no residue (no orphan groups/scribbles).
result: pass (via synthetic proposals on UrbanBlock) — 2026-07-25: 5 desaturated `[?] <name> (90%)` groups + the legend `[?] 5 proposal(s) pending -- run DG STRUCTURE CONFIRM` rendered live (NOT the unsupported-stub path). 4.2a: a single Ctrl+Z removed all 5 groups + legend together. 4.2b: clear_preview left no residue. Confidence renders as fraction×100 (0.9 → 90%) per CanvasListenerComponent.cs:316. Preview mechanism confirmed; not exercised on real LLM output or the Frame fixture.

### 3. Concurrent-solve safety (Assumption A2)
expected: Triggering preview_structure while the canvas is mid-solve does not crash Rhino or corrupt the document (InvokeOnCanvasWrite marshals correctly to the UI thread).
result: pass — 2026-07-25 (session 2). Solve forced by continuously dragging the `11_Const_Gr` integer slider (`f23be078`, 115 of 236 components downstream); `gh_preview_structure` fired on a 20 s delay so the call landed mid-solve. No crash, no document corruption; `previewed: 5` returned and all 5 desaturated groups + legend rendered once the solve settled. InvokeOnCanvasWrite marshals correctly (Assumption A2 holds).

### 4. Accept / reject / partial accept (ROADMAP SC3)
expected: DG STRUCTURE CONFIRM lists pending proposals; Accept converts preview group to a permanent Phase-34-style convention group with `source: recognized` (dg.recognized.<guid> ValueTable marker) that SURVIVES save + reopen and parses identically to a hand-made tag; Reject removes cleanly; partial accept leaves the rest pending.
result: pass — 2026-07-25 (session 2). Pending listed all 5 proposals as p0..p4. Partial accept (Accept=[p0,p1], Reject=[p2], p3/p4 untouched) → `Accepted 2, rejected 1, 2 pending`; accepted groups renamed to convention names with solid kind colours, rejected group removed, untouched pair still pending. Accept-all (`*`) then save + close + reopen: a fresh `/computgraph/context/pull` returns `11_Pat_2 SUBPLOT` (source=recognized, hostPatternId=cg:1:pat:11_1 → nesting detected, rendered purple), `TargetScr` (Variable/Integer, recognized), `Result` (Emergent/Text, recognized), `ScrRatio` (Interface/Input, recognized) — 0 parser warnings. Durability + parse-parity confirmed. One defect surfaced downstream: `Num` (Const on a bare Number component) came back with an EMPTY dataType and no warning — see F5.

### 5. Mixed accept/reject undo (WR-05 fix)
expected: One Apply with some proposals accepted and some rejected → a single Ctrl+Z restores the rejected preview groups (GH_RemoveObjectAction) and reverts the accepted restyles coherently.
result: pass — 2026-07-25 (session 2). After the mixed Apply of test 4, a single Ctrl+Z restored the rejected `p2` group and reverted the `p0`/`p1` restyles together from one GH_UndoRecord ("DG confirm structure"). WR-05 fix confirmed. Note: DG STRUCTURE CONFIRM's Pending/Status outputs do not refresh on undo (the component does not re-solve on an undo event) — force a recompute to read post-undo state; the toggle must be dropped to False first so the recompute does not create a rising edge.

### 6. Re-preview stale undo record (IN-12)
expected: Run preview_structure twice in a row (second call auto-clears the first preview). Pressing Ctrl+Z twice walks the two undo records without leaving orphan groups or resurrecting cleared previews inconsistently.
result: FAIL — 2026-07-25 (synthetic proposals, UrbanBlock): after the second preview auto-clears the first, the second Ctrl+Z throws Grasshopper's "Undo failed: Object could not be found". Root cause confirmed (F4): the auto-clear `RemovePendingPreviewObjects` removes the first preview's objects via `doc.RemoveObject(obj, false)` (no undo bookkeeping, CanvasListenerComponent.cs:386) but leaves the first preview's undo record (R1) on GH's stack. Ctrl+Z #1 undoes the second record fine; Ctrl+Z #2 undoes R1, whose add-action targets objects that were already deleted → not found. The `false` flag is correct for the explicit clear_preview (deliberately non-undoable, why test 2/4.2b passed) but wrong when a live undo record still references those objects.

## Summary

total: 6
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 1

## Findings

### F1 — Recognition has no graceful degradation on output-token truncation
Cold recognition on a large untagged canvas (UrbanBlock: 221 untagged / 233 total) makes the
LLM emit a proposal set exceeding the adapter's hardcoded `max_tokens: 4096`
(llm_gateway.py:171/232), producing unterminated JSON → `bad_json` ×3 with no actionable
hint. The `too_many_proposals` violation (cg_recognition.py:128) DOES advise "scope to a
single procedure_index", but it can only fire after valid JSON parses — the user who most
needs that advice (truncation before any valid parse) never sees it. Suggested fix: detect
truncated-JSON and surface the scoping hint directly. Severity: medium (real large-canvas
UX gap; the Frame fixture is small enough to never hit it).

### F2 — Silent full-scope fallback when procedure_index matches an empty/absent procedure
`_filtered_untagged_node_ids` (cg_recognition.py:466-489) falls back to ALL untagged nodes
when `_procedure_member_ids(procedure_index)` is empty — the caller believes they scoped and
did not, and silently hits F1. Reproduced live: a tagged Procedure 11 with 0 members caused
`procedure_index=11` to no-op back to all 214 untagged nodes. Suggested fix: return a
distinct signal (or 422) when the requested procedure has no members, rather than silently
widening scope. Severity: medium.

### F3 — Recognition produces no usable proposals on the available DeepSeek models
Two distinct failures on the same scoped prompt: `deepseek-chat` returned `valid:true` but
0 proposals from 14 candidates, rejecting every node with circular "does not match
<NN>_IntF_<Name> / Interface grammar" rationales — i.e. it treated the annotation-convention
grammar as a FILTER to test untagged nodes against rather than a TARGET vocabulary to propose
from (untagged nodes never match the naming grammar by definition — that is why they need
classifying). It also had obvious material it refused (a "FLOOR H" Number Slider → Var; bare
Number nodes → Const). `deepseek-v4-pro` returned empty text ×3 on the large recognition
prompt while answering a trivial probe fine (28 completion tokens) — a large-prompt
robustness limit, not an adapter bug (the reasoning_content hypothesis was disproved by the
probe). Open question: is the grammar-as-filter inversion a prompt defect in
`_build_recognition_prompt` or a model-capability limit? Not resolvable without a
frontier-class model (Anthropic/OpenAI) on the identical prompt. Severity: high (blocks SC1
quality validation on the deployed provider).

### F4 — Re-preview orphans the prior undo record → second Ctrl+Z crashes
See test 6. The auto-clear at the top of `HandlePreviewStructure` (WR-01 fix for registry
overwrite) removes the previous preview's objects without reconciling GH's undo stack,
leaving a dangling add-record. Undoing past the current record throws "Undo failed: Object
could not be found". This is the exact scenario IN-12 / test 6 was authored to verify, and
it fails. Does NOT block the single-preview → confirm → publish path. Suggested fix: when
auto-clearing on re-preview, also invalidate/discard the previous preview's undo record (or
compose the clear + new render into one coherent record). Severity: medium (edge case, but a
hard crash/breakpoint when hit).

### F5 — An accepted proposal can be structurally unpublishable (dataType inference gap)
`InferParameterDataType` (CanvasAnnotationParser.cs:447-488) classifies only four component kinds —
slider, value list, panel, boolean. Any other member (notably a bare **Number** component, an entirely
ordinary Constant source) yields `classified.Count == 0` → `(null, null, null)`: a null dataType **and
no warning**. Three compounding effects: (a) the context pull looks clean (0 warnings) while carrying an
invalid parameter; (b) nothing validates dataType at accept time, so Phase 35 happily converts the
proposal into a permanent group; (c) Phase 36's publish then 422s the ENTIRE payload —
`Unsupported dataType None on parameter 'cg:1:const:12_Const_Num'. ParameterShape_dataType requires it
(sh:minCount 1)` — so 11 valid nodes could not land because of 1 invalid one. Live-repro'd; worked
around by ungrouping the offending Const. Suggested fix: infer a default (Float) for numeric-ish
members OR emit a warning at parse time AND validate at accept time, plus consider per-entity rather
than all-or-nothing publish rejection. Severity: high (blocks the terminal integration gate on a
realistic canvas). Cross-phase: 34 (parser) / 35 (accept) / 36 (publish).

## Gaps

- Tests 1/2/6 not run on the intended Frame fixture (no Frame `.gh` exists — JSON fixtures
  only). Test 2 verified with synthetic LLM-bypass proposals, so preview MECHANICS are proven
  but recognition→preview integration is not. To fully close SC1/SC2 on-fixture: either
  rebuild the Frame canvas in Rhino from `frame-cg-context.json` and save it as `frame.gh`,
  or run against UrbanBlock with a frontier-class LLM configured.
- Tests 3/4/5 closed 2026-07-25 (session 2) on UrbanBlock with synthetic proposals — the accept path,
  nesting detection, durability across save+reopen and mixed-undo are all proven, but with LLM-authored
  proposals never having reached the confirm gate. Only test 1 (quality) remains, and only for want of
  a frontier-class model.
- Test 6 (F4) remains a FAIL and needs a code fix, not a retest.

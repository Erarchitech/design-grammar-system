---
status: testing
phase: 35-llm-recognition-canvas-preview
source: [35-VERIFICATION.md]
started: 2026-07-19T13:10:00Z
updated: 2026-07-26T00:00:00Z
---

## Current Test

number: 1
name: Frame recognition quality (ROADMAP SC1)
expected: Recognition proposes entities whose member sets match the reference annotation for the majority of blocks, with confidence + rationale.
awaiting: a frontier-class LLM (Anthropic/OpenAI) — the only remaining blocker; tests 2-6 are closed

## Test conditions (2026-07-25 session)

Group 4 of `.planning/phases/v9.0-PIPELINE-UAT.md` was run against the **UrbanBlock_V7**
canvas, NOT the Frame fixture — at the time the Frame definition was believed to exist only
as JSON test fixtures (`DG/tests/DG.Tests/Fixtures/frame-cg-context.json`,
`data-service/fixtures/frame_recognition_fewshot.json`), with no Frame `.gh` file on disk
(whole-profile scan negative). **Superseded 2026-07-26 — see "Frame source recovered" below.**
Active LLM: DeepSeek via the OpenAI-compatible adapter
(`deepseek-chat`, then `deepseek-v4-pro`). Because live recognition produced no usable
proposals (see finding F3), tests 2 and 6 were exercised with a **synthetic proposals
payload** (real untagged UrbanBlock node GUIDs, kinds Var/Const/Pat/Emg/IntF) posted
straight to `gh_preview_structure` — the LLM was bypassed. This validates the
preview/undo mechanism but NOT recognition quality, and not on the intended fixture.

## Frame source recovered (2026-07-26)

The "no Frame `.gh` on disk" finding above is **wrong**. Two candidate source files were
located by the architect outside the scanned tree:

| File | Size | Git |
|---|---|---|
| `docs/Bridge_Truss_V4_OntologyMapping.gh` | 126 KB | untracked, not ignored |
| `docs/Truss_Joint_V4_RH7.3dm` | 20.4 MB | untracked, not ignored |

**Identity is plausible but NOT mechanically confirmed.** Supporting evidence: Corpus A's two
procedures are `2D Truss Configuration` / `2D Footer Configuration`, and
`frame_recognition_fewshot.json` cites `Truss` ×4, `Footer` ×2, `DivideLine` ×1. Against it:
`frame-cg-context.json` records `definition.fileName = "frame.gh"`, a different name.

That name is weak evidence either way — the fixture's whole `definition` block is synthetic:
`documentId` is `3fa85f64-5717-4562-b3fc-2c963f66afa6` (the canonical Swagger placeholder UUID)
and `capturedAt` is a round midnight timestamp. It was hand-authored, not captured. Confirming
identity requires a real `/computgraph/context/pull` off the recovered file and a node-GUID
comparison against the fixture.

**Consequences:**

1. **Not usable as Corpus B.** Corpus A is derived from this same definition, and the few-shot
   examples in the live prompt are drawn from it. Grading on it would be train/test
   contamination on top of the `tier0Evidence: false` circularity that Corpus B exists to
   escape (AI-SPEC §1b). Corpus B stays on an independently-authored canvas.
2. **Corpus A could be re-grounded.** Plan 35-05 had to hand-repair `frame-cg-context.json`
   (34 nodes, originally 1 wire, both `_Proc` groups member-less). A live pull would replace a
   reconstruction with a capture. Blocked on: Corpus A is frozen (`contextSha256`,
   `frozenAtCommit`) and 35-11 is closed — this is a re-plan decision, not an edit.
3. **UAT test 1 could finally run on Frame.** It has never been executed on the intended
   fixture; the recovered file makes that possible once a frontier-class model is available.

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
result: pass — 2026-07-26 (synthetic proposals, UrbanBlock_V7, post-fix build; was FAIL on 2026-07-25). Two `preview_structure` calls in ONE listener session: `AlphaOne (90%)` + `AlphaTwo (80%)` then `BetaOne (70%)`. A `/computgraph/context/pull` between the calls proved the auto-clear really ran (canvas went `[?] AlphaOne, [?] AlphaTwo` → `[?] BetaOne`). Ctrl+Z #1 removed `BetaOne` and **restored both Alphas + the `2 proposal(s)` legend**; Ctrl+Z #2 removed them with **no "Undo failed" dialog**. Post-press pull: zero preview groups remaining. The newly-covered `preview → clear_preview → Ctrl+Z` path was verified in the same session (`GammaOne`/`GammaTwo`, `cleared: 2`): one Ctrl+Z restored both, a second removed them, no dialog. Original 2026-07-25 failure and root cause: the auto-clear removed the first preview's objects via `doc.RemoveObject(obj, false)` while leaving that preview's undo record (R1) on GH's stack, so Ctrl+Z #2 hit an add-action targeting already-deleted objects. **Testing note for future re-runs:** F4 only reproduces when `preview_structure` runs twice in the SAME listener session — a first attempt after a Rhino restart did not exercise it (the restart empties `PreviewRegistry`, so the auto-clear had nothing to remove), though it did re-confirm that single-preview undo is unregressed on the fixed build.

### 7. Accept-time publishability gate (G12 / UAT F5)
expected: Accepting a mixed set where one Var/Const/Emg proposal's members cannot be typed by the parser blocks THAT proposal only — it stays pending with a Warning naming the offending component — while every other proposal in the same Apply converts to a permanent convention group; Status reports the blocked count.
result: pending — code complete 2026-07-26 (35-09: CanvasAnnotationParser.TryInferParameterDataType public seam + per-entity gate in StructureConfirmComponent, Release build clean, 384 DG tests pass). Needs a live Rhino session to observe. Note: since 028ff0e types bare Number/Integer/Text/geometry params, a member the parser genuinely cannot type is now needed to trigger it (e.g. a component in neither the widget nor the primitive tier); the unit tests cover the inference contract directly.

## Summary

total: 7
passed: 5
issues: 0
pending: 1
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

**F4 CLOSED 2026-07-26** — fixed via `/gsd-audit-fix` (option 2: one coherent record) and **live-verified
on UrbanBlock_V7**; test 6 flipped FAIL → pass. Both the re-preview path and the newly-covered
`clear_preview` path were exercised, each with a `/computgraph/context/pull` before and after every step
so the canvas state is evidence, not recollection.
- `RemovePendingPreviewObjects` now takes the `GH_UndoRecord` that owns the removal and adds a
  `GH_RemoveObjectAction` per object *before* calling `doc.RemoveObject(obj, false)` — the same
  record-then-remove ordering `StructureConfirmComponent.ApplyToDocument` uses for its reject branch
  (WR-05, already live-proven by test 5). The legend scribble is tracked the same way.
- `HandlePreviewStructure` creates its `"DG structure proposal"` record *before* the WR-01 auto-clear
  and hands it in, so one record now spans "remove previous preview + render new one". Ctrl+Z #1 removes
  preview 2 **and restores preview 1**; Ctrl+Z #2 then undoes preview 1's own record, which finds its
  objects present and removes them cleanly. No dangling add-record, no "Object could not be found".
- `HandleClearPreview` was carrying the identical latent crash — the finding calls the untracked removal
  "correct for the explicit clear_preview", but the preview's add-record stays live after a clear too, so
  `preview → clear_preview → Ctrl+Z` throws the same error. It now pushes its own `"DG clear preview"`
  record (only when something was actually removed). **Behavior change:** the explicit clear is undoable
  where it previously was not; RCGN-02's "removes every trace" and test 2's 4.2b no-residue check are
  unaffected.
- Verified (automated): `dotnet build ./DG/DG.sln -c Release` → 0 warnings / 0 errors against the real
  Rhino 8 Grasshopper SDK; `dotnet test` → 377/377. The listener lives in `DG.Grasshopper`, which
  `DG.Tests` does not reference (GH types need the Rhino runtime), so **this path has no automated
  coverage and can only ever be closed by a live Rhino run.**
- Verified (live, 2026-07-26): binary provenance checked before testing — the deployed
  `%APPDATA%\Grasshopper\Libraries\DG\DG.gha` is byte-identical to the post-fix Release build
  (SHA256 `65927F65…`) and contains the new `"DG clear preview"` record string, and Rhino started
  12:38:57 against a 12:33:03 `.gha`, so the running instance had the fixed code. Re-preview: two
  previews → Ctrl+Z ×2, no dialog, canvas clean. Clear: preview → `clear_preview` (`cleared: 2`) →
  Ctrl+Z ×2, no dialog, canvas clean. See test 6 for the full sequence.
- Residual (not fixed, pre-existing, out of F4's scope): `PreviewRegistry` is not undo-aware. After
  Ctrl+Z #1 the canvas shows preview 1 while the registry still holds preview 2's entries, so
  `get_preview_status` and `clear_preview` are blind to the restored groups until Ctrl+Z #2 removes
  them. Making the registry undo-aware needs a custom `IGH_UndoAction`, which is a design change.

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

**Status 2026-07-26 — fixed (a) + (b) via `/gsd-audit-fix`; (c) left open by design.**
- (a) `InferParameterDataType` now has a two-tier precedence. Widget members (slider > value list >
  panel > boolean) still win outright; when a group holds none, a **primitive fallback tier**
  (number > integer > text > geometry) types bare GH params — `Number`→Float, `Integer`→Integer,
  `Text`/`String`→Text, and the 15 exact geometry param names→Geometry. The F5 repro
  (`12_Const_Num` holding a bare Number) now infers Float. Splitting the tiers also keeps the
  pre-existing "conflicting member component types" warning from firing on the very common
  slider-plus-Number-param shape.
- (a′) When members are present but none type, the parser no longer returns silently: it appends a
  `…dataType is unset and publishing will reject the payload` warning, so the context pull stops
  looking clean. Member-less groups stay quiet on purpose (tag-then-populate is a normal workflow) —
  they are caught by the pre-flight below instead.
- (b) `ComputgraphPublishComponent.PublishCanvas` gained a pre-flight that refuses to POST when any
  parameter still has a null dataType, naming every offending id in a What/Where/How-to-fix status.
  This is the accept-side guard in effect: an unpublishable group is now reported locally and
  actionably instead of arriving as a server 422 that discards the whole payload.
- (c) **Still open — per-entity instead of all-or-nothing publish rejection.** Deliberately not
  taken: partial-write semantics change the `/computgraph/publish` response contract and interact
  with MERGE idempotency and stale-entity reporting. That is a design decision, not a mechanical
  fix. With (a) and (b) in place it is no longer on the critical path — the wholesale 422 is now
  unreachable from the canvas, since the publish component fails first.
- Verification: 7 new xUnit cases in `CanvasAnnotationParserTests` (bare-Number→Float; Integer/Text/
  Brep/Curve theory; slider-beats-bare-Number with no conflict warning; untypeable-member warning).
  Full suite **375 pass / 2 fail**, the 2 being the documented `DesignStateValidationFlowTests`
  order-dependency flake (both pass in isolation — re-confirmed). `DG.sln` Release builds clean with
  `GRASSHOPPER_SDK` defined, so the pre-flight is real-path compiled, not the `#else` stub.
- **Live retest 2026-07-26 — PASS. F5 closed.** Plugin redeployed to
  `%APPDATA%\Grasshopper\Libraries\DG` (26.07 12:33) and Rhino restarted; the `Num` Const was
  re-grouped on UrbanBlock_V7 and published. Context pull reported **0 warnings** (correct now — the
  member types, so there is nothing to warn about) and the publish **succeeded**. Neo4j confirms the
  previously-impossible node:

  ```
  cg:1:const:11_Const_Num | Num | Constant | Float | domain <null> | tagged | dg:D11F0CBE622F3039
  ```

  Null domain is correct — a bare Number param has no slider range. Published subgraph is now
  **12 nodes** (Object 1, Behavior 1, Algorithm 1, Procedure 2, Pattern 2, Parameter 4, Interface 1)
  vs. 11 on 2026-07-25; the Num Const is the +1 that used to sink the whole payload. No other
  parameter changed: `11_Const_Gr` Integer, `12_Var_TargetScr` Integer, `12_Emg_Result` Text.
- Still open from this finding: only **(c)**, per-entity publish rejection — off the critical path.

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
- Test 6 (F4) closed 2026-07-26 — code fix landed and live-verified on UrbanBlock_V7 (both the
  re-preview and the newly-covered `clear_preview` undo sequences). Still synthetic proposals, still
  not the Frame fixture; the preview/undo MECHANISM is now fully proven, recognition→preview
  integration is not. No automated coverage is possible — `DG.Tests` does not reference
  `DG.Grasshopper`.
- Observation from the F4 retest (not a blocker, no fix attempted): `PreviewRegistry` is in-process, so
  a preview left on the canvas when Rhino closes becomes a **permanent orphan** on reopen — the restarted
  listener's registry never knew it, so `clear_preview` cannot reach it and `DG STRUCTURE CONFIRM` cannot
  see it; it just parses as an ordinary untagged group. One such leftover (`[?] 12_Var_TargetScr (92%)`,
  from an earlier session) sat on the canvas throughout the 2026-07-26 retest and had to be excluded by
  hand when reading results. Same root cause as the registry residual under F4.

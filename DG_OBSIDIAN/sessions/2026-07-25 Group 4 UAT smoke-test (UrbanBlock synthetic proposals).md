# 2026-07-25 — Group 4 UAT smoke-test (UrbanBlock synthetic proposals)

## Summary
Executed Group 4 (E2E spine) of v9.0-PIPELINE-UAT.md against UrbanBlock_V7 (not the intended Frame fixture — Frame exists only as JSON test fixtures; no `.gh` file on disk). Live testing revealed:
- **Plumbing passes end-to-end** (bridge pull → procedure_index scoping → gateway → recognize → validate cycle completes, `valid:true, attempts:1`)
- **Recognition quality fails** (deepseek-chat: 0 proposals / grammar-as-filter inversion; deepseek-v4-pro: empty on large prompt)
- **Preview mechanism solid** (synthetic proposals render live, 4.2a/4.2b undo/clear pass)
- **Re-preview bug found** (IN-12, test 6: second Ctrl+Z crashes with "Object could not be found")

## What was tested

- **4.1 (plumbing)** ✅ PASS (quality blocked on DeepSeek model limitations)
- **4.2a (single-undo)** ✅ PASS (5 groups + legend disappear in one Ctrl+Z)
- **4.2b (clear_preview)** ✅ PASS (no residue)
- **4.2c (re-preview stale-undo, IN-12)** ❌ FAIL (second Ctrl+Z → crash)
- **4.3–4.5** pending (session ended before DG STRUCTURE CONFIRM / publish tests)

## Key findings

**F1** — Recognition has no graceful degradation on output-token truncation (221/233 untagged canvas → bad_json ×3, scoping hint unreachable)
**F2** — Silent full-scope fallback when procedure_index matches empty procedure (live-repro'd: empty Proc 11 → silences the scope, back to 214 nodes)
**F3** — Recognition produces no usable proposals on available DeepSeek (chat: 0 proposals, grammar-as-filter inversion; v4-pro: empty text ×3)
**F4** — Re-preview orphans prior undo record → second Ctrl+Z crashes (auto-clear removes objects but leaves dangling add-record)

## Test conditions

- **Canvas:** UrbanBlock_V7 (221 untagged / 236 total nodes), tagged with Object marker + Procedure 12 (10 members)
- **LLM:** DeepSeek via OpenAI adapter (deepseek-chat, then deepseek-v4-pro)
- **Proposals:** Synthetic (bypassed recognition) — 5 real UrbanBlock node GUIDs, kinds Var/Const/Pat/Emg/IntF, confidence 0.9 each
- **Plumbing tested:** bridge → gateway → recognize → JSON extract → schema validate; preview → undo → clear

## Next steps

- Tests 4.3–4.5 (concurrent-solve, accept/reject, publish) require continuing from a clean single-preview state
- F1/F2 block cold recognition on large canvases; F3 blocks quality validation without a frontier-class model
- F4 (IN-12) needs a fix to auto-clear undo bookkeeping
- Full closure requires either Frame fixture (`.gh` file rebuild from JSON) or a different LLM

## Files modified

- `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` (results + findings + caveat re. UrbanBlock/synthetic)

---
tags: [session]
date: 2026-07-07
---

# LABEL component — Var input → Name output

**Context:** GSD audit-fix workflow was invoked with a feature request to add a new LABEL component to the Grasshopper plugin (v7.0 milestone). The audit source (`audit-uat`) returned 0 defects — no UAT files exist and all 8 VERIFICATION files passed.

**Work done:**
1. Created `LabelComponent.cs` — synchronous passthrough `GH_Component` accepting a `DG.Variable` (Var input) and outputting its `Name` as text, following the same synchronous pattern as `DesignStateDeconstructComponent`
2. Added `LabelInputMissing()` and `LabelCastFailed()` error templates to `ErrorMessageTemplates.cs`
3. Added `Label24` icon slot to `DgIcons.cs` (fallback icon until `.png` resource is embedded)

**Commit:** `82ed38e` — `feat(grasshopper): add LABEL component — shows DG.Variable name from Graph`
**Build:** ✅ 0 errors, 0 warnings
**Tests:** ✅ 214/214 passed (no regressions)

**Component contract:**
- Name: `LABEL` / `LABEL`
- Input: `Var` (DG.Variable) — a variable from METAGRAPH or RULE DECONSTRUCT
- Output: `Name` (text) — the variable's `Name` property
- Icon: `Label24` (embedded resource, fallback until `Label24.png` is added)

**Related:** [[sessions/2026-07-07 DesignStateLabel input and output]] (earlier label-related component work)

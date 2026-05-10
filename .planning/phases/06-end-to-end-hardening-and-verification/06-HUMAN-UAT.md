---
status: partial
phase: 06-end-to-end-hardening-and-verification
source: [06-VERIFICATION.md]
started: 2026-05-09T18:00:00Z
updated: 2026-05-10T18:00:00Z
---

# Phase 6: End-to-End Hardening and Verification — Human UAT

## Current Test

[awaiting human testing]

## Tests

### 1. Full State Lifecycle (INTG-01)

**Steps:**
1. Open Grasshopper in Rhino 8
2. Drop DESIGN STATE component on canvas
3. Add 2 inputs: wire a Number Slider ("Height" = 75) and a Boolean Toggle ("Active" = true)
4. Wire DESIGN STATE → Classificator.State
5. Wire existing rules → Classificator.Variables + Classificator.Values
6. Wire Classificator → Validator
7. Set Validator.SendRules = true, confirm data-service URL
8. Trigger validation (Validator.Run = true)
9. Open Model Viewer for the project
10. Verify the new run appears with state data (stateId, parameterCount = 2)
11. Switch to "Design State" grouping — verify the run appears under the correct state group

**Expected:** Run appears in both GH output and Model Viewer with state data. Design State grouping shows the run under its state group.

result: passed (with note)
note: Run appears in Model Viewer but state data not visible in sidebar. State section should show under Rule section — tracked as future improvement.

---

### 2. Legacy No-State Flow (INTG-02)

**Steps:**
1. Disconnect DESIGN STATE from Classificator (or don't wire State input at all)
2. Trigger validation (Validator.Run = true, SendRules = true)
3. Verify no errors or warnings appear on Classificator or Validator
4. Open Model Viewer
5. Verify the new run appears without state data
6. Switch to "Design State" grouping — verify the run appears under "No State" bucket

**Expected:** Validation works identically to pre-v2.0. No errors, no state in the run.

result: passed

---

### 3. Reinstatement Round-Trip (REIN-01..03)

**Steps:**
1. Capture a state with DESIGN STATE (Height = 75, Floors = 5)
2. Change sliders to different values (Height = 50, Floors = 3)
3. Use VALIDATION RUNS to retrieve runs for the project
4. Connect the States output to REINSTATE.State
5. Wire DESIGN STATE.State → REINSTATE.DesignState
6. Set REINSTATE.Apply = true (button click)
7. Verify sliders snap back to Height = 75, Floors = 5
8. Check REINSTATE.Report output — all parameters should show "Applied"

**Expected:** Sliders restored to saved values. Report shows all parameters Applied.

result: passed

---

### 4. Error Message Quality (INTG-03)

**Steps:**
1. Wire an unsupported input type (e.g. a Curve) to DESIGN STATE → check the warning bubble
2. Verify the warning says something like "Design state capture skipped: parameter 'X' has unsupported type 'Y'. Only Number, Integer, and Boolean inputs are supported."
3. Remove a slider that was previously captured in state
4. Connect that old state to REINSTATE and trigger Apply
5. Check the REINSTATE Report — verify the missing parameter shows "MissingTarget" status
6. Verify error messages contain the parameter name and a fix suggestion

**Expected:** Messages are human-readable with parameter name, what went wrong, and how to fix.

result: passed
note: Fixed in fb8079e. Warning bubble appears when Boolean True is wired to Apply input. With Button wired, only report output (no warning) — acceptable behavior since Button is momentary.

---

### 5. Grouping Switch + Resize Handle (Phase 5 pending UAT)

**Steps:**
1. Open Model Viewer with at least 2 validation runs
2. Toggle between "Rule" and "Design State" grouping in the ValidationRunsStrip
3. Verify grouping changes correctly without errors
4. Drag the resize handle between the runs strip and the viewer
5. Release and verify the new width persists
6. Reload the page — verify the resize preference survives

**Expected:** Grouping switch works. Resize handle works and persists across reloads.

result: passed

---

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Sign-Off

| # | Scenario | Status | Tester | Date | Notes |
|---|----------|--------|--------|------|-------|
| 1 | Full State Lifecycle | [x] | User | 2026-05-10 | Passed. State sidebar display tracked as future improvement |
| 2 | Legacy No-State Flow | [x] | User | 2026-05-10 | Passed |
| 3 | Reinstatement Round-Trip | [x] | User | 2026-05-10 | Passed |
| 4 | Error Message Quality | [x] | User | 2026-05-10 | Passed after fix fb8079e. Warning with Bool Toggle; report-only with Button — OK |
| 5 | Grouping Switch + Resize Handle | [x] | User | 2026-05-10 | Passed |

## Gaps

---
status: testing
phase: 38-ai-generated-grasshopper-script-inputs
source: [38-04-SUMMARY.md, 38-05-SUMMARY.md, 38-06-SUMMARY.md]
started: 2026-07-27T00:00:00Z
updated: 2026-07-27T00:00:00Z
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  gap_snapshot: "testing::scenarios=3"
---

# Phase 38 UAT — In-Rhino Verifications

These three items are the Tier 2 checks `38-VALIDATION.md`'s Manual-Only
Verifications table names — they require a live Rhino/Grasshopper session
and a human, and cannot be automated from this repository's test suites.
Every `result:` field below is left `[pending]` for the human running this
session to fill; this document is the instrument, not the record of a run
that has not happened.

## Environment Note

Before running any of the three items below: 4 `DesignStateValidationFlowTests`
(xUnit, `DG/tests/DG.Tests/`) fail fast when Neo4j is down, and 4
`test_dg_context.py` tests (pytest, `data-service/tests/`) fail when run from
the host because the `neo4j` hostname resolves only inside the Docker compose
network. Both are environment-dependent, not regressions — a UAT run should
not be blocked by them, and their presence in a pre-run `dotnet test`/
`pytest` pass does not indicate a defect introduced by this phase.

## Tests

### 1. PARAMETER REINSTATE round-trip (GHIN-02, SC2)

expected: Every parameter in the accepted candidate reports a success ReStatus and its slider shows the accepted value.
result: [pending]

Steps:

1. Publish the Frame definition (`DG COMPUTGRAPH PUBLISH`).
2. In the ui-v2 Model screen's "AI input candidates" panel, generate candidates for the `direct-parameter` fixture rule (`R_STRUCT_FRAME_HEIGHT_VAR_V`).
3. Accept one candidate.
4. Add a VALIDATION GRAPH component to the canvas and refresh it — confirm the accepted ParamState appears in its `DesignState` output (the additive `StandaloneStatesQuery` read, plan 38-05).
5. Wire that `DesignState` into PARAMETER REINSTATE and trigger it.
6. Observe the sliders move and read the per-parameter `ReStatus` output.

### 2. JOIN A on a real definition (D-01, D-02)

expected: Every eligible parameter carries a reinstateParameterId equal to the PARAMETER STATE input NickName, and any unresolvable parameter has the property absent and is reported in excludedParameters at generation with reason unresolved-reinstate-id.
result: [pending]

Steps:

1. On the Frame definition, deliberately set at least one PARAMETER STATE input's NickName to something DIFFERENT from that parameter's convention-derived name (the trivially-equal case is explicitly not what this test verifies — the divergence is the entire point of JOIN A).
2. Publish the definition.
3. Inspect the published `:Parameter` nodes (via Neo4j Browser or the `/computgraph/generate-inputs` response's `boundParameters[]`).
4. Confirm the divergent parameter's `reinstateParameterId` equals the NickName you set, not the convention-derived `parameterName`.
5. If any published parameter has no resolvable PARAMETER STATE wiring at all, confirm it appears in a `generate-inputs` response's `excludedParameters[]` with `reason: "unresolved-reinstate-id"`.

### 3. SC3 — nothing reaches the canvas before acceptance (GHIN-04)

expected: No slider value changes at any point between generation and an explicit Accept click, and the browser network tab shows zero POSTs to /computgraph/candidates/accept.
result: [pending]

Steps:

1. With the Frame definition open in Rhino/Grasshopper and its sliders at known values, open the ui-v2 Model screen's "AI input candidates" panel with the browser's network tab visible.
2. Generate candidates.
3. Reject every candidate shown, without clicking Accept on any of them.
4. Observe the Grasshopper canvas throughout steps 2–3: confirm no slider value changed at any point.
5. Confirm the network tab shows zero POST requests to `/computgraph/candidates/accept` for the whole session.

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

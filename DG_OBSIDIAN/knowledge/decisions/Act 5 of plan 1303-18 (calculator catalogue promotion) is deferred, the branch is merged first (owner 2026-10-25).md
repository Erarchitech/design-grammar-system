---
tags: [decision, phase-1303, plan-1303-18, catalogue, dgopn-05]
date: 2026-10-25
---

# Act 5 of plan 1303-18 is deferred; the branch is merged into master first

**Decision (owner, 2026-10-25 evening):** skip act 5 (live promotion of a generated calculator into the company catalogue, reuse in a second project of UAT-A, isolation for UAT-B, retire) for now; the next important step is to push `feature/mapping-mvp` and merge it into `master`.

**State left for act 5:**
- Calculator `calc_gen_e5c9bd4c09` for `ex:hasMinProjectionClearanceMm` (sha256 `bce2dcf4…`, project `str-openings-01`) is **pending**; it computes 309 of 313 boxes (minimum plan gap to a column or wall within 5 m).
- The review card reads the latest run `c40c4a59…` (2026-10-25 16:57) automatically; no run is chosen by hand. The owner did not find the card in the Web UI Mapping panel: locate it first next time.
- Companies: `str-openings-01` and `v12-hexagonal-facade-01` are UAT-A, `degram-uat-b` is UAT-B. The UAT-A catalogue already holds one **retired** entry for this property (`CC-89bf00d4…`, the 0.0 calculator of the morning).
- Resolve probe before confirmation: `v12-hexagonal-facade-01` → unsupported, "no catalogue calculator" (control).
- Probe scripts: `/tmp/v13_read_1303.py`, `/tmp/v13_resolve_1303.py` in the data-service container (recreated containers lose them; copies in the session scratchpad are not kept).
- Known display gap: the review card's verdict counts (`load_verdict_counts`) still read the legacy ValidationEntity rows (passed 125 instead of 121 + 4 without a verdict); same fix as `72846b4` applies.

**Why:** the owner found the purpose and the panel unclear and prefers to land the accepted work (plans 1303-24/25, D-66…D-72) in `master` first.

**How to apply:** plans 1303-18 and 1303-23 stay open (DGOPN-05 partial). Next session: explain the act in the UI terms the owner sees, then run steps 1-4 of 1303-18 Task 3.

Related: [[The check ends with its verdict, a non-verdict is never shown as a violation, calculators read by bounding box (Phase 1303-25, D-70 to D-72)]].

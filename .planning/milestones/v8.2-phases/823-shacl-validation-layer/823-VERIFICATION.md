---
phase: 823-shacl-validation-layer
verified: 2026-07-13
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
retroactive: true
retroactive_note: >
  Phase 823 was closed at milestone ship (2026-07-12) via the user-approved
  checkpoint in 823-06 with no formal VERIFICATION.md (recorded as a known
  verification override in MILESTONES.md). This document closes that gap:
  written 2026-07-13 during the v8.1/v8.2 gap-closure session, backed by
  fresh in-container test runs and a live SHACL round-trip — not by replaying
  the original execution logs.
---

# Phase 823: SHACL Validation Layer — Retroactive Verification Report

**Phase Goal:** Every validation run also checks DesignState/Rule instance data against SHACL shapes, with results architects can read without any semantic-web background.
**Verified:** 2026-07-13 (retroactive; see frontmatter note)
**Requirements:** SHCL-01, SHCL-02

## Goal Achievement

### Observable Truths (success criteria from v8.2 ROADMAP)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On each validation run, DesignState/Rule instance data is translated to RDF and validated against SHACL shapes, alongside (not replacing) the SWRL VALIDATOR | ✓ VERIFIED | `data-service/app.py` publish path (L1478–1483): after the existing SWRL-result persistence, `_call_shacl_validate(project, run_id)` (L1333) → `_persist_shacl_report` (L1380) writes `shaclReportJson` onto the Run node; the whole block is non-fatal by construction (a sidecar failure degrades to `status: unavailable`, never blocks the publish). Live round-trip 2026-07-13: `POST dg-reasoner:/shacl/validate {project: v8-ui-smoke}` → 200 `{conforms: true, results: [], counts: {violation: 0, warning: 0, info: 0}}` (the D-10 envelope). SWRL VALIDATOR untouched — 234/234 DG unit tests pass. |
| 2 | A documented rule-partition/precedence policy states which rule categories are checked by SHACL vs. the SWRL VALIDATOR | ✓ VERIFIED | `spec/RULE-PARTITION-POLICY.md` — normative contract: partition line (D-12: SWRL owns architect-authored design compliance; SHACL owns structural data integrity), 8-row decision table with a test for future categories, single-authoring principle with re-homing (never verdict-merging) as the remedy (D-13), enforcement discipline (D-14). |
| 3 | SHACL violations surface through ErrorMessageTemplates (What+Where+How-to-fix); raw RDF/SHACL vocabulary never reaches the architect | ✓ VERIFIED | `DG.Core/Services/ErrorMessageTemplates.cs` L164–169: `ShaclViolation(severity, what, where, howToFix)` (Phase 823, D-15). `ValidatorComponent.cs` maps findings through it, capped at Warning/Remark — comment at L131: "a SHACL data-integrity finding must never render this [as Error]"; not-evaluated runs render a Remark (L156). `ModelScreen.jsx` findings render focusLabel / what / "Where:" / "Fix:" fields (L946–949 region) — no `sh:focusNode`/`sh:sourceShape` vocabulary anywhere in the render path; missing `shaclReportJson` renders as "not checked" (L904–924), `unavailable`/`timeout` statuses get their own non-error branch. |
| 4 | Violation severity (info/warning/violation) displays with a Solibri-style treatment | ✓ VERIFIED | `ModelScreen.jsx` SHACL Data Integrity panel: three per-severity collapsible sections (`violation`/`warning`/`info` variants, L196–198 state + section map at L947–950 region) with per-severity counts from the report envelope; severity variants drive the badge treatment per 823-UI-SPEC.md (reviewed and user-approved at the 823-06 checkpoint). |

**Score:** 4/4 truths verified

### Test Evidence (fresh runs, 2026-07-13, inside the running containers)

| Suite | Command | Result |
|---|---|---|
| dg-reasoner (incl. 3 SHACL report tests + ValidGraph ABox export fidelity + live n10s/Neo4j round-trip) | `docker exec dg-reasoner python -m pytest tests -q` | **39 passed** |
| data-service (incl. reasoner proxy + publish/persist paths) | `docker exec data-service python -m pytest tests -q` | **168 passed** |
| DG C# (SWRL VALIDATOR side, SHACL DTOs in DG.Core.Validation, ValidatorComponent surfacing) | `dotnet test DG/tests/DG.Tests/` | **234 passed** (one intermittent order-dependent flake in `E2E.DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve` observed on a single run — passed in isolation and on full-suite re-run; flagged as a separate follow-up task, unrelated to SHACL) |
| Live SHACL round-trip | `httpx.post('http://localhost:8000/shacl/validate', {project: 'v8-ui-smoke'})` from inside the sidecar | 200, D-10 envelope |

### Required Artifacts

| Artifact | Expected | Status |
|---|---|---|
| `ontology/dg-shapes.ttl` | 8 version-controlled data-integrity NodeShapes | ✓ VERIFIED — `grep -c "a sh:NodeShape"` = 8; volume-mounted read-only at `/app/ontology/dg-shapes.ttl` (confirmed in-container) |
| `spec/RULE-PARTITION-POLICY.md` | Normative partition contract | ✓ VERIFIED (see truth 2) |
| `spec/DATABASE.md` | `shaclReportJson` documented as Run property | ✓ VERIFIED — L102/L108: envelope shape, pre-823 absence semantics ("not checked, never an error"), governed-by pointer |
| `data-service/app.py` | `_call_shacl_validate` + `_persist_shacl_report` in publish path, non-fatal | ✓ VERIFIED — L1333/L1380/L1478–1483 |
| `dg-reasoner` `/shacl/validate` | `{project, run_id?}` contract, run-scoped ValidGraph ABox with `owl:AllDifferent` UNA | ✓ VERIFIED — live 200 + `test_validgraph_export.py`/`test_shacl_report.py` in-container |
| `DG.Core.Validation` SHACL DTOs + `ValidatorComponent` surfacing | Warning/Remark cap, ErrorMessageTemplates wording | ✓ VERIFIED (see truth 3) |
| `ui-v2` Model screen SHACL panel | Solibri-style severity panel, missing-report handling | ✓ VERIFIED (see truths 3–4) |

### Defects found & fixed during this retroactive verification

1. **`dg-reasoner/tests/test_shacl_report.py` container-layout failure** — `SHAPES_PATH` resolved via `parents[2]` which lands on `/` in the image layout (`/app/tests`), so the 3 SHACL report tests raised `FileNotFoundError` when the suite ran in-container (the very way the 821/822 verification gates run it). Fixed 2026-07-13: repo-relative path with fallback to the volume-mounted `/app/ontology/dg-shapes.ttl`. Suite now 39/39 in-container.
2. **`data-service/tests/test_error_responses.py::test_publish_validation_missing_config` stale patch set** — patched only `app.get_integration_config`, but the publish route also has the deliberate env-driven `_auto_configure_integration` fallback; with `SPECKLE_*` env vars present (as in the container) the fallback auto-configures and the route legitimately returns 200. Fixed 2026-07-13: test now patches both lookups. Suite now 168/168 in-container.

Both are test-environment isolation defects, not product defects; fixes are in the repo source (live containers were patched via `docker cp` for the evidence runs and will pick the fix up permanently at next image build).

---

_Verified: 2026-07-13 — retroactive gap-closure session (evidence: fresh in-container pytest runs, live sidecar round-trip, source assertions)_

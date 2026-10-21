---
phase: 1303
slug: pravilo-gh-obekt
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-20
---

# Phase 1303 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Scope: plans 1303-16…18 (D-54…D-58, promotion of confirmed generated calculators, DGOPN-05) only. Plans 01–15 predate this file and are validated by their own SUMMARY/UAT records.
> Source: `1303-RESEARCH.md` § Validation Architecture (V1–V14).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 on Python 3.14 (data-service, tools/de01); node:test + browser runner (ui-v2); pytest in the DeGram clone `D:\dgb\src` for the optional component task |
| **Config file** | `data-service/tests/conftest.py`; no other config |
| **Quick run command** | `cd data-service && python -m pytest tests/test_property_scripts.py tests/test_property_calculator_llm.py tests/test_property_calculator_review.py tests/test_dg_knowledge.py tests/test_route_inventory.py tests/test_security_boundary_spec.py -q -p no:cacheprovider` |
| **Full suite command** | `cd data-service && python -m pytest tests -q -p no:cacheprovider` + `python -m pytest tools/de01/tests -q` + `npm --prefix ui-v2 test` + `npm --prefix ui-v2 run build` |
| **Estimated runtime** | ~60 s quick; ~10 min full |

Known host baseline (classify by cause, never by count): 4 `test_dg_context` endpoint failures + `neo4j:7687` DNS errors; `tools/de01/tests` golden-fixture runner failure is environmental. `test_reproducibility_scope_drift.py` is red at plan start and must turn green in Wave 0.

---

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** quick command + `tests/test_cross_project_matrix.py` + `python -m pytest tools/de01/tests -q` + `npm --prefix ui-v2 test`
- **Before `/gsd-verify-work`:** full suite classified against the baseline, `npm --prefix ui-v2 run build`, and the V13 live pass
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Bound to plans 1303-16 (store + guards), 1303-17 (resolver + routes) and 1303-18 (UI + rollout + live). The plans' `<automated>` blocks hold the exact commands; this table records the mapping.

| Check | Task(s) | Behavior | Test Type | Automated Command | File Exists | Status |
|-------|---------|----------|-----------|-------------------|-------------|--------|
| V1 | 1303-17-T1 | Resolution order file → company → stored → LLM; no LLM call on a shared hit | unit | `pytest tests/test_property_scripts.py -k shared` | ❌ W0 | ⬜ pending |
| V2 | 1303-16-T2, 1303-17-T1 | sha256/AST integrity at resolve; `calc_gen_<hex>` re-validates | unit | `pytest tests/test_property_scripts.py tests/test_property_calculator_llm.py -k "integrity or rename"` | ❌ W0 | ⬜ pending |
| V3 | 1303-17-T2 | Candidates: samples, n/min/max, verdict counts per rule | unit | `pytest tests/test_property_calculator_review.py` | ❌ W0 | ⬜ pending |
| V4 | 1303-16-T3 (store), 1303-17-T3 (routes) | Confirm gate codes (409/422/404), idempotent double confirm | unit + route | `pytest tests/test_property_calculator_store.py tests/test_property_calculator_review.py tests/test_property_calculator_routes.py` | ❌ W0 | ⬜ pending |
| V5 | 1303-16-T2/T3, 1303-17-T1, 1303-18-T2 (live) | Reject survives saves; reject A → regenerate B → reject B → regenerate A refuses A; explicit regenerate | unit + live | `pytest tests/test_property_calculator_store.py tests/test_property_scripts.py -k reject` | ❌ W0 | ⬜ pending |
| V6 | 1303-17-T1, 1303-18-T2 (live) | Vocabulary merge deterministic; module constant unmutated | unit + live | `pytest tests/test_dg_context.py -k vocabulary tests/test_dg_knowledge.py`; live `POST /context/assemble` in container | ❌ W0 / live | ⬜ pending |
| V7 | 1303-16-T3, 1303-17-T1 | Retire removes from resolve and vocabulary, cascades to project copies, keeps history | unit | `pytest tests/test_property_calculator_store.py tests/test_property_scripts.py -k retire` | ❌ W0 | ⬜ pending |
| V8 | 1303-16-T1, 1303-17-T3 | Route policy rows = SECURITY-BOUNDARY block; DeGram token refused on decisions (D-57); claim-untagged and property-edit routes cannot touch calculators | unit | `pytest tests/test_route_inventory.py tests/test_security_boundary_spec.py tests/test_cross_project_matrix.py tests/test_graph_routes.py -q` | partial | ⬜ pending |
| V9 | 1303-16-T1 | Reproducibility scope drift green with `generate_calculator` registered | unit | `python -m pytest tools/de01/tests/test_reproducibility_scope_drift.py` | ✅ (red now) | ⬜ pending |
| V10 | 1303-18-T1 | `mappingApi` helpers + review card; no request on mount | node + browser | `node --test ui-v2/tests/mapping-api.test.mjs`; `npm --prefix ui-v2 test`; `npm --prefix ui-v2 run build` | partial | ⬜ pending |
| V11 | 1303-18-T1 | Every new UI string has RU | node | `npm --prefix ui-v2 test` | ✅ | ⬜ pending |
| V12 | 1303-16-T1 | Spec rows for the new node | doc check | `grep -n CatalogueCalculator spec/DATABASE.md spec/LPG-OWL-MAPPING.md` | ❌ W0 | ⬜ pending |
| V13 | 1303-18-T3 | Live end-to-end: generate → run → confirm → reuse in a second project with zero LLM calls → retire; raw Neo4j and log excerpts embedded in evidence | live | deployed stack, evidence in `test/str-openings-01/evidence/` | manual | ⬜ pending |
| V14 | deferred | DeGram component candidates action (owner-gated, D-57) | unit (component) | in `D:\dgb\src`: `python -m pytest tests/degram -q` (command assumed) | ❌ | ⬜ deferred |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/test_property_calculator_store.py` — store lifecycle: review state survives saves, rejected-sha guard, confirm/reject/retire transactions (fake session with an explicit catalogue-node branch)
- [ ] `data-service/tests/test_property_calculator_review.py` — candidates read model
- [ ] `data-service/tests/test_property_calculator_routes.py` (or an extended route test) — policy rows, 409/422 codes, cross-project matrix
- [ ] `test_property_scripts._Session` gets a catalogue-node branch so old tests do not feed rule rows to the new loader
- [ ] `spec/REPRODUCIBILITY.md` row for `property_calculator_llm.py|generate_calculator` (turns the drift test green)
- [ ] ui-v2 browser fixture for the review card, keeping the "no request on mount" expectations

Framework install: none needed.

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|----------|------------|-------------------|
| V13 live promotion and reuse | Needs the deployed stack, a real run with SendValid and the LLM provider log | Rebuild data-service and UI from `git archive <commit>`, run the property check on a property with no catalogue entry, confirm in the Mapping panel, ingest a rule in a second project, read the provider log for zero calculator-generation calls, retire, re-ingest |
| V6 live vocabulary | 4 host endpoint tests cannot reach Neo4j | `POST /context/assemble` inside the data-service container with the service token; check the merged `computable_properties` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

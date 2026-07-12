---
phase: 821
slug: dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-12
---

# Phase 821 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (mirrors `data-service/tests/`) |
| **Config file** | none — Wave 1 scaffolds `dg-reasoner/tests/` (+ `conftest.py`) |
| **Quick run command** | `pytest dg-reasoner/tests -m "not integration"` |
| **Full suite command** | `pytest dg-reasoner/tests` |
| **Estimated runtime** | ~5s unit; ~60–120s full (integration incl. HermiT) |

---

## Sampling Rate

- **After every task commit:** Run `pytest dg-reasoner/tests -m "not integration"`
- **After every plan wave:** Run `pytest dg-reasoner/tests` (integration when docker is up)
- **Before `/gsd-verify-work`:** Full suite green (integration tiers require live neo4j + JRE)
- **Max feedback latency:** ~5 seconds (unit tier)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 821-01-01 | 01 | 1 | REAS-05 | — | Sidecar builds; `/health` 200; no hardcoded creds | build+unit | `docker compose build dg-reasoner` / `pytest dg-reasoner/tests/test_health.py` | ❌ W1 | ⬜ pending |
| 821-01-02 | 01 | 1 | REAS-05 | — | n10s procedures respond | integration | `pytest dg-reasoner/tests/test_n10s_smoke.py -m integration` | ❌ W1 | ⬜ pending |
| 821-02-01 | 02 | 2 | REAS-05 | — | ARG.pos + HAS_BODY/HEAD.order survive translation | unit | `pytest dg-reasoner/tests/test_ontology_export.py` | ❌ W1 | ⬜ pending |
| 821-03-01 | 03 | 3 | REAS-05 | — | `/reason/consistency` + `/shacl/validate` return well-formed JSON; builtin rules stripped+counted | unit | `pytest dg-reasoner/tests/test_routes.py` | ❌ W1 | ⬜ pending |
| 821-04-01 | 04 | 4 | REAS-05 | — | proxy forwards with short timeout; live round-trip no error; drift-immunity | unit+integration | `pytest data-service/tests/test_reasoner_proxy.py` / `pytest dg-reasoner/tests/test_roundtrip_integration.py -m integration` | ❌ W1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `dg-reasoner/tests/conftest.py` — shared fixtures (rdflib graph fixture, committed Turtle fixture loader, integration skip-if-neo4j-unreachable marker)
- [ ] `dg-reasoner/tests/fixtures/` — committed graph-shaped fixture (≥1 multi-atom-body rule, a BuiltinAtom, both ARG positions)
- [ ] pytest is available in the sidecar image (add to `dg-reasoner/requirements.txt`)

*Scaffolded in Wave 1 (Plan 01) alongside the sidecar skeleton.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidecar failure/hang never blocks a concurrent Speckle-publish/validation call to data-service | REAS-05 | Requires deliberately stalling the sidecar and issuing a concurrent hot-path call — awkward to automate deterministically in CI | With `dg-reasoner` paused (`docker compose pause dg-reasoner`), call `POST /reasoner/consistency` (expect fast proxy timeout, not a hang) AND concurrently a `/validation/...` call (expect normal latency). The short httpx timeout on the proxy is the automated backstop. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 1 scaffolding dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 1 scaffolds all MISSING test infrastructure references
- [x] No watch-mode flags
- [x] Feedback latency < 5s (unit tier)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-12

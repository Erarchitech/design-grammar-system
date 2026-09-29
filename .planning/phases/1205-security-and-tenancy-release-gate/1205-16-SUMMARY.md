---
phase: 1205-security-and-tenancy-release-gate
plan: "16"
subsystem: security
tags: [spec, drift-test, route-policy, rotation-runbook, secrets, deployment-profiles]
requires:
  - phase: 1205-01
    provides: secrets_policy known-default lists, check_env_file.py
  - phase: 1205-09
    provides: compose loopback bindings, multi-user override, compose parser
  - phase: 1205-10
    provides: route_policy table and route enumeration helpers
  - phase: 1205-14
    provides: relay routes and Cypher scope enforcement (82 policy rows)
provides:
  - spec/SECURITY-BOUNDARY.md normative contract with four machine-checked blocks
  - data-service/tests/test_security_boundary_spec.py drift test (spec vs code vs compose)
  - rotation runbook (D-13), known-default list (D-11), gate statement (D-18/GATE12-05)
  - pointer sections in API, DEPLOYMENT and GRASSHOPPER specs
affects: [1205-17, 1205-18, 1205-19]
tech-stack:
  added: []
  patterns: ["HTML-comment delimited fenced blocks parsed by pytest (SWRL-SUBSET / REPRODUCIBILITY pattern)"]
key-files:
  created:
    - spec/SECURITY-BOUNDARY.md
    - data-service/tests/test_security_boundary_spec.py
  modified:
    - spec/API.md
    - spec/DEPLOYMENT.md
    - spec/GRASSHOPPER.md
    - CLAUDE.md  # UNCOMMITTED by design, owner to commit
key-decisions:
  - "Blocks were generated from the code and compose at authoring time, then verified by the test, so the spec starts equal to reality and any later change fails the suite."
  - "The n8n default is listed only as its SHA-256 digest; the spec's leak scan also hashes every spec token against the digest set to catch a plaintext copy."
  - "Public-routes block is the public policy rows plus POST /connectors/heartbeat; /designstate/capture is also connector-self but is documented in section 3.2/5, not in the allowlist, per the plan."
  - "docs untouched beyond the plan: README.md legacy references are recorded as unsupported (section 7), not edited, because README is not in this plan's file list."
requirements-completed: []  # ALGN12-17..20 and GATE12-05 close only after live plans 1205-18/19
duration: ~45min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 16: Security boundary contract and drift test Summary

`spec/SECURITY-BOUNDARY.md` is the normative contract for trust zones, deployment profiles, principals, the 82-row route policy, the known-default secret list, published ports and the rotation runbook, and a new pytest fails the suite if any of its four fenced blocks drifts from the code or compose files it mirrors.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Author spec/SECURITY-BOUNDARY.md | 8495bfa |
| 2 | Spec drift test across code, routes and compose | af43ca5 |
| 3 | Pointer sections in API/DEPLOYMENT/GRASSHOPPER specs, guarded CLAUDE.md pointer | ff6b9c1 (specs); CLAUDE.md not committed |

## What was built

- **Spec** with ten sections: trust zones, two profiles (what varies and what never varies, D-19), three principals with cookie/CSRF/lifetime/role/error vocabulary, four machine-checked blocks, named carve-outs, removed and restricted routes, unsupported legacy callers, accepted gaps, the ordered rotation runbook, and enforcement/ownership (including the add-a-route procedure). The Overview states the gate is judged with `DG_DEPLOYMENT=multi-user` and blocks external multi-user evaluation only.
- **Blocks:** `public-routes` (4 rows), `route-policy` (82 rows), `known-default-secrets` (6 literals, 1 prefix, 1 sha256 digest), `published-ports` (10 local + 7 multi-user rows).
- **Drift test** (16 tests): every block compared in both directions; route-policy block also compared to the registered FastAPI routes (reusing `test_route_inventory` helpers) and published-ports to the compose parser from `test_compose_boundary`; induced-mismatch proof (removed row + changed role + extra port line = exactly 3 distinct mismatches); leak scan (no 64-hex outside the digest block, no synthetic suite secret, no known-default literal outside its block, no token hashing to a known digest).
- **Pointers:** three spec sections; API.md also drops the removed `/execution-result/latest/{workflow}` row and marks the n8n and Neo4j sections as internal/historical.

## Verification

- `python -m pytest data-service/tests/test_security_boundary_spec.py -q`: 16 passed (host).
- Host run together with `test_compose_boundary.py` and `test_route_inventory.py`: 749 passed.
- In-container (`data-service`, test file copied in with `docker cp`, no rebuild needed because the running image already holds the 82-row `route_policy`; file removed afterwards): 16 passed. Both `DG_KNOWLEDGE_REPO_ROOT=/mnt/repo` resolution and the sibling imports work in the image.
- Marker check prints `ok`. `12345678|minioadmin` appears only on the two known-default literal lines; `filter-repo`/force-push appear only in the section 9 "never" rule; the only 64-hex string is the digest line.
- Full in-container suite was not re-run (no data-service code changed); last baseline 2062 passed, 1 skipped, 12 known environmental failures.

## CLAUDE.md (owner action required, NOT committed)

Per the guarded procedure: baseline `git diff CLAUDE.md` saved to `.planning/phases/1205-security-and-tenancy-release-gate/claude-md-baseline-1205.diff` (42 insertions, 0 deletions, uncommitted and untracked) before editing. One paragraph was inserted immediately after the owner's uncommitted "Reproducibility contract" paragraph; nothing else changed. `git diff --numstat CLAUDE.md` now reads 44 insertions, 0 deletions (42 baseline + paragraph + blank line). Nothing was staged: `git diff --cached` never listed CLAUDE.md or the baseline file.

CLAUDE.md therefore carries the owner's pre-existing uncommitted lines (DSH delegation section and the Reproducibility contract paragraph) plus this pointer, and must be committed by the owner. Pointer text for the owner:

> **Security boundary contract:** `spec/SECURITY-BOUNDARY.md` governs the trust zones, the local and multi-user deployment profiles, the three principal types, the public-route allowlist and full route-policy table, the known-default secret list and the rotation runbook — consult it before adding a route, a principal, a published port or a secret, and update its machine-checked fenced blocks if such a change shifts the boundary.

## Accepted residuals recorded in the spec (with source)

Recorded in section 5 (carve-outs) or section 8 (accepted gaps) of `spec/SECURITY-BOUNDARY.md`:

- Shared-vocabulary exemption in the Cypher project-scope validator (1205-06, T-1205-06-04).
- `claim-untagged` claims every `project IS NULL` node, which would include untagged shared ontology nodes if any were ever loaded untagged; live graph had 0 untagged nodes on 2026-09-29 (1205-12). Owner decision needed on label exclusion.
- `POST /projects` reads the graph before taking the store lock (small race on the graph half of the name check); threats T-1205-12-06 and T-1205-12-07 accepted in plan 12.
- Rule/Atom merge keys are id-only under schema v4; 1205 fails closed on cross-project collision; project-qualified keys are a Schema Change Propagation follow-up (1205-06/14).
- data-service cold-start race: no healthcheck, no `service_healthy` condition, no restart policy (1205-09).
- Login rate limiting and audit logging deferred (CONTEXT Deferred Ideas); TLS/Secure-cookie, Neo4j RBAC, external IdP, MinIO 9000, read-only repo mount, project-name probing, shared vocabulary across tenants, direct-Bolt unsupported in multi-user.
- n8n `$env` access needs `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (1205-09); unverified until the live publish in 1205-18.
- Legacy callers of removed routes (unsupported, section 7): `test/smoke_e2e.sh`, `test/smoke_graph_query.sh`, `test/smoke_rules_ingest.sh`, `test/test_phase04_update_flow.sh`, `test/test_spec_llm.py`, `test/test_spec_schema.py`, archived `graph-viewer/` (including `graph-viewer/index.html`), and README.md lines 172-173 on `/execution-result/latest/{workflow}`. `spec/API.md:29` was updated in this plan; README.md was not edited (outside this plan's file list) and remains a follow-up.

## Deviations from Plan

None in behavior. Two small scope notes:

- **[Rule 2 - stale docs]** `spec/API.md` and `spec/DEPLOYMENT.md` also had statements made false by Phase 1205 (removed `latest/{workflow}` route, browser-facing n8n/Neo4j base URLs, port table bindings, `graph-viewer/entrypoint.sh` config injection). Corrected them in the same commit as the pointer sections rather than leaving contradictory text next to the new contract.
- The in-container run used `docker cp` instead of a data-service rebuild (same approach as 1205-15); the image already contained the current route policy.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes; documentation and tests only.

## Issues Encountered

None.

## Self-Check: PASSED

- spec/SECURITY-BOUNDARY.md, data-service/tests/test_security_boundary_spec.py, this SUMMARY: present.
- Commits 8495bfa, af43ca5, ff6b9c1: present in git log.
- CLAUDE.md and the baseline diff: unstaged and uncommitted as required.

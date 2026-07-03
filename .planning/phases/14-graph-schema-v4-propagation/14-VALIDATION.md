---
phase: 14
slug: graph-schema-v4-propagation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-03
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

This is a **propagation phase**: most artifacts are text/config/schema files with no
executable unit-test surface. Validation leans on (a) trivial grep/file-diff checks per
task, and (b) live smoke calls against the running Docker stack per wave. See
`14-RESEARCH.md` §Validation Architecture for the sourced detail.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (`DG.Tests`) for C#; no automated framework covers n8n / Cypher / config-file / schema-text edits — those validate via grep + live scripted HTTP against the Docker stack |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj` |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~Neo4jRuleRepositoryVariableKindTests"` (cheap smoke that the C# read-side patch didn't break existing behavior) |
| **Full suite command** | `dotnet test .\DG\tests\DG.Tests\` (E2E tests tagged `[Trait("Category","E2E")]` need the live Docker stack — run with a category filter or separately) |
| **Estimated runtime** | ~15–30s for the filtered unit run; E2E adds live-stack round-trips |

---

## Sampling Rate

- **After every task commit:** Run the relevant grep/file-diff check (near-instant) for text/config artifacts; run the filtered xUnit command for the `Neo4jRuleRepository.cs` coalesce patch.
- **After every plan wave:** Full live smoke pass — re-import both n8n workflows, one live ingest call, one live query call, one direct-Cypher spot-check of the resulting nodes.
- **Before `/gsd-verify-work`:** Full suite green + a repo-wide `grep -rn "DefState\|ObjectState"` (excluding `.git`, `graphify-out`, archived `.planning/milestones`) returns zero hits in runtime files.
- **Max feedback latency:** ~30 seconds for the fast path; wave-level live smoke may take a few minutes against Docker.

---

## Per-Task Verification Map

> Task IDs are provisional (`14-PP-TT`) until the planner finalizes plan/wave numbers.
> Threat refs point at the single real threat: destructive migration `DELETE` (T-14-MIG).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-xx | 01 | 1 | SCHM-07 | — | N/A | manual (file-diff) | `grep -n "SCHEMA VERSION" cypher_template.txt` + review v4 block | ✅ | ⬜ pending |
| 14-01-xx | 01 | 1 | SCHM-08 | — | N/A | manual (file-diff) | `grep -n "version" training/dataset_schema.json` + mirror review | ✅ | ⬜ pending |
| 14-02-xx | 02 | 2 | SCHM-09 | — | N/A | smoke (live HTTP) | POST `/n8n/webhook/dg/rules-ingest`, assert written Rule node has `.SWRL` | ❌ W0 | ⬜ pending |
| 14-02-xx | 02 | 2 | SCHM-10 | — | N/A | smoke (live HTTP) | POST `/n8n/webhook/dg/graph-query`, assert generated Cypher uses `r.SWRL` | ❌ W0 | ⬜ pending |
| 14-03-xx | 03 | 2 | SCHM-11 | — | N/A | grep + visual | `grep -rn "DefState\|ObjectState\|DataProperty" graph-viewer/` → 0; browser color check | ✅ | ⬜ pending |
| 14-04-xx | 04 | 2 | SCHM-12 | — | N/A | integration (live) | fresh publish → `MATCH (r:ValidationRun) WHERE r.ValidStatus IS NOT NULL RETURN count(r)` | ❌ | ⬜ pending |
| 14-04-xx | 04 | 2 | SCHM-12 / D-14 | — | N/A | grep + Cypher | `grep -rn "ValidationGraph" data-service DG/src DG/tests` → 0; `MATCH (n {graph:'ValidationGraph'}) RETURN count(n)` → 0 post-migration | ❌ | ⬜ pending |
| 14-05-xx | 05 | 3 | SCHM-13 | T-14-MIG | dry-run count printed; dev-only guard present before DELETE | live migration | seed → dry-run → execute → `MATCH (n:DesignState) WHERE n.kind IN ['DefState','ObjectState'] RETURN count(n)` → 0 | ❌ W0 | ⬜ pending |
| 14-05-xx | 05 | 3 | D-14.1 | T-14-MIG | dry-run count printed; dev-only guard on the 1169-node `SET` | live migration | `MATCH (n {graph:'ValidationGraph'}) RETURN count(n)` before(>0)/after(0) | ❌ | ⬜ pending |
| 14-06-xx | 06 | 3 | SCHM-14 | — | N/A | file-exists + grep | `test -f training/updated_cypher_reference_examples_v4.cypher && grep -rl "DefState\|ObjectState" test/*.json` → none | ✅ | ⬜ pending |
| 14-00-xx | 00 | 1 | SCHM-06(D-06) | — | N/A | unit (xUnit) | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~Neo4jRuleRepositoryVariableKindTests"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **Ingest smoke script** — bash/`.py`/`.sh` in `test/`: POSTs a live rule to `/n8n/webhook/dg/rules-ingest`, asserts the resulting Neo4j `Rule` node has `.SWRL` set (covers SCHM-09). Account for the n8n `import:workflow` gotcha (top-level `id` field required — see RESEARCH Pitfalls).
- [ ] **Query smoke script** — for `/n8n/webhook/dg/graph-query`, asserts returned/generated Cypher references `r.SWRL`, not `r.text` (covers SCHM-10).
- [ ] **Migration seeding script** — Cypher run once before the migration demo, inserting a handful of v3-kind DesignState nodes (some Run-linked, some orphaned) so SCHM-13 / D-10 orphan-delete and D-14 layer-move are actually exercised (dev DB currently holds **zero** DesignState nodes — confirmed live). Covers SCHM-13's precondition.
- [ ] No new xUnit framework needed — `DG.Tests` already covers the single C# unit behavior this phase touches.

*The three scripts above are the Nyquist-required Wave 0 items — the planner MUST include tasks that create them before the waves that depend on them (Wave 2 ingest/query smoke, Wave 3 migration).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| v4 schema text is correct & self-consistent | SCHM-07, SCHM-08 | Text-content contract, not executable — correctness is human-judged against `port-iri-map-V7.md` | Diff-review `cypher_template.txt` v4 block and `dataset_schema.json`; confirm kinds {ObjState,ParamState,PropState}, Run props {ValidStatus,SendStatus} (no `Status` text field per D-01), Rule props {SWRL,RuleName,RuleDescription}, and `graph='ValidGraph'` layer note (D-14) |
| NeoVis renders 3 state-kind colors distinctly | SCHM-11 | Visual rendering in the browser | Open `http://localhost:8080`, load a graph with all three kinds, confirm ObjState/ParamState/PropState render in the three assigned hues; confirm no `DataProperty` group artifacts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (grep/file/xUnit/live-HTTP) or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 smoke/seed scripts above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s on the fast path
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

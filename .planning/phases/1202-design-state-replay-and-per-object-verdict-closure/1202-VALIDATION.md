---
phase: 1202
slug: design-state-replay-and-per-object-verdict-closure
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-21
---

# Phase 1202 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (C#, `DG.Tests`) + pytest (Python, `data-service/tests`, `tools/de01/tests`) |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj` (net9.0 only); no single pytest config — invoked directly via `python -m pytest <path>` per STATE.md baseline commands |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ -v minimal` for any `DG.Core`/`DG.Grasshopper` change; `python -m pytest data-service/tests -q -k <touched module>` for any `data-service` change |
| **Full suite command** | `dotnet test DG/tests/DG.Tests/ -v minimal && python -m pytest data-service/tests -q && python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` |
| **Estimated runtime** | ~180 seconds (502+ xUnit tests, 823+ pytest tests, 33 DE-01 offline tests) |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/ -v minimal` (C# changes) or `python -m pytest data-service/tests -q -k <touched module>` (Python changes)
- **After every plan wave:** Run full `DG.Tests` (502+) + `data-service/tests` (823+) suites
- **Before `/gsd-verify-work`:** Full suite must be green, plus one live DE-01 run (`python -m pytest tools/de01/tests/test_de01_runner.py -q`, no `-k "not live"` filter — requires the compose stack)
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1202-01-01 | 01 | 0 | ALGN12-10 | — | New `IValidGraphRepository` per-object method has test coverage before implementation | unit | `dotnet test DG/tests/DG.Tests/ -v minimal --filter Neo4jValidGraphRepositoryTests` | ❌ W0 | ⬜ pending |
| 1202-01-02 | 01 | 0 | ALGN12-11 | — | `ON CREATE SET` immutability regression test proves re-publish does not overwrite `statePayloadJson`/`rulesJson`/`createdAt` | unit | `python -m pytest data-service/tests -k publish` | ❌ W0 | ⬜ pending |
| 1202-02-01 | 02 | 1 | ALGN12-08 | — | Design State identity explicitly classified (capture-event key + content hash) | unit | `dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests` | ✅ extend existing | ⬜ pending |
| 1202-03-01 | 03 | 1-2 | ALGN12-09 | — | publish→query→replay preserves canonical state hash, membership manifest, schema version, normative members | unit + integration | `dotnet test` (serializer round-trip) + `python -m pytest tools/de01/tests/test_de01_runner.py -k "not live"` | ✅ unit; ⚠️ live DE-01 needs Docker | ⬜ pending |
| 1202-04-01 | 04 | 2 | ALGN12-10 | — | Mixed per-object outcomes remain distinct through persistence and C# retrieval | unit + integration | `dotnet test` (new repository method) + live DE-01 `compare_legs` state comparison | ❌ W0 dependency | ⬜ pending |
| 1202-05-01 | 05 | 2 | ALGN12-11 | — | Mutable operational/run status separated from immutable snapshot identity | unit + integration | `python -m pytest data-service/tests -k publish` | ❌ W0 dependency | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Exact Task IDs/plan numbers above are placeholders reflecting the requirement→plan mapping anticipated from CONTEXT.md/RESEARCH.md; the planner assigns final plan/task numbering.*

---

## Wave 0 Requirements

- [ ] Extend `Neo4jValidGraphRepositoryTests.cs` with test stubs for the new additive `IValidGraphRepository` per-object verdict method — covers ALGN12-10
- [ ] Add `ON CREATE SET` immutability regression test in `data-service/tests` (re-publish same `runId` must not overwrite `statePayloadJson`/`rulesJson`/`createdAt`) — covers ALGN12-11
- [ ] New sibling fixture material under `fixtures/golden/` (D-17 mixed pass/fail per-object replay fixture, built from existing `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`, never editing frozen `fixture.json`) — covers ALGN12-09/ALGN12-10 test data
- [ ] Framework install: none — xUnit and pytest are already present, no new dependency required

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live DE-01 replay leg (`tools/de01/legs.py:run_leg_replay`) reproduces canonical state hash and mixed per-object verdicts end-to-end | ALGN12-09, ALGN12-10 | Requires the live compose stack (Neo4j + data-service + Grasshopper harness); Docker Desktop was confirmed NOT running on the research machine at research time (2026-09-21) — this is an environment dependency, not a design gap | Bring up `docker compose up -d`, rebuild `data-service` with `--no-cache` after any `app.py` change (no source volume mount), rebuild the GH plugin (`dotnet build DG/DG.sln -c Release`) if D-04 changed `ObjectStateComponent`, then run `python -m pytest tools/de01/tests/test_de01_runner.py -q` without the `-k "not live"` filter |
| Grasshopper canvas re-wire after `ObjectStateComponent` ID-minting convergence (D-04) | ALGN12-08 | Visual/interactive GH canvas behavior (identity no longer Label-sensitive) cannot be asserted by an automated test | Open a test .gh canvas, rename an `ObjectStateComponent` instance's label, confirm the resulting ObjState ID no longer changes (per D-04) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

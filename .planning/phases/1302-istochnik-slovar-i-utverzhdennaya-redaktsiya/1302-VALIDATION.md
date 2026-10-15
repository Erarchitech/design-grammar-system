---
phase: "1302"
slug: "istochnik-slovar-i-utverzhdennaya-redaktsiya"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-14"
---

# Phase 1302 — Validation Strategy

> Planning-time test contract, not execution evidence. Entry gates in ROADMAP.md remain open. Commands for new test files are prospective, not reported as passing. Task IDs are reconciled to the ten final plans (25 tasks); latency, Wave 0 and independent sign-off remain unproven.

## Test Infrastructure

| Property | Value |
|---|---|
| **Framework** | Existing pytest/FastAPI TestClient, Node `--test`, DG.Tests (.NET) |
| **Config file** | `data-service/requirements.txt`, `ui-v2/package.json`, `DG/tests/DG.Tests/DG.Tests.csproj` |
| **Quick run command** | `python -m pytest data-service/tests/test_route_inventory.py -q` (existing); add relevant focused DGKN test once created |
| **Full suite command** | `python -m pytest data-service/tests -q`; `npm --prefix ui-v2 test`; `dotnet test DG/tests/DG.Tests/` (only in authorized isolated environment) |
| **Estimated runtime** | Not measured; re-measure in execution environment |

## Sampling Rate

- **After each offline task:** run the focused affected test plus route inventory when routes change; no Git commit implied.
- **After wave 1 (08):** pause implementation until actual owner entry decision; offline matrix may exist without permission to execute plans 01–07/09–10.
- **After each admitted product wave:** run relevant backend/UI/C# suite only in an authorized isolated environment.
- **Before `/gsd-verify-work`:** full suites green, independent live/source/transaction evidence and per-ID acceptance where required.
- **Max feedback latency:** Not yet measured; establish for each proposed focused test in Wave 0.

## Per-Task Verification Map

Planning reconciliation: **25/25** exact task IDs from ten executable plans (01–10), including checkpoints. Commands are prospective, never reported as run. “Path exists” is not a test pass; latency unknown until measured. 08 is the first wave and blocks dependent implementation while the entry gate remains open.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior / task | Test Type | Automated Command | File Exists | Status / latency |
|---|---|---|---|---|---|---|---|---|---|
| 1302-01-T1 | 01 | 2 | DGKN-01, DGKN-04, DGKN-05, DGKN-07 | See plan STRIDE register | Task 1: HTTP source-linked rule proposal, preview and explicit confirmation | tracer | `python -m pytest data-service/tests/test_dgkn_revision.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_revision.py | ⬜ pending; latency unknown |
| 1302-01-T2 | 01 | 2 | DGKN-01, DGKN-04, DGKN-05, DGKN-07 | See plan STRIDE register | Task 2: Source ACL and single-project scope negative matrix | auto | `python -m pytest data-service/tests/test_dgkn_source.py data-service/tests/test_dgkn_scope.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_source.py, data-service/tests/test_dgkn_scope.py | ⬜ pending; latency unknown |
| 1302-01-T3 | 01 | 2 | DGKN-01, DGKN-04, DGKN-05, DGKN-07 | See plan STRIDE register | Task 3: Fence legacy HTTP writes and align route security contract | auto | `python -m pytest data-service/tests/test_dgkn_revision.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_revision.py | ⬜ pending; latency unknown |
| 1302-02-T1 | 02 | 3 | DGKN-02, DGKN-03 | See plan STRIDE register | Task 1: Company release and private draft lifecycle | auto | `python -m pytest data-service/tests/test_dgkn_vocabulary.py data-service/tests/test_route_inventory.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_vocabulary.py | ⬜ pending; latency unknown |
| 1302-02-T2 | 02 | 3 | DGKN-02, DGKN-03 | See plan STRIDE register | Task 2: Retirement with stable historical references | auto | `python -m pytest data-service/tests/test_dgkn_vocabulary.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_vocabulary.py | ⬜ pending; latency unknown |
| 1302-03-T1 | 03 | 4 | DGKN-04, DGKN-05 | Gate / human authority | Task 1: Authorize transactional store and published revision identity | checkpoint:decision | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-03-T2 | 03 | 4 | DGKN-04, DGKN-05 | See plan STRIDE register | Task 2: Real two-writer CAS, rollback and audit verification | auto | `python -m pytest data-service/tests/test_dgkn_concurrency.py data-service/tests/test_dgkn_revision.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_concurrency.py, data-service/tests/test_dgkn_revision.py | ⬜ pending; latency unknown |
| 1302-04-T1 | 04 | 7 | DGKN-06 | Corpus / tampering | Task 1: Pin manifest at actual evaluator corpus boundary | auto | `dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~Neo4jRuleRepositoryVariableKindTests` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-04-T2 | 04 | 7 | DGKN-06 | Corpus / tampering | Task 2: Historical read and recheck without verdict mutation | auto | `python -m pytest data-service/tests/test_dgkn_history.py data-service/tests/test_route_inventory.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_history.py | ⬜ pending; latency unknown |
| 1302-04-T3 | 04 | 7 | DGKN-06 | Gate / human authority | Task 3: Verify real corpus consistency and historic read-back | checkpoint:human-verify | `python -m pytest data-service/tests/test_dgkn_history.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_history.py | ⬜ pending; latency unknown |
| 1302-05-T1 | 05 | 8 | DGKN-08, DGKN-09 | Gate / human authority | Task 1: Destination approval authority and evidence policy | checkpoint:decision | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-05-T2 | 05 | 8 | DGKN-08, DGKN-09 | See plan STRIDE register | Task 2: Independent copy, destination adaptation and guarded activation | auto | `python -m pytest data-service/tests/test_dgkn_copy.py data-service/tests/test_route_inventory.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_copy.py | ⬜ pending; latency unknown |
| 1302-05-T3 | 05 | 8 | DGKN-08, DGKN-09 | Gate / human authority | Task 3: Accept actual destination check and appointed approval | checkpoint:human-verify | `python -m pytest data-service/tests/test_dgkn_copy.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_copy.py | ⬜ pending; latency unknown |
| 1302-06-T1 | 06 | 9 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | See plan STRIDE register | Task 1: Canonical typed registry and server confirmation enforcement | auto | `python -m pytest data-service/tests/test_dgkn_commands.py data-service/tests/test_route_inventory.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_commands.py | ⬜ pending; latency unknown |
| 1302-06-T2 | 06 | 9 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | See plan STRIDE register | Task 2: Web source, vocabulary, revision, history and copy review | auto | `node --test ui-v2/tests/dgkn-review.test.mjs` | ❌ Wave 0: ui-v2/tests/dgkn-review.test.mjs | ⬜ pending; latency unknown |
| 1302-06-T3 | 06 | 9 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | See plan STRIDE register | Task 3: Typed web command parser/help and integration | auto | `node --test ui-v2/tests/dgkn-commands.test.mjs` | ❌ Wave 0: ui-v2/tests/dgkn-commands.test.mjs | ⬜ pending; latency unknown |
| 1302-07-T1 | 07 | 10 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | Gate / human authority | Task 1: Approve source authority, provider coverage and human appointments | checkpoint:decision | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-07-T2 | 07 | 10 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | See plan STRIDE register | Task 2: Execute safety matrix and reconcile per-task Nyquist validation ledger | auto | `python -m pytest data-service/tests/test_dgkn_source.py data-service/tests/test_dgkn_vocabulary.py data-service/tests/test_dgkn_revision.py data-service/tests/test_dgkn_concurrency.py data-service/tests/test_dgkn_history.py data-service/tests/test_dgkn_scope.py data-service/tests/test_dgkn_copy.py data-service/tests/test_dgkn_commands.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_source.py, data-service/tests/test_dgkn_vocabulary.py, data-service/tests/test_dgkn_revision.py, data-service/tests/test_dgkn_concurrency.py, data-service/tests/test_dgkn_history.py, data-service/tests/test_dgkn_scope.py, data-service/tests/test_dgkn_copy.py, data-service/tests/test_dgkn_commands.py | ⬜ pending; latency unknown |
| 1302-07-T3 | 07 | 10 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | Gate / human authority | Task 3: Independent entry/exit and UI sign-off | checkpoint:human-verify | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-08-T1 | 08 | 1 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | See plan STRIDE register | Task 1: Offline source, governance and revision contract inventory | auto | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-08-T2 | 08 | 1 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10 | Gate / human authority | Task 2: Admit or pause all dependent Phase 1302 product work | checkpoint:decision | `python tools/degram/workspace.py verify` | ✅ path exists; not run | ⬜ pending; latency unknown |
| 1302-09-T1 | 09 | 5 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07 | See plan STRIDE register | Task 1: Graph model and normative propagation | auto | `python -m pytest data-service/tests/test_dgkn_revision.py data-service/tests/test_security_boundary_spec.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_revision.py | ⬜ pending; latency unknown |
| 1302-09-T2 | 09 | 5 | DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07 | See plan STRIDE register | Task 2: Mandatory tracked graph consumer/writer propagation decision | auto | `python -m pytest data-service/tests/test_n8n_workflow_boundary.py data-service/tests/test_dgkn_revision.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_revision.py | ⬜ pending; latency unknown |
| 1302-10-T1 | 10 | 6 | DGKN-06 | Corpus / tampering | Task 1: Publish request carries and validates full input manifest | auto | `python -m pytest data-service/tests/test_dgkn_history.py data-service/tests/test_validation_run_immutability.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_history.py | ⬜ pending; latency unknown |
| 1302-10-T2 | 10 | 6 | DGKN-06 | Corpus / tampering | Task 2: Atomic run/manifest persistence and exact read-back | auto | `python -m pytest data-service/tests/test_dgkn_history.py data-service/tests/test_validation_run_immutability.py -q` | ❌ Wave 0: data-service/tests/test_dgkn_history.py | ⬜ pending; latency unknown |

*Status: ⬜ pending · ✅ green only on executed output plus required external evidence · ❌ red · ⚠️ flaky. Checkpoint automation is structural/necessary but never substitutes for independent human authority. 25 commands are specified, not verified runnable or passing.*

## Wave 0 Requirements

- [ ] Create focused `test_dgkn_source.py`, `test_dgkn_vocabulary.py`, `test_dgkn_revision.py`, `test_dgkn_concurrency.py`, `test_dgkn_history.py`, `test_dgkn_scope.py`, `test_dgkn_copy.py`, `test_dgkn_commands.py` under `data-service/tests/`; establish two-project, foreign-company and revoked-source fixtures. Add `ui-v2/tests/dgkn-review.test.mjs`, `ui-v2/tests/dgkn-commands.test.mjs` and extend existing `DG/tests/DG.PublishWireHarness/Program.cs`/C# tests to compare actual emitted corpus payload to persisted run. No Wave 0 item is complete at planning.
- [ ] Establish real isolated Neo4j concurrent-writer harness and actual evaluator-manifest equality test before asserting DGKN-05/06; current authorization does not include live DB writes.
- [ ] Inventory and fence all legacy mutation routes/writers; keep existing route inventory and security regressions.
- [ ] Establish permitted CDE source list, steward/approver appointments and source-transfer permissions before live work; fresh destination run and human approval are acceptance evidence, not offline mock assertions.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| CDE authority and access to permitted exact source revision | DGKN-01, DGKN-08 | External authority and revocation cannot be certified by local fixture | After authorization, use an approved source/object/fragment; record actual access/pin outcome and denied/revoked case without copying private material into the public fork. |
| Destination human approval against a new destination-scoped check | DGKN-09 | Human acceptance is a distinct operation | Inspect destination project/revision, fresh run and scope, non-verdict state, reviewer identity and approval; refuse source-run reuse. |
| Steward/approver appointment and 1300/1301 entry conditions | DGKN-02, DGKN-03, DGKN-09 | Owner-controlled governance prerequisites | Verify named authority and scoped access evidence before dependent activation; `workspace.py verify` is structural only (`productAccepted: false`), not this sign-off. |

## Validation Sign-Off

- [ ] All 25 final plan tasks have exact `<automated>` verify and `<fails_when>`; task/command map independently reconciled after execution (mapping alone is not runnable proof).
- [ ] Sampling continuity: no three consecutive executable tasks without automated verify.
- [ ] Wave 0 creates every referenced test and measures focused feedback latency.
- [ ] No watch-mode flags.
- [ ] Real CAS/corpus/source/approval evidence obtained under separate authorization.
- [ ] Record per-task observed command exit/result, elapsed focused latency and maximum feedback interval; unknown until executed, no assumed sub-60s claim.
- [ ] Named independent validation reviewer checks exact task map, Wave 0 proofs, real integration and latency and records sign-off or refusal separately from product owner acceptance.
- [ ] Set `nyquist_compliant: true` and `wave_0_complete: true` only on proven prerequisites and independent review; both remain false in this planning draft.

**Approval:** pending independent verification and entry-gate review

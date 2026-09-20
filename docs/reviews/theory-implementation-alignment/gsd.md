# GSD planning audit and proposed traceable updates

## Scope and method

Read-only audit of `.planning/`, explicitly including `.planning/milestones/`, active phases, archived phases, future milestone packages, quick tasks, research, debug, and codebase notes. Current proof was checked against source/tests and the captured GSD query; historical reports were not promoted to current evidence. No planning files, source files, fixes, completion flags, milestone activation, or commits were made.

Inventory is persisted in `docs/reviews/theory-implementation-alignment/evidence/gsd-inventory.json`; proposals are persisted in `.../gsd-proposed-updates.json`.

## Inventory and coverage

- **665** files under `.planning/`; **664** decoded text files and **1** binary/undecodable file.
- **63** phase directories: **12 active**, **42 archived**, **9 future**.
- **181 PLAN** files and **170 SUMMARY** files.
- **17 UAT/HUMAN-UAT**, **43 VERIFICATION**, **29 VALIDATION**, **1 deferred-items**, and **36 REVIEW** artifacts.
- Captured `gsd-tools query audit-uat`: **5 files / 10 items**. This is incomplete: raw inventory finds 17 UAT files, and Phase 40 documents that Phase 28 and Phase 36 are omitted by the CLI query. Block-scalar `expected:` fields are also parser-sensitive.

The inventory distinguishes **current proof** (latest verification/source/test evidence), **historical reports** (archived milestone evidence), and **manual/uncertain** outcomes. Raw parser item counts are not treated as unique defects.

## Current reconciliation findings

1. **Control-plane drift.** STATE correctly points at Phase 40 after Phase 33's out-of-sequence closeout, but ROADMAP/PROJECT/REQUIREMENTS still disagree on phase and requirement states. Phase 35 is measured below its SC1 gate; Phase 36 has a passed frontmatter/body `gaps_found` conflict; Phase 37 and 38 retain live/manual gates; Phase 39 verification passed while its validation frontmatter still says planned.
2. **Phase 35 SC1 is a measured failure, not merely blocked.** Current evidence reports M1 **0.03125 (1/32)** on Corpus B/A3 against **0.60**. A0f/A5 remains an unanswered causal diagnostic, not a reason to suspend the A3 contract verdict.
3. **Phase 35's measurement instrument needs a separate disposition.** CR-01, CR-02, CR-03, and WR-04 remain confirmed in the current verification. Existing cassette numbers replay, but the next paid/diagnostic sweep is not instrument-ready without those issues being fixed or explicitly accepted.
4. **Phase 32.1 has load-bearing identity review findings.** Golden-vector parity is current proof; registry-anchor MERGE incompatibility and unescaped `|` boundaries are unresolved review findings and must not be hidden by the complete checkbox.
5. **Phases 36–38 are mixed, not uniformly complete.** 36's provenance chain was code-fixed but awaits live Rhino verification; 37's deterministic service is green but its Frame edit/publish loop is human-needed; 38's in-Rhino PARAMETER REINSTATE/JOIN A/no-side-effect checks remain pending.
6. **Phase 39 passed its investigation goal with disclosed limits.** The watcher loop and guardrails are live-reproduced, but auto-run `ValidStatus` is uniformly false (F-39-01). W-39-A and W-39-B remain documentation/follow-up warnings. This is not production auto-validation completion.
7. **Archived v8.2/v8.1 summaries are stale.** 822 and 823 were later closed; 824 remains the original v8.2 manual tail; 825 is a separate follow-up with three Rhino checks. PROJECT and MILESTONES still preserve older override-closeout wording. v8.1 formal-closeout language also differs between control files.
8. **Future packages are intentionally isolated.** v9.1 (910–917), v10.0 (41–49), and v11.0 (1101–1109) must not be activated or counted. The old v4.0 BOT bridge remains future scope. Existing v11.0 publication-contract tasks are not duplicated as new v9.0 work.

## Proposed updates

| ID | Phase/component | Class | Priority | Sequence | Proposed disposition |
|---|---|---|---|---:|---|
| GSD-ALIGN-001 | Active v9.0 control-plane status | auto | P0 | 1 | Reconcile STATE.md, ROADMAP.md, PROJECT.md, and active REQUIREMENTS.md into one status vocabulary: completed code, verified, human_needed, failed, blocked-not-failed, and deferred. Update the v9.0 progress table and requirement traceability rows from disk evidence; do not mark a requirement complete solely because code exists. |
| GSD-ALIGN-002 | UAT inventory and audit-query coverage | auto | P0 | 2 | Add a machine-readable UAT coverage register generated from raw per-file scans, retaining the captured gsd-tools audit as a secondary source. Record omitted files, parser-sensitive block scalars, result counts, and whether an item is current proof, historical report, manual, or skipped. |
| GSD-ALIGN-003 | Phase 35 recognition quality and eval harness | auto | P0 | 3 | Record SC1 as a measured FAIL, not blocked: M1=0.03125 (1/32) < 0.60 on Corpus B / A3. Keep the frontier-provider A0f/A5 comparison as a separate unresolved diagnostic follow-up. Do not claim RCGN-01 complete while the quality gate fails. |
| GSD-ALIGN-004 | Phase 35 evaluation instrument integrity | auto | P0 | 4 | Keep the published metrics citable only with an explicit instrument caveat until CR-01, CR-02, CR-03, and WR-04 are resolved or formally accepted. Add a follow-up plan covering distinct permutation generation, negotiated-mode single source of truth, non-empty recording assertion, and permutation replay. |
| GSD-ALIGN-005 | Phase 35 remaining human verification | manual | P1 | 5 | Retain two explicit manual items: G12 mixed-accept publishability gate and real LLM recognition→preview seam. Mark them manual, not passed by synthetic-proposal tests; report UrbanBlock versus Frame fixture substitution. |
| GSD-ALIGN-006 | Phase 32.1 identity review findings | auto | P0 | 6 | Do not describe DGID-01..06 as unqualified release-ready. Carry CR-01 registry-anchor reconciliation and CR-02 delimiter ambiguity into an owned follow-up before relying on pre-mint/bind-before-publish or cross-language identity guarantees; separately disposition WR-01..WR-04. |
| GSD-ALIGN-007 | Phases 36-38 status reconciliation | auto | P0 | 7 | Reconcile latest verification/UAT statuses without erasing manual gates: Phase 36 remains partial/human-needed until provenance is live-verified; Phase 37 remains human-needed until its live Frame interface-removal test; Phase 38 remains human-needed until all three in-Rhino checks pass. |
| GSD-ALIGN-008 | Phase 29 and 28 live-provider UAT | manual | P1 | 8 | Keep the live provider-switch and live graph-query checks manual/pending; correct parser-sensitive UAT representation so the audit query can see them, without treating unit/live-container proof as the missing human outcome. |
| GSD-ALIGN-009 | Phase 39 stale validation metadata and warnings | auto | P0 | 9 | Reconcile 39-VALIDATION.md frontmatter with the passed 39-VERIFICATION.md, preserving W-39-A, W-39-B, and F-39-01 as disclosed warnings/open design follow-up. Do not convert the prototype into production auto-validation completion. |
| GSD-ALIGN-010 | v8.2/v8.1 archived status drift | auto | P1 | 10 | Correct archived control summaries only: v8.2 must say 822 and 823 closed/passed and 824 remains the only original v8.2 human item; list Phase 825 separately as follow-up with its own 3 manual checks. v8.1 must not remain described as formally pending where MILESTONES records the retrospective closeout. |
| GSD-ALIGN-011 | Future milestone isolation and old BOT bridge | skip | P2 | 11 | No activation, renumbering, or duplicate planning task. Record these packages as intentionally isolated; classify v4.0 BOT bridge as future scope, not an active stale defect. Keep v11.0 1101-1109 publication-contract tasks as the owner for full V8 alignment and do not copy them into Phase 40 or v9.1/v10.0. |
| GSD-ALIGN-012 | Historical archived UAT/verification reports | skip | P1 | 12 | Classify old human_needed/partial reports as historical evidence unless a current control file explicitly reopens them. Do not bulk-mark archived items passed or re-run them as part of the v9.0 audit; only carry forward items referenced by current STATE, MILESTONES, or active requirements. |
| GSD-ALIGN-013 | Phase 40 readiness and cross-phase closeout | manual | P0 | 13 | Use Phase 40 as the sole active closeout owner for live E2E/manual UAT reconciliation, documentation, and the narrow V8 publication preflight. Before execution, turn its validation map into a status ledger and keep INTG-01/02/03/04 separate from Phase 35 quality and v11.0 full migration. |

## Traceability rules for execution

- `auto` means the status can be reconciled from current artifacts and source/tests; it does **not** authorize changing files in this audit.
- `manual` means a live Rhino/provider/operator observation or an uncertain outcome is required. It stays unresolved until a human records evidence.
- `skip` means preserve historical provenance or future isolation; do not reopen, activate, or bulk-mark passed.
- Any finding described as uncertain must be manual. No current proof is inferred from a plan, a stale SUMMARY, a code-only check where the criterion is live behavior, or a synthetic proposal where real LLM output is required.
- Phase 40 owns the active closeout ledger and its narrow V8 publication preflight. v11.0 owns the full V8 repository/publication/runtime/manuscript migration.

## Key evidence anchors

- Control files: `.planning/STATE.md:7-18,29-72,383-398`; `.planning/ROADMAP.md:643-660`; `.planning/REQUIREMENTS.md:156-179`; `.planning/PROJECT.md:50-60,74-78`; `.planning/MILESTONES.md:3-7,19-32`.
- UAT coverage limitation: `docs/reviews/theory-implementation-alignment/evidence/gsd-audit-uat.json:1-139`; `.planning/phases/40-e2e-validation-and-docs/40-VALIDATION.md:81-83,98-99`.
- Phase 35: `.planning/phases/35-llm-recognition-canvas-preview/35-VERIFICATION.md:21-65,85-100,140-173,213-227`; `35-UAT.md:78-106,278-334`.
- Phase 32.1: `.planning/phases/32.1-cross-platform-identity-and-mapping-dg-id/32.1-REVIEW.md:43-123`.
- Phases 36–39: `36-VERIFICATION.md:1-8,19-43,138-170`; `37-VERIFICATION.md:1-36,101-113`; `38-VERIFICATION.md:1-40,60-77`; `39-VERIFICATION.md:1-29,81-98,230-268`.
- Archived/future boundaries: `.planning/MILESTONES.md:60-68`; `.planning/milestones/v9.1-ROADMAP.md:1-13`; `v10.0-ROADMAP.md:1-12`; `v11.0-ROADMAP.md:1-36,260-272`.

## Result

The requested read-only audit is complete. Exact updates are machine-readable in `evidence/gsd-proposed-updates.json`; exhaustive inventory and coverage counts are in `evidence/gsd-inventory.json`. No fixes, commits, completion marks, or milestone activation were performed.


---

## Execution record — reconciliation performed 2026-09-20

> **This section was appended after the read-only audit.** The audit body above is unchanged.
> The reconciliation it proposed has now been executed as the standalone GATE12-01 pass.
> Full ledger: `.planning/reconciliation/GSD-ALIGN-RECONCILIATION.md`.

| Class | Items | Outcome |
|---|---|---|
| `auto` | 001, 002, 003, 004, 006, 007, 009, 010 | **Reconciled** from disk evidence |
| `manual` | 005, 008, 013 | **Remain open** — live environment / human observation required |
| `skip` | 011, 012 | **Unchanged** — isolation and provenance preserved |

### Coverage register (GSD-ALIGN-002) — recomputed 2026-09-20

Raw per-file scan of all `*UAT*.md` under `.planning/`:

- **17 UAT files** — matches this audit's inventory count exactly.
- **42 result items** (`^[[:space:]]*result:`).
- **4 block-scalar `expected: |` fields** — in `28-UAT.md` (2), `34-UAT.md` (1), `37-UAT.md` (1).

**The `audit-uat` CLI result is PARTIAL and its omissions are named:**

Re-running the query on 2026-09-20 returns **0 files / 0 items**, not the 5/10 captured by this
audit. This is a regression caused by v9.0 archival: the query scans `.planning/phases/` only,
and that directory now holds no executed phases — all 17 UAT files live under
`.planning/milestones/`.

| # | Omission cause | Scope |
|---|---|---|
| 1 | Archive-scope blindness — query does not scan `.planning/milestones/` | **17 of 17 files.** Supersedes the Phase 28 / Phase 36 note above: every file is now omitted |
| 2 | Block-scalar `expected:` block-literal sensitivity | 4 items (28, 34, 37) — pre-existing, as this audit recorded |
| 3 | Structural non-conformance — prose `## Test N`, no `result:` field | 2 files (824, 825) — unparseable by design, not missing |
| 4 | Non-result artifact — a test plan | 1 file (`v9.0-PIPELINE-UAT.md`) |

**Per-item disposition:** 42 `auto` (mechanically parseable), 6 `manual` (824 ×3 + 825 ×3
in-Rhino checks), 13 `skip` (v1.1 ×5 + v2.0 ×8 historical, per GSD-ALIGN-012), 0 `uncertain`.

**Until the query also scans `.planning/milestones/`, the raw inventory in the reconciliation
ledger is the authoritative UAT coverage record.**

### Defects found beyond the audit's findings

1. **Broken evidence chain (GSD-ALIGN-001).** `.planning/milestones/v9.0-REQUIREMENTS.md`
   claimed the v9.0 traceability record "remains ... at `.planning/REQUIREMENTS.md` ... preserved
   unchanged in the worktree." Commit `0e46ec3` had replaced that file with v12.0's requirements.
   Recovered from `git show 0e46ec3^:` and the counts re-derived — **47 / 9 / 4 = 60, agreeing
   exactly** with the archive's stated figures. The false claim is corrected in place.
2. **4 stale archived-phase paths (GSD-ALIGN-001)** pointing at `.planning/phases/40-*`, which
   moved to `.planning/milestones/v9.0-phases/40-*`. Corrected; both targets verified to resolve.
3. **Stale active-phase list (GSD-ALIGN-001).** `.planning/PROJECT.md` listed v9.0's phases 28–40
   under the **v12.0** milestone heading, marking "Phase 29 — next to plan" although v9.0 closed
   2026-09-19. Replaced with the v12.0 phase list plus an explicit v9.0 carry-forward block.
4. **Phase 825 omitted from the v8.2 closeout (GSD-ALIGN-010).** Control files described 824 as
   "the ONLY remaining v8.2 verification item", but `825-VERIFICATION.md` has carried
   `human_needed` / `behavior_unverified: 3` since 2026-07-13. `STATE.md` contradicted itself —
   its Key Decisions section already recorded 825's deferred UAT. Both are now listed separately.

### Status corrections applied

| Artifact | Before | After |
|---|---|---|
| `35-UAT.md` test 1 | `result: blocked (provider availability)` | `result: FAIL (SC1 quality gate)` — M1 = 0.031 < 0.60, Corpus B / A3, n = 32. Original text preserved; the superseded "not resolved to a pass or fail" clause is marked in place |
| `39-VALIDATION.md` | `status: planned` | `status: passed-with-warnings` — agrees with `39-VERIFICATION.md`; W-39-A, W-39-B, F-39-01 preserved as disclosed open items |

**No test was re-run, no status upgraded on the strength of code alone, and no archived
verification evidence was rewritten.**

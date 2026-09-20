# GSD Control-Plane Reconciliation — GSD-ALIGN-001..013

**Executed:** 2026-09-20
**Gate:** GATE12-01 — hard prerequisite for v12.0 Phase 1200 planning/execution
**Register:** `docs/reviews/theory-implementation-alignment/evidence/gsd-proposed-updates.json` (authoritative)
**Audit source:** `docs/reviews/theory-implementation-alignment/gsd.md`

This is a **standalone reconciliation pass**, not a v12.0 phase. It reconciles control-plane
status against disk evidence. It does **not** re-run tests, does not convert manual evidence
into completion, and does not reopen archived items.

## Disposition summary

| Class | Items | Disposition |
|---|---|---|
| `auto` | 001, 002, 003, 004, 006, 007, 009, 010 | **Reconciled** below from disk evidence |
| `manual` | 005, 008, 013 | **Remain open** — require live environment/human observation. Not reconcilable here |
| `skip` | 011, 012 | **No change** — isolation/provenance preserved, not reopened |

**GATE12-01 is satisfied for the `auto` class.** The three `manual` items are, by the register's
own classification, not resolvable by a reconciliation pass; they do not block Phase 1200.

---

## Count method (GSD-ALIGN-001)

All counts below are **derived from disk**, not asserted:

- Phase status = the `status:` frontmatter of that phase's **latest** verification artifact,
  cross-read against its UAT artifact.
- Requirement counts = `grep -cE '^- \[x\] \*\*[A-Z]+-[0-9]'` over the v9.0 traceability record
  recovered from `git show 0e46ec3^:.planning/REQUIREMENTS.md`.
- UAT counts = raw per-file scan of all 17 `*UAT*.md` files under `.planning/`.

**No requirement is marked complete solely because code exists.**

---

## GSD-ALIGN-001 — Active v9.0 control-plane status [auto] → RECONCILED

v9.0 closed by override closeout on 2026-09-19 and its phases were archived to
`.planning/milestones/v9.0-phases/`. The drifted *active* progress table the register cites
(`ROADMAP.md:643-660`) **no longer exists** — `.planning/ROADMAP.md` is now v12.0's, and the
v9.0 ROADMAP was rewritten as a closeout summary. The reconciliation therefore records the
**final archived** status ledger rather than editing a live table.

### Phase status ledger — one row per phase, backed by its latest artifact

| Phase | Verification | UAT | Reconciled status | Code proof | Live proof |
|---|---|---|---|---|---|
| 28 cloud-llm-connector | `human_needed` | `testing` | **human_needed** | yes | no — live provider switch unobserved (→ 008) |
| 29 dg-aware-context-layer | `human_needed` | `resolved` | **human_needed** | yes | no — SC4 live answer unobserved (→ 008) |
| 30 orchestration-eval | *no artifacts* | — | **deferred** | — | — (ORCH-01..04 → v10.0) |
| 31 rules-ingest-rebuild | *no artifacts* | — | **deferred** | — | — (RING-01..05 → v10.0) |
| 32 computgraph-serialization-core | `passed` | — | **verified** | yes | n/a |
| 32.1 cross-platform-identity (DG ID) | `passed` | — | **verified-with-open-review** | yes | n/a — 2 unresolved Critical review findings (→ 006) |
| 33 dg-canvas-bridge | `passed` | `testing` | **verified** | yes | yes — live in-Rhino round-trip user-approved 2026-07-28 |
| 34 ontology-tagging-components | `human_needed` | `testing` | **human_needed** | yes | partial |
| 35 llm-recognition-canvas-preview | `gaps_found` | `testing` | **failed (quality) / plumbing verified** | yes | partial — SC1 measured FAIL (→ 003) |
| 36 computgraph-persistence-display | `passed` | `testing` | **human_needed** | yes | no — SC3/F6 provenance not live-verified (→ 007) |
| 37 script-structure-validation | `human_needed` | `testing` | **human_needed** | yes | no — SC1 live Frame interface-removal test (→ 007) |
| 38 ai-generated-script-inputs | `human_needed` | `testing` | **human_needed** | yes | no — 3 in-Rhino checks (→ 007) |
| 39 designstate-auto-validation | `passed` | — | **verified-with-warnings** | yes | yes — 26/26; W-39-A, W-39-B, F-39-01 disclosed (→ 009) |
| 40 e2e-validation-and-docs | `human_needed` | *(PIPELINE-UAT plan)* | **human_needed — active closeout owner** | partial | partial — Session B blocker `D-40-SB-01` (→ 013) |

**Phase 40 remains the active frontier and sole closeout owner** (register item 013).

### Requirement traceability — derived counts

The v9.0 archive (`.planning/milestones/v9.0-REQUIREMENTS.md`) states 47 complete / 9 deferred /
4 pending. **Verified against the recovered record:**

| Disposition | Count | Families |
|---|---:|---|
| Complete `[x]` | **47** | implementation/documentation requirements |
| Deferred `[ ]` | **9** | `ORCH-01..04` (4) + `RING-01..05` (5) → v10.0 |
| Pending/qualified `[ ]` | **4** | `INTG-01..04` |
| **Total** | **60** | |

Counts **agree**. No future v9.1 / v10.0 / v11.0 phase is counted as active or complete.

### Defect found and corrected: broken evidence chain

`.planning/milestones/v9.0-REQUIREMENTS.md` asserts that `.planning/REQUIREMENTS.md`
"remains the authoritative detailed traceability record ... preserved unchanged in the worktree."

**This is false as of commit `0e46ec3` ("chore: close v9.0 and activate v12.0")**, which replaced
`.planning/REQUIREMENTS.md` with the v12.0 requirements. The v9.0 traceability table exists only
in git history.

Additionally, **4 stale path references** point at `.planning/phases/{28,29,...,40}-*`, which moved
to `.planning/milestones/v9.0-phases/` during archival:

| File | Stale refs | Status |
|---|---:|---|
| `.planning/milestones/v9.0-ROADMAP.md` | 1 | corrected |
| `.planning/milestones/v9.0-REQUIREMENTS.md` | 3 | corrected |

Both files are corrected by this pass — **pointer repair only**; no verification evidence,
status, or count is rewritten.

---

## GSD-ALIGN-002 — UAT inventory and audit-query coverage [auto] → RECONCILED

### Raw inventory (computed, not asserted)

```
find .planning -name "*UAT*.md"        -> 17 files
grep -cE '^[[:space:]]*result:'        -> 42 result items
grep -cF 'expected: |'                 -> 4 block-scalar expected fields
```

| File | Items | Block scalars | Result values |
|---|---:|---:|---|
| `v1.1/01-HUMAN-UAT.md` | 2 | 0 | (unlabelled) |
| `v1.1/02-HUMAN-UAT.md` | 1 | 0 | (unlabelled) |
| `v1.1/04-HUMAN-UAT.md` | 2 | 0 | (unlabelled) |
| `v2.0/03-HUMAN-UAT.md` | 3 | 0 | 3 passed |
| `v2.0/06-HUMAN-UAT.md` | 5 | 0 | 5 passed |
| `v8.2/822-UAT.md` | 3 | 0 | (unlabelled; 822-VERIFICATION `passed`) |
| `v8.2/824-UAT.md` | 0 | 0 | prose `## Test N` structure — **unparseable by design** |
| `v8.2/825-UAT.md` | 0 | 0 | prose `## Test N` structure — **unparseable by design** |
| `v9.0/28-UAT.md` | 1 | **2** | (unlabelled) |
| `v9.0/29-UAT.md` | 1 | 0 | 1 pass |
| `v9.0/33-UAT.md` | 4 | 0 | 2 pass + 2 unlabelled |
| `v9.0/34-UAT.md` | 5 | **1** | 3 pass + 2 unlabelled |
| `v9.0/35-UAT.md` | 7 | 0 | 5 pass, 1 blocked, 1 pending |
| `v9.0/36-UAT.md` | 4 | 0 | 3 pass, 1 partial |
| `v9.0/37-UAT.md` | 1 | **1** | (unlabelled) |
| `v9.0/38-UAT.md` | 3 | 0 | (unlabelled) |
| `v9.0/v9.0-PIPELINE-UAT.md` | 0 | 0 | **test plan, not a result record** |
| **Total** | **42** | **4** | |

### The `audit-uat` query result is PARTIAL — omissions named

The register recorded the CLI seeing **5 files / 10 items**. **Re-running it today returns
0 files / 0 items** — a regression caused by v9.0 archival:

```
node .claude/gsd-core/bin/gsd-tools.cjs query audit-uat
-> {"results": [], "summary": {"total_files": 0, "total_items": 0}}
```

**Root cause:** the query scans `.planning/phases/` only. That directory is now empty (v12.0 has
no executed phases), and all 17 UAT files live under `.planning/milestones/`.

**Named omissions, by cause:**

1. **Archive-scope blindness (17 of 17 files)** — the query does not scan `.planning/milestones/`.
   This supersedes the register's Phase 28 / Phase 36 omission note: *every* file is now omitted.
2. **Block-scalar sensitivity (4 items, in 28/34/37)** — `expected: |` block scalars are dropped.
   Pre-existing known defect; matches the recorded memory note.
3. **Structural non-conformance (2 files: 824, 825)** — prose `## Test N` sections with no
   `result:` field. Legitimately unparseable, not missing.
4. **Non-result artifact (1 file: v9.0-PIPELINE-UAT.md)** — a test *plan*, correctly carrying no
   results.

### Disposition per UAT item

| Disposition | Count | Basis |
|---|---:|---|
| `auto` — mechanically parseable result on disk | 42 | raw `result:` scan |
| `manual` — needs live/human observation | 6 | 824 (3) + 825 (3) in-Rhino checks |
| `skip` — historical archived report, not reopened | 13 | v1.1 (5) + v2.0 (8) — see 012 |
| `uncertain→manual` | 0 | none |

**Totals are computed from the inventory above, not manually asserted.**

---

## GSD-ALIGN-003 — Phase 35 recognition quality [auto] → RECONCILED

**Confirmed from disk.** `35-VERIFICATION.md` (`status: gaps_found`, 2026-07-27) already records
the correct finding, in its own words:

> "Measured, on exactly the corpus and arm SC1 names, at M1 = 0.03125 against a required 0.60 —
> 1 of 32 reference blocks matched. ... This is a measured failure, not an absent measurement."

**The drift is downstream of that verification**, exactly as the register says:

| Surface | Current | Reconciled |
|---|---|---|
| `35-UAT.md` test 1 | `result: blocked (provider availability)` | **FAIL** — M1 = 0.031, Wilson 95% CI [0.006, 0.157], n = 32, corpus = `urbanblock_slice`, arm = A3, threshold = 0.60 |
| `35-EVAL-REPORT.md` verdict | "SC1 still blocked on provider availability" | **SC1 contract verdict = FAIL**, reported separately from the F3 diagnostic branch |
| `RCGN-01` traceability | complete | **partial — plumbing satisfied, quality gate failed** |

**Separation required by the acceptance criteria — and honoured here:**

- **Contract question (answered):** did A3 on Corpus B clear 0.60? **No — FAIL by ~19x.**
- **Diagnostic question (unresolved):** prompt defect vs. DeepSeek capability ceiling? Needs the
  A0f/A5 frontier arms (`claude-sonnet-5`), which did not run — no Anthropic/OpenAI key was
  configured. The three F3 decision-rule branches remain unselected.

"Blocked" conflated these two. The A0f/A5 follow-up is **not part of SC1's stated gradeable
form** and is carried as a named diagnostic follow-up, owned by the recognition-quality gap —
**not** by v11.0, which is publication alignment, not recognition remediation.

`RCGN-01` must not be claimed complete while the quality gate fails.

---

## GSD-ALIGN-004 — Phase 35 evaluation instrument integrity [auto] → RECONCILED

**Disposition table — current-number validity vs. future-instrument readiness:**

| Finding | Effect on the *existing* M1 = 0.031 | Effect on *future* sweeps |
|---|---|---|
| CR-01 duplicate permutation generation | none — historical cassettes stand | must report shortfall, not silently dedupe |
| CR-02 negotiated-mode single source of truth | none | A4 replay must use its **actual** negotiated mode |
| CR-03 non-empty recording assertion | none | a zero-recording sweep must exit **non-green** |
| WR-04 permutation replay | none | `report.py` must be able to replay permutation cassettes |

**Ruling:** the published metrics remain **citable only with an explicit instrument caveat**
until these four have disposition. The existing **17 cassettes** and **9 scored / 1 skipped**
replay facts remain **historical evidence** — they are not silently regenerated, and no new SC1
run may be labelled citable/reproducible until the four findings are resolved or formally
accepted.

**Manual gate:** any new **paid** sweep requires explicit human approval before execution.

---

## GSD-ALIGN-006 — Phase 32.1 identity review findings [auto] → RECONCILED

Phase 32.1 `32.1-VERIFICATION.md` is `passed` (7/7 plans, DGID-01..06 met) — but that verifies
**source and unit** correctness. `32.1-REVIEW.md` carries **2 unresolved Critical findings**:

| ID | Finding | Risk |
|---|---|---|
| CR-01 | registry-anchor / publish-path label mismatch | orphaned duplicate nodes |
| CR-02 | unescaped `\|` in the cross-language hash join | cross-boundary identity collision |

**Reconciled status: `verified-with-open-review`.** DGID-01..06 are **not** described as
unqualified release-ready. Source/unit verification is explicitly distinguished from unresolved
**integration correctness**.

**Follow-up required before** v9.1 activation or any real second-platform connector, with
regression scenarios:

1. mint → bind → publish retains the binding;
2. cross-boundary delimiter inputs cannot collide;
3. schema docs and routes agree.

**Owner:** v12.0 **Phase 1203** (identity convergence) — which already owns the identity
authority/conflict/detach/provenance policy. No v11.0 publication task is duplicated for these
**runtime** defects.

---

## GSD-ALIGN-007 — Phases 36-38 status reconciliation [auto] → RECONCILED

**Status matrix — code proof vs. live proof, keyed to the latest report:**

| Phase | Latest verification | Code proof | Live proof | Reconciled |
|---|---|---|---|---|
| 36 computgraph-persistence-display | `passed` | yes — seam tests | no — **F6 provenance not live-verified** | **human_needed** — SC3 **not** complete from seam tests alone |
| 37 script-structure-validation | `human_needed` | yes — SVAL code requirements may be complete | no — live Frame interface-removal test | **human_needed** — closeout blocked on SC1 live proof |
| 38 ai-generated-script-inputs | `human_needed` | yes — GHIN code + evaluation proof | no — 3 in-Rhino checks | **human_needed** — live PARAMETER REINSTATE / JOIN A / no-side-effect unproven |

**Manual gates are preserved, not erased.** Phase 36's `passed` frontmatter reflects code-level
verification; it does **not** discharge the live provenance gate. Code requirements being
complete never implies phase closeout.

---

## GSD-ALIGN-009 — Phase 39 stale validation metadata [auto] → RECONCILED

**Confirmed drift:**

| Artifact | Frontmatter | Reconciled |
|---|---|---|
| `39-VALIDATION.md` | `status: planned` | **passed-with-warnings** |
| `39-VERIFICATION.md` | `status: passed` (26/26 must-haves, 2026-07-28) | unchanged — authoritative |

The two now **agree on the phase result**. Preserved as **disclosed warnings**, not hidden:

- **W-39-A** — `spec/DATABASE.md` does not document the widened `:ValidationRun` semantics
  (`trigger` / `verdictSource` / `capturedAt` / `completedAt` / `attempts` / `lastError` + the
  `captured -> completed | superseded | failed` state machine +
  `IntegrationConfig{provider:'AutoValidation'}`).
  *Human decision requested:* document now, or defer alongside ADR follow-up item 1.
- **W-39-B** — `39-03-SUMMARY.md:132` carries an unreconcilable "~1.5 s dg-reasoner SHACL
  round-trip" figure (2.0 s debounce + 1.5 s exceeds the recorded 2.679 s SC1 total).
  **Labelled historical/stale wherever surfaced.** Both deliverable documents already handle it
  correctly.
- **F-39-01** — auto-runs are SHACL-validated **before** their own `ValidStatus` is written, so
  every auto-run self-violates `RunStatusShape_valid` and the conservative fallback flips every
  ObjState false. **Remains an OPEN semantic limitation**, explicitly *not* a failure hidden by
  the `passed` status.

**The prototype is not converted into production auto-validation completion.** Phase 39 remains
"Investigation + prototype + ADR only" per REQUIREMENTS line 127.

---

## GSD-ALIGN-010 — v8.2 / v8.1 archived status drift [auto] → RECONCILED

**Archival wording only. No reactivation; no historical verification evidence rewritten.**

### v8.2 closeout chronology (exact)

| Phase | Verification | UAT file | Status |
|---|---|---|---|
| 822 OWL 2 DL + Reasoner wiring | `passed` | `822-UAT.md` | **closed 2026-07-13** — 3 frontend scenarios live-passed |
| 823 SHACL Validation Layer | `passed` | *(retroactive verification)* | **closed 2026-07-13** — 4/4 |
| 824 CONNECTOR credential integration | `human_needed` | `824-UAT.md` | **OPEN** — 3 in-Rhino checks |
| 825 CONNECTOR token simplification | `human_needed` | `825-UAT.md` | **OPEN** — 3 in-Rhino checks |

**Correction made:** `822` and `823` are **not** counted as outstanding.

**Defect found:** control files describe 824 as *"the ONLY remaining v8.2 verification item."*
**This is incorrect.** `825-VERIFICATION.md` is also `human_needed` with 3 in-Rhino checks
(`behavior_unverified: 3`). Phase 825 is a **separate follow-up** with its own UAT file and was
omitted from the v8.2 closeout summary entirely.

**Reconciled:** 824 and 825 are listed **separately**, each naming its own UAT file. 825 is
recorded as follow-up work, not as part of the original v8.2 scope.

### v8.1 formal-closeout language

`MILESTONES.md` records the retrospective closeout (2026-07-13 gap-closure session: retroactive
VERIFICATION.md docs for 810–813 plus the 813 plan summary). `PROJECT.md` still describes the
formal `/gsd-complete-milestone` pass as "still pending." These are **consistent** —
retrospectively closed, formal pass never run — and are stated that way rather than as a conflict.

---

## Manual items — NOT reconcilable by this pass

Recorded as open with named owners. **No completion claim is made for any of them.**

### GSD-ALIGN-005 — Phase 35 remaining human verification [manual]

Two explicit manual items retained:

1. **G12 mixed-accept publishability gate**
2. **Real LLM recognition → preview seam**

**Not passed by synthetic-proposal tests.** All synthetic preview/accept passes are labelled
**mechanism-only**. Both remain pending/manual until a human records live evidence.

**Fixture substitution reported:** UrbanBlock_V7 was used, not Frame. Frame recovery is **not**
treated as Corpus B — the two recovered Frame source files share the definition that Corpus A and
the few-shot examples are drawn from, so grading on them would be train/test contamination
(architect decision, 2026-07-26).

**Requires:** Rhino + provider availability.

### GSD-ALIGN-008 — Phase 29 and 28 live-provider UAT [manual]

- **Phase 28** — manual/pending until a **no-restart provider switch** is observed live.
- **Phase 29 SC4** — manual/pending until a live answer **cites v4 state kinds from real data**.
- **No claim of provider-output equivalence is added.**

Unit/live-container proof is **not** treated as the missing human outcome. The parser-sensitive
representation (2 block scalars in `28-UAT.md`) is named in GSD-ALIGN-002 above so the audit
query can eventually see these items.

**Requires:** external provider + n8n state.

### GSD-ALIGN-013 — Phase 40 readiness and cross-phase closeout [manual]

**Phase 40 is the sole active closeout owner** for live E2E/manual UAT reconciliation,
documentation, and the narrow V8 publication preflight.

- The only Phase 40 manual items are the **two E2E legs** and the **provider drill**; all other
  checks have mechanical proofs.
- **INTG-03 records Phase 35/37/38 manual and failed/partial outcomes accurately** — not as a
  generic pass. Session B recognition remains an accepted blocker under **`D-40-SB-01`**
  (both tested providers reproduced `output_truncated` at the 512-token cap with one residual
  candidate; fixture reduction was deliberately **not** used to force a pass).
- **INTG-01** has measured sub-legs but **no new Speckle publish** side effect.
- **V8 preflight is recorded separately** from v11.0 migration.
- **No completion mark before live evidence.**

**Depends on:** 001, 002, 003, 007, 008, 009 — all now reconciled or explicitly open.
**Requires:** highest execution and environment risk (live Rhino / LLM / Speckle).

---

## Skip items — provenance preserved, NOT reopened

### GSD-ALIGN-011 — Future milestone isolation and BOT bridge [skip]

**No activation, no renumbering, no duplicate planning task.**

| Package | Boundary | Activation prerequisite |
|---|---|---|
| v9.1 DG Canvas Chatbot | isolated, phases **910–917** | v12.0 Phases 1200–1203 complete (GATE12-02) |
| v10.0 Script Intelligence | isolated, phases **41–49** | v12.0 1200–1204 + v11.0 semantic-boundary gate (GATE12-03) |
| v11.0 Publication Contract | isolated, phases **1101–1109** | owns full V8 alignment |
| v4.0 BOT Ontology Bridge | **future scope** | none — *not* an active stale defect |

No proposal duplicates v11.0's CNTR / CINV / BUND / RTON / SPEC / ALGN / MANU / KNOW / RELE work.
v4.0 is **not** used to explain active v9.0 status.

### GSD-ALIGN-012 — Historical archived UAT/verification reports [skip]

Old `human_needed` / `partial` reports are **historical evidence** unless a current control file
explicitly reopens them.

- Archived reports **retain their original status and verification date**. Nothing is bulk-marked
  passed; nothing is re-run as part of this pass.
- **Carry-forward list contains only:** v8.2 **824** and **825**, plus active v9.0 items.
- Every carried-forward item above has a current source path and a current owner/phase.
- No current blocker list contains an archived item solely because an old report says
  `human_needed`.

---

## Effect on v12.0 Phase 1200

| Item | Effect |
|---|---|
| **GSD-ALIGN-001** | Status vocabulary now consistent across the control plane → Phase 1200's canonical status vocabulary is designed against **true** status, not drift |
| **GSD-ALIGN-002** | UAT register computed from raw scans → 1200's gate wording rests on real coverage (17 files / 42 items), and the `audit-uat` regression is a **named known limitation** |
| **GSD-ALIGN-003** | Phase 35 SC1 is a **measured FAIL**, not "blocked" → no control-plane doc claims a passing recognition gate |

**GATE12-01 is satisfied for its `auto` class.** Phase 1200 planning may proceed.
The three `manual` items are, by classification, not resolvable here and do not block 1200.

---

## Known limitation introduced by archival

`query audit-uat` scans `.planning/phases/` only and therefore returns **0/0** while
`.planning/phases/` holds no executed phases. Until the query also scans `.planning/milestones/`,
the **raw inventory in this document is the authoritative UAT coverage record**. This supersedes,
and is broader than, the previously recorded block-scalar sensitivity.

---

*Reconciliation executed 2026-09-20. Read-only with respect to verification evidence:
no test was re-run, no status upgraded, no archived artifact rewritten.*

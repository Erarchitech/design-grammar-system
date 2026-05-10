# Phase 6: End-to-End Hardening and Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `06-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 06-end-to-end-hardening-and-verification
**Areas discussed:** E2E test approach & scope, Error-message hardening (INTG-03), Legacy regression evidence (INTG-02), Verification artifacts & closure

---

## E2E test approach & scope

### Q1 — Primary E2E verification approach

| Option | Description | Selected |
|--------|-------------|----------|
| Automated + manual checklist | C# integration tests + 06-HUMAN-UAT.md cross-phase scenarios. Most lessons from v2.0-GAP-CLOSURE.md addressed. | ✓ |
| Automated only | Pure C# integration tests; risks repeating Phase 3's blind spot for canvas-side wiring. | |
| Manual UAT checklist only | Cheapest, but no automated regression guard. | |

**User's choice:** Automated + manual checklist.

### Q2 — Backend the C# E2E test hits

| Option | Description | Selected |
|--------|-------------|----------|
| Live docker-compose stack | Test asserts stack is up; seeds temp project; cleans up. Mirrors how UAT runs. | ✓ |
| Testcontainers | Hermetic per-test containers; ~15-30s startup; new dependency. | |
| Mocked HTTP / in-memory Neo4j | Defeats gap-closure lesson — Phase 3 already did this. | |

**User's choice:** Live docker-compose stack.

### Q3 — Mandatory test matrix scenarios (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Happy path: capture → persist → retrieve → reinstate (INTG-01) | Whole chain in one scenario; INTG-01 cannot flip without it. | ✓ |
| Legacy no-state regression (INTG-02) | Validation runs without DESIGN STATE — confirm chain still works, statePayloadJson is null. | ✓ |
| State filter + rule filter retrieval | Confirm Phase 3 filter contract under live data. | ✓ |
| Reinstate failure modes (REIN-03 surfaces) | MissingTarget, TypeMismatch, OutOfRange — overlaps INTG-03. | ✓ |

**User's choice:** All four.

### Q4 — Manual UAT structure

| Option | Description | Selected |
|--------|-------------|----------|
| One 06-HUMAN-UAT.md cross-phase smoke test | New file; combines Phase 5 pending UAT step 6 with INTG-01/03 checks. | ✓ |
| Augment existing 03-HUMAN-UAT.md | Mixes phase ownership. | |
| Inline checklist in 06-VERIFICATION.md | No separate UAT file. | |

**User's choice:** One 06-HUMAN-UAT.md cross-phase smoke test.

---

## Error-message hardening (INTG-03)

### Q1 — Surfaces to harden (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Grasshopper component bubbles | AddRuntimeMessage on DesignState/Classificator/Validator/Reinstate. | ✓ |
| data-service HTTP error bodies | Structured `{error, hint, code}` JSON instead of bare 500s. | ✓ |
| Model-viewer toast / banner | Extend Phase 5's "Could not load grouped runs. Try again." retry pattern. | ✓ |
| Server logs / structured logging | Operators get full traceability while user-facing text stays short. | ✓ |

**User's choice:** All four.

### Q2 — What "actionable" means

| Option | Description | Selected |
|--------|-------------|----------|
| What+Where+How-to-fix | "Reinstatement blocked: parameter 'wallHeight' has type Boolean in saved state but Slider is Number. Reconnect a matching slider or recapture state." | ✓ |
| What+Where (no how-to-fix) | Concise but forces the user to reason about resolution. | |
| What + error code only | Compact and log-friendly but unhelpful for non-technical architects. | |

**User's choice:** What+Where+How-to-fix.

### Q3 — Error vocabulary vs. ReinstatementStatus enum

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse + extend (parallel SerializationError enum) | Keep ReinstatementStatus for reinstatement; add small enum for serialization/persistence. | ✓ |
| Unified DGErrorCode enum | Cleaner taxonomy but breaks Phase 4 contract. | |
| Free-text only | No structured way to test or filter errors. | |

**User's choice:** Reuse + extend.

### Q4 — Where error messages get tested

| Option | Description | Selected |
|--------|-------------|----------|
| Unit per component + 1 E2E + manual UAT | C# unit tests assert format per call site; pytest covers data-service bodies; one E2E error-path assertion; UAT confirms in-Rhino rendering. | ✓ |
| E2E only | Less granular failure isolation. | |
| Manual UAT only | Easiest to author but messages can drift silently. | |

**User's choice:** Unit per component + 1 E2E + manual UAT.

---

## Legacy regression evidence (INTG-02)

### Q1 — Regression evidence that flips INTG-02 to Validated

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run full suite + 1 E2E no-state scenario | dotnet test + pytest + new LegacyNoState_FlowStillWorks. | ✓ |
| Dedicated DG.Tests.Regression project | Stronger ongoing guard but bigger scope. | |
| Manual UAT only | Risky given gap-closure history. | |

**User's choice:** Re-run full suite + 1 E2E no-state scenario.

### Q2 — Specific assertions for the no-state scenario (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| run.statePayloadJson = null in Neo4j | Direct read after publish. | ✓ |
| Classificator + Validator solve without State input wired | GH-side regression. | ✓ |
| /validation/runs/{project} returns state: null | Phase 5 Plan 01 projection contract. | ✓ |
| Model-viewer "No State" bucket renders the run | Stretch — could move to manual UAT. | ✓ |

**User's choice:** All four.

### Q3 — When regression runs (gating)

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot before milestone close | Run once, capture commit SHA + counts in 06-VERIFICATION.md. | ✓ |
| Pre-commit hook | Slows local commits; out of character for this codebase. | |
| GitHub Actions on PR | Most rigorous but introduces a new system. | |

**User's choice:** One-shot before milestone close.

---

## Verification artifacts & closure

### Q1 — Closure artifacts authored at Phase 6 end (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| 06-VERIFICATION.md | Goal-backward report following Phase 4 format. | ✓ |
| 06-HUMAN-UAT.md | Cross-phase smoke checklist (per Area 1 D-04). | ✓ |
| 06-01-SUMMARY.md | Standard plan summary. | ✓ |
| v2.0 Milestone Audit / closure note | Could be deferred to /gsd-complete-milestone. | ✓ (but deferred per Q4 below) |

**User's choice:** All four (audit later folded into /gsd-complete-milestone).

### Q2 — Closure rule for INTG-01 / INTG-03 in REQUIREMENTS.md traceability

| Option | Description | Selected |
|--------|-------------|----------|
| Validated only after both automated E2E green AND human UAT pass | Most defensive given gap-closure history. | ✓ |
| Validated when automated E2E passes; UAT informational | Risks Rhino-side blind spots. | |
| Validated when UAT passes; automated supplementary | Trusts user as ground truth. | |

**User's choice:** Both automated + human UAT.

### Q3 — Phase 5 verification scope

| Option | Description | Selected |
|--------|-------------|----------|
| Backfill 05-VERIFICATION.md separately, keep Phase 6 scoped to INTG-* | Cleanest separation. | ✓ |
| Fold Phase 5 verification into 06-VERIFICATION.md | Mixes phase ownership. | |
| Skip Phase 5 verification | Risky given gap-closure history. | |

**User's choice:** Backfill 05-VERIFICATION.md separately.

### Q4 — Where the v2.0 Milestone Audit lives

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to /gsd-complete-milestone after Phase 6 closes | Matches v1.1 pattern; archives phases to .planning/milestones/v2.0-phases/. | ✓ |
| Author .planning/v2.0-MILESTONE-AUDIT.md inside Phase 6 | Couples milestone-level writing into a phase plan. | |
| Skip a dedicated audit | Lightest; relies on reader stitching from 6 SUMMARYs. | |

**User's choice:** Defer to /gsd-complete-milestone.

---

## Claude's Discretion

The user explicitly delegated:
- Specific test naming for the four E2E scenarios (D-03 names are guidance, not contract).
- Concrete copy of every user-facing error string (templates locked, strings free).
- C# project layout under `DG/tests/DG.Tests/E2E/`.
- Pytest organization for new data-service error-body tests.
- Russian/English copy choices for user-facing messages.

## Deferred Ideas

- CI wiring (GitHub Actions / pre-commit) — out of scope for v2.0.
- Dedicated DG.Tests.Regression project — single E2E scenario sufficient.
- Folding Phase 5 verification into Phase 6 — backfill separately.
- v2.0-MILESTONE-AUDIT.md inside Phase 6 — defer to /gsd-complete-milestone.
- Update 06-01-PLAN.md `<context>` block to fix stale `.planning/milestones/v2.0-REQUIREMENTS.md` reference — the planner should do this during replan.
- Russian-language UAT copy — discretionary.

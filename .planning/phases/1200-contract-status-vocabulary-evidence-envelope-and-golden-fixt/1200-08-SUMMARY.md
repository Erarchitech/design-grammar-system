---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 08
subsystem: evidence-contract
tags: [de01, canonical-json, evidence-envelope, requirements-ledger, docker]

requires:
  - phase: 1200-06
    provides: cross-language canonical JSON decimal-scale parity fix
  - phase: 1200-07
    provides: DE-01 compare_legs silent-disagreement classification fix

provides:
  - First genuine four-leg DE-01 run (data-service, dg-reasoner, csharp, replay all available) against the corrected code
  - Reconciled ALGN12-01..04 checkbox state in .planning/REQUIREMENTS.md, each traceable to a named SUMMARY
  - Owner re-confirmation of the Phase 1200 freeze with both defects, their fixes, and the live run in view
  - A new finding routed to Phase 1201: dg-reasoner is not targeting the seeded golden objects (SHACL empty-target-set no_population on all three)

affects: [1201-parser-evaluator-conformance]

key-files:
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "ALGN12-02 re-closed on 1200-06's evidence alone (cross-language hash parity fix, recomputed golden vector, both suites passing)"
  - "ALGN12-04 stays open: 1200-07's classification fix is proven correct by the live run, but the requirement's own acceptance condition ('supported cases agree canonically') is not met — dg-reasoner disagreed with the other three legs on 2 of 3 objects — and inputHash/outputHash were null on every leg, so CR-01 could not be confirmed at the live service boundary"
  - "Owner re-affirmed the Phase 1200 freeze with CR-01, CR-02, their fixes, and this live run in view, superseding the 2026-09-20 pre-defect approval; routed the dg-reasoner finding to Phase 1201 rather than blocking the freeze"
  - "Owner confirmed canonicalizationVersion stays at 1 — the decimal scale-preservation fix is a clarification of existing rule 2, not a breaking change; already-recorded hashes remain valid"

requirements-completed: []

coverage:
  - id: D1
    description: "Live four-leg DE-01 run executed against corrected code (GAP-3 closed)"
    verification:
      - kind: manual_procedural
        ref: ".de01/de01-report.md generated 2026-09-20T12:33:43Z, postdating 1200-06 (12:25:49) and 1200-07 (12:31:03) commits"
        status: pass
    human_judgment: true
    rationale: "Only a human reading the live report can distinguish genuine cross-leg agreement from the structural silence of unavailable legs, per the plan's explicit prohibition on an executor inferring this outcome"
  - id: D2
    description: "ALGN12-01..04 checkbox state reconciled to evidence in REQUIREMENTS.md"
    requirement: "ALGN12-01, ALGN12-02, ALGN12-03, ALGN12-04"
    verification:
      - kind: other
        ref: "python regex verify command in 1200-08-PLAN.md Task 2 <verify>"
        status: pass
    human_judgment: false
  - id: D3
    description: "Owner re-confirmation of Phase 1200 freeze with both defects and the live run in view"
    verification: []
    human_judgment: true
    rationale: "ROADMAP gate 'accepted by the owner' cannot be satisfied by an agent; the plan explicitly prohibits self-approval"

duration: ~50min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 08: Live DE-01 Run, Requirement Reconciliation, Owner Freeze Confirmation

**GAP-3 closed: the four-leg DE-01 comparison ran for the first time against the corrected code, surfacing a new dg-reasoner finding; ALGN12-02 is re-closed on evidence, ALGN12-04 stays open and routes to Phase 1201, and the owner re-affirmed the Phase 1200 freeze with all of this in view.**

## Performance

- **Started:** 2026-09-20T12:20Z (Docker Desktop startup)
- **Completed:** 2026-09-20T13:14Z
- **Tasks:** 3/3 (2 human-verify checkpoints, 1 auto)
- **Files modified:** 1 (`.planning/REQUIREMENTS.md`)

## Task 1: Live four-leg DE-01 run (GAP-3)

### Environment setup (not part of files_modified, infrastructure only)

1. Brought up `neo4j`, `dg-reasoner`, `data-service` via `docker compose up -d`. `data-service` initially crash-looped (`neo4j:7687 connection refused`) because it started before Neo4j's Bolt listener was ready — resolved by waiting for Neo4j to accept connections, then `docker compose up -d data-service` again.
2. Applied `fixtures/golden/seed.cypher` unchanged via `cypher-shell -f`, run inside the `neo4j` container (`docker cp` + `docker exec`) since `cypher-shell` is not on the host. Confirmed 18 nodes seeded under `project: 'DG-1200-GOLDEN'`.
3. **Found and fixed an infrastructure defect not in this plan's original scope:** the running `data-service` container was built from a stale image (created 2026-09-19T21:59) that predated the same day's Phase 1200 code changes (`app.py` last modified 2026-09-20T09:00) — its `/app/app.py` had no `_build_publish_evidence_envelope` function at all. This caused the data-service and replay legs to fail with "evidenceEnvelope absent from view/persisted run" for a reason unrelated to CR-01/CR-02: the container was simply running old code. Fixed with `docker compose build --no-cache data-service` + `docker compose up -d data-service`. This is a deviation (Rule 1, auto-fixed infrastructure bug) — necessary to get a genuine run at all; the alternative (reporting the run as blocked) would have been true but uninformative, since the actual blocker was a stale image, not Docker being down.
4. Confirmed `dotnet build DG/DG.sln -c Release` succeeds: 0 warnings, 0 errors.
5. `dg-reasoner` has no host-published port by default (confirmed in `docker-compose.yml` and `tools/de01/README.md`, both unmodified). To get a genuine reading rather than accepting a host-side timeout, I temporarily added a docker-compose **override file** (`docker-compose.de01-override.yml`, never merged into the tracked `docker-compose.yml`) publishing `dg-reasoner`'s internal port 8000 to host port 18001, ran DE-01 from the host with `--dg-reasoner-url http://localhost:18001`, then removed the override file and recreated `dg-reasoner` from the original `docker-compose.yml` alone. `git status --short docker-compose.yml` shows no diff.

### The run

```
python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json --out-dir .de01 \
  --data-service-url http://localhost:8000 --dg-reasoner-url http://localhost:18001
```

Report generated `2026-09-20T12:33:43Z` (`.de01/de01-report.json`, `.de01/de01-report.md` — gitignored evidence artifacts, not committed).

### The six observations (verbatim from the report)

**a. Leg availability:** All four legs report `available: true` — `csharp`, `data-service`, `dg-reasoner`, `replay`. None deliberately stopped; all genuinely reachable.

**b. silent_disagreement_count: 3.** Not zero. Real verdicts exist (`passed`/`failed` from data-service, csharp, replay), but `dg-reasoner` reported `no_population` on **all three** golden objects (`OBJ_GOLD_EMPTY`, `OBJ_GOLD_FAIL`, `OBJ_GOLD_PASS`). Warnings appendix, verbatim: *"dg-reasoner reported conforms=true with zero SHACL findings -- mapped to no_population (not passed) because pySHACL's empty-target-set conforms=true is the exact collapsed-status behavior this contract's vocabulary exists to separate out."* This means dg-reasoner's SHACL shapes are not matching (targeting) these seeded objects at all — a real disagreement, not a structural artifact of absent legs.

**c. ObjectPropertyAtom row (`R_GOLD_HEIGHT_MAX_75_V` / `OBJ_GOLD_FAIL`):** csharp reports `failed, unsupported`. Verbatim reason: *"What: atom 'R_GOLD_HEIGHT_MAX_75_V_A4' (ObjectPropertyAtom, belongsToDistrict(?b, ?d)) has no resolvable type on the C# leg. Where: DG.Core.Parsing.SwrlRuleParser.ResolveAtomType has no ObjectPropertyAtom branch (returns only BuiltinAtom/ClassAtom/DataPropertyAtom). How to fix: Phase 1201's ALGN12-05 adds the missing branch. This is a pre-declared, by-design non-result."* This matches the pre-declared expectation exactly. However, because dg-reasoner **also** disagrees on this same row (`no_population`), the row's overall classification is `silent_disagreement` (from the dg-reasoner/data-service/csharp/replay 3-way split: `['failed', 'no_population', 'unsupported']`), not an isolated declared non-equivalence standing alone — the two findings are entangled in this run's output rather than separable, because the classifier operates per-row across all available legs.

**d. Other rows:** `OBJ_GOLD_PASS` — data-service/csharp/replay all agree `passed`; dg-reasoner alone disagrees (`no_population`). `OBJ_GOLD_EMPTY` — data-service/replay read `unknown` (not `failed`, correctly avoiding the collapsed-boolean trap per D-04), csharp/dg-reasoner read `no_population`; the four-way split is itself the silent disagreement for this row.

**e. Hash parity:** **Not observable.** `inputHash` and `outputHash` are `null` for every leg on every one of the 3 comparison rows in `de01-report.json`. CR-01's fix (verified at the unit-test level in 1200-06) could not be confirmed at this live cross-service boundary in this run.

**f. Run result:** FAIL. `silent_disagreement_count = 3 > 0`, exit code 1. Per the plan's instructions this is genuine information, not something to re-run or paper over. No file under `fixtures/golden/` or `tools/de01/` was modified — confirmed via `git status --short` before and after.

**New finding routed to Phase 1201:** dg-reasoner's SHACL shapes are not targeting the seeded `DG-1200-GOLDEN` objects, producing a false `no_population` (empty-target-set `conforms=true`) instead of a real evaluation on `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`. This is separate from the already-known, pre-declared `ObjectPropertyAtom` C#-leg gap (ALGN12-05).

**User (owner) response:** "run recorded" — accepted the six observations as reported, no request to re-run or alter anything.

## Task 2: Reconcile ALGN12-01..04 in REQUIREMENTS.md

- **ALGN12-01, ALGN12-03:** left `[x]` — untouched, per verifier's original finding that these remain genuinely satisfied. Confirmed `fixture.json` itself (ALGN12-03's subject) was not touched by 1200-06 — only the sibling `canonical-vectors.json` gained a vector under the freeze policy.
- **ALGN12-02:** closed `[x]`. Justification: 1200-06-SUMMARY shows the C# leg now derives decimal scale from `decimal.GetBits` and renders via `ToString("F{scale}")`, matching Python's `format(Decimal, "f")`; a new golden vector with trailing-zero decimals was added with a digest recomputed from an actual run of `canonical_json.py` (not hand-authored); both `dotnet test` (13/13 on the writer tests, 442/446 overall with 4 known pre-existing Neo4j-env failures) and `pytest` (67/67) pass; the four pre-existing vectors reproduce their original digests unchanged.
- **ALGN12-04:** left `[ ]`, open. Justification requires **both** citations per the plan:
  - 1200-07-SUMMARY: the classification fix landed (guard fires on any non-empty non-declarable-status set), corrected tests green (13 passed), a second live instance of the same defect shape found and fixed in the existing suite.
  - This plan's Task 1 live run: **executed genuinely** (all four legs available, against corrected code) — closing GAP-3 — but the run's own result (`silent_disagreement_count = 3`) means the requirement's acceptance condition ("supported cases agree canonically... unsupported cases are typed rather than silently divergent") is not yet demonstrated. The dg-reasoner SHACL-targeting gap is a real, uncorrected disagreement. Additionally, `inputHash`/`outputHash` were null throughout, so CR-01 remains unproven at this boundary.
- Updated the Phase 1200 note in `.planning/REQUIREMENTS.md` to replace the `gaps_found` note with a `gap-closure, 2026-09-20` note naming: both defects, both closure plans (1200-06, 1200-07) by number, what the live run established and did not establish, and the finding routed to Phase 1201.
- Verify command (from `1200-08-PLAN.md` Task 2 `<verify>`) passes: `ALGN12-01=x, ALGN12-02=x, ALGN12-03=x, ALGN12-04=' '`, note cites both `1200-06` and `1200-07`.
- `git diff --name-only` for this task: only `.planning/REQUIREMENTS.md`. `git diff --stat`: 2 insertions, 2 deletions (checkbox line + note line).

**Committed:** `5e9a7a3` — `docs(1200-08): reconcile ALGN12-01..04 against live evidence`

## Task 3: Owner re-confirmation of the Phase 1200 freeze

Presented the owner with the six-point review from `<how-to-verify>`: both defects and their independent reproduction in `1200-VERIFICATION.md`; the CR-01 fix in 1200-06; the CR-02 fix in 1200-07 (explicitly flagging it as a stricter-than-shipped judgment call — any single non-declarable status now fails agreement); the live run's actual content (the dg-reasoner finding, the ObjectPropertyAtom case behaving as pre-declared, the null hashes); `spec/EVIDENCE-CONTRACT.md` §6's scale-preservation clarification at `canonicalizationVersion: 1`; and the explicit decision needed on whether the dg-reasoner finding blocks the freeze or routes to Phase 1201.

**Owner's verbatim ruling (via structured question, options as given):**

- Freeze decision: **"Re-affirm freeze; route finding to 1201 (Recommended)"** — selected option text: *"Accept the contract as frozen. The dg-reasoner no_population finding and the null-hash observation become named gaps for Phase 1201 to resolve, alongside ALGN12-05. ALGN12-04 stays open in REQUIREMENTS.md until 1201 closes them."*
- `canonicalizationVersion` question: **"Keep canonicalizationVersion at 1 (Recommended)"** — selected option text: *"Treat this as a clarification/bugfix to an always-intended rule, not a contract change. Matches 1200-06's own framing and avoids invalidating already-recorded hashes."*

This acceptance is given with CR-01, CR-02, their fixes, and the live four-leg run (including its new finding) in view — it supersedes, and is distinct from, the 2026-09-20 pre-defect approval recorded in `1200-05-SUMMARY.md`. The dg-reasoner SHACL-targeting finding and the null-hash observation do **not** block the freeze; both are routed to Phase 1201 as named gaps alongside the already-known ALGN12-05 (`ObjectPropertyAtom`/`SwrlRuleParser.ResolveAtomType`) item. `canonicalizationVersion` remains `1` in `spec/EVIDENCE-CONTRACT.md` — no further edit was needed since 1200-06 already recorded it that way.

## Decisions Made

- Diagnosed and fixed a stale `data-service` Docker image out-of-band from this plan's declared scope, because a run against it would have reproduced the same 3-of-4-legs-error shape the plan exists to move past, for a reason unrelated to CR-01/CR-02 or Docker availability. Documented as a deviation rather than silently worked around.
- Used a throwaway `docker-compose.de01-override.yml` (never committed, removed after the run) to publish dg-reasoner's port for one genuine host-side four-leg run, rather than leaving dg-reasoner permanently unreachable from the host or editing the tracked `docker-compose.yml`.
- ALGN12-04 closure was withheld even though the classification mechanism is proven correct, because the plan's must-haves are explicit that this requirement needs the *deliverable* (clean agreement) demonstrated, not just the *mechanism* (correct classification) proven.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Auto-fixed infrastructure bug] Stale data-service Docker image**
- **Found during:** Task 1 (live DE-01 run setup)
- **Issue:** The running `data-service` container was built from an image created 2026-09-19T21:59, before `app.py` was last modified 2026-09-20T09:00 (same day's earlier Phase 1200 plans). The container's `/app/app.py` had no `_build_publish_evidence_envelope` function, so every `/validation/publish` call silently produced no `evidenceEnvelopeJson`, and both the data-service and replay legs failed with "evidenceEnvelope absent."
- **Fix:** `docker compose build --no-cache data-service && docker compose up -d data-service`. Re-seeded the graph afterward (teardown + reapply `fixtures/golden/seed.cypher` unchanged) since stale publish attempts had left partial `:ValidationRun` nodes.
- **Files modified:** None (infrastructure only; no source file changed).
- **Verification:** `docker exec data-service grep -n "_build_publish_evidence_envelope" /app/app.py` returned the function definition after rebuild; the data-service and replay legs then reported `available: true`.
- **Committed in:** N/A (infrastructure state, not a git-tracked change).

---

**Total deviations:** 1 auto-fixed (infrastructure).
**Impact on plan:** Necessary to obtain a genuine four-leg run at all — without it, the run would have reproduced the exact pre-existing 3-of-4-legs-error report the plan exists to move past, masking the actual state of the corrected code. No scope creep into source files.

## Issues Encountered

- `dg-reasoner` has no host-exposed port by default (by design, per `tools/de01/README.md`); resolved with a temporary, non-committed compose override rather than editing tracked infrastructure.
- Git-Bash path mangling (`MSYS_NO_PATHCONV`) required for several `docker exec`/`docker cp` invocations targeting absolute container paths like `/tmp/...` and `/app/...`; not a project issue, a host shell quirk.

## User Setup Required

None beyond the Docker Desktop startup already covered by this plan's `user_setup` block and Task 1's checkpoint.

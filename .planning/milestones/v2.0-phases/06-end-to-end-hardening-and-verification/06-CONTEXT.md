# Phase 6: End-to-End Hardening and Verification - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the v2.0 milestone gate by proving the full state lifecycle works end-to-end (INTG-01), confirming the legacy no-state flow has not regressed (INTG-02), and ensuring serialization, persistence, and reinstatement errors surface as actionable user-facing messages (INTG-03). Verification only — no new product features. Phases 1-5 deliver the capability; Phase 6 makes it provably correct and ships.

</domain>

<decisions>
## Implementation Decisions

### E2E test approach
- **D-01:** Hybrid verification: automated C# integration tests in `DG/tests/DG.Tests/E2E/` plus a manual UAT checklist at `06-HUMAN-UAT.md`. Single source of truth for human verification.
- **D-02:** Automated tests target the live `docker compose` stack (Neo4j on `:7687`, data-service on `:8000`). The runner asserts the stack is up before tests start; tests seed a temp project, exercise the flow, and clean up. No Testcontainers, no in-memory mocks — gap-closure lesson is that mocked chains hide the real failure mode.
- **D-03:** Mandatory test matrix in `DesignStateValidationFlowTests.cs`:
  - `HappyPath_CaptureToReinstate` — full chain (DESIGN STATE → Classificator → Validator → publish → Neo4j → VALIDATION RUNS retrieval → REINSTATE apply). Closes INTG-01.
  - `LegacyNoState_FlowStillWorks` — same flow with State input unwired; asserts `run.statePayloadJson` is null and `state` field returns null in retrieval projection. Closes INTG-02.
  - `Filtering_StateAndRule` — asserts state filter, rule filter, both, and neither return correct subsets (regression lock for Phase 3).
  - `ReinstateFailureModes_ProduceActionableMessages` — exercises `MissingTarget`, `TypeMismatch`, `OutOfRange` and asserts the `Report` output contains the documented user message templates. Overlaps INTG-03.

### Manual UAT
- **D-04:** `06-HUMAN-UAT.md` is one cross-phase smoke test that includes Phase 5 Plan 02's pending step 6 (grouping switch + resize handle UAT). Numbered scenarios cover GH canvas wiring, viewer interaction, and error rendering — the surfaces automated tests can't reach.

### Error-message hardening (INTG-03)
- **D-05:** Hardening covers four surfaces: Grasshopper component bubbles (`AddRuntimeMessage` on DesignState, Classificator, Validator, Reinstate), data-service HTTP error bodies (FastAPI structured JSON `{error, hint, code}` instead of bare 500s), model-viewer toast/banner (extends Phase 5's `Could not load grouped runs. Try again.` retry pattern), and structured server-side logs.
- **D-06:** Message template is `What+Where+How-to-fix`. Pattern: `"{What failed}: {specific identifier}. {How to fix}."` Example: `"Reinstatement blocked: parameter 'wallHeight' has type Boolean in saved state but Slider is Number. Reconnect a matching slider or recapture state."`
- **D-07:** Error vocabulary reuses + extends the existing 7-value `ReinstatementStatus` enum (Phase 4 contract). Add a parallel small `SerializationError` enum on the persistence side covering at minimum: `NoStateProvided`, `MalformedStatePayload`, `MissingParameterId`, `TimestampMissing`. Each enum value maps to one user-facing template — keeps messages testable.
- **D-08:** Error-message tests live at three levels: C# unit tests per component asserting message format from each call site, Python pytest covering data-service error bodies, and a single E2E assertion in `DesignStateValidationFlowTests.cs` confirming one error-path scenario produces the documented user message. Manual UAT confirms in-Rhino rendering.

### Legacy regression (INTG-02)
- **D-09:** Regression evidence = re-run full existing test suite (`dotnet test DG/tests/DG.Tests/` — current 49 tests + new E2E additions; `pytest data-service/tests/` — current 20 tests) plus the new `LegacyNoState_FlowStillWorks` E2E scenario.
- **D-10:** No-state E2E assertions: (a) `ValidationRun` is created with `run.statePayloadJson = null`; (b) Classificator + Validator components don't error or warn when State input is unwired; (c) `GET /validation/runs/{project}` returns the run with `state: null` per Phase 5 Plan 01 projection; (d) model-viewer "No State" bucket renders the run when grouping mode is `state`. Item (d) lives in 06-HUMAN-UAT.md if too costly to automate.
- **D-11:** Gating is one-shot before milestone close. No CI/pre-commit wiring — out of character for this codebase. Run results (commit SHA, counts, durations) are captured in `06-VERIFICATION.md`.

### Verification artifacts & closure
- **D-12:** Phase 6 produces three documents: `06-VERIFICATION.md` (goal-backward report following the Phase 4 pattern: Observable Truths, Required Artifacts, Key Link Verification, Behavioral Spot-Checks, Requirements Coverage, Anti-Patterns, Gaps), `06-HUMAN-UAT.md` (cross-phase smoke checklist), `06-01-SUMMARY.md` (standard plan summary).
- **D-13:** Requirement-closure rule for INTG-01 and INTG-03 in `.planning/REQUIREMENTS.md` traceability table: status flips to **Validated** only when automated E2E is green AND human UAT signed off. INTG-02 flips to **Validated** when D-09 evidence is captured.
- **D-14:** Phase 5 verification is **out of scope for Phase 6**. Backfill a separate `05-VERIFICATION.md` (via `/gsd-validate-phase 5` or hand-written) asserting MVGP-01..03 against the production bundle. Keeps phase ownership clean and the v2.0 milestone audit readable.
- **D-15:** Cross-milestone audit is **deferred to `/gsd-complete-milestone`** after Phase 6 closes. That step archives `.planning/phases/` to `.planning/milestones/v2.0-phases/` per the convention in [CLAUDE.md](CLAUDE.md) and writes the milestone closure note. Mirrors the v1.1 pattern.

### Claude's Discretion
- Specific test naming for the four E2E scenarios (the names in D-03 are guidance, not contract).
- Concrete copy of every user-facing error string. Decisions D-06 and D-07 lock the template + vocabulary; the planner/executor writes the strings.
- C# project layout under `DG/tests/DG.Tests/E2E/` (single file vs subfolder, fixture/helper organization).
- Pytest organization for the new data-service error-body tests.
- Russian/English copy choices for user-facing messages (project precedent is English in source, Russian acceptable in UAT docs and Obsidian).

### Folded Todos
None — no todos matched.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

> Note on stale path: the existing `06-01-PLAN.md` and the previous `06-CONTEXT.md` referenced `.planning/milestones/v2.0-REQUIREMENTS.md`, which does not exist. Per the convention in [CLAUDE.md](CLAUDE.md) ("`.planning/phases/` always holds the **currently active milestone**"), the active v2.0 requirements live at `.planning/REQUIREMENTS.md`. The planner should update `06-01-PLAN.md` `<context>` block to point at the correct path during replanning.

### Requirements & milestone
- `.planning/REQUIREMENTS.md` §"Integration and Safety" — INTG-01, INTG-02, INTG-03 acceptance criteria + traceability table that Phase 6 must update.
- `.planning/REQUIREMENTS.md` §"Phase 3.1 — Gap Closure (retroactive)" — context for why Phase 6 must follow data flow end-to-end, not check components in isolation.
- `.planning/v2.0-GAP-CLOSURE.md` — Phase 1/2 retrospective; "Recommended planning safeguards" section is the standard Phase 6 verification must hit.
- `.planning/ROADMAP.md` — milestone v2.0 phase list and progress table that flips on close.

### Phase artifacts feeding Phase 6
- `.planning/phases/02-classificator-state-input-and-run-persistence/02-01-PLAN.md` — Classificator State input contract (DGCL-01, DGCL-02).
- `.planning/phases/03-validation-runs-retrieval-component/03-01-PLAN.md` — VALIDATION RUNS contract (DGCL-03, DGRN-01..03).
- `.planning/phases/04-reinstatement-component/04-VERIFICATION.md` — Phase 4 verification template (mirror in 06-VERIFICATION.md).
- `.planning/phases/05-model-viewer-grouping-by-rule-state/05-01-SUMMARY.md` — `state` projection contract on `/validation/runs/{project}`.
- `.planning/phases/05-model-viewer-grouping-by-rule-state/05-02-SUMMARY.md` — ValidationRunsStrip behavior + pending UAT step 6 (folded into 06-HUMAN-UAT.md per D-04).

### Project conventions
- [CLAUDE.md](CLAUDE.md) §"Repository Structure" — planning archive convention used at milestone close (D-15).
- [CLAUDE.md](CLAUDE.md) §"Common Commands" — `dotnet build .\DG\DG.sln -c Release`, `dotnet test .\DG\tests\DG.Tests\`.
- [CLAUDE.md](CLAUDE.md) §"Known Gotchas" — Docker layer caching `--no-cache` requirement is relevant when E2E tests rebuild data-service.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ReinstatementStatus` enum** (DG/src/DG.Core/Models/ReinstatementStatus.cs): 7 values (Applied, MissingTarget, TypeMismatch, AmbiguousTarget, OutOfRange, Unchanged, WouldApply). Pattern to extend for serialization errors per D-07.
- **`ReinstatementParameterReport`** (DG/src/DG.Core/Models/ReinstatementParameterReport.cs): per-parameter error report shape. Reusable in serialization-error reporting.
- **`DesignStateReinstatementService.Validate`** (DG/src/DG.Core/Services/DesignStateReinstatementService.cs): stateless validation entry point — call site for unit-level message tests under D-08.
- **`_project_state_summary`** (data-service/app.py): defensive JSON projector. Phase 6 should add an analogous defensive error-builder to convert exceptions to structured `{error, hint, code}` HTTP bodies.
- **`ValidationRunsStrip`** error state (graph-viewer/model-viewer/src/ValidationRunsStrip.jsx): existing `Could not load grouped runs. Try again.` + retry pattern is the template for new viewer error surfaces (D-05).
- **`xUnit` infrastructure** (DG/tests/DG.Tests/DG.Tests.csproj): existing test runner — add an `E2E/` subfolder and an integration-test trait/category to allow `--filter` to run unit-only or E2E-only.
- **Existing pytest fixture infrastructure** (data-service/tests/conftest.py): leverage for new error-body tests.

### Established Patterns
- **TDD with RED-before-GREEN**: Phase 5 Plans 01 and 02 both wrote failing tests before implementation. Phase 6 should follow the same pattern for the error-message and E2E scenarios.
- **Per-environment exception coverage**: Phase 5 Plan 01 caught `RecursionError` for Python 3.11 container compat (Python 3.14 dev did not raise). Same care needed for Phase 6 error tests if any deal with deep input.
- **Defensive JSON projection that "never raises"**: `_project_state_summary` contract; replicate for error-body builder.
- **Phase 4 VERIFICATION.md table layout**: Observable Truths / Required Artifacts / Key Link / Behavioral Spot-Checks / Requirements Coverage / Anti-Patterns / Gaps. Direct template for 06-VERIFICATION.md.
- **Phase 3 HUMAN-UAT.md numbered scenario style** (referenced in v2.0-GAP-CLOSURE.md): direct template for 06-HUMAN-UAT.md.
- **Status legend in `.planning/REQUIREMENTS.md`**: `Code Complete` → `Validated` transition with commit/date evidence. Phase 6 traceability updates follow this exact pattern.

### Integration Points
- **`DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs`** — new file, the single E2E test class.
- **`data-service/app.py`** — exception handlers / response models; needs a structured error helper.
- **`data-service/tests/test_*.py`** — new test file for HTTP error body assertions.
- **`graph-viewer/model-viewer/src/App.jsx`** — extend the `runsError` pattern from Phase 5 Plan 02 to other failure paths (state load, reinstatement-related fetches if any).
- **`DG/src/DG.Grasshopper/Components/{ClassificatorComponent,ValidatorComponent,ReinstateComponent}.cs`** — `AddRuntimeMessage` call sites for D-05.
- **`.planning/REQUIREMENTS.md`** traceability table — INTG-01, INTG-02, INTG-03 status flip per D-13.
- **`.planning/ROADMAP.md`** — Phase 6 row in progress table flips from Planned to Complete on milestone close.

</code_context>

<specifics>
## Specific Ideas

- "Mirror Phase 4's VERIFICATION.md format" — the user-explicit template choice; Phase 4 is the cleanest goal-backward report in the project.
- "Match Phase 3's HUMAN-UAT numbered-scenario style" — proven format for live integration sign-off.
- Reuse Phase 5's "retry affordance" microcopy pattern for new viewer error surfaces — keeps UX consistent.
- The 7-value `ReinstatementStatus` enum's *names* are good user-facing language already (`MissingTarget`, `TypeMismatch`, etc.) — message templates should keep that vocabulary visible to architects, not hide it behind error codes.

</specifics>

<deferred>
## Deferred Ideas

- **CI wiring (GitHub Actions / pre-commit)** — considered in D-11, deferred. Not character-appropriate for v2.0; revisit if a future milestone introduces a need for automated regression on every commit.
- **Dedicated `DG.Tests.Regression` project** — considered in INTG-02 evidence, deferred. Single E2E scenario + full-suite re-run is sufficient for v2.0.
- **Folding Phase 5 verification into Phase 6** — rejected; backfill 05-VERIFICATION.md separately per D-14.
- **`v2.0-MILESTONE-AUDIT.md` authored inside Phase 6** — rejected; defer to `/gsd-complete-milestone` per D-15.
- **Update `06-01-PLAN.md` `<context>` block to fix the stale `.planning/milestones/v2.0-REQUIREMENTS.md` ref** — small follow-up; the planner should fix this during the replan triggered by this updated context. Not a Phase 6 deliverable on its own.
- **Russian-language UAT copy** — not blocking; `06-HUMAN-UAT.md` may include parallel RU strings if helpful for the user, but that's discretionary.

</deferred>

---

*Phase: 06-end-to-end-hardening-and-verification*
*Context gathered: 2026-05-08*

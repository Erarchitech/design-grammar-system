---
phase: 1303-pravilo-gh-obekt
plan: "19"
subsystem: dg-core-validation
tags: [d-61, d-62, dgopn-06, swrl-subset, context-participants, rule-evaluator, binding]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-15 (generated calculators); RuleEvaluator, DesignStateBindingService, SWRL-SUBSET contract from phases 7 and 1201"
provides:
  - "DG.Core.Parsing.RuleVariableRoles: SubjectVariable, IsContextOnly, IsContextAtom, ContextAtoms (one shared classifier)"
  - "binder skips context-only variables, so the acceptance rule yields the rows of its one-class form"
  - "evaluator answers context atoms as matched and discloses them in the Passed/Failed message"
  - "FailingBindingFormatter and the Grasshopper RULE DECONSTRUCT Objects output skip context-only variables"
  - "spec/SWRL-SUBSET.md describes the context-participant semantics"
affects: [1303-20, 1303-21, 1303-22, 1303-23]
tech-stack:
  added: []
  patterns:
    - "classify once per EvaluateRule over the exact atoms evaluated (internal RoleAnalysis), public per-call wrappers for other callers"
    - "violation-pattern encoding: a matched atom is Failed, so a context atom returns Failed/null without resolving variables"
key-files:
  created:
    - DG/src/DG.Core/Parsing/RuleVariableRoles.cs
    - DG/tests/DG.Tests/RuleVariableRolesTests.cs
    - DG/tests/DG.Tests/RuleEvaluatorContextParticipantTests.cs
  modified:
    - DG/src/DG.Core/Services/DesignStateBindingService.cs
    - DG/src/DG.Core/Validation/RuleEvaluator.cs
    - DG/src/DG.Core/Validation/FailingBindingFormatter.cs
    - DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs
    - DG/tests/DG.Tests/DesignStateBindingServiceTests.cs
    - spec/SWRL-SUBSET.md
key-decisions:
  - "Disclosure text is pinned: ' Asserted by the rule, not verified: Slab(?s), hostedBy(?o, ?s), Column(?c), projectsOnto(?c, ?s), Wall(?w), projectsOnto(?w, ?s).' appended after the unchanged message, only for Passed or Failed."
  - "Atom names in the disclosure use PredicateLabel, else the last segment of PredicateIri after '#' or '/', else the IRI as written."
  - "No field was added to RuleEvaluationResult; the sentence reaches the evidence envelope and the GH report through the existing Message/detail flow."
  - "A context-only variable inside an ObjectPropertyAtom that has a literal argument keeps that atom refused (Unsupported) while the variable is still excluded from binding: refusing beats guessing."
requirements-completed: []
requirements_partial: [DGOPN-06]
duration: ~45min
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 19: Context participants in the C# validator Summary

A rule that names Slab, Column and Wall next to the checked Opening and relates them with `hostedBy` / `projectsOnto` now validates exactly like its one-class form; the participants are asserted by the rule, not bound, and disclosed in the result message, while joins, headless rules and argument-less object-property atoms keep the typed `unsupported` refusal.

## Performance

- Tasks: 3 of 3, three task commits, no deviations.
- Test counts, `dotnet test .\DG\tests\DG.Tests\` (net9.0): before 795 total, 790 passed, 5 failed; after 816 total, 811 passed, 5 failed. The 21 added tests all pass; the same 5 tests fail before and after.

## Accomplishments

- `RuleVariableRoles` (Task 1): subject = head[0] position-1 variable; context-only = not subject, in the body, not in the head, only in `ClassAtom`/`ObjectPropertyAtom`; context atom = body `ClassAtom` of a context-only variable, or a two-variable `ObjectPropertyAtom` whose arguments are subject or context-only with at least one context-only. `VariableTypeInferrer` and `VariableKind` are untouched (a test pins that `?s`, `?c`, `?w` still infer as Object).
- Binder (Task 2): `BuildBindings` skips context-only variables before classification, so they never reach `RuleVariableUnclassified`, and Slab/Column/Wall ObjStates never produce rows or `BindingServiceNoObjectBindings`.
- Evaluator (Task 2): `EvaluateAtom` returns `Failed`/null for a context atom before the ObjectPropertyAtom refusal; `EvaluateRule` classifies once over the exact atoms it evaluates and appends the disclosure when status is Passed or Failed. A rule without context atoms keeps its message byte for byte (`Rule violated by 1 binding(s).` pinned).
- `FailingBindingFormatter.ExtractClassVariables` skips context-only variables (output equals the one-class form's `o(O1): d(300)`).
- Task 3: the Grasshopper `RuleDeconstruct` Objects output skips context-only variables; the METAGRAPH `ObjectsQuery` is unchanged so the classes stay mappable (D-62). `spec/SWRL-SUBSET.md` §1.1 (definitions), §2 (new refusal scope plus "asserted, not evaluated" paragraph) and the §3 table row ("ObjectPropertyAtom evaluation outside a context atom") are updated; both machine-checked fenced blocks are byte-identical.

## Pinned disclosure text

For the acceptance rule: `Rule violated by 1 binding(s). Asserted by the rule, not verified: Slab(?s), hostedBy(?o, ?s), Column(?c), projectsOnto(?c, ?s), Wall(?w), projectsOnto(?w, ?s).` and, when passing, `Rule passed for all bindings. Asserted by the rule, not verified: ...` (same list).

## Task Commits

1. Task 1, RuleVariableRoles classifier and tests: `2ed3102`
2. Task 2, binding, evaluation, disclosure, failing-binding text: `71ca2c8`
3. Task 3, Grasshopper Objects output and SWRL-SUBSET: `8a51f14`

## Verification

- `dotnet test .\DG\tests\DG.Tests\ --filter FullyQualifiedName~RuleVariableRolesTests`: 11 passed.
- Focused run (RuleVariableRolesTests, DesignStateBindingServiceTests, RuleEvaluatorContextParticipantTests): 33 passed.
- `... --filter FullyQualifiedName~SwrlSubsetConformanceTests`: 13 passed.
- Full suite: 816 total, 811 passed, 5 failed. Failures, identical before and after this plan (baseline taken before any edit):
  - `DG.Tests.E2E.DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve`, `Filtering_StateAndRule`, `LegacyNoState_FlowStillWorks`, `ReinstateFailureModes_ProduceActionableMessages`: Neo4j authentication error (documented environment baseline).
  - `DG.Tests.FrameAblatedCorpusEmitterTests.EmitFrameAblatedCorpus_MatchesCommittedGoldenFiles`: fails at baseline too, before any change of this plan, not investigated (outside this plan's files; the plan brief named only four baseline failures, so this fifth one is flagged here).
- Grasshopper compile: Rhino 8 SDK present, so `dotnet build .\DG\src\DG.Grasshopper\DG.Grasshopper.csproj -c Release --no-incremental` compiled `RuleDeconstructComponent` under `GRASSHOPPER_SDK` for net48 and net7.0-windows: 0 errors, 38 pre-existing nullable warnings. `DG.gha` was only copied inside the repo `bin` output (the project's own post-build copy); nothing was installed into Rhino. The full `DG.sln` build was not run.
- The existing refusal tests (`RuleEvaluatorTests`, `ValidStatusMapperTests`, `ValidationPublishPackageBuilderTests`) pass unchanged. `DG.PublishWireHarness` and `DG.De01Harness` were not run separately.

## Deviations from Plan

None. The plan was executed as written. Note on process: the RED step of the TDD flow was a compile failure only for Task 1 (the test file was written before the classifier); for Task 2 the implementation was written before the first test run, so a separate failing run was not recorded.

## Issues Encountered

- `git status` shows many pre-existing modified tracked `bin/`/`obj/`/`graphify-out/` files and untracked `.claude/` GSD files; none were staged. Builds in this plan rewrote more tracked `bin`/`obj` output; those were left alone as instructed.
- `DG/tests/DG.Tests` line endings: new files are LF in the working copy and git warns about the CRLF conversion; this matches the repository's autocrlf behavior.

## Known Stubs

None.

## Threat Flags

None. No network, auth, file-access or schema surface was added.

## Next

Plan 1303-20 (LLM writes multi-participant rules), then 21-23; DGOPN-06 stays open until plan 23 (DG.gha built and installed there).

## Self-Check: PASSED

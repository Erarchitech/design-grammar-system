# DGMODE planning self-check

## Verdict

Scoped plans 1301-42..47 are prepared for DGMODE-01..04 only. Structural checks passed with one explained wave warning. This is an inline controller self-check, NOT independent GSD checker approval. The owner explicitly chose inline continuation without further subagents. Implementation, offline product tests and live acceptance have not run.

## Scope and preservation

- Existing 01–41 PLAN files were not rewritten in this slice; foreign modifications to 1301-16-PLAN.md and 1301-PLAN-CHECK.md were present before this work and remain untouched.
- Added six plans plus supplemental RESEARCH, VALIDATION and this PLAN-CHECK; amended only the DUAL-MODE brief's status/navigation.
- No source implementation changes; child git status is clean at final check.
- No requirement completion edits, phase closure, HOST-05/DGCL/recovery acceptance, old release execution or deployment.
- No commits/push/build/install/Desktop launch, package installation, paid inference, server/CAD mutations or public artifact publication.
- Durable no-isolated-subagent instruction is stored in user memory. No further subagents were used after the inline-continuation decision.

## Actual checks

| Check | Observed result |
|---|---|
| python tools/degram/workspace.py verify | Passed; child HEAD = gitlink b619e02e3725869b1ab5125951d3311e3656dc9a; context installed; productAccepted false |
| GSD verify plan-structure, all six plans | valid true, errors []; tasks 2/2/2/3/3/5 |
| GSD frontmatter validate --schema plan, all six | valid true, no missing required fields; plan 43 file-list amendment was then rechecked by plan-structure and parsed graph check |
| Wave/dependency check through actual extractFrontmatter | 42–47 waves 29–34, chain 42→43→44→45→46→47, no dependency on old 41 |
| Actual parseMustHavesBlock, not only generic frontmatter get | Nonzero truths/artifacts/key_links with required object fields on all plans |
| Must-have counts, plans 42..47 | 3/2/2; 3/2/2; 4/2/3; 3/3/2; 3/3/2; 4/3/2 (truths/artifacts/key_links) |
| Task fields and requirement scope script | Every task has read_first/action/verify/acceptance_criteria; only DGMODE-01..04 in requirements |
| Encoding check for six PLANs | UTF-8 without BOM; LF, no CR characters |
| git diff --check for edited DUAL-MODE brief | Exit 0; Git warns autocrlf may convert LF on a future Git write; current plans verified LF |
| Child git status --short | Empty |

The first custom checker invocation falsely compared parser string wave with a numeric value and exited at plan 42. Corrected to Number(m.wave), then reran successfully for all six. This was a checker-script type issue, not invalid plan YAML. A temporary tool-classifier timeout blocked one read-only command attempt; no bypass was used, subsequent permitted check completed.

## Explained warnings / limits

1. GSD plan-structure warns `Wave > 1 but depends_on is empty` for 42. Intentional: this is the independent first plan of a newly requested additive slice, while wave numbering continues the existing phase (old max 28). Adding a fake dependency on 41 would incorrectly force unrelated release work. Plans and brief explain this explicitly.
2. GSD verify references on 44 reported the Windows absolute execute-plan path missing and the future 43-SUMMARY missing. Dedicated Glob confirms execute-plan.md exists at the named path. The prior-plan SUMMARY is an execution output expected only after dependency completion. No empty summary was fabricated. Source references newly created by the slice are listed under each plan's mandatory artifacts section; existence is not claimed before execution.
3. Generic frontmatter get flattens object-list fields to strings; parseMustHavesBlock correctly parses artifacts/key_links objects. The latter was directly exercised and its field counts checked. Do not rewrite must_haves through the lossy frontmatter setter.
4. Planning host Node is v20.20.0; Desktop engines require ^22.22.0 || ^24.11.0 || >=26.0.0. Select an already installed supported runtime before execution tests, or report blocker. No implicit install. Recorded in validation supplement.
5. The plan set includes broad real lifecycle seams, especially 44/45; execution must remain serial with one source writer and controller integration. No shortcut to renderer-only switching or mock-only acceptance is valid.
6. New test files are planned outputs. Product tests/typecheck were not run because source was not implemented. nyquist_compliant and wave_0_complete remain false. Independent checker did not run; this limitation is not waived or renamed a pass.

## Requirement/acceptance map

| Requirement | Implementation plans | Proof / gated acceptance |
|---|---|---|
| DGMODE-01 | 42 config/override/migration, 44 main authority, 45 visible target | 46 restart/real-path; 47 actual installation and both targets |
| DGMODE-02 | 42 ownership, 43 profile/migration/scoped purge, 45 renderer scope | 46 same-home equal-ID A→B→A with real CLI/filesystem; 47 owner local-state check |
| DGMODE-03 | 44 main/backend lease/quiesce/strict teardown, 45 dispatch fences | 46 races/no replay/TLS/grants/boundaries; 47 authorized live checks |
| DGMODE-04 | 46 production-path tests and offline evidence | 47 versioned guide/live evidence and explicit requirement verdicts |

## Key design checks

- Existing DEGRAM_DG_ORIGIN precedence is explicit/visible and cannot silently route a selected mode elsewhere.
- Legacy cookies are adopted in place for one proven origin; unknown config keys and Revit adapter settings survive migration.
- Origin participates in profile manifests/names and ALL destructive paths, including purge-project and D-30 cleanup.
- Selected/effective/error states and crash-after-persist semantics are defined; no automatic fallback.
- Main/backend, not renderer-only idle state, protects in-flight work; delayed A responses cannot contaminate B or later A generation.
- One temporary installation home tests collision; a second stock sentinel is not used to hide cross-environment state leakage.
- Native bridges stay local and existing grants/security/runtime isolation remain applicable.
- Child source tests precede separately authorized commit/push; gitlink only after remote publication; build/install/launch/live gates are separate.

## Execution boundary

Start at 1301-42 only when implementation is requested, then follow explicit dependencies through 47. Do not run a blanket execute-phase that includes the older unexecuted plans. Stop at plan-47 authorization checkpoints. All DGMODE requirements remain Pending; no independent requirement or hosted gate closes automatically.

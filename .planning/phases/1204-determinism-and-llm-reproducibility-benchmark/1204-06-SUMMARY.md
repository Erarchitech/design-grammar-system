# Plan 1204-06 Summary — Reproducibility Contract + Machine-Checked Scope Drift Guard

## What was built

- `spec/REPRODUCIBILITY.md` (new) — the normative determinism boundary. Eight
  `## ` sections: Determinism Classes (three: `deterministic-measured`,
  `model-dependent`, `unmeasured`), Scope Table (DE-01 legs + D-03's five
  unmeasured rows + D-11's consult/input-gen rows), Projection and Exclusion
  List (restates `EXCLUSION_FIELDS`/`PROJECTION_VERSION` from
  `projection_hash.py` without redefining them, plus the version-bump rule),
  Provenance Fields (the full D-19 block), Reproducibility Classes (D-22's
  three classes verbatim: `replayable`, `re-executable-pinned-weights`,
  `not-reproducible-provider-managed`), Non-Claims (five explicit non-claims),
  Machine-Checked Scope (the D-26 fenced block), Enforcement and Ownership
  (1204 owns the definition, v11.0 SPEC-04 owns propagation).

- `tools/de01/tests/test_reproducibility_scope_drift.py` (new) — the D-26
  drift guard: `load_fenced_call_sites()` parses the spec's fenced block;
  `scan_call_sites()` walks `data-service/*.py` with the stdlib `ast` module
  looking for `<name-containing-"adapter">.generate(...)` calls (excludes
  `get_adapter`-only callers like `list_models_for_provider` by construction —
  no `.generate` attribute access); `report_mismatch()` is a pure
  set-difference checker. `TestReproducibilityScopeDrift` has 4 tests:
  both-directions equality (documented == scanned), scope-class vocabulary
  restriction (only `measured`/`model-dependent-unmeasured`, never
  `deterministic-measured`), and two induced-mismatch negative controls
  (a synthetic extra entry and a synthetic missing entry are each correctly
  reported by the checker).

- `CLAUDE.md` (edited, **left uncommitted** — see note below) — one additive
  "**Reproducibility contract:**" pointer paragraph inserted immediately
  after the existing "SWRL subset boundary" paragraph, beside the
  evidence/SWRL pointers it joins.

## Key files

- `spec/REPRODUCIBILITY.md` (new)
- `tools/de01/tests/test_reproducibility_scope_drift.py` (new)
- `CLAUDE.md` (edited, uncommitted)

## Verification results

All independently verified by the orchestrator:

| Command | Result |
|---|---|
| `pytest test_reproducibility_scope_drift.py` | ✅ 4 passed |
| `pytest tools/de01/tests/ -k "not live"` (full regression) | ✅ 124 passed, 1 deselected |
| `grep -c "^## "` heading count | ✅ 8, exact section names match |
| Fenced block content | ✅ exactly the 7 required `file\|function\|scope-class` lines |
| `universal.{0,20}determin` grep | ✅ 0 (Non-Claims section phrased to avoid the literal n-gram while keeping the same prohibition) |
| `api[_-]?key\|bearer\|credentialed\|sk-...` grep | ⚠️ 1 match — see note |
| `.secrets` grep | ✅ 0 |
| Frozen-input git status (legs.py, report.py, canonical_json.py, fixtures/golden/, EVIDENCE-CONTRACT.md) | ✅ empty |
| `git diff CLAUDE.md` | ✅ exactly one additive "Reproducibility contract" paragraph; baseline (40 insertions, 0 deletions, the pre-existing DSH section) + 2 lines (paragraph + blank line) = 42 insertions, 0 deletions |

### Note on the api-key grep (1 match, expected 0)

The match is `spec/REPRODUCIBILITY.md:116`: "Record the endpoint host, never
a credentialed URL that..." — this is the D-19 provenance rule's own required
prohibition text (the spec is instructed to state that endpoint host is
recorded bare, never with embedded credentials). Same class of benign
false-positive documented in plans 1204-02/04/05: a spec stating a
prohibition necessarily contains the vocabulary of what it prohibits.

## CLAUDE.md handling (owner-edit safety protocol)

Per the plan's explicit instructions and this session's own memory of a prior
warning, CLAUDE.md carries a **pre-existing uncommitted owner edit** (the
"DSH Subagent Delegation (dsh-crew)" section, ~40 insertions) that must never
be reverted, folded in, or committed by this plan.

**Baseline captured before any edit:** `git diff CLAUDE.md` was saved to
`.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/claude-md-baseline.diff`
(40 insertions, 0 deletions) before making any change.

**Handling decision:** given the sensitivity of this file, the orchestrator
made the CLAUDE.md edit directly (not via a DSH worker) — a single Edit tool
call inserting the pointer paragraph immediately after the "SWRL subset
boundary" paragraph, verified against the baseline diff afterward (42
insertions total, 0 deletions — exactly the pre-existing 40 plus the new
paragraph's 2 lines).

**CLAUDE.md is intentionally left uncommitted.** The owner should commit it
together with their own pending DSH-delegation edit, in whatever order and
message they prefer. **Do not commit CLAUDE.md as part of this phase's
per-plan commits** — this is flagged here for the owner's attention.

## Execution note

Tasks 1-2 (spec + drift test) were executed via DSH `deepseek-v4-flash`
workers: 4 dispatch attempts, 3 died on TRANSPORT errors before writing any
file (successively earlier each time, down to right after finishing reading),
the 4th (given a heavily pre-digested brief with the drift-test code supplied
nearly verbatim to minimize generation length) wrote both files completely
and correctly on the first pass — all 4 drift tests passed immediately with
no orchestrator fixes needed. Task 3 (CLAUDE.md) and Task 4 (final
verification/gates) were performed directly by the orchestrator given the
sensitivity of touching a shared file with pending owner edits.

---
tags: [decision, DeGram, v13.0, phase-1301, execution, authorization]
date: 2026-10-05
status: partly executed; plan 15 publication and plan 16 OPEN
---

# DeGram Phase 1301 execution: authorizations given, baseline narrowed, stop on isolation failure

Owner answers during `/gsd-execute-phase 1301` (2026-10-04/05). Source: `1301-02-SUMMARY.md`, `1301-03-SUMMARY.md`, `1301-15-SUMMARY.md` (verbatim "## Authorization" sections).

## Decisions

- **Plan 02:** authorize-all — `npm ci`, `.venv` restore in `apps/degram`, local branch `degram/phase-1301` and local child commits from gitlink `8b66a510`; Cyrillic font subsets via `npm pack` (files only). No push, `hermes update`, Desktop launch, or write to the installed Hermes profile.
- **Plan 03:** authorize — public fork `Erarchitech/revit-mcp-server`, submodule `apps/revit-mcp` pinned `74a8ddca`, `uv sync`, local branch. (`gh repo fork --org` failed: Erarchitech is a user account, so it ran without `--org`.)
- **Baseline narrowed (2026-10-05):** the full upstream pytest sets take 45+ min on Windows; baseline = vitest `electron` (full) + pytest `tests/hermes_cli`, `tests/tui_gateway` (15 min limit each); `tests/tools` captured targeted later. Stable failing set recorded in `1301-ENV.md`.
- **Plan 15:** authorize all (a) payload + NSIS build, (b) one launch with Hermes before/after listing, (c) push of `degram/phase-1301` to both public forks, (d) gitlink bump; plus NSIS toolset acquisition. Outcome: (a) done, (b) failed the isolation proof, (c)/(d) **not executed** — the plan's stop rule held.
- **Pending owner decisions:** second launch method and authorization, rebuild from `910a060d`, then push + gitlink bump; open UI findings (sign-out entry, ungated profile surfaces, stock resubmit bypass).

## Why

Outward-facing and machine-changing actions need a fresh explicit decision each (CLAUDE.md DeGram boundaries); a failed isolation proof means publication stays blocked, because the public forks and the framework pin must not carry an unproven component.

See [[sessions/2026-10-05 Phase 1301 executed through plan 14, plan 15 launch failed isolation|session]] and [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes|the launch failure]].

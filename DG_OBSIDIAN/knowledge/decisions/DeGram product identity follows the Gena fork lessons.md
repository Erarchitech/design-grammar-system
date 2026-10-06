---
tags: [decision, DeGram, v13.0, phase-1301, identity, branding]
date: 2026-10-06
status: implemented (component a9e56d7e, pushed); verified on DeGram-Setup-0.1.0.exe
---

# DeGram product identity follows the Gena fork lessons

## Context

The owner asked to study the Genpro «Гена» Hermes fork (`GenproMM/MastermindServices/12_GenproAI_HermesFork`, installed as `Gena.exe`, shortcut «Мастермайнд»), which fully replaced the icon and product name, runs beside the stock Hermes and keeps its own AppData folders.

## Decision (owner, 2026-10-06)

- **Genpro and Gena are a reference only.** Their code patterns and lessons may be adapted; no URL, key or config from them may be used to connect DeGram.
- **Icon:** the owner-supplied halftone hexagon (91 dots, centre + five rings) on a rounded light tile (dark variant `#0d1117`), 19-dot reduced mark at 16–32 px, also as the in-app BrandMark; rendered by `apps/desktop/scripts/generate_degram_icons.py` over the upstream filenames. Supersedes the 2026-10-04 wordmark-derived icon; the Oswald «DeGram» text wordmark stays on the sign-in surface.
- **Vendor:** CompanyName / copyright `Erarchitech` (matches `com.erarchitech.degram`).
- **Version:** pilot `0.x`, starting `0.1.0`; bump the patch for every installer build and never reuse a number.
- **Window title** `DeGram`; locked REST paths answered in the preload; no command published to the user PATH.
- **Surface list and rules** live in `spec/degram/WORKSPACE.md` (identity and isolation surface): narrow upstream edits, packaged-build identity checks, no inherited `HERMES_HOME`, PID-scoped kills, no user env/PATH writes, no update feed.

## Consequences

The fork's `icons-freshness-check.yml` lane fails by design; upstream `scripts/generate_icons.py` must not be run in the fork. The next installer is `0.1.1`.

Related: [[knowledge/debugging/Commit build driver overrode the DeGram icon, version and vendor]], [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes]].

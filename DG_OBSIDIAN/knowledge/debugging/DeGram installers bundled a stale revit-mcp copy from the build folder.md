---
tags: [debugging, degram, build, revit-mcp, phase-1301, v13.0]
date: 2026-10-09
status: open (fix planned in 1301-23)
---

# DeGram installers bundled a stale revit-mcp copy from the build folder

## Symptom

Fixes to the Revit adapter fork `apps/revit-mcp` never reached an installed DeGram. On PC1 the 0.1.5 install still had the upstream `extension.json` (`builtin "True"`, `default_enabled "False"`), and its `main.py` had no `json_body`. G-8..G-12 had to be hand-patched into the installed `resources\revit-mcp` for the live UAT (see [[knowledge/debugging/DeGram Revit adapter could not load under pyRevit IronPython 3.4]]).

## Cause

`apps/degram/apps/desktop/electron-builder.config.cjs` :72 takes the adapter source from `DEGRAM_REVIT_MCP_SOURCE`. Without it, the source is `path.resolve(__dirname, '../../../revit-mcp')`. The installers are built from the clean clone `D:\dgb\src`, so that path resolves to `D:\dgb\revit-mcp`.

That folder is a plain robocopy made on 2026-10-05, with no `.git`. It is byte-identical to fork commit `937384f`. `D:\dgb\run-build.sh` never sets `DEGRAM_REVIT_MCP_SOURCE`. So every installer from 0.1.0 to 0.1.5 shipped that copy, whatever the fork or the framework gitlink held.

`tools/degram/workspace.py verify` cannot see this. It checks the gitlink, the child HEAD and the remotes, not what the build bundles.

## Fix (planned, plan 1301-23)

- Clone `apps/revit-mcp` with `--no-hardlinks` into `D:\dgb\revit-mcp-src`, detached at the gitlink commit.
- Export `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` in `run-build.sh`.
- After the build, check `release\win-unpacked\resources\revit-mcp`:
  - `extension.json` has `default_enabled "True"`;
  - `main.py` contains `json_body`;
  - `revit_mcp\views.py` imports from `urllib.parse`;
  - there is no `tests\` directory.
- Record all of this in `1301-BUILD.md`.

## Lesson

Every bundled sibling repository needs an explicit, recorded source commit. A default relative path into the build folder silently freezes whatever was copied there first.

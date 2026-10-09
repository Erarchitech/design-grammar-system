---
tags: [debugging, degram, build, windows, shell]
date: 2026-10-09
---

# Backslashes lost in a shell edit corrupted the DeGram build adapter path

## Symptom

0.1.6 build started with `DEGRAM_REVIT_MCP_SOURCE='D:\dgb<CR>evit-mcp-src'` in `D:\dgb\run-build.sh`. The build ran for ~10 minutes toward packaging with a path that does not exist (it would have failed or bundled a wrong adapter).

## Cause

The path was written through `sed` and an inline Python heredoc from Git Bash: the single backslashes were swallowed (`\r` became a carriage return). The line looked right in a terminal because the CR overwrote the line.

## Fix

- Rewrote the file with the Write tool (no shell escaping) and checked with `od -c` that the line has literal `\dgb\revit-mcp-src`.
- Stopped the build processes belonging to `D:\dgb` only (after owner approval) and re-ran.
- The interrupted `flavored_assets` step of `scripts/bundles/desktop.py` had left 66 icon files under `apps/desktop/assets` modified in the throwaway clone; `git checkout -- apps/desktop/assets` there restores the clean checkout the build requires. Also clear the ReadOnly flag on `build\agent-payload` before re-running.

## Rule

Write Windows paths with Write/Edit, never through sed or heredocs in Git Bash; verify with `od -c`.

## Related

- [[knowledge/debugging/DeGram installers bundled a stale revit-mcp copy from the build folder]]
- [[sessions/2026-10-09 Phase 1301 gap plans 18-23 executed and DeGram 0.1.6 shipped]]

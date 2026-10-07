---
tags: [decision, degram, phase-1301, installer, payload]
date: 2026-10-07
---

# DeGram payload ships only what variant degram can use

**Status:** accepted by the owner 2026-10-07 (option 1 of 2: offline, only what is needed). Component `75e65495`, `7f9c33c1`.

## Context

The 0.1.2 installer was 1.79 GB (6.1 GB unpacked): the full Hermes payload — llama.cpp for four GPU backends (1.9 GB), Chromium, git, ffmpeg, a venv with every extra (1.1 GB) and an 892 MB uv-cache. The agent of variant degram registers only clarify, todo, the degram toolset and Revit MCP (D-22) and reaches a model only through the DG relay (D-16). The reference fork (Mastermind, 315 MB) ships a few tools and downloads its Python dependencies after install; that was option 2, rejected because the first start would need the network.

## Decision

- Tools: the pm-required ones (ffmpeg, node, npm, ripgrep, uv) plus Python. Optional tools are dropped. Dropping a required one would report "install out of sync" on every start.
- Python: the core dependencies plus extras `acp`, `cron`, `mcp`, `pty`, `vision`, `web` (`DEGRAM_EXTRAS` in `scripts/bundles/native.py`). Opt-in extras are refused.
- uv-cache: only the wheels the venv installed (`prune_uv_cache_to_dists`), so an offline rebuild of the same set still resolves.
- Verified before the build: a venv with exactly these extras started `serve` in variant degram and imported 24 runtime modules.

## Result

0.1.3: installer 490 MB, 1.6 GB unpacked, 32,130 files, longest path 168 (F-11 closed; installs into the default per-user dir). Remaining candidate: ffmpeg 427 MB needs a drift-skip for variant degram.

Related: [[knowledge/debugging/DeGram graph tool answer was spilled to a file the agent cannot read|G-1]], [[sessions/2026-10-07 Phase 1301 DeGram pairing connector, rules read fix, 490 MB installer and no Hermes name|session]].

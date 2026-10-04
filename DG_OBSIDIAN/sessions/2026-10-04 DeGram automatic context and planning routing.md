---
tags: [session, DeGram, gsd, context, workspace]
date: 2026-10-04
---

# Session: DeGram automatic context and planning routing

## Session summary

сессия: С явного разрешения владельца снят блокер прошлой сессии — корневые AGENTS.md и CLAUDE.md получили протокол планирования DeGram, в child установлен генерируемый `.hermes.md`, и загрузка контекста проверена кодом самого Hermes из трёх рабочих каталогов.

Продолжение [[sessions/2026-10-04 DeGram official fork and framework workspace]] (пункт «What remains» №1).

## Done and verified

- **Root `AGENTS.md`:** new section «Design Grammars framework — agent routing» above the Perplexity MCP block (block untouched). Covers single authority (`.planning`, `DG_OBSIDIAN`), DeGram preflight, cross-repository planning rules, child routing, boundaries.
- **Root `CLAUDE.md`:**
  - DeGram row in knowledge routing;
  - `.degram/index/` and broad `apps/degram/` sweeps in the do-not-search list;
  - `apps/degram`, `integration/`, `spec/` and `tools/degram` in the repository structure;
  - new section «DeGram component» (one authority, 4-step automatic preflight, cross-repo planning rules, owner boundaries, session-end commits with the submodule);
  - DeGram commands in Common Commands;
  - v13.0 as priority 0.
- **`tools/degram/workspace.py install-context`** (new, test written first and observed failing, then passing): writes `apps/degram/.hermes.md` byte-for-byte from `integration/degram/component-context.md`, adds `/.hermes.md` to the child's Git-local `info/exclude`, and refuses to overwrite if upstream ever tracks the file. `verify` now reports `componentContextInstalled`; `protected-context-installation` stays in `pending` only while the copy is missing or stale.
- **Template** `component-context.md`: added the GSD rule (planning from the child resolves `project_root` to the framework; plans name `apps/degram/...` paths and the committing repository; child commit before gitlink bump).
- Docs that still said BLOCKED were updated: `spec/degram/WORKSPACE.md` (context protocol, onboarding step 2), `integration/degram/IMPLEMENTATION.md`, `DG_OBSIDIAN/degram/Repository topology.md`.

Checks:
- `python -m unittest discover -s tools/degram/tests -v`: 5/5 pass.
- `workspace.py verify`: gitlink = HEAD `8b66a51`, `componentContextInstalled: true`; child `git status --porcelain` is empty.
- `gsd-sdk query init.progress` inside `apps/degram` returns `project_root` = framework root and the v13.0 STATE.
- Hermes `build_context_files_prompt` from the fork source, run with the installed venv interpreter only, `HERMES_HOME` and `home_override` in the session scratchpad:
  - `apps/degram` and `apps/degram/apps/desktop` load the full `.hermes.md` (2431 chars, no injection block);
  - the framework root loads the new AGENTS.md section (5332 chars).
- `git diff --check` is clean; `graphify update .` was run.

## Findings

- Hermes loads only the first project context type: `.hermes.md` wins over the `AGENTS.md` chain, including from `apps/desktop`. The routing text therefore requires reading the child and Desktop `AGENTS.md` explicitly.
- Codex inside the child stops at the child's Git root and does not see the framework AGENTS.md. Claude Code loads the parent CLAUDE.md, but project memory is keyed to the working path. **DeGram work therefore continues from the framework root.** See [[knowledge/decisions/DeGram work runs from the framework root with generated child routing]].

## What remains

1. Phase 1301: `/gsd-progress`, then `/gsd-plan-phase 1301`. Only `1301-01` is done. Runtime isolation (`HERMES_HOME`, Electron userData, app ID, updater) is the prerequisite for any Desktop launch and for the DG adapter.
2. The previous session's integration package was committed separately as `b99933c`. Its files are at their end-of-that-session state, reconstructed by reversing this session's edits; the `WORKSPACE.md` hash matches the one recorded in `workspace-verification.json`. Still uncommitted: that session's `.planning/PROJECT.md`, `ROADMAP.md` and `STATE.md` edits, which are mixed with other sessions' uncommitted changes.
3. `.planning/STATE.md` was corrected in the working tree only (the stale "automatic context blocked" sentence). The file carries larger uncommitted changes from earlier sessions.
4. Phase 1300 acceptance gates are unchanged and OPEN.

## Not done

No Hermes or Desktop launch, `hermes update`, package install, Docker operation, child commit, push, or change to the installed Hermes profile.

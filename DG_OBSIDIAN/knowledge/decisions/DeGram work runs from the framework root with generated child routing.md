---
tags: [decision, degram, gsd, context, v13]
date: 2026-10-04
status: accepted
---

# DeGram work runs from the framework root with generated child routing

## Decision

1. **Working place:** v13.0 DeGram tasks are planned and executed from the Design Grammars framework root (Claude Code on `design-grammar-system`). Component source is edited by `apps/degram/...` paths from there. Agents enter `apps/degram` only for child Git operations and child tests.
2. **Entry points:**
   - root `AGENTS.md` carries the framework/DeGram routing for Hermes and Codex;
   - root `CLAUDE.md` carries the full DeGram planning protocol;
   - the child gets a generated `.hermes.md` (from `integration/degram/component-context.md` via `python tools/degram/workspace.py install-context`), kept out of the public fork by a Git-local `info/exclude` rule.
3. The template is the single editable source; the generated copy is never edited. `workspace.py verify` reports whether the copy is current (`componentContextInstalled`).

## Why

- Project memory and the session protocol are keyed to the framework path. Claude Code opened in the child loads the parent CLAUDE.md but uses a different project memory.
- GSD invoked in the child already resolves the framework `.planning`, so planning authority stays single from either directory. Doc commits still belong to the framework repository.
- Hermes loads only the first project context type (`.hermes.md` before the `AGENTS.md` chain), so a child `.hermes.md` routes to the framework without editing upstream `AGENTS.md`. Codex stops at the child's Git root, so the child cannot rely on the framework `AGENTS.md`.
- Hermes inside the child is not a working environment until Phase 1301 runtime isolation exists: it must not run against the installed user profile.

## Consequences

- Cross-repository plans name the committing repository per task. Child commit and fork push come before the framework gitlink bump.
- A fresh clone needs `git submodule update --init apps/degram` + `workspace.py install-context`.

Sources: [[sessions/2026-10-04 DeGram automatic context and planning routing]], `spec/degram/WORKSPACE.md`, [[degram/index]].

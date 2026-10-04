# Design Grammars framework — agent routing

This checkout is the Design Grammars (DG) framework. `CLAUDE.md` in this directory holds the full project rules (architecture, graph schema v4, schema-change propagation, contracts in `spec/`, session protocol); read it before any change.

## Single authority

- **Planning:** `.planning/` (GSD) is the only roadmap, requirements set and phase state. Start with `.planning/STATE.md`, then the relevant sections of `ROADMAP.md` and `REQUIREMENTS.md`.
- **Knowledge:** `DG_OBSIDIAN/`. Read `00-home/index.md` and `00-home/Current priorities.md` first; indexes before folders.
- No second `.planning`, roadmap or vault anywhere in the tree, including submodules.

## DeGram component (`apps/degram`)

`apps/degram` is a Git submodule: the DeGram fork (https://github.com/Erarchitech/degram) of NousResearch/hermes-agent. It is an integral DG component; its separate Git history exists only to keep upstream updates possible, not to host a separate product.

Before planning or changing anything that touches DeGram:

1. Run `python tools/degram/workspace.py verify`: gitlink, remotes, required context files, no competing authority in the child, and whether the child routing file is installed.
2. Read `DG_OBSIDIAN/degram/index.md` and `spec/degram/WORKSPACE.md` (ownership table, update workflow, boundaries).
3. For edits under `apps/degram/**`, also follow `apps/degram/AGENTS.md`; Desktop edits additionally need `apps/degram/apps/desktop/AGENTS.md` and `DESIGN.md`.

Planning rules for work spanning both repositories:

- Phases 1300-1307 (milestone v13.0 DeGram Agent) live in framework `.planning/phases/`. GSD resolves the framework `.planning/` even when invoked from inside `apps/degram`.
- Every plan path into the submodule is written as `apps/degram/...`, and each task states which repository commits it (framework or component).
- Order for a cross-repository change: verify and commit in the child, push to the fork (with authorization), bump the framework gitlink, then run `python tools/degram/workspace.py verify` on the exact pair. Never commit a gitlink whose object is absent from the fork.
- Never mark framework GSD work complete from a child-side summary alone.

Child-side routing: Hermes started inside `apps/degram` reads `apps/degram/.hermes.md`, generated from `integration/degram/component-context.md` by `python tools/degram/workspace.py install-context` (Git-local exclude, never committed to the fork). Edit the template and re-run the installer; never edit the generated copy.

Boundaries: no `hermes update` in the submodule; no launching upstream Hermes against the installed user profile (Phase 1301 runtime isolation comes first); never copy `.secrets/`, credentials, `Publications/` or unpublished manuscripts into the public fork.

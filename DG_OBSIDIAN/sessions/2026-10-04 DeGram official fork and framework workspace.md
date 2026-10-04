---
tags: [session, DeGram, Hermes, framework, workspace]
date: 2026-10-04
---

# Session: DeGram official fork and framework workspace

## Session summary

сессия: По принятому решению владельца создан официальный fork Hermes для DeGram, подключён к Design Grammars как pinned submodule и подготовлены единые planning/knowledge/indexing contracts; автоматическая загрузка общего контекста остаётся заблокированной защитой AGENTS.md.

## Owner decision and scope

- Owner accepted the topology: official Hermes fork + pinned submodule under the Design Grammars framework, one canonical Obsidian vault and one GSD authority.
- DeGram remains an integral Design Grammars component. Separate Git history is used only to preserve upstream updateability; it is not a second product roadmap or knowledge base.
- The decision authorized the public upstream-only fork, local submodule registration and integration workspace files. It did not authorize Docker/service operations, CAD/graph/CDE writes, paid inference, package installation, a Desktop launch, or modification of the installed Hermes/profile.

## Implemented and verified

- Created public GitHub fork: `https://github.com/Erarchitech/degram`, parent `NousResearch/hermes-agent`, `fork=true`, public.
- Added `apps/degram` submodule at `8b66a51036c1e20920a17cdd049fdf55c968d683`; verified local child HEAD, superproject gitlink and remote `main` are equal. `origin` is the fork and `upstream` is `https://github.com/NousResearch/hermes-agent.git`.
- Created framework-owned integration contract `spec/degram/WORKSPACE.md`, routing manifest `integration/degram/workspace.json`, explicit resolver/verifier `tools/degram/workspace.py`, repeatable offline code index command `tools/degram/index_code.py`, test suite and verification evidence.
- One canonical authority remains framework `.planning` and `DG_OBSIDIAN`; DeGram knowledge entry points are `DG_OBSIDIAN/degram/index.md` and `Repository topology.md`. No duplicate GSD project, vault, evaluator or private-material copy was created in the public fork.
- `python -m unittest discover -s tools/degram/tests -v` passed 4/4. The tests cover framework resolution from root/component/nested Desktop, missing context, unsafe/sensitive path refusal, actual gitlink/remote verification and offline index command construction.
- `python tools/degram/workspace.py verify` passed: hashes all required framework and upstream context files; verifies `origin`, `upstream`, the gitlink and no competing `.planning`/`DG_OBSIDIAN` inside the child.
- Ran `python tools/degram/index_code.py` without LLM calls. Evidence recorded 15,128 DG nodes / 26,343 edges; 44,687 selected component nodes / 127,651 edges; 60,197 framework nodes / 153,520 edges. It resolves existing `DeGramWorkspace` and Hermes `JsonRpcGatewayClient`; this is navigation evidence, not API/IPC compatibility or product acceptance.
- `integration/degram/workspace-verification.json` confirms 8 checks, child cleanliness, GitHub fork data and graph artifact hashes. Scoped `git diff --check` and staged diff check passed.

## What remains

1. **Automatic bidirectional context is blocked.** A protected root `AGENTS.md` write was denied because the attached client cannot answer approval requests. The change was not retried or bypassed; root AGENTS.md and child `.hermes.md` remain unchanged. `integration/degram/component-context.md` is only a proposed, uninstalled routing document. Continue from an approval-capable client, obtain explicit protected-file approval, install allowed entry points, and verify actual Hermes startup context from framework and child working directories. Until then use `python tools/degram/workspace.py context` explicitly.
2. Make an explicitly authorized scoped framework commit/push for `.gitmodules`, gitlink and the integration documentation/tools. The public fork exists, but other framework clones cannot reproduce this uncommitted integration yet. Never add the broad pre-existing dirty tree or all `graphify-out` churn.
3. Implement Phase 1301 Desktop runtime isolation before launching a shell: separate `HERMES_HOME`, Electron userData, application identity and DeGram-owned update policy. Do not point it at the user's installed Hermes/profile.
4. Then implement and test the first actual DG adapter/authentication slice through supported Hermes Desktop seams. Keep Design Grammars backend ownership, server-side authorization and canonical evaluator/evidence boundaries intact.
5. Phase 1300 remains incomplete: selected V8 candidate/loading/build/GH evidence, independent technical verifier/owner receipts and stale source-digest rebind/review are still OPEN. The withdrawn baseline comparison must not return.
6. `graphify update .` warned that one SQL source was unparsed because optional `tree_sitter_sql` is not installed and conservatively retained one filtered source. Do not install anything merely to silence this; assess it when SQL graph coverage matters.

## Files authored or edited in this session

- `.gitmodules`; `apps/degram` gitlink
- `.gitignore`, `.graphifyignore`
- `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`
- `DG_OBSIDIAN/00-home/index.md`, `DG_OBSIDIAN/00-home/Current priorities.md`
- `DG_OBSIDIAN/degram/index.md`, `DG_OBSIDIAN/degram/Repository topology.md`
- `integration/degram/{workspace.json,component-context.md,workspace-verification.json,IMPLEMENTATION.md}`
- `spec/degram/WORKSPACE.md`
- `tools/degram/{workspace.py,index_code.py,tests/test_workspace.py,tests/test_index_code.py}`
- Local ignored `.degram/index/*` graphs and the child Git-local `info/exclude` cache rule; neither belongs in the public fork.

## Not done

No commit, framework push, child source commit/push, submodule branch change, Docker rebuild/restart, desktop launch/build, product adapter, CAD/model save, graph mutation, secret read, package install, paid inference or installed Hermes/profile change.

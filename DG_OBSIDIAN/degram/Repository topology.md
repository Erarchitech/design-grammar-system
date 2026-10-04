---
tags: [decision, degram, architecture]
date: 2026-10-04
---
# Repository topology

## Owner decision

The owner requires DeGram to be an integral part of Design Grammars with bidirectional development context. The proposed official upstream fork, pinned submodule and shared Obsidian/GSD topology was accepted: «Решение принимается. Реализуй».

## Canonical organization

Public fork: https://github.com/Erarchitech/degram, parent https://github.com/NousResearch/hermes-agent. Framework location: `apps/degram`. Preserve upstream layout to reduce update conflicts. Git history is separate; product governance is not.

One canonical knowledge vault: `DG_OBSIDIAN`. One GSD authority: framework `.planning`, including all existing v13 requirements and retained gates. Read indexes and relevant contracts rather than copying everything into the prompt. Context routing in both directions is explicit because submodule Git-root discovery does not automatically inherit the outer root.

Implementation/runbook: `spec/degram/WORKSPACE.md`; manifest: `integration/degram/workspace.json`. Explicit context resolution works from root and child. Automatic context is installed (2026-10-04, owner-approved): root `AGENTS.md` and `CLAUDE.md` carry the DeGram routing/planning protocol; the child `.hermes.md` is generated from `integration/degram/component-context.md` by `workspace.py install-context` and kept out of the fork by a Git-local exclude. Public fork contains no DG private research or internal planning. Graphify uses local per-repository indexes plus a namespaced framework merge. Code graph edges are navigation, not evidence of API compatibility.

## Consequences

Two-repository commits require child-first verification/publication and then a pinned framework gitlink; no automatic commit/push. No product acceptance is inferred. Installed Hermes, its profiles and Docker are untouched. Before running a DeGram shell, implement separate runtime home, Electron data/app identity and fork-owned update policy.

See [[degram/index]] and [[sessions/2026-10-04 DeGram scope revision and first client increment]].

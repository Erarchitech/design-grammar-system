# DeGram as a Design Grammars framework component

## Accepted decision

The owner accepted the official Hermes fork + pinned submodule + shared context topology and instructed implementation on 2026-10-04. This authorizes creation of the public upstream-only fork, local submodule registration and workspace integration. It does not authorize publishing internal DG materials, runtime deployment, CAD/graph writes, paid inference or changing the installed Hermes/profile. No product requirement is accepted by this setup; Phase 1300 and its retained gates remain open.

## Repository and authority

- Framework root: Design Grammars, the directory containing this file and `.planning/PROJECT.md`.
- Component: `apps/degram`, Git fork https://github.com/Erarchitech/degram of https://github.com/NousResearch/hermes-agent.
- Preserve upstream layout. Desktop is `apps/degram/apps/desktop`; Python agent and `apps/shared` remain in the same fork.
- `.gitmodules` + the superproject gitlink identify the selected component commit. `integration/degram/workspace.json` records the original upstream base, not a floating release certification.
- Product requirements, phases 1300–1307, task ownership and acceptance have one authority: framework `.planning/`. Do not initialize an independent competing GSD project in the fork.
- Framework knowledge has one authority: `DG_OBSIDIAN`, with the `degram/index.md` entry point. Do not mirror manuscript/private material into the public fork.

## Bidirectional context protocol

From the framework: read root AGENTS.md, CLAUDE.md, active STATE/ROADMAP/REQUIREMENTS, the DeGram knowledge index and the relevant contract before changing a producer/consumer. Then read the component's root and area AGENTS.md before changing upstream code.

From the component: execute `python ../../tools/degram/workspace.py context` from the component root, then read the listed context files as relevant. The tool checks existence and returns exact file hashes, not a claim that an LLM read or understood them. From nested directories use the absolute script path or run the same command from framework root with `--from apps/degram/apps/desktop`. Missing framework context fails closed; never silently use a stale copied vault or invent an independent roadmap.

**Automatic context installation is BLOCKED:** the host refused the protected root AGENTS.md edit because the attached client cannot answer approval requests. No retry or alternative-path write is authorized. `integration/degram/component-context.md` is an uninstalled proposed routing document, not an active `.hermes.md`. Root AGENTS.md and child context remain unchanged. A working approval UI and explicit protected-file approval are required before installing root/child entry points and verifying actual startup injection. Until then use the explicit context command; automatic bidirectional loading is not claimed.

Load indexes first and specific sections on demand; do not preload the entire vault or upstream. Runtime users do not receive development context or cross-project permissions because developers share a workspace.

## Ownership and compatibility

| Surface | Authority | Consumer |
|---|---|---|
| Company/project access and graph data | DG backend/security contracts | DeGram typed adapter |
| Rule compiler, evaluator, evidence/status | Existing DG/v11/v12 owners | DeGram displays, never replaces verdict |
| Native process/window/IPC | Hermes Electron boundaries | DeGram Desktop integration |
| Agent sessions/tools/streaming | Hermes Python backend | Desktop renderer |
| Requirements/release and integration evidence | DG GSD | Both repositories |

Actual adapters are not implemented by this workspace setup. Existing `ui-v2/#degram` is only a reusable web slice, not a Desktop delivery. API/MCP/IPC edges must be supported by contract tests; a graphify merged graph alone does not prove them.

## Reproducible onboarding

1. Clone the framework with submodules, or run `git submodule update --init apps/degram`.
2. Verify `origin` points at the DeGram fork and register the official upstream locally if absent: `git -C apps/degram remote add upstream https://github.com/NousResearch/hermes-agent.git`. This was done for the current checkout. No automatic protected-context bootstrap is implemented while approval is blocked.
3. Run `python tools/degram/workspace.py verify` and `python -m unittest discover -s tools/degram/tests -v`.
4. Read `.planning` from the framework root. Plan paths spanning the submodule must name their repository; do not assume a root commit includes child changes.
5. Run `python tools/degram/index_code.py` for offline code-only component indexing and a namespaced combined graph. Generated indexes are local and must not be published into the upstream fork.

Graphify also writes per-source AST caches under each scanned area's `graphify-out/` despite external `--out`. The current submodule's Git-local `info/exclude` ignores `**/graphify-out/`; add the same local ignore on a fresh clone before indexing. It is not a source change and must not be pushed. The component remains source-clean.

## Update and contribution workflow

`origin` is the DeGram fork; `upstream` is official Hermes. Do not run managed `hermes update` on this checkout, do not point normal Hermes at it and do not launch the unbranded upstream shell against the user's live profile. Fetch/merge upstream only as a deliberate scoped task on a development branch. The initial local clone is shallow; fetch the necessary history before merge/rebase, do not rewrite the fork's history blindly.

A cross-repository change is not atomic: verify the child, publish its explicitly approved commit, then update the framework gitlink and run integration checks on the exact pair. Never commit a gitlink whose object is absent from the shared fork. Do not close GSD from a child summary alone. This setup keeps child source unchanged; it creates no child commit or push. `git submodule add` stages only `.gitmodules` and the gitlink as part of registration; the framework integration files still require an explicitly authorized commit before another checkout can reproduce them.

Before any Desktop launch/build, implement and test separate runtime home, Electron userData, app identity and update channel. Current workspace provisioning does NOT implement that runtime isolation, product branding, installer, login or DG integration. Those remain Phase 1301 work; do not claim install acceptance. Prefer supported plugin/adapter seams over core edits. Preserve upstream MIT notices; DeGram is not an official Nous product.

## Code graph boundaries

Keep the existing DG graph and a separate component AST index; build a framework-local combined graph with graphify's supported merge command. Exclude runtime homes, credentials, publications, dependencies, generated graphs and the nested fork from the root scan. Derived graph freshness and source commit/hash provenance must be explicit. Do not mutate the global personal graph or installed profile. See the generated graph manifest for actual coverage/counts, not assumed completeness.

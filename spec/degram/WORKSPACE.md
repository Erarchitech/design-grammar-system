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

**Automatic context is installed (2026-10-04, owner-approved).** Framework side: root `AGENTS.md` carries the framework/DeGram routing section (Hermes and Codex load it from the framework root) and root `CLAUDE.md` carries the DeGram planning protocol (Claude Code also loads it as a parent memory file inside `apps/degram`). Component side: `python tools/degram/workspace.py install-context` generates `apps/degram/.hermes.md` byte-for-byte from `integration/degram/component-context.md` and adds `/.hermes.md` to the child's Git-local `info/exclude`; the fork stays source-clean. `workspace.py verify` reports `componentContextInstalled`; a missing or stale copy does not fail verification but keeps `protected-context-installation` in `pending` until the installer is re-run. Hermes loads only the first project context type, so inside the child `.hermes.md` replaces the upstream `AGENTS.md` chain; the routing text therefore requires reading the child and Desktop `AGENTS.md` explicitly. Verified with the fork's own `build_context_files_prompt` under an isolated scratch home: routing loaded from `apps/degram` and `apps/degram/apps/desktop`, framework section loaded from the framework root, no injection block.

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
2. Verify `origin` points at the DeGram fork and register the official upstream locally if absent: `git -C apps/degram remote add upstream https://github.com/NousResearch/hermes-agent.git`. This was done for the current checkout. Then run `python tools/degram/workspace.py install-context` to generate the child `.hermes.md`.
3. Run `python tools/degram/workspace.py verify` and `python -m unittest discover -s tools/degram/tests -v`.
4. Read `.planning` from the framework root. Plan paths spanning the submodule must name their repository; do not assume a root commit includes child changes.
5. Run `python tools/degram/index_code.py` for offline code-only component indexing and a namespaced combined graph. Generated indexes are local and must not be published into the upstream fork.

Graphify also writes per-source AST caches under each scanned area's `graphify-out/` despite external `--out`. The current submodule's Git-local `info/exclude` ignores `**/graphify-out/`; add the same local ignore on a fresh clone before indexing. It is not a source change and must not be pushed. The component remains source-clean.

## Update and contribution workflow

`origin` is the DeGram fork; `upstream` is official Hermes. Do not run managed `hermes update` on this checkout, do not point normal Hermes at it and do not launch the unbranded upstream shell against the user's live profile. Fetch/merge upstream only as a deliberate scoped task on a development branch. The initial local clone is shallow; fetch the necessary history before merge/rebase, do not rewrite the fork's history blindly.

A cross-repository change is not atomic: verify the child, publish its explicitly approved commit, then update the framework gitlink and run integration checks on the exact pair. Never commit a gitlink whose object is absent from the shared fork. Do not close GSD from a child summary alone. This setup keeps child source unchanged; it creates no child commit or push. `git submodule add` stages only `.gitmodules` and the gitlink as part of registration; the framework integration files still require an explicitly authorized commit before another checkout can reproduce them.

Before any Desktop launch/build, the separate runtime home, Electron userData, app identity and update channel must be in place and tested. Phase 1301 implements them on `degram/phase-1301` (see Product identity and isolation surface); install acceptance is claimed only from Phase 1301 UAT, never from a build alone. Prefer supported plugin/adapter seams over core edits. Preserve upstream MIT notices; DeGram is not an official Nous product.

### Development branches and the build clone (owner decision 2026-10-25)

Component work happens only in this submodule on `degram/milestone13` (framework branch `gsd/milestone13`). The build clone `D:\dgb\src` is build-only: it pulls `degram/milestone13` from the submodule and never carries its own commits (four Phase 1303 commits made there were folded into `degram/milestone13`, `b619e02e`). The separate clone `C:\Users\Admin\source\repos\degram` (fork `main`, no DeGram code) is not a working base. Decision: `DG_OBSIDIAN/knowledge/decisions/DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls.md`.

## Product identity and isolation surface

DeGram runs beside an installed Hermes on the same PC. Every fork file that carries its identity or its isolation is listed here, so an upstream merge knows which conflicts are DeGram's own. Edits are gated on the `degram` variant (`HERMES_DESKTOP_VARIANT=degram`); stock variants stay byte-identical in behaviour, and tests assert both sides.

| Concern | Fork path (under `apps/degram/apps/desktop/`) | DeGram value |
|---|---|---|
| Names, appId, CLI, feed | `product-identity.cjs`, `electron/product-identity.ts` | `DeGram`, `com.erarchitech.degram`, `degram`, no release feed |
| Packaging | `electron-builder.config.cjs` | productName/exe `DeGram`, `degram://`, per-user NSIS, `extraMetadata.author` `Erarchitech` (exe CompanyName, copyright, uninstall Publisher), `extraMetadata.version` (pilot `0.1.0`; bump the patch for every installer build, never reuse a number) |
| Build driver | `scripts/bundles/desktop.py` (repo root of the component) | `degram_icon_overlay` lays the committed icons over the commit build's red badge render; `package_version_args` passes no `extraMetadata.version` override for degram. Verify identity on the packaged exe and `app.asar`, never on the repo files: the 2026-10-06 rebuild from `69eb9a1d` still shipped the commit-badge Nous icon and version 0.0.0 |
| Runtime home, userData, lock | `electron/degram/isolation.ts`, `applyDesktopIdentity` in `electron/main.ts` | fixed `%LOCALAPPDATA%\DeGram\{home,userData}`; inherited `HERMES_HOME` ignored; `HOME_OVERLAP` fails closed; never attaches to a running Hermes backend |
| AUMID, native window title | `electron/main.ts` (`setAppUserModelId`, `APP_WINDOW_TITLE`) | `com.erarchitech.degram`, `DeGram` |
| Page title | `src/degram/window-title.ts` (called from `src/main.tsx`) | `DeGram` / `DeGram HUD` over index.html's `<title>Hermes</title>` |
| Locked REST paths | `electron/degram/rest-lock.ts` (used by `electron/preload.ts`) | preload answers paths outside `/api/{ws,health,status}` with the backend's own `403 DEGRAM_LOCKED`, without sending; keep in step with `ALLOWED_REST_PATHS` in `degram_variant/lockdown.py` |
| User PATH | `hermes_cli/_launchers.py` (`expose_cli`) | variant degram publishes no command and never writes `HKCU\Environment` |
| Icons | `scripts/generate_degram_icons.py` → `assets/icon{,-dark}.{png,ico,icns}`, `assets/icon-mac.png`, `public/apple-touch-icon.png`, `public/nous-girl{,-dark}.png` (BrandMark) | owner's halftone-hexagon mark (2026-10-06), upstream filenames kept; 16–32 px frames use a 19-dot reduced mark. Never run upstream `scripts/generate_icons.py` here (it restores the Nous art); its `icons-freshness-check.yml` lane fails on the fork by design |

Rules, adapted from the Genpro «Гена» Hermes fork (`GenproMM/MastermindServices/12_GenproAI_HermesFork`, studied 2026-10-06):

1. Keep every upstream-file edit narrow and recognisable; its cost is the next merge. Replace binary assets in place under the same filenames so no import site changes.
2. Verify identity on a packaged build (exe version resource, icon hash, window and taskbar title, shortcut, uninstall entry), never on a dev `electron .` run, which shows Electron's own icon. Windows caches shortcut icons; point shortcuts at the exe or `resources\icon.ico`.
3. The agent home never derives from an inherited `HERMES_HOME`: an installed Hermes commonly exports it user- or machine-wide.
4. Process cleanup targets owned PIDs or the DeGram install root, never the image name `hermes.exe`; Gena's install and update once killed the other product's gateway this way.
5. No bootstrap stage may write user-level environment variables or publish a `hermes` command to the user `PATH` for DeGram. Gena's finish stage overwrote a co-installed Hermes' `HERMES_HOME`; DeGram's first launch (2026-10-06) minted `%LOCALAPPDATA%\DeGram\home\bin\hermes.cmd` and put it first in the user PATH, because upstream `expose_cli` takes its Windows branch before the bundled-payload skip (fixed by F-07, component `69eb9a1d`). Upstream `tests/hermes_cli/test_hermes_home_shared_launchers.py` also writes the real user PATH on Windows: never run it on a pilot PC.
6. No updater feed and no `hermes update`; the upstream feed targets NousResearch.

## Revit adapter component

`apps/revit-mcp` is a second pinned Git submodule, registered under `additionalComponents` in `integration/degram/workspace.json` (Phase 1301, D-09). `origin` is the owner fork `https://github.com/Erarchitech/revit-mcp-server.git` of `upstream` `https://github.com/Demolinator/revit-mcp-server.git` (MIT; keep upstream notices). The gitlink is pinned to upstream commit `74a8ddca6ee5119063dc685f8dad7e8b52b0a769`; the fork carries upstream content only and never receives `.secrets/`, `DG_OBSIDIAN/`, `Publications/` or manuscripts.

- The read-only allowlist (D-09, D-10, D-23) is implemented inside this fork on the local branch `degram/phase-1301`; the framework never edits the child from the root. Child commits and any push to the fork need explicit owner authorization (the push is a separate plan step); a gitlink is bumped only after its object exists on the fork.
- `uv sync --frozen` inside `apps/revit-mcp` restores the locked environment from the upstream `uv.lock` (no new package, no lock rewrite). The resulting `.venv` is ignored.
- `python tools/degram/workspace.py verify` checks every additional component the same way as `apps/degram`: gitlink equals child HEAD, `origin`/`upstream` match the manifest, and no competing planning authority (`.planning/`, `ROADMAP.md`, `DG_OBSIDIAN/`) exists in the child. The report lists each component under `components`. A failure blocks the task; it is not worked around.
- The component context file (`.hermes.md`) and context hashes apply to `apps/degram` only.

## Code graph boundaries

Keep the existing DG graph and a separate component AST index; build a framework-local combined graph with graphify's supported merge command. Exclude runtime homes, credentials, publications, dependencies, generated graphs and the nested fork from the root scan. Derived graph freshness and source commit/hash provenance must be explicit. Do not mutate the global personal graph or installed profile. See the generated graph manifest for actual coverage/counts, not assumed completeness.

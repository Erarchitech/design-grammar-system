# DeGram framework workspace — implementation result

Status: **PARTIAL**; protected context installed 2026-10-04 (see Update below). This report covers repository/workspace provisioning, not Desktop product delivery or Phase 1300 acceptance.

## Verified implementation

- Public fork https://github.com/Erarchitech/degram read back from GitHub: fork=true, parent=NousResearch/hermes-agent, private=false.
- Submodule `apps/degram` pinned at `8b66a51036c1e20920a17cdd049fdf55c968d683`; remote main and local HEAD match. origin=fork, upstream=official. Child source clean; only generated AST caches ignored locally.
- One shared `.planning` and `DG_OBSIDIAN` authority, explicit repository decision added to PROJECT/ROADMAP/STATE and Obsidian indexes. No requirement/phase closed.
- `tools/degram/workspace.py context|verify` resolves the same framework from root, component root and nested Desktop location. It verifies required context files/hashes, selected gitlink/remotes and absence of competing child planning/vault. It is an explicit preflight, not automatic prompt injection.
- Four tests passed. Context routing, unsafe paths and actual gitlink verification were developed with observed RED→GREEN; repeatable indexing command contract also observed RED→GREEN.
- `tools/degram/index_code.py` ran end-to-end without LLM calls. DG index: 15128 nodes / 26343 edges. Scoped component: 44687 / 127651. Combined framework: 60197 / 153520. Queries resolve both DeGramWorkspace and JsonRpcGatewayClient. Artifact digests independently verified in `workspace-verification.json`.
- Scoped whitespace checks and staged whitespace check passed. Root index initially empty; submodule registration staged only `.gitmodules` and `apps/degram`. No commit or push was performed.

## Blocking limitation

The host rejected the protected root AGENTS.md edit because the attached client cannot answer approval requests. The user has not granted that tool-level permission. No retry/alternate-path write was attempted. Root AGENTS.md is unchanged; child `.hermes.md` does not exist. `component-context.md` is only a proposed, uninstalled routing artifact.

Automatic bidirectional startup context is therefore **not complete**. Continue in an approval-capable client/session, obtain the protected-file permission, install the root/child entry points, and verify actual Hermes startup context from both working directories. Do not treat generic source availability or this report as that verification.

## Boundaries / known limitations

- No Docker/service restart, package installation, installed Hermes/profile change, CAD/graph/Drive write, paid inference or internal-document publication.
- Fork is source only: no DeGram branding, installer, isolated runtime identity/update channel or DG Desktop adapter implemented. These are subsequent product work.
- Root graph update preserved backups and applied new excludes. One SQL file could not be extracted because tree_sitter_sql is not installed; one existing filtered source was conservatively retained. Component indexing covers Desktop, shared transport, tui_gateway and agent only. Graphs are not acceptance evidence or a whole-upstream semantic index.
- Canonical integration files are local/uncommitted. Another machine cannot reproduce the superproject integration until an explicitly authorized scoped commit/push includes its gitlink and files. The public fork itself already exists independently.

Runbook: `spec/degram/WORKSPACE.md`. Evidence: `integration/degram/workspace-verification.json`. No autonomous update/install action follows from this report.

## Update 2026-10-04: context installed

With explicit owner approval, root `AGENTS.md` gained the framework/DeGram routing section (Perplexity block preserved) and root `CLAUDE.md` the DeGram planning protocol. `workspace.py install-context` (new, tested RED→GREEN, 5/5 tests) generated the child `.hermes.md` from `component-context.md` under a Git-local exclude; `verify` reports `componentContextInstalled: true` and the child stays clean. `gsd-sdk` invoked inside `apps/degram` resolves `project_root` to the framework. Hermes startup context was checked with the fork's `build_context_files_prompt` under a scratch `HERMES_HOME`/`home_override`. No Hermes launch, install, commit or push.

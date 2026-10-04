# DeGram / Design Grammars development context

This checkout is the DeGram component of the Design Grammars framework, based on the official NousResearch/hermes-agent upstream. This routing file is generated locally from the framework's integration/degram/component-context.md; do not edit the generated copy.

Before any framework-related change, resolve the shared context from this repository root:
`python ../../tools/degram/workspace.py context`

Read ../../AGENTS.md, ../../CLAUDE.md, ../../.planning/STATE.md and the relevant sections of ../../.planning/ROADMAP.md and ../../.planning/REQUIREMENTS.md. Then read ../../DG_OBSIDIAN/degram/index.md and ../../spec/degram/WORKSPACE.md. These relative paths are anchored to this file, not a nested shell cwd. A missing framework is a blocking setup error, not permission to create another plan/vault.

Read this repository's AGENTS.md explicitly too; this .hermes.md routing layer must not hide upstream engineering rules. Follow its area routing table; Desktop edits require apps/desktop/AGENTS.md and DESIGN.md. Shared requirements, decisions and acceptance live only in the outer framework. Use the fork for source and upstream-compatible changes, not copies of private DG knowledge.

Planning (GSD) always runs against the framework: GSD commands invoked from here resolve `project_root` to ../.. and read/write only ../../.planning. Never create .planning, a roadmap or a vault in this repository. Plans that touch this repository name its files as `apps/degram/...` and say which repository commits each change; the child commit is verified and pushed to the fork before the framework gitlink is bumped.

From either repository, inspect the producer and consumer contract before API/IPC changes. Root commits cannot include uncommitted submodule source. Never mark shared GSD work complete from a child summary alone. No commits/push, deployment or installer execution without applicable authorization.

Do not launch upstream Hermes here against the installed user profile. Runtime home, Electron userData/app ID and DeGram-owned updater still need separate implementation before a development launch. Product users do not inherit developer access to the framework vault. No secrets, unpublished manuscripts or provider credentials belong in this public fork.

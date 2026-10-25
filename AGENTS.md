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

<!-- PERPLEXITY-MCP-START -->
# Perplexity MCP Server

## Available Tools

- **perplexity_search** — Fast web search with source citations. Use for quick factual lookups. Works with or without authentication.
- **perplexity_reason** — Step-by-step reasoning with web context. Requires Pro account.
- **perplexity_research** — Deep multi-section research reports (30-120s). Requires Pro account.
- **perplexity_ask** — Flexible queries with explicit model/mode/follow-up control.
- **perplexity_compute** — ASI/Computer mode for complex multi-step tasks. Requires Max account.
- **perplexity_models** — List available models, account tier, and rate limits.
- **perplexity_retrieve** — Poll results from pending research/compute tasks.
- **perplexity_export** — Export a saved history entry as PDF, markdown, or DOCX. Uses Perplexity's native export when available.
- **perplexity_sync_cloud** — Sync Perplexity cloud history into the local history store.
- **perplexity_hydrate_cloud_entry** — Hydrate a single cloud-backed history entry by id.
- **perplexity_list_researches** — List saved research history with status.
- **perplexity_get_research** — Fetch full content of a saved research.
- **perplexity_login** — Open browser for Perplexity authentication.
- **perplexity_doctor** — Run diagnostic checks against your Perplexity MCP install. Returns a Markdown report; pass probe:true for a live search probe.

## Usage Guidelines

1. **Start with perplexity_search** for quick questions. Only escalate to research or reason when depth is needed.
2. **Check rate limits** with perplexity_models before batch operations.
3. **Always cite sources** from search results in your responses.
4. **For multi-turn conversations**, pass the follow_up_context JSON from perplexity_ask responses back in subsequent calls.
5. **Long-running research**: perplexity_compute may time out. Use perplexity_retrieve with the returned research_id to poll for results.
6. **Language parameter**: Defaults to en-US. Set explicitly for non-English queries.

## Model Selection

| Tool | Default Model | Best For |
|------|--------------|----------|
| perplexity_search | pplx_pro | General web search |
| perplexity_reason | claude46sonnetthinking | Step-by-step analysis |
| perplexity_research | pplx_alpha | Deep research reports |
| perplexity_compute | pplx_asi | Complex multi-step tasks |
<!-- PERPLEXITY-MCP-END -->

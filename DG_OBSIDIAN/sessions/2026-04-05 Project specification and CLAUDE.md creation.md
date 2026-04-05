---
tags: [session]
date: 2026-04-05
---

# 2026-04-05 Project specification and CLAUDE.md creation

## Summary

Created comprehensive project specification (`spec/`) and `CLAUDE.md` in project root, sourced from the Obsidian knowledge vault.

## Files Created

### `CLAUDE.md` (project root)
- AI assistant context file with architecture overview, session protocol, graph schema v3, common commands, current priorities, and known gotchas

### `spec/` directory (8 documents)
- `README.md` — Table of contents
- `PROJECT.md` — Product overview, problem statement, target audience
- `ARCHITECTURE.md` — 12+ service map, data flows (ingest, query, validation, direct), nginx proxy routes
- `DATABASE.md` — Neo4j graph schema v3: node labels, relationships, Rule/Atom ID formats, violation pattern, complete Cypher example
- `API.md` — All API routes: data-service (18 endpoints), n8n webhooks (2), Neo4j proxy, async polling pattern
- `GRASSHOPPER.md` — C# solution structure, 5 GH components, validation pipeline, build commands
- `UI.md` — SPA component tree, page flow, GraphViewerPage modes, Model Viewer features
- `DEPLOYMENT.md` — Docker Compose, port map, volumes, rebuild commands
- `DECISIONS.md` — 9 ADRs covering SPA architecture, SWRL parsing, project isolation, LLM prompts, auth, Speckle publish, violation inversion, async polling, config injection

## Decisions

None (documentation-only session).

## Next Steps

- Consider adding `spec/` to `.gitignore` or tracking it in git
- Keep `CLAUDE.md` updated when architecture changes
- Use CLAUDE.md as the entry point for Claude Code / Copilot sessions

---
tags: [decision]
date: 2026-07-05
---

# Phase 20: E2E Validation and Docs — Context Decisions

## What

Phase 20 is the v7.0 milestone wrap-up: validate the full pipeline end-to-end, document breaking changes for canvas migration, refresh repo/AI-assistant docs to schema v4 and the 14-component set, and update the knowledge vault.

## Decisions

- **E2E approach**: Manual checklist + Docker automation (GH manual, Docker via curl/Cypher). Fresh + existing test data. Fix critical bugs inline — Phase 20 IS the last chance before release. Full chain, all outputs verified.
- **Release notes**: Dedicated `docs/RELEASE-NOTES-v7.0.md`. Full per-component re-wiring guide with ASCII wiring diagrams. Complete: breakage + features + upgrade instructions.
- **Docs strategy**: Targeted per-doc updates. copilot-instructions.md gets full schema+components rewrite. CLAUDE.md gets schema+factual section updates. Verified via SC#3 grep gate + manual review.
- **Vault**: Archive stale notes to `DG_OBSIDIAN/archive/`. Full graphify regeneration via `scripts/refresh_graphify.sh`. Update index + session note + priorities.
- **Order of operations**: E2E first → fix bugs → docs update → release notes → DG_OBSIDIAN refresh last.

## Why

Phase 20 closes the v7.0 milestone by ensuring the complete 14-component pipeline actually works together, and every architect upgrading from v2.0 has clear migration instructions.

## How to Apply

- Downstream agents (gsd-planner) MUST read `20-CONTEXT.md` before planning Phase 20
- The E2E checklist doubles as a release artifact — architects use it to verify their own v7.0 install
- DG_OBSIDIAN notes for deleted components (CLASSIFICATOR, VALIDATION RUNS) go to `archive/`, not deletion

## Related

- [[sessions/2026-07-05 Phase 20 discuss — E2E Validation and Docs|Discussion session]]
- `.planning/phases/20-e2e-validation-and-docs/20-CONTEXT.md`
- `.planning/phases/20-e2e-validation-and-docs/20-DISCUSSION-LOG.md`
- [[Phase 19 Deconstruct and Reinstate Components decisions]]

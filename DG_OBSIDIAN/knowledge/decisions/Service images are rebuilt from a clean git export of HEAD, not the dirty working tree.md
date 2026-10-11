---
tags: [decision, docker, release, degram]
date: 2026-10-11
---

# Service images are rebuilt from a clean git export of HEAD, not the dirty working tree

## Context

Plan 1301-36 required rebuilding `data-service` and `design-grammars` "from the committed framework tree only". The owner consented to the rebuild ("rebuild ok"). The working tree held uncommitted runtime edits from other sessions (`data-service/cypher_allowlist.py` +108 lines, `dg_context.py`, `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx`) that belong to no plan of the gap round. `docker compose build` uses the working tree as build context and would have shipped them.

## Decision

Export HEAD (`git archive HEAD data-service ui-v2` into a short temp directory), `docker build --no-cache` each context with the compose image names (`design-grammar-system-data-service`, `design-grammar-system-design-grammars`), then `docker compose up -d --no-build design-grammars data-service`. Compose services here have plain `build:` contexts and no `image:` override, so the tags line up. Verify the container image ids equal the freshly built ids.

## Consequences

- The running stack contains only committed code; the other sessions' edits stay out until they are committed and the services are rebuilt again.
- Record the exclusion in the build record (`1301-BUILD.md`) so the live behaviour is not mistaken for the working tree.
- `docker compose build` from the dirty tree is not acceptable for a release build while unrelated edits are pending.

## Related

- [[sessions/2026-10-11 Phase 1301 gap round executed and DeGram 0.1.10 built]]
- [[knowledge/decisions/DeGram access is granted by the project owner, not pasted by the user]]

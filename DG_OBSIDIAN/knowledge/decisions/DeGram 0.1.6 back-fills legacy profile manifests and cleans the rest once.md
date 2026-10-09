---
tags: [decision, degram, phase-1301, profiles, d-30]
date: 2026-10-09
---

# DeGram 0.1.6 back-fills legacy profile manifests and cleans the rest once (D-30)

## Context

Profiles made by DeGram 0.1.0-0.1.5 have no `degram-scope.json`, so a membership revoke cannot tell which user and project they belong to (the directory name is a one-way hash). Deleting local chat history is irreversible.

## Decision

Owner chose `backfill-and-cleanup` (2026-10-09): a profile that matches a scope the user opens gets its manifest; on the first 0.1.6 start after sign-in the profiles still without a manifest are deleted once (marker `degram-legacy-cleanup.done`). Rejected: `backfill-only` (stale data like `scope-dee1…` stays) and `wipe-all-legacy` (also deletes current v12 history).

## Consequences

- Plan 20 implementation takes the signed-in user's current memberships as a keep list and back-fills those profiles before deleting, otherwise a cleanup at sign-in would delete everything (the rejected wipe option). Company-key profiles and anything no longer openable are still deleted. The marker is not written if a removal failed.
- Chat history of projects the user can no longer open is lost on this PC.
- Live observation of the cleanup is open (plan 16 Task 3).

## Related

- [[sessions/2026-10-09 Phase 1301 gap plans 18-23 executed and DeGram 0.1.6 shipped]]
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` D-30

---
tags: [debugging, degram, profiles, security]
date: 2026-10-26
---

# Environment-owned profile names must remain covered by the scope backend gate

## Symptom and cause

Plan 1301-43 changes DeGram profile hashes from legacy 16-hex to origin-owned 32-hex suffixes. The existing `apps/degram/apps/desktop/electron/degram/scope-gate.ts` recognized only `scope-<16 hex>` names, bare or prefixed with `conn:local::`.

Its `assertCanStart` deliberately leaves non-DeGram profiles untouched. Without updating that matcher, a 32-hex scope would be misclassified as a generic profile and bypass the inactive-scope backend-start refusal (including renderer reconnect paths).

## Fix and evidence

Recognize exactly **16 or 32** lowercase hex characters (case-normalized by the existing helper), keeping all unrelated profiles unchanged. Regression test asserts recognition of both new bare/pool-key names and refusal to start a new-style scope before the controller allows it.

Expanded Electron tests: 295/295; full Desktop typecheck passed on 2026-10-26. Offline evidence only; no installed runtime launch or live security acceptance. Changes remain uncommitted in the component under plan 43's separate commit gate.

## Reuse

When changing persistent identity formats, inspect every classifier, guard and reconnect path consuming names, not only the serializer and manifest. Successful profile CLI tests cannot prove backend-gate coverage.

See [[sessions/2026-10-26 DeGram plan 1301-43 environment profiles and restartable migration]], [[knowledge/decisions/DeGram dual mode is an additive plan slice with explicit runtime gates]].

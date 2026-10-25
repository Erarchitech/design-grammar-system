---
tags: [degram, framework, moc]
---
# DeGram — integrated Design Grammars component

DeGram is the Hermes-derived Desktop component of Design Grammars, not an independent framework or a replacement for its server.

- [[degram/Repository topology|Accepted repository topology and context ownership]]
- [[knowledge/decisions/DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls|Where DeGram is developed: submodule on `degram/milestone13`, build clone pulls only (2026-10-25)]]
- Product plan: framework `.planning/STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`; phases 1300–1307 retain their owners.
- Workspace/contract entry point: `spec/degram/WORKSPACE.md`.
- Machine-readable routing: `integration/degram/workspace.json`.
- Source: `apps/degram`; official Desktop remains at its upstream `apps/desktop` path.
- Existing read-only web increment: `ui-v2/src/degram` and `1301-01-SUMMARY.md`.
- No second vault, second authoritative roadmap, copied manuscript corpus or duplicate evaluator.

## Current boundary

Public upstream fork and local integrated workspace are provisioned separately from product implementation. Desktop branding/build/runtime isolation, DG authentication and actual adapters still require implementation and tests. Phase 1300 V8/ownership acceptance remains open. Do not restore withdrawn comparative baseline experiments.

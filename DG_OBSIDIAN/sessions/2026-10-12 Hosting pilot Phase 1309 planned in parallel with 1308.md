---
tags: [session, hosting, degram, phase-1309]
date: 2026-10-12
---
# Hosting pilot: Phase 1309 planned alongside 1308

## Outcome

The owner requested a fast hosting pilot while continuing Phase 1308 independently. A host-neutral DG package without local Ollama/GPU is the planning target; the personal CV and knowledge graph remain separate workloads. The university-lab plan is a conditional campus deployment path, not permission to host personal services or bypass IT.

- Survey: `.planning/research/hosting-deployment-survey-2026-10-12.md`.
- Milestone ownership: Phase 1309 in `.planning/ROADMAP.md`, `HOST-01..06` in `.planning/REQUIREMENTS.md`.
- Scope and research: `.planning/phases/1309-dg-hosting-package-without-local-ollama/1309-CONTEXT.md` and `1309-RESEARCH.md`.
- Eight execution plans `1309-01-PLAN.md` through `1309-08-PLAN.md` in that directory. Their dependency chain separates offline Compose/edge/package/recovery preparation from a frozen 1308/1301 integration, private staging and authorized external UAT. Executable clean bundle, narrow mounts, edge and backup/restore are specified. Permission-dependent local sandbox tests are checkpoints, not implicit authorization or static PASS.
- Campus P01–P16 remains in `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md` and consumes the generic hosted package rather than defining a competing one.

## Evidence and limits

The eight plan files and `HOST-01..06` coverage/dependency references were checked; `python tools/degram/workspace.py verify` passed. Compose parser findings in `1309-RESEARCH.md` are offline only: `!reset null` removes the inherited Ollama service, whereas profiles-only does not remove its dependency. No hosted overlay, bundle, backup utility, server, public endpoint or runtime UAT has been implemented. No purchase, service operation, paid inference or deployment was authorized.

Two plan-check passes exposed missing executable assembly/edge/recovery work and then premature permission-dependent tests; the plans were revised. The final checkpoint edits have not had a third independent checker pass; do not label plan quality independently accepted on that basis.

## Resume

1. Re-read `1309-CONTEXT.md`, `1309-RESEARCH.md`, eight plans and the current 1308 state; check concurrent working-tree changes before editing shared files.
2. Re-run the plan checker on the final revisions. With separately scoped execution authorization, begin plan 01's offline Compose tracer; plans 02–04 have explicit local runtime permission gates. No integration freeze before the owner hands off a tested 1308/1301 candidate.
3. Decide host, data/export policy, budget, domains, backup destination and reviewer slice at their gates. Campus additionally needs IT/data-owner approval. Private staging, external route and invitations are separate decisions.

No 1309 requirement or 1307 release gate is marked complete.
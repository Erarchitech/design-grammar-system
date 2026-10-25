# Phase 1309 — DG hosting package without local Ollama

Status: context only, planning not started (2026-10-12). Authority: `.planning/ROADMAP.md` and HOST-01..06 in `.planning/REQUIREMENTS.md`. Research: `.planning/research/hosting-deployment-survey-2026-10-12.md`; campus-specific conditional plan: `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md`.

## Locked scope from owner request

Prepare **DG** for external hosting; exclude the local Ollama/GPU service from the hosted package while retaining local development behavior. On 2026-10-12 the owner requested planning the hosting pilot **now, in parallel with their Phase 1308 work**. Phase 1309 offline preparation can proceed without waiting for 1308 completion. Only integration/private staging consumes the specific frozen and tested 1308/1301 build. No execution, deployment, purchase, public ingress, paid model calls or commit is authorized by phase creation or this planning instruction. Personal CV and personal knowledge graph inform host choice but are distinct workloads, not DG product features or a second planning authority.

## Parallel work lanes and cutover gates

- **Lane A (1309 offline, now):** compose feasibility/tracer, CPU-only service graph, tests, curated release layout, security contract and backup runbook. Work on `docker-compose.hosted.yml`, `deploy/hosted/**` and dedicated tests, not 1308's live data-service/UI/DeGram files. If a shared base file must change, stop for explicit single-writer coordination and rerun both suites against the same revision.
- **Lane B (1308, owner-controlled):** finish UI/role/export/connector sessions and live cleanup under its own plan and approval checkpoints. Never infer that an unchecked plan is shipped because the code exists.
- **Integration seam:** freeze a commit/release manifest for framework and component; assert 1301/1308 consumed APIs, client, schema/security contracts against exactly those revisions. Private staged deployment and remote tests are blocked until scope-specific authorization, not until every v13 product phase ends.
- **Pilot gate:** accept a deliberately bounded browser-first review, with DeGram read/chat only if separately verified on a Windows PC. No native GH authoring or direct Bolt claim. Explicit owner and (if campus) IT go/no-go, restore/reboot, tenancy, external TLS and negative tests precede invitations. Full 1307 product release remains separate.

## Plan-phase decisions to resolve

- Confirm hosted pilot capacity, provider/region/budget and university data policy before binding host-specific topology. A hosted overlay should be portable across an approved VPS and an approved campus server.
- Model provider remains remote/operator-controlled; test denied path without upstream call, and live paid path only with explicit quota authorization.
- Current Compose n8n dependency on Ollama and GPU reservation must be absent from the *effective merged config*, not merely unused at runtime. Preserve local profile tests.
- Release allowlist, immutable image/digest manifest, separate personal workload boundaries and backup/restore design are required. Never bundle `DG_OBSIDIAN`, unpublished manuscripts, `.secrets/`, user profiles or the whole development repository.
- Verify Speckle external origins and object storage upload/download, HTTPS, cookies/proxy trust, invite-only access, project isolation, single-process JSON auth store and remote DeGram browser/Windows cases.
- P09 of the campus plan consumes the generic package; P10–P16 and equivalent VPS cutover require fresh host-specific approval. Phase 1309 success does not imply 1307 release acceptance or DGBN-01 completion.

## Verification scope

Start with failing merged-config/security tests and private, sanitized Linux staging; then only after explicit authorization do live external browser/Windows, encrypted backup restore and reboot/load trials. Preserve expected/actual results and no-go outcomes. Prefer staged rollback before opening any public reviewer route.

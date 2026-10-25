# Phase 1309: DG hosting package without local Ollama — Research

**Researched:** 2026-10-12
**Domain:** Host-neutral, CPU-only, invite-only DG pilot packaging
**Confidence:** HIGH for current Compose graph and requirements; MEDIUM for proposed hosted topology pending private Linux proof; LOW for host capacity/policy until owner/IT confirmation. This is research, not implementation or authorization.

## User Constraints

Locked scope from `1309-CONTEXT.md:5-26`: prepare **DG** for external hosting without the local Ollama/GPU service while preserving local development; offline 1309 runs now in parallel with owner-controlled 1308. Do not edit 1308's live data-service/UI/DeGram files; shared base changes require single-writer coordination. Integration consumes a frozen, tested 1301/1308 release, not assumed completion. The browser-first bounded pilot, remote model control, no automatic paid inference, release allowlist, HTTPS/Speckle/S3, backup/restore and negative security checks are mandatory. No implementation, deployment, purchase, public ingress, paid calls, commit, disk erase or service changes are authorized here. Personal CV/graph are separate workloads. Campus P09 consumes the generic package; P10–P16 require distinct permission. Full 1307 acceptance and remote GH/DGBN-01 are separate gates. [VERIFIED: `.planning/phases/1309-dg-hosting-package-without-local-ollama/1309-CONTEXT.md:5-26`; `.planning/ROADMAP.md:514-526`; `.planning/REQUIREMENTS.md:117-124`]

## Summary

**Primary recommendation:** Plan an offline tracer/test of a third, last-applied hosted overlay and a curated runtime manifest before any private deployment. Assert the **merged** model, not the YAML fragment, and freeze a precise release after 1308 lands. Host-specific DNS/TLS/backup destinations belong to a separate approved deployment branch. [VERIFIED: `docker-compose.multi-user.yml:9-19`; `.planning/ROADMAP.md:514-526`; `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md:159-168`]

A read-only Compose CLI probe (`Docker Compose v2.40.3-desktop.1`, `config --no-interpolate`) on the current base + multi-user + stdin experiment found that `ollama: !reset null` removes the **service** from `config --services`, but leaves the named top-level `ollama` volume; `n8n.depends_on: !reset []` removes both dependencies, whereas `!override [data-service]` retains the needed one. A profiles-only experiment retains Ollama in the model and retains n8n's dependency on it. These are offline parser observations, not an implemented overlay or a Linux deployment test. [VERIFIED: CLI probe 2026-10-12; `docker-compose.yml:103-148,312-318`; Docker Compose merge/profile docs below]

## Architectural Responsibility Map

| Capability | Owner | Boundary / planning consequence |
|---|---|---|
| Runtime packaging | 1309 overlay + `deploy/hosted/` | DG-only immutable allowlist, CPU graph, config assertions [VERIFIED: `1309-CONTEXT.md:9-22`] |
| Auth and tenancy | Existing DG data-service | Single enforcement point; do not duplicate at edge [VERIFIED: `spec/SECURITY-BOUNDARY.md:15-32`] |
| Model provider | Operator-set DG LLM settings | Relay permits one configured upstream, no fallback; deny test before live quota-approved call [VERIFIED: `spec/SECURITY-BOUNDARY.md:138-148`] |
| TLS/ingress | Approved host edge | DG/Speckle/blob routes only; host-specific network authority [VERIFIED: `.planning/REQUIREMENTS.md:121-124`] |
| Campus branch | P09–P16 | Consume package, do not fork another product topology [VERIFIED: `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md:10-14,49-61`] |

## Standard Stack

Use the existing Docker Compose CLI and existing DG/Speckle containers; add no third-party package during offline planning. The observed Compose version supports `!reset` and `!override`; require an explicit minimum compatible Compose version in the eventual runbook and verify on the target Linux engine. `docker compose config` renders the merged actual model; later files override/merge earlier ones and paths resolve relative to the first file. [CITED: https://docs.docker.com/reference/cli/docker/compose/config/][CITED: https://docs.docker.com/reference/compose-file/merge/][CITED: https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/]

Speckle's public OSS Docker Compose path is documented for development/evaluation/testing, **not recommended for production**; treat this as a bounded pilot risk and do not call it an HA production deployment. [CITED: https://docs.speckle.systems/developers/server/deployment-options]

## Architecture Patterns

### Service graph and Ollama removal (HOST-01)

Current base has **15 services**, including `ollama` with `ollama/ollama:latest`, loopback port 11435 and NVIDIA GPU reservation; n8n depends on `data-service` **and** `ollama` and inherits `OLLAMA_URL`, `OLLAMA_HOST`, `OLLAMA_MODEL`. The multi-user file resets only Neo4j/n8n ports and sets deployment/registration flags. [VERIFIED: `docker-compose.yml:103-148`; `docker-compose.multi-user.yml:24-37`]

Plan last-applied `docker-compose.hosted.yml` after `docker-compose.yml` and `docker-compose.multi-user.yml`. In the third file, remove the inherited service with `ollama: !reset null`; reset/replace `n8n.depends_on` to retain **only** `data-service` (prefer `!override` with version gate); reset inherited n8n Ollama env keys to null, and reset the top-level `ollama` volume if no other use remains. Do not merely set `profiles: [local]`: profiled services can be explicitly targeted and the unprofiled n8n dependency makes the model invalid unless the dependency is removed. Profile filtering also does not constitute absence from the effective definition. [VERIFIED: offline `docker compose ... -f - config --no-interpolate --services` experiments; Docker Compose profile/merge docs below]

**Exact experiment (read-only):** stdin overlay `services: {n8n: {depends_on: !override [data-service]}, ollama: !reset null}` yielded 14 service names and no Ollama. Repeating with `depends_on: !reset []` yielded `n8n deps None`; top-level `ollama` volume remained until separately reset. A profiles-only overlay yielded `profiled service True` and `n8n deps` containing `ollama`. [VERIFIED: CLI probe 2026-10-12; `docker-compose.yml:125-148,312-318`]

Test `config --no-interpolate --format json` with harmless placeholders for structural assertions; a separately sanitized interpolation test must verify actual URLs/ports and fail required-variable omissions without printing secrets. Assertions: no service `ollama`, no GPU/NVIDIA reservation in **any** service, no dangling depends_on, no `OLLAMA_*` env in hosted n8n, no published port except controlled ingress, no localhost public origins, and original two-file local/multi-user configurations unchanged. `--services` alone is insufficient: inspect volumes, environment, devices, ports and dependency graph. Never publish interpolated `config` output or use a real `.env` in evidence. [CITED: https://docs.docker.com/reference/cli/docker/compose/config/]

### Release layout and ingress (HOST-02/03)

Curate a clean build context/release tree: pinned image digests (including built DG images via registry digest or reproducible source revision plus resulting image digest), framework git revision and DeGram gitlink/image manifest, only required `data-service`, `dg-reasoner`, `ui-v2`, `neo4j`, `n8n` workflows, Speckle bootstrap and approved fixture/tool subset. Explicitly exclude `.secrets`, `DG_OBSIDIAN`, `Publications`, whole repo read-only bind, developer profiles/cache and generated credentials. `data-service` currently binds `.:/mnt/repo:ro` plus `./data-service/data:/app/data`; n8n binds `./n8n:/files`; replacing the broad mount requires a named fixture/knowledge-ingest capability test, not blindly deleting it. Existing floating Speckle/MinIO/Ollama images and `build` directives are not immutable release evidence. [VERIFIED: `docker-compose.yml:44-101,103-148,186-206,240-309`; `.planning/REQUIREMENTS.md:119-120`]

Current `design-grammars` publishes `8080:80`, `speckle-ingress` `8090:8080` on all interfaces; MinIO 9000/9001, data-service 8000 and reasoner 8001 remain on loopback even after multi-user. A host firewall alone is not a substitute for eliminating unintended published ports. Choose a single approved HTTPS edge with explicit DG/Speckle and (if supported) signed S3 object routes; bind upstream ports to loopback/private edge network, check IPv4 **and IPv6**, deny admin/db/Bolt/n8n/MinIO-console/CAD bridge externally. Keep internal DNS (`neo4j`, `speckle-ingress`, `speckle-minio`, `n8n`) internal. `GH_BRIDGE_HOST=host.docker.internal` resolves the Linux **server**, not a reviewer's Windows PC; do not promise remote native GH. [VERIFIED: `docker-compose.yml:44-101,150-165,186-199,299-310`; `docker-compose.multi-user.yml:17-23`; `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md:28-37`]

Set one approved external HTTPS DG origin (`DG_BASE_URL`, UI endpoint), Speckle origin (`SPECKLE_BASE_URL` in both data-service and UI, `CANONICAL_URL`, `FRONTEND_ORIGIN`, frontend `NUXT_PUBLIC_API_ORIGIN`/`NUXT_PUBLIC_BASE_URL`), secure cookies (`DG_COOKIE_SECURE=true`), and public HTTPS S3 endpoint separately from internal `S3_ENDPOINT=http://speckle-minio:9000`. Current public values are localhost, and base `S3_PUBLIC_ENDPOINT=http://localhost:9000` fails remote clients. Speckle's public endpoint must be reachable via HTTPS by client machines for presigned URLs; verify URL host/path/signature preservation, browser CORS, upload ETag, import completion and download from a separate client. Do not expose 9001 console or assume a reverse-proxy path prefix preserves S3 signatures; a distinct object hostname is the safer test candidate. If modern upload is excluded from pilot, say so explicitly. [VERIFIED: `docker-compose.yml:59-68,150-165,201-255`; CITED: https://docs.speckle.systems/developers/server/deployment/kubernetes-with-helm; CITED: https://docs.speckle.systems/developers/api/guides/file-uploads]

Set `DG_TRUSTED_PROXIES` only to actual edge CIDRs; both data-service and UI consume it and UI generates nginx real-IP config, so test spoofed X-Forwarded-For from an untrusted client and secure-cookie/CSRF behavior behind TLS. `/neo4j/` and `/n8n/` UI locations are 404 tombstones, while `/llm/`, `/reasoner/` and `/data-service/` are proxied to data-service; test route policy, not URL naming alone. [VERIFIED: `docker-compose.yml:76-85,159-165`; `ui-v2/entrypoint.sh:8-24`; `ui-v2/nginx.conf:36-80,133-140`; `spec/SECURITY-BOUNDARY.md:15-24`]

### Health, recovery and backup consistency (HOST-04)

Most app services lack healthchecks/restart policies; Speckle components have `restart: unless-stopped`, but startup `depends_on` is currently service-start ordering, not application readiness. Add meaningful checks (DB query, HTTP readiness, blob bucket/API, n8n/UI/Speckle) with bounded startup grace and dependencies conditioned on health where valid, plus restart policy, then test cold boot, partial failure and host reboot. Do not mistake `healthy` for an end-to-end reviewer workflow. The data-service Dockerfile runs a **single** uvicorn process; preserve one replica/worker because auth/session/settings files under `DG_DATA_DIR` are JSON file-backed. [VERIFIED: `docker-compose.yml:1-318`; `data-service/Dockerfile:23-24`; `spec/SECURITY-BOUNDARY.md:9-11`; CITED: https://docs.docker.com/reference/compose-file/services/]

Inventory persistence: Neo4j named volume, Speckle PostgreSQL/MinIO/Redis volumes, n8n volume, bind-backed `data-service/data`, plus encrypted LLM settings key and all bootstrap/service/Speckle/MinIO/n8n secrets. Design a coordinated checkpoint (quiesce writers or tested database-native snapshots/dumps, PG-consistent dump, object store version/inventory, JSON auth/settings and workflow/export state) with manifest/timestamps and explicit recovery order; Redis may contain transient queues, so define drain/replay semantics rather than assume a crash-consistent volume copy. Encrypt an off-machine backup and independently restore to an isolated target; verify logins, memberships, project/model/object reads, revocation and key decryption, and document RPO/RTO and rollback. A VPS snapshot alone is not multi-store consistency proof. Neo4j Community online backup must not be assumed (earlier survey cites offline dump mode). [VERIFIED: `docker-compose.yml:17-18,92-94,128-130,175-199,312-318`; `spec/SECURITY-BOUNDARY.md:9-11`; `.planning/research/hosting-deployment-survey-2026-10-12.md:21-30`]

### Staged authorization and acceptance (HOST-05/06)

1. **Now/offline:** scope browser-first slice, release allowlist, `config` structural and sanitized tests, threat/restore runbook; no live services or shared 1308 edits. Test local two-file development remains intact. [VERIFIED: `1309-CONTEXT.md:9-26`]
2. **Freeze seam:** after owner 1308 integration, record framework revision + DeGram gitlink, APIs/schema/security contracts, image digests and fixtures; run applicable 1301/1308 suites against that exact release. No inferred product acceptance. [VERIFIED: `1309-CONTEXT.md:12-23`; `.planning/ROADMAP.md:516-525`]
3. **Authorized private staging:** owner approves private sanitized Linux target and data/provider scope; test no-upstream deny, secure ingress/network negatives, restore, cold boot, measured concurrent load, two-project isolation and stale/revoked sessions. Do not call paid provider without separate quota permission. [VERIFIED: `.planning/REQUIREMENTS.md:119-124`]
4. **Authorized remote proof:** off-network browser and separate Windows DeGram PC test login, grant/session exchange, reads/chat if enabled, object streaming, logout/revoke, reconnect and foreign-project refusal. Direct Bolt GH is unsupported in multi-user; native write requires DGBN-01 and distinct evidence. [VERIFIED: `spec/SECURITY-BOUNDARY.md:119-159`; `docker-compose.multi-user.yml:21-23`; `.planning/REQUIREMENTS.md:123`]
5. **Host cutover:** select VPS or campus, classify data/export and backup location, owners/budget/DNS/TLS; for campus obtain institution-specific written IT/data-owner approval and discrete permissions for P07 disk erase, P10 deployment, P12 external path, P15 go/no-go and P16 invitation. Personal CV/graph remain separate credentials/storage/release. [VERIFIED: `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md:10-21,49-72`; `.planning/REQUIREMENTS.md:124`]

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| Compose service deletion/merge | Official `!reset`/`!override` and `docker compose config` structural inspection, not regex on YAML [CITED: https://docs.docker.com/reference/compose-file/merge/] |
| TLS, signed object URLs | Approved reverse proxy and Speckle/S3 native signing; never forge browser URL replacements [CITED: https://docs.speckle.systems/developers/api/guides/file-uploads] |
| Database backup | Database-aware dumps/checkpoint + isolated restore, not live volume tar alone [VERIFIED: `.planning/REQUIREMENTS.md:122`] |

## Common Pitfalls

- `profiles` only hides Ollama from default invocation, not from explicit target or inherited dependency; test the model and active graph. [CITED: https://docs.docker.com/reference/compose-file/profiles/]
- `!reset []` on n8n dependencies erases **data-service** too; use tested replacement or re-add it. `ollama: !reset null` does not remove top-level volume. [VERIFIED: offline Compose CLI probe; `docker-compose.yml:125-148,312-318`]
- Multi-user is not hosted: all-interface 8080/8090, localhost public origins, broad repo bind and unpinned images remain. [VERIFIED: `docker-compose.yml:61-68,92-94,150-165,201-255,299-310`; `docker-compose.multi-user.yml:24-37`]
- A passing `config` with `--no-interpolate` does not prove required secrets/origins; a real interpolated dump can leak credentials. Preserve only redacted assertions and hashes. [CITED: https://docs.docker.com/reference/cli/docker/compose/config/]
- Provider-export policy defaults allowed for a new project; freeze/verify owner-approved export setting **before** real external inference, with denied-path no-call evidence. [VERIFIED: `spec/SECURITY-BOUNDARY.md:143-148`]

## Code Examples / Planner Test Skeleton

Conceptual **future** overlay fragment (not committed or tested as a full release):

```yaml
# Source: https://docs.docker.com/reference/compose-file/merge/
services:
  ollama: !reset null
  n8n:
    depends_on: !override
      - data-service
    environment:
      OLLAMA_URL: !reset null
      OLLAMA_HOST: !reset null
      OLLAMA_MODEL: !reset null
volumes:
  ollama: !reset null
```

The identifiers above are quoted from `docker-compose.yml:103-148,312-318` and the syntax from official Compose merge docs. Validate on the actual release with `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml -f docker-compose.hosted.yml config --no-interpolate --format json`; parse services, `depends_on`, environment, volumes, deploy devices and ports, then separately validate interpolated sanitized fixture. [VERIFIED: CLI probe; CITED: https://docs.docker.com/reference/cli/docker/compose/config/]

## Open Questions / Limits

- Owner: supported reviewer count/features, concurrency/RPO/RTO, data classification, paid provider/quota, DNS/region/budget and whether file uploads are in pilot. No institution policy or server inventory is verified. [VERIFIED: `.planning/research/hosting-deployment-survey-2026-10-12.md:5-21,44-49`]
- Establish the **minimum Compose version** in the release after Linux validation; `!override` support and target parser/version are not proven by the Windows probe. [CITED: https://docs.docker.com/reference/compose-file/merge/]
- Verify exact runtime mount dependencies and Speckle release compatibility with signed S3 endpoint and API feature flags on pinned images; no live application/backup test occurred here. [VERIFIED: `docker-compose.yml:92-94,201-255`]
- Resolve any apparent conflict between static port inventory test in `spec/SECURITY-BOUNDARY.md:318-342` (base + multi-user) and a new third hosted profile through an **additive dedicated hosted test/contract**, without modifying the owner's 1308 runtime files or overwriting the established two-profile contract. [VERIFIED: `spec/SECURITY-BOUNDARY.md:318-342`; `data-service/tests/test_security_boundary_spec.py` identified by `spec/SECURITY-BOUNDARY.md:7-9`]

## Sources

- [Docker Compose merge specification](https://docs.docker.com/reference/compose-file/merge/)
- [Docker Compose multiple-file merge](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
- [Docker Compose profiles](https://docs.docker.com/reference/compose-file/profiles/)
- [Docker Compose config CLI](https://docs.docker.com/reference/cli/docker/compose/config/)
- [Docker Compose service definition and depends_on](https://docs.docker.com/reference/compose-file/services/)
- [Speckle deployment options](https://docs.speckle.systems/developers/server/deployment-options)
- [Speckle deployment configuration, S3 public endpoint](https://docs.speckle.systems/developers/server/deployment/kubernetes-with-helm)
- [Speckle file uploads and presigned object URLs](https://docs.speckle.systems/developers/api/guides/file-uploads)

# DG hosting deployment survey — broadened use

Date: 2026-10-12. Status: research and planning only; no purchase, lab inspection, IT approval, deployment or public access. Related authority: `.planning/ROADMAP.md` Phase 1309 (HOST-01..06), `.planning/REQUIREMENTS.md`. The conditional campus execution branch remains `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md`. Earlier research and its provenance are in `DG_OBSIDIAN/sessions/2026-10-08 Server hosting research for DG reviewers.md`.

## Decision frame

The initial goal was an invite-only external DG reviewer pilot on a university lab PC. The owner now also wants a personal CV website and personal knowledge graph, plus DG access beyond the university network. These are three workloads with different publication and data-policy boundaries. No actual university policy, server inventory, personal graph size, hosting budget or domain/ownership facts have been supplied. The former personal VPS brief (`docs/vps-contabo-context.md`) sets €25/month for an 8 GB VPS, but its budget and scope need reconfirmation; 8 GB is not an established fit for this DG stack.

Provisional choice, **not a purchase decision**: static CV on an independent static host; EU Linux VPS for DG and, only if data classification and measured capacity permit, an isolated private personal graph. Do not share DG Neo4j database, credentials, backups or networks with the personal graph. A separate VM/host is preferable if institutional/BIM data policy, graph sensitivity, or contention requires it. If a linked-notes garden is enough, a static graph view avoids a second running Neo4j. University lab is a DG-only alternative conditional on written IT/data-owner approval; never assume personal use is permitted. Institutional examples illustrate policy variance, not this university's rules.[11][12]

## Current published options (observed 2026-10-12)

| Host | Displayed configuration/terms | Suitability and reservation |
|---|---|---|
| netcup VPS Lite 4 G12.5s | 16 vCore, 32 GB RAM, 640 GB SSD, IPv4+IPv6, €30.86/month incl. displayed German 19% VAT, one-month minimum; rolling traffic throttling to 100 Mbps beyond the published threshold.[1] | Best provisional reversible starting point, but virtual cores are not dedicated physical cores; benchmark and check actual checkout tax, location, storage performance, backup price and contention. Above the old €25/month ceiling even before extras. |
| netcup VPS 4000 G12.5 | 12 vCore, 32 GB RAM, 512 GB SSD, €38.56/month incl. displayed German VAT on selected 24-month term.[2] | Capacity fit on paper, but long commitment is unsuitable before tests. |
| Hetzner dedicated AX42-1 | €97.30/month + €49 setup excluding VAT and IPv4 on the 2026 price list.[3] | Stronger isolation/upgradability, but not the cost-first pilot choice. |
| DigitalOcean general-purpose VM | 8 dedicated vCPU/32 GiB VM displayed at $252/month; 500 GiB volume $50/month, before backups/tax.[4][5] | Operationally flexible, but comparatively expensive for always-on capacity. |
| University lab PC | No institution-specific hosting/personal-use entitlement or hardware details verified. | May be appropriate for approved DG research/data custody, not assumed suitable for personal CV/graph. Follow P01–P16 only with separate approvals. |

These are advertised examples, not equivalent CPU guarantees or binding quotes. 24–32 GB RAM and 200–500 GB storage are engineering envelopes from the earlier DG survey, not measured minimums. Add off-host backup, domain, taxes and possible LLM consumption when pricing. Avoid treating VPS snapshots as a consistent, tested backup of Neo4j/PostgreSQL/MinIO/n8n/auth stores.

## Three workload boundaries

- **CV:** static HTML/build on Cloudflare Pages or another static host, with a personal domain; Pages Free displays 500 builds/month.[6] Only allowlisted, reviewed content from the personal graph may become public. No browser database key.
- **Private personal graph:** separate Neo4j Community instance/volume/secret/backup/network on the VPS only if capacity and ownership permit. Community supports offline dump; online backup command is Enterprise-only.[10]
  AuraDB Free is a prototype option with inactivity/data-retention caveats, not sole durable storage.[8][9]
  AuraDB Professional starts at $0.09/GB-hour (about $65.70 per 730-hour month at 1 GB) and includes daily backups with seven-day retention.[7]
  If only backlinks and published notes are wanted, evaluate static Quartz instead of live Cypher.[14]
- **DG:** distinct multi-user Compose stack and only approved HTTPS ingress. DeGram/Revit/Rhino remain on Windows clients. No public Bolt, databases, admin UI, local CAD listeners or Docker socket. Keep authenticated app access separate from network location; a VPN may be used for administration, not as a substitute for project authorization.[13]

**University policy gate:** ask this university's IT/lab/data owner whether personal CV, personal graph, research data, off-campus reviewer access, DNS/TLS, backups, external inference and retention on leaving are allowed. Do not mix university-owned/restricted data into a personal graph by default. Prior institutional examples cannot answer this gate.[11][12]

## DG release preparation — Phase 1309

1. Freeze supported reviewer/browser/native slice and data classification; distinguish supported remote HTTP path from unsupported direct-Bolt GH use (DGBN-01 remains with 1303). Do not consume unresolved 1300/V8/v12/1307 gates by claiming hosting readiness.
2. Produce one host-neutral `docker-compose.hosted.yml` overlay after base + multi-user. In the *merged* configuration remove active Ollama service, NVIDIA reservation and n8n dependency on Ollama; preserve developer-local behavior. Remote model settings stay operator-controlled, with no paid calls absent permission.
3. Pin release images and curated file mounts; set real DG/Speckle/S3 origins, trusted proxy/secure cookies, restricted bind/edge reachability, TLS and upload/stream tests. The current base has floating images/localhost origins and broad repository mount; the multi-user overlay alone is not a public production profile.
4. Prove DB/admin/CAD ingress closed, negative auth/tenancy cases, single data-service worker, start/health/reboot, encrypted off-host backup and isolated restore. Measure resource use and concurrent users; choose VPS size from evidence.
5. On approved off-network clients, test browser and Windows DeGram login/pairing, project isolation, revocation, model loading, reconnect and only declared native features. Owner's go/no-go and host-specific authorization precede publication. The campus P09 package step should consume this release rather than fork it.

**Stop conditions:** no lab disk erase, VPS purchase, network opening, secrets or project data transfer, image build/restart, paid inference or Git publication is implied by this survey. Host-neutral offline planning can proceed; private runtime tests and public operation each need their own scope-specific approvals.

## Open owner decisions

1. Is the old €25/month maximum still binding, and is it compute-only or all-in including backup/tax/domain?
2. Is the personal graph a private Cypher/API database, a curated public digital garden, or both? How large/sensitive is it?
3. Must any DG/BIM data remain under institutional custody, and what external access does university IT allow?
4. What reviewer concurrency, geography, availability/recovery targets and remote GH/native features must the first pilot promise?

## Sources

[1] https://www.netcup.com/en/server/vps/vps-lite-4-g12s-iv-1m
[2] https://www.netcup.com/en/server/vps/vps-4000-g12.5-iv-24m-eu
[3] https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment
[4] https://www.digitalocean.com/pricing/droplets
[5] https://www.digitalocean.com/pricing/volumes
[6] https://developers.cloudflare.com/pages/platform/limits
[7] https://neo4j.com/pricing
[8] https://neo4j.com/free-graph-database
[9] https://neo4j.com/docs/aura/managing-instances/instance-actions
[10] https://neo4j.com/docs/operations-manual/current/backup-restore/modes
[11] https://policies.iu.edu/policies/it-01-appropriate-use-it-resources/index.html
[12] https://policy.tennessee.edu/procedure/it0002-k-acceptable-use-of-it-resources-ut-knoxville-website-hosting-and-content
[13] https://csrc.nist.gov/pubs/sp/800/207/final
[14] https://quartz.jzhao.xyz

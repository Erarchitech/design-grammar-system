# University lab DG reviewer deployment — execution and handoff plan

Created: 2026-10-08
Status: PLAN ONLY — no lab PC inspected, no IT request sent, no Linux installed, no public service deployed.

## 1. Goal and authority

Make Design Grammars accessible online to invited reviewers using a university laboratory PC, including DeGram installed on reviewers' Windows workstations. Prove project isolation, working model/graph access, DeGram connectivity, backup restoration and restart recovery before opening the pilot.

This is a supporting operational plan inside the framework's sole planning authority, `.planning/`. Phase 1309 (HOST-01..06) now owns **host-neutral DG packaging and readiness**; this P01–P16 plan remains the conditional **university-lab deployment** branch. It does not supersede ROADMAP/REQUIREMENTS, close a v13 requirement, or authorize a public launch. Scope fits the deployment decision in DGCN-04, consumes DGCL-01..07 capabilities and supplies evidence for the existing Phase 1307 reviewer-PC/release gate. Full remote Grasshopper repository use additionally depends on DGBN-01 in Phase 1303. Relevant v11/v12 semantic/security gates remain applicable. Do not mark whole milestones complete from hosting success.

The expanded personal CV/knowledge-graph goals are compared in `.planning/research/hosting-deployment-survey-2026-10-12.md`. They are **not** added to this university plan: no personal hosting on campus without written institution-specific permission; a personally controlled VPS plus a separate static CV host is the provisional alternative. Phase 1309 must produce a portable DG package rather than a campus-only overlay. P09 consumes its verified package; P10–P16 retain separate host-specific authorization. The first package excludes local Ollama and GPU requirements while leaving local development unchanged.

Planning is authorized by the present request. Future disk erasure, package installation, live service operations, secret rotation, data transfer, paid inference, CAD access, firewall changes, Git commits and publication need scope-specific authorization. University IT approval and the owner's execution permission are separate prerequisites. Do not reuse permissions from an earlier PC or deployment.

**Working defaults, not owner-approved final decisions:**
- Invite-only pilot, initially 2–5 concurrent reviewers and a small, sanitized fixture collection.
- Ubuntu Server 24.04 LTS x86-64 on a dedicated lab PC. Prefer 32 GB installed RAM; a 24 GB allocation target is acceptable and 16 GB requires a bounded workload trial. Prefer a 500 GB physical SSD/NVMe with at least 200 GB available for the application. These are capacity targets, not measured minimums. Physical cores, hardware threads and cloud vCPUs are not equivalent; record the actual CPU model.
- DG, databases, model relay and self-hosted Speckle on Linux. DeGram and any required Revit/Rhino run locally on a supported Windows client. No Linux server GPU is needed with remote inference.
- Native CAD work is optional for browser review, but any claimed native DeGram feature must be tested on the separate Windows client.
- Public HTTPS through a university-approved edge or host reverse proxy; administration over university VPN. No public database or CAD bridge endpoints.
- All task dependencies below are **AND** dependencies. A failed or unverified prerequisite blocks dependent work, not unrelated tasks.

## 2. What has actually been verified

Repository inspected: `docker-compose.yml` (15 defined services, including Ollama), `docker-compose.multi-user.yml`, `.env.example` (template only), `spec/SECURITY-BOUNDARY.md`, `docs/degram/CLEAN-INSTALL.md`, `spec/degram/WORKSPACE.md`, active roadmap/requirements and vault priorities. Workspace preflight passes on the pair observed on 2026-10-08; rerun next session. This proves repository wiring, not product acceptance.

Important findings to carry forward:
- Current base Compose contains NVIDIA/Ollama reservation and n8n dependency; it is not a CPU-only production package.
- Public DG/Speckle/S3 URLs contain localhost. Server-side `GH_BRIDGE_HOST=host.docker.internal` targets the Linux server after migration, not a reviewer's PC.
- Multi-user overlay removes Neo4j/n8n host ports but leaves 8080/8090 on all host interfaces. It does not add TLS.
- `data-service` has JSON auth/settings stores requiring one process/worker (`spec/SECURITY-BOUNDARY.md`, single-process auth store). Do not scale it horizontally or add workers without a separate store redesign.
- Spec records a data-service cold-start race and missing restart/health guarantees; live reboot testing is required.
- Whole repository mount into data-service needs narrowing without breaking required fixtures/tools.
- Speckle `S3_PUBLIC_ENDPOINT` points to localhost:9000. HTTPS object upload/download paths need explicit design and testing; do not expose MinIO's admin console to fix this.
- Direct-Bolt GH repositories are unsupported in multi-user mode. Existing server-initiated local GH operations also need capability-specific assessment; moving the server alone does not make them remote.
- Clean-install documentation contains stale relay setup instructions. Current security contract says the DeGram relay consumes Web UI LLM settings; do not resurrect the obsolete separate config writer.
- STATE/ROADMAP include older snapshots than recent vault/build evidence. Reconcile the relevant capability evidence before relying on a completion claim; do not silently rewrite global state.

## 3. Dependency register and progress tracker

Use these exact IDs in future updates. Initial status is NOT STARTED for every task. READY means prerequisites exist, not that execution is authorized. DONE requires linked evidence and actual outcome.

| ID | Task | Depends on | Responsible | Initial availability |
|---|---|---|---|---|
| P01 | Define pilot scope and acceptance | - | Owner + agent | Ready to discuss |
| P02 | Submit university IT request | - | Owner + university IT | Ready to draft/send with approval |
| P03 | Inventory lab PC and preserve Windows | - | Owner + lab administrator | Ready on the actual lab PC |
| P04 | Obtain IT approval and settle network design | P02 | University IT + owner | Blocked |
| P05 | Audit software capability/release readiness | P01 | Agent + owner | Blocked |
| P06 | Approve data, backup and recovery design | P01 | Owner + IT + agent | Blocked |
| P07 | Install Linux after explicit erase checkpoint | P03, P04, P06 | Owner + lab administrator | Blocked |
| P08 | Harden host and prepare container runtime | P07 | Administrator + agent | Blocked |
| P09 | Build and privately test deployment package | P04, P05, P06 | Agent + owner | Blocked |
| P10 | Deploy private lab instance and pilot data | P08, P09 | Administrator + agent | Blocked |
| P11 | Prove backup restore and reboot recovery | P06, P10 | Administrator + agent | Blocked |
| P12 | Enable restricted external HTTPS test path | P04, P10 | University IT + administrator | Blocked |
| P13 | Verify external browser/security experience | P12 | Owner + test reviewer + agent | Blocked |
| P14 | Verify external DeGram/client experience | P05, P12 | Owner + Windows test reviewer | Blocked |
| P15 | Review evidence and authorize pilot opening | P11, P13, P14 | Owner + university IT | Blocked |
| P16 | Open invited pilot and operate it | P15 | Owner + administrator | Blocked |

**Parallel work:** P01/P02/P03 can begin independently. After P01, P05/P06 can run while IT processes P02/P04. After the prerequisite approvals, P07/P08 (lab hardware) and P09 (deployment engineering) can run in parallel on separate targets. After P10, P11 and P12 can proceed independently; after P12, P13/P14 can run in parallel, coordinating shared data and provider quotas. P15 waits for all three evidence branches.

**Dependency summary:**
- Administration: P02 → P04.
- Hardware: P03 + P04 + P06 → P07 → P08.
- Software: P01 → P05/P06; P04 + P05 + P06 → P09.
- Integration: P08 + P09 → P10.
- Recovery: P06 + P10 → P11.
- External proof: P04 + P10 → P12 → P13 and P14 (P14 also requires P05).
- Opening: P11 + P13 + P14 → P15 → P16.

## 4. Task instructions and completion gates

### P01 — Define pilot scope and acceptance

1. Confirm reviewer count, expected concurrency, review dates, data sensitivity and whether access is worldwide or university-VPN-only.
2. Identify required experiences separately: browser review; DeGram graph/model chat; local native Revit/GH inspection; remote GH authoring/publishing. Recommended first slice: browser review + scoped DeGram reads/chat, with native reads only where demonstrated.
3. Identify the system owner, technical administrator and substitute contact. Choose a non-sensitive fixture and a second project for negative isolation tests.
4. Agree acceptable outage/recovery targets and observable performance expectations before testing. Proposed recovery targets: at most one day of data loss and one working day to restore, subject to IT/owner acceptance. Do not claim these as achieved.
5. Confirm whether model/API use is permitted and who pays; agree a provider-side spending control or operator response. An automatic per-user budget enforcement feature is not assumed to exist.

**Done when:** owner records the named pilot features, excluded features, tester(s), data policy and pass/fail expectations. If full native remote workflows are required, P05 must clear their implementation gaps rather than silently narrow the goal.

### P02 — Submit the IT request

Draft the request below; owner sends or explicitly authorizes sending. Record a ticket ID/contact, not passwords.

> We request approval to host an invite-only architectural research application (Design Grammars) for external reviewers on a university-owned laboratory PC. The proposed host runs Ubuntu Server and Linux Docker containers. Please confirm: permission to reimage/dedicate the device and keep it powered on; an approved server VLAN/DMZ or other isolated placement; either a routable public address, a static internal address with inbound HTTPS NAT, or an institutional HTTPS reverse proxy; DNS names and certificate/renewal ownership; inbound TCP 443 and, only if required by the certificate method, TCP 80; VPN-restricted SSH administration; required outbound DNS/time/update/container-registry/LLM-provider access; Docker subnet compatibility with campus/VPN routes; permission and conditions for storing project/BIM and user account data and sending approved context to an external LLM; off-machine backup destination, retention and incident-response responsibilities. The application currently uses local invite-only accounts, not native university SSO. Please confirm whether this is acceptable and whether outside reviewers can obtain VPN access if public HTTPS is not permitted.

**Done when:** ticket/request has been sent with owner's approval and a contact is assigned. Sending a request is not approval.

### P03 — Inventory lab PC and preserve the existing system

Perform on the **lab PC**, not the developer computer hosting this conversation.

1. Record CPU model/architecture, cores/threads, RAM, SSD model/capacity/free space/health, wired NIC, BIOS power-loss recovery and ownership/asset ID. Windows Settings/System Information and Disk Management suffice; do not infer hardware from this chat's local terminal.
2. Confirm the machine can be dedicated continuously, physical access is controlled, and there is acceptable cooling/power/UPS support. If Windows must remain usable at the same time, ask IT for a managed Linux VM/hypervisor or another host; do not dual boot a reviewer server.
3. List data/software that must survive and obtain the lab owner's reimage permission. Make and check a recovery image/backup, record its location and recovery procedure, and preserve any BitLocker/recovery material in IT's secure store.
4. Record hardware shortfalls and upgrade/alternative decisions. 16 GB is not an automatic failure; it requires an approved low-concurrency trial and measured limits. HDD-only or unreliable hardware is a reason to change the host.

**Done when:** inventory and recoverable Windows backup are documented and the machine's availability is confirmed. No disk is erased in this task.

### P04 — Obtain IT approval and settle the network design

Wait for written IT approval, then record:
- Approved topology: (A) campus reverse proxy → private server; (B) public HTTPS/NAT → host TLS proxy; or (C) university VPN-only access with approved external guest accounts.
- Assigned host address/reservation, prefix, gateway, DNS resolvers, VLAN and permitted routes. Never choose an unused-looking static address yourself. Static public IPv4 is not mandatory if an institutional reverse proxy solves inbound access.
- Real DNS names replacing placeholders `dg.UNIVERSITY_DOMAIN` and `speckle.UNIVERSITY_DOMAIN`. Both can share one edge/IP. Decide whether the pilot actually needs separately reachable Speckle ingress and S3 object endpoint; DG-proxied reads do not by themselves prove uploads work.
- Certificate owner/method: university-managed, ACME HTTP-01 (port 80), TLS-ALPN-01 if supported, or DNS-01. Port 80 is not mandatory if the chosen method does not need it. University IT controls DNS and renewal permissions.
- Allowed outbound endpoints, approved proxy/CA trust if HTTPS inspection exists, and campus/VPN subnets that Docker must not overlap. Do not disable certificate validation to bypass a campus CA problem.
- Exact management ingress restrictions and staged reviewer-test access. Address IPv4 and IPv6 consistently; do not publish AAAA before the IPv6 path is secured and tested.

**Done when:** written permission and specific network/DNS/TLS choices are available. If inbound hosting is refused, use an IT-approved VPN/reverse-proxy alternative or return to a VPS. Do not deploy an unapproved tunnel to bypass the university firewall.

### P05 — Audit product capabilities and select a reproducible release

1. Re-read root AGENTS/CLAUDE, `.planning/STATE.md`, relevant roadmap/requirements and `DG_OBSIDIAN/00-home/Current priorities.md`; then `DG_OBSIDIAN/degram/index.md` and `spec/degram/WORKSPACE.md`.
2. Run `python tools/degram/workspace.py verify`. Reconcile recent build/UAT records with stale summary pointers. Use actual test/build evidence, not merely `productAccepted` or a session summary.
3. Map P01 features to tested server/client paths. Specifically assess direct-Bolt repositories, server-initiated `host.docker.internal` GH calls, relay configuration, pairing and Speckle upload/download behavior across different machines.
4. Identify applicable security/credential debt and semantic/V8 gates. Keep a capability table with supported, blocked and excluded rows. Required blocked features need fixes owned by the existing phase/component before deployment can claim them.
5. Select framework/component revisions and a DeGram installer with actual hashes, clean-PC prerequisites and scope-specific acceptance. Do not assume the most recent installer has been tested just because it was built.
6. Define the deployment file/image allowlist. Do not ship `.git` history, manuscript folders, vault content, `.secrets/`, personal Hermes profiles or the full development workspace. Explicitly list necessary runtime fixtures/ontology/tools.

**Done when:** a versioned release candidate and capability/debt matrix exist; no unresolved critical issue affects the claimed pilot slice. Hosting alone does not close DGBN-01 or DGCL acceptance.

### P06 — Approve data, secrets and recovery design

1. Prefer new sanitized pilot data; decide whether any existing project will instead be migrated. Get source-owner approval for each data set and external LLM export policy.
2. Choose backup destination outside this PC, institutional access controls, encryption, retention, quota and restore target. Proposed retention: seven daily and four weekly restore sets, pending size and IT approval. Local copies are not the off-machine backup.
3. Plan consistent backups for Neo4j, PostgreSQL, MinIO, n8n volume/credentials key and `data-service/data`. Identify all configuration and encryption keys needed to restore, including `LLM_MASTER_SECRET`. Neo4j Community dump may require database downtime; plan a bounded quiesced backup window rather than assume Enterprise online backup.
4. Decide whether to regenerate test accounts/pairings or preserve approved ones. Restoring encrypted settings requires original decryption material or deliberate re-encryption; replacing a DB environment password alone does not rotate an initialized database account.
5. Define owners for backup failures, low disk, certificate expiry, OS updates and outages, plus an emergency way to close external access.

**Done when:** owner/IT approve data selection, secure secret handling, backup location, recovery targets and rollback method. Secret values stay out of the plan, evidence and chat.

### P07 — Install Linux (destructive human checkpoint)

**Stop before erasing anything:** P03 backup recovery checked + P04 reimage/network permission + P06 data/recovery design + explicit owner approval of the exact PC/disk.

1. Verify installer origin/checksum using official Ubuntu instructions at execution time. Install Ubuntu Server 24.04 LTS x86-64 unless IT requires another supported distribution; document deviations and Docker compatibility.
2. Use an approved dedicated disk layout, hostname and administrator account. Decide encryption and unattended-reboot unlock policy with IT before selecting it.
3. Configure assigned networking or DHCP reservation from P04, wired Ethernet and approved time/DNS. Disable sleep/hibernation and enable approved power-loss recovery.
4. Keep internet application ingress closed. Retain local console/recovery access.

**Done when:** Linux boots, inventory matches P03, admin can recover locally, network settings match IT allocation, and Windows recovery material remains available.

### P08 — Harden host and prepare runtime

1. Apply OS updates, set administrator SSH keys and verify a second session before disabling password/root SSH login. Restrict administration to approved VPN/source addresses.
2. Install Docker Engine and Compose plugin using current official instructions for the chosen distro; do not use Docker Desktop. Verify Compose supports the merge/reset features the deployment overlay will use.
3. Configure host firewall and Docker network rules together. Published Docker ports may bypass ordinary UFW expectations: rely on safe bind addresses, approved edge controls and explicit Docker-aware filtering, then verify from another machine. Never assume `ufw status` proves container isolation.
4. Set approved Docker address pools to avoid campus/VPN conflicts. Decide whether TLS termination runs on the host or university edge; a host proxy can forward to loopback app ports, whereas an edge proxy needs source-restricted reachability to the lab ingress.
5. Configure automatic security updates, supervised reboot window, disk/log limits and monitoring notifications. Docker-group access is effectively root-level; grant narrowly.

**Done when:** management access works only through the approved route; runtime works; externally reachable ports match policy; no application is publicly exposed yet.

### P09 — Build and privately verify the deployment package

May run on an isolated test machine while P07/P08 run. Do not restart the owner's existing stack. Implement only after scoped authorization and load relevant development/test skills.

Proposed host-neutral Phase 1309 paths (not created by this planning task):
- `docker-compose.hosted.yml` — layer AFTER base and multi-user overrides, without active Ollama/GPU.
- `deploy/hosted/README.md` — topology-specific installation, startup, upgrade and rollback commands.
- `deploy/hosted/Caddyfile` — only if host Caddy is selected; institutional TLS may use different configuration.
- `tools/security/tests/test_hosted_deployment.py` — merged-config/policy tests.
- `deploy/hosted/backup-restore.md` — tested consistency/restore procedure.

The university branch consumes the Phase 1309 release manifest and adds only approved campus-specific network/TLS details. Do not create a separate competing university Compose authority.

Existing paths likely to need scoped changes: `docker-compose.yml`, `docker-compose.multi-user.yml`, `ui-v2/nginx.conf`/entrypoint if real-proxy changes need it, `spec/SECURITY-BOUNDARY.md`, relevant Compose/security tests, and `docs/degram/CLEAN-INSTALL.md` for confirmed deployment instructions. Preserve local development behavior. Child source changes, if required, use `apps/degram/...` paths with component ownership and separate authorization.

Implementation checklist:
1. Add failing tests for the production merge: no active GPU/Ollama dependency; multi-user + invite-only; secure cookies; intended app bindings; exactly one data-service worker; no broad/private repo mount; deterministic image versions and no plaintext-secret output.
2. Remove/profile optional Ollama safely and remove its n8n dependency in the final merged model. Validate actual merged services; simply not calling Ollama is insufficient.
3. Pin a compatible set of Speckle/MinIO images and build release images reproducibly. Document component digests and allowlisted runtime mounts.
4. Configure actual DG, Speckle frontend/canonical and any S3 public origins. Preserve internal Docker URLs. Resolve browser upload/presigned S3 URL requirements; if needed provide an approved TLS object endpoint with strict policy, never the MinIO console. If direct Speckle upload is excluded, explicitly exclude and test the chosen publication path.
5. Keep 8080/8090 loopback-only with a host proxy, or private and restricted to the institution's proxy address when edge topology requires it. Do not concatenate new ports while retaining old all-interface entries; use supported Compose reset/override semantics.
6. Configure proxy trusted source addresses narrowly, secure cookie propagation, forwarded scheme/client IP handling, streaming/cancellation, upload limits and TLS certificate persistence. Do not wildcard trust every proxy or cache authenticated model payloads publicly.
7. Add measured memory/concurrency controls, startup retries/health dependencies and restart behavior. Preserve one-process file-store safety. Review Speckle bootstrap SQL as configuration for unsafe seed accounts/project visibility before using it in a new installation; do not publish secrets in the review output.
8. Use test-only secrets for offline validation. Review `docker compose ... config` privately or use `config --quiet`/a sanitized parser; resolved Compose output can reveal actual secrets.
9. Run relevant existing security/Compose/config.js/delegation/proxy tests plus the new tests in the established isolated environment. Check the updated normative port policy agrees with the merged deployment; existing two-profile tests do not automatically cover the new overlay.
10. Produce a minimal private tracer deployment: authenticated DG login + permitted project read + model load; validate with temporary TLS/networking appropriate to staging. Verify rollback to the previous staging release before expanding.

**Done when:** tests and a private Linux runtime probe pass; deployment documentation and immutable release manifest exist; owner reviews the actual security boundary. Files are not committed/pushed unless authorized. This is not public release acceptance.

### P10 — Deploy privately on the lab server

1. Transfer the allowlisted release and approved fixture data securely. Create restricted server storage/secrets without printing values. Use `.env.example` as a list of names, not usable defaults. Prefer fresh pilot secrets; follow the rotation/re-encryption runbook if migrating existing stores.
2. Use the exact P09/Phase 1309 documented three-layer Compose invocation; no standalone base `docker compose up` on the server. An example structure, valid only AFTER Phase 1309 has created/tested the new file:
   `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml -f docker-compose.hosted.yml up -d`
3. Initialize accounts/DB/schema/workflows in the tested order. Verify n8n workflows are active/published, not merely imported. Resolve bootstrap tokens and privacy before model testing.
4. Keep reviewer ingress disabled or source-restricted. Check service health, invite-only auth, permissions, permitted remote-model path (without an actual paid call until separately authorized) and actual image/config versions.
5. Configure system LLM settings and per-project export permission only after consent. Paid test calls require a separate small bounded authorization. Verify a denied request incurs no upstream call before testing an allowed one.

**Done when:** all required private pilot functions run on this Linux host, no missing public-origin dependency remains, no GPU is required, and readiness evidence is recorded.

### P11 — Restore, reboot and capacity proof

1. Run the real backup procedure and check encrypted copies are present off-machine with integrity metadata.
2. Restore into an isolated clean target, not over the only working instance. Prevent restored n8n/cron/webhooks or copied tokens from sending external requests during the test. Confirm representative graph/rule/model/account state and settings decrypt correctly.
3. Reboot the lab server in an agreed test window. Prove automatic service recovery, certificate persistence, clean startup order, and intact data. Verify chosen disk-encryption policy permits intended recovery.
4. Run the agreed concurrent workload; capture memory/disk/CPU, worker failures, latency and provider usage. No invented response-time or minimum-memory claims. If limits fail, tune, upgrade or reduce scope with owner approval, then rerun.
5. Record actual data-loss window and restore duration against P01/P06 targets. Configure and test alerts for backup failure and disk capacity.

**Done when:** restore and reboot actually pass and the agreed pilot load is sustainable. Failed recovery blocks P15 even if the website works.

### P12 — Restricted external HTTPS test path

1. IT activates the staged route for the tester/VPN cohort, not all reviewers. Confirm DNS, TLS chain, hostname, renewal ownership, reachability and NAT hairpin/split-DNS behavior as applicable.
2. If public ACME validation is needed, expose only the necessary validation/proxy endpoint; never temporarily expose the whole application unauthenticated to get a certificate.
3. Test from an approved off-campus client. Check port reachability only for the assigned host and approved scope; do not scan the campus network.
4. Check IPv4 and enabled IPv6 for bypass paths; unauthorized access to 8080/8090, databases, admin services and local CAD bridges must fail according to the topology.

**Done when:** an external tester reaches the intended HTTPS site with valid trust, administration remains restricted, and no alternative app/DB path bypasses policy.

### P13 — Browser and security acceptance

1. Use two isolated projects and distinct non-admin users. Prove unauthenticated access is rejected, self-registration is off, a reviewer sees only their project, and tampered project/object URLs do not reveal the other project's graph or Speckle geometry.
2. Verify model loading and any claimed upload/publication path end-to-end; check browser requests for localhost URLs, mixed content and leaked credentials. Owner-only settings must be inaccessible to reviewers.
3. Verify logout/membership removal stops new protected reads. Record expected vs actual errors without logging raw tokens, cookies or model API keys.
4. Run the repository checker on the server using the deployed URLs and the installed test environment. Existing supported flags were verified in `tools/security/check_live_boundary.py`:
   `python tools/security/check_live_boundary.py --profile multi-user --ui-url https://DG_HOST --data-service-url http://127.0.0.1:8000 --host 127.0.0.1 --json-out CHECK_REPORT_PATH`
   Replace placeholders only with P04 values. This assumes the chosen deployment retains the local data-service binding; adapt to the tested network if not. This checker covers only selected routes and refused ports; it does NOT replace external exposure, tenancy or restore tests.
5. Recheck exposure separately from the approved off-campus client and behind any institutional auth gateway. A university login page masking an API failure is not a passing application test.

**Done when:** agreed browser functions and negative security cases pass with reproducible evidence. Any cross-project leak or auth bypass blocks opening and closes staged ingress until fixed.

### P14 — External DeGram acceptance

1. On a separate supported Windows PC, verify the selected installer hash and clean-install prerequisites. No personal Hermes profile may be changed. Confirm the remote origin and the actual installed client version.
2. Point DeGram to `https://DG_HOST` using the supported origin setting; sign in and pair as the same permitted user. Keep pairing/token values out of screenshots/logs.
3. Select an authorized project; read rules/graph and open the reused model viewer. Verify forbidden project access is denied.
4. Test LLM export denied/allowed paths, streaming, cancel, provider/server failure, reconnect, token renewal, and pairing/member revocation. Budget/provider outages are operational failures, not compliance verdicts.
5. For claimed native reads only: install the approved Revit/Rhino components and test local document selection, busy/off states and context isolation. Keep loopback bridges on the client. The university server must not call an unauthenticated public client listener. Do not treat direct-Bolt GH authoring as supported unless its HTTP capability gate has independently passed.
6. Record this pilot evidence under existing phase ownership. It does not mark all Phase 1307 or all DGCL IDs complete automatically.

**Done when:** every DeGram feature promised in P01 works on the remote PC; excluded native/write features are visible in reviewer instructions, not hidden failures.

### P15 — Go/no-go checkpoint

Owner and IT review all evidence from P11/P13/P14 and relevant security/release gates. Confirm:
- Accepted scope, data/export policy, patched release versions and expected reviewer load.
- Working backup alerts, actual restore, reboot recovery, monitoring, certificate renewal and responsible contacts.
- No unresolved critical security/tenancy issue; limitations and any noncritical accepted debt named explicitly.
- Clean rollback/emergency network closure procedure and release/data recovery points available.
- Pilot access period, invitation method, approved role assignments and maintenance schedule.

**Done when:** both owner and IT explicitly permit the defined external pilot. Silence, successful `compose up`, or a model-generated PASS is not approval. If approval is declined, keep staging private and record the blocking task.

### P16 — Open and operate the invited pilot

1. Open the approved reviewer path; retain DG authentication and project memberships. Only send invitations after P15; use the approved communication channel.
2. Give reviewers the HTTPS URL, supported feature scope, DeGram installer/hash/origin instructions if needed, and support contact. Do not send infrastructure credentials or model keys.
3. Conduct one actual reviewer session, confirm functioning access and check resource/backup alerts.
4. Record deployed versions, access expiry and next maintenance/recovery-test dates. Keep framework planning ownership intact and capture a vault session/handoff when requested.
5. At pilot end, revoke accounts/pairings as agreed, close unneeded ingress and follow retention/deletion policy.

**Done when:** approved reviewers have successfully used the declared functions, operational ownership is active and evidence is filed. Broader product release remains subject to its existing phase gates.

## 5. Stop rules and rollback

- No erase before the P07 checkpoint; keep Windows recovery outside the target disk.
- No application public opening before P15. Restricted external testing at P12 is separately approved and is not a general launch.
- No public Bolt/n8n/MinIO console/CAD listeners or Docker socket at any stage.
- No blind rsync/copy of live database directories; use version-compatible dumps or documented quiesced snapshots.
- No `docker compose down -v`, schema migration, credential rotation or restore over source data without explicit scope/backup approval.
- A security incident triggers IT's incident protocol and disables external ingress first; preserve necessary evidence securely.
- For failed upgrades: stop writes, preserve failure evidence/current data, restore the verified compatible release and data set, then rerun smoke tests. Application rollback alone may not undo DB migrations.
- University refusal is a topology/hosting decision, not a reason to bypass its controls. Approved VPS remains an alternative, not an automatic purchase.

## 6. Evidence and recording convention

For future execution, create supporting evidence under `.planning/research/university-lab-deployment/` (proposed; not created now), with one sanitized `Pxx` note per task and append-only actual test results. Keep this plan's progress table updated. Never store passwords, raw tokens, recovery keys, private IP inventories not needed for the project, or university confidential documents in a public repo. Sensitive IT ticket/secret data stays in approved institutional storage; reference it by handle.

Task completion record template:
- ID, date, executor, exact target host/release (sanitized where necessary).
- Prerequisites checked and authorization reference.
- Actions actually performed and changes made.
- Expected vs observed result, commands/tests and evidence links.
- Status: DONE / BLOCKED / IN PROGRESS, with named blockers.
- Next dependency-ready tasks; rollback state.

## 7. Next-session entry point

**Start with P01, P02 and P03 only.** No hardware or university connectivity facts have been collected yet. You can send the IT request and collect inventory while software readiness is assessed; do not wipe Windows or buy hardware first.

Bring back:
- Lab PC CPU model, RAM and SSD/free-space details (not serial numbers or credentials).
- Whether the machine can be dedicated continuously and reimaged; backup status.
- University IT contact/ticket and any answer about public HTTPS, VPN, DNS, TLS and Docker.
- Expected reviewers/concurrency and the exact desired DeGram/native feature scope.

Paste this to resume:

> Continue `.planning/UNIVERSITY-LAB-DEPLOYMENT-PLAN.md`. This is the university lab PC deployment, not the developer workstation. Re-read project rules, current phase/vault state and rerun the DeGram preflight. Review P01/P02/P03 first, ask for missing lab/IT facts, record prerequisite evidence and identify only dependency-ready work. Do not erase disks, install software, change services/firewalls, transmit data, spend on LLMs, commit/push or open public access without the corresponding explicit approval. Keep the plan updated and do not infer completion from the previous chat.

## 8. Plan validation (authoring-time only)

Dependencies and task IDs will be checked mechanically for uniqueness, missing references and cycles. That check verifies the plan's structure only. All live deployment tasks remain unexecuted. No new GSD phase or authoritative roadmap is created; no project source or existing planning state is changed by this plan-only task.

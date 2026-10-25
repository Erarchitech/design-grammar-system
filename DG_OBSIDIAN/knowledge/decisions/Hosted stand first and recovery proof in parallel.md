---
tags: [decisions, phase1309, hosting, deployment]
date: 2026-10-25
---

# Hosted stand first; full multi-store recovery proof in parallel on the server

**Decision (owner, 2026-10-25):** Phase 1309 no longer gates every deployment behind a hash-exact offline recovery proof. A private stand with **test data only** is deployed first; the interim backup is the already-proven two-store v3 subset plus provider disk snapshots; the full six-store recovery proof (HOST-04) is done afterwards on the server itself.

**Why:** the phase had run almost a month. Every native check cost a round trip (prepare a package, owner runs it by hand on `DESKTOP-OS4Q8CP`, owner sends a report) because Docker is forbidden on the development PC, and each change also went through independent review cycles. The real critical path (choose and buy a server, first Linux run) had not started, and the first real run found five defects that offline work could not have found ([[knowledge/debugging/Fresh-server deployment traps found on the first real Linux run|debugging]]).

**Alternatives considered:**
1. Keep the old order (full recovery proof, then freeze, then deploy). Rejected by the owner: months of delay, no multi-user feedback.
2. Owner runs scripts on the server and relays output. Rejected for speed; the owner chose a throwaway server with SSH access for the assistant, key created per server and revocable.

**Consequences / limits:**
- Data on the stand is synthetic and reproducible; loss is accepted by the owner. Snapshots (Contabo) are the interim backup.
- The stand is **not a frozen release**: Speckle images use floating tags, MinIO is replaced by `cgr.dev/chainguard/minio:latest`, certificates come from `nip.io` names.
- Plan 1309-04 stays open: producer barrier, real PostgreSQL bounded transport (Go supervisor built by the owner in Docker on the target PC, dump budget = measured size × 1.5), profile admission.
- Not verified: Speckle object upload through the public object origin, reachability from Russia, load, restore.

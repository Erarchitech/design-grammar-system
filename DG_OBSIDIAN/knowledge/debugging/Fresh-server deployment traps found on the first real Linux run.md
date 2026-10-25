---
tags: [debugging, deployment, docker, hosting, phase1309]
date: 2026-10-25
---

# Fresh-server deployment traps found on the first real Linux run

Offline Compose parsing on Windows passed everything below. Only the first real run on a clean Ubuntu 24.04 VPS (Contabo, 2026-10-24/25) exposed them. All are now covered by tests in `deploy/hosted/tests/test_server_kit.py` or fixed in `deploy/hosted/server/`.

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose up` stops: `pull access denied for minio/minio`, every other pull `Interrupted` | Official MinIO images are no longer pullable from Docker Hub (nor `quay.io/minio/minio:latest`) | `docker-compose.server.yml` sets `speckle-minio` to `cgr.dev/chainguard/minio:latest` (uid 65532, `/data` world-writable in the image). Newer MinIO than the owner's PC; Speckle only needs S3 |
| (predicted from code, not run) first PostgreSQL init fails, later restarts skip init scripts so the bootstrap silently never applies | `speckle/bootstrap-local.sql` is mounted into `docker-entrypoint-initdb.d` and inserts into Speckle tables that do not exist on an empty database | Not mounted by the server overlay; `deploy.sh` applies it after the schema and the apps `spklwebapp`, `explorer` exist (idempotent) |
| `bootstrap-server.sh` exits 141 right after Docker starts, firewall never enabled | `sshd -T \| awk '...{print; exit}'` under `set -euo pipefail`: awk exits early, sshd gets SIGPIPE, pipeline fails | awk reads to EOF; test forbids early-exiting readers after a pipe |
| `n8n update:workflow ... not found` | Command deprecated in n8n 2.4.8; one file already carried its own `id`, the script assumed the file name | `publish:workflow --id=<id from the file>`; restart n8n once afterwards (it runs the published version) |
| LLM test answers `No API key configured` although `apiKeyConfigured: true` | `resolve_active_provider` needs provider **and model** and key; the panel had saved `model: null` | `PUT /llm/settings {"model": "..."}` keeps the stored key; set the model in the panel |
| Contabo reinstall dialog has no SSH-key field | Key must be added by hand after password login (`~/.ssh/authorized_keys`) | Procedure in the session note |
| (risk, fixed pre-emptively) services without `restart:` stay down after a reboot; Caddy's static `.2` could be taken by a container started earlier | Base compose only restarts Speckle services; Docker allocates dynamic addresses from the start of the subnet | `restart: unless-stopped` for all 15 services; `ip_range` in the upper half of the edge subnet |

**Also learned:** the DG API requires header `X-DG-CSRF: 1` on state-changing calls (including login); `/llm/settings` writes are admin-only, so only the bootstrap admin can set the key; self-registration is off, new users come by invite code (72 h, shown once).

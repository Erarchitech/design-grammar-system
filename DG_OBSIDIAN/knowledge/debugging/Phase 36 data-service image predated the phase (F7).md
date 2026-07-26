---
tags: [debugging, deployment, docker, phase-36]
date: 2026-07-25
status: fixed
---

# F7 — data-service container had never been rebuilt since before Phase 36 shipped

**Context:** v9.0-PIPELINE-UAT Group 4.5. First `DG COMPUTGRAPH PUBLISH` attempt returned:

```
Computgraph publish failed (404): {"detail":"Not Found"}
```

## Root cause

The running `data-service` container's `/openapi.json` listed `/computgraph/context/pull` (Phase 33) and `/computgraph/recognize` (Phase 35) but **not `/computgraph/publish`** (Phase 36). `data-service` builds via `build: ./data-service` with no source bind-mount, so `app.py` is baked into the image at build time — a code change on disk does nothing to a running container until it's rebuilt.

Phase 36 had shipped "code complete" with `36-VERIFICATION.md` written and all unit tests green, but the live stack had never once run `docker compose build data-service` since. **No Phase 36 endpoint had executed outside unit tests before this session.**

## Fix

```powershell
docker compose build data-service
docker compose up -d data-service
```

Confirmed via `/openapi.json` that `/computgraph/publish` was now present. LLM settings persisted through the rebuild (survives because they're stored in `data-service/data/`, a volume-mounted path, not baked into the image).

## Takeaway

After any phase that adds a data-service route, rebuild the container **before** starting UAT — don't trust `*-VERIFICATION.md` "code complete" as a deployment claim. This is the data-service analog of the existing [[Docker layer caching can serve stale index.html]] gotcha for the UI container.

## Related

- `.planning/phases/36-computgraph-persistence-display/36-UAT.md`

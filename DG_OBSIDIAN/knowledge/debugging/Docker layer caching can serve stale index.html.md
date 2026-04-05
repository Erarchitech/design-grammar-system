---
tags: [debugging, docker, caching]
date: 2026-04-05
---

# Docker Layer Caching Can Serve Stale index.html

## Problem

After editing `graph-viewer/index.html`, running `docker compose up -d design-grammars` without `--no-cache` may serve the old version because Docker's build cache reuses the COPY layer.

## Symptoms

- UI changes don't appear after rebuild
- Old components or styling visible
- New features missing

## Solution

Always rebuild with `--no-cache`:

```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```

Then force-refresh in browser: **Ctrl+Shift+R** or use incognito mode.

## Root Cause

The `Dockerfile` COPY layer hash is based on file content. If Docker's build context hasn't changed from its perspective (e.g., editor hasn't flushed, or the change is to an intermediate artifact), the cached layer is reused.

## Related

- [[Browser cache prevents seeing UI updates after rebuild]]
- [[Deployment uses Docker Compose with nginx reverse proxy]]

---
tags: [debugging, browser, cache]
date: 2026-04-05
---

# Browser Cache Prevents Seeing UI Updates After Rebuild

## Problem

Even after a successful Docker rebuild, the browser may show the old UI due to aggressive caching.

## Symptoms

- Docker rebuild completes, container restarts, but old UI appears
- New components/styles not visible
- `config.js` still has old values

## Solutions

1. **Hard refresh**: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. **Incognito/private window**: bypasses all cache
3. **DevTools**: Network tab → "Disable cache" checkbox (while DevTools open)
4. **Clear site data**: DevTools → Application → Clear storage

## Prevention

Nginx config includes `Cache-Control: no-cache, must-revalidate` for both `/` and `/model-viewer/` routes. However, this doesn't guarantee the browser honors it in all cases.

## Related

- [[Docker layer caching can serve stale index.html]]
- [[Deployment uses Docker Compose with nginx reverse proxy]]

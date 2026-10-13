---
tags: [debugging, docker, ui-v2, deployment]
date: 2026-10-13
status: resolved
---

# docker compose build alone leaves the old design-grammars container running

**Symptom:** after rebuilding Docker, none of the Phase 1308 changes showed in the browser, the RU/EN language dropdown included.

**Cause:** the image `design-grammar-system-design-grammars:latest` had been rebuilt (18:05), but the running `design-grammars` container had been created a day earlier and still ran the previous image. `docker compose build` only builds the image. It does not recreate the container. `data-service` looked current only because an `up` had happened two seconds after its build.

**How it was found:**
- `docker ps` showed the container on an image id other than the `latest` tag.
- The container's `index.html` was dated the day before.
- `grep "Interface language"` over its bundle found nothing, while the new image's bundle contained the string.

**Fix:** `docker compose up -d --no-deps --force-recreate design-grammars`, then a hard refresh (Ctrl+Shift+R).

**Rule:** after building the UI image, always recreate the container:
`docker compose build --no-cache design-grammars && docker compose up -d design-grammars`.

To check what is live, compare `docker ps` (container image and creation time) with `docker images`, and grep the served bundle for a string from the new code.

Related: [[sessions/2026-10-13 SVOD rebrand, ALNST and Tektur design system, drawn landing hero]]

# Phase 1308 — Rollout record (plans 19 and 20)

Live rollout of the committed 1308 code into `data-service` and `design-grammars` (WEBUI-11). Probes use no credentials; this record holds ids, hashes and status codes only.

## D-32 closure (D-45, D-05) — 2026-10-13T22:05Z

Read-only, against the running `data-service` container (image `sha256:f98c3b8e3709…`, untagged, started 2026-10-13T17:03:26Z).

| Check | Command | Result |
|---|---|---|
| `degram_policy.py` in the image | `docker exec data-service sh -c "tr -d '\r' < /app/degram_policy.py \| sha256sum"` | `db7762923c61d6e147ca3d1d188796673ced1a9cb7b9d13cf1843b2bff3762a5` |
| `degram_policy.py` at HEAD `42a9ead` | `git show HEAD:data-service/degram_policy.py \| tr -d '\r' \| sha256sum` | `db7762923c61d6e147ca3d1d188796673ced1a9cb7b9d13cf1843b2bff3762a5` |
| Default policy, unknown project | `docker exec data-service python -c "import degram_policy; print(degram_policy.policy_for_project('zz-1308-probe'))"` | `{'providerExportAllowed': True, 'wholeDefinitionAllowed': False}` |

**Verdict: D-32 closed.** The running image carries the committed `degram_policy.py` byte-for-byte (CR removed), and a project with no stored policy gets the D-05 defaults: provider export allowed, whole-definition export refused.

## Build plan (D-46) — dry run, nothing built or restarted

| Item | Value |
|---|---|
| HEAD at dry run | `42a9ead6ae74a65b35e4d7dc1da1345f0785e8c6` |
| Tree `HEAD:data-service` | `b787ca846efa4c6554b7e38a74c14704e44de710` |
| Tree `HEAD:ui-v2` | `9b2c05e425e3d0fafee1a8f4de22ac29ca5a98d4` |
| Last commit touching the sources | `28fa6f6` (SVOD design session) |
| Export | `git archive HEAD data-service ui-v2 \| tar -x -C C:/dgsrc1308` (new empty directory) |
| Export checks | `data-service/app.py`, `d49_store_cleanup.py`, `connector_session.py`, `Dockerfile`; `ui-v2/package.json`, `Dockerfile` present; `app.py` has 5 × `auth/connector-session`; `ui-v2/src/i18n` has «Свод правил проекта»; `cypher_allowlist.py` and `dg_context.py` in the export hash-equal HEAD, not the working tree |

The tree hashes, not HEAD, gate the build: committing this record moves HEAD without touching `data-service/` or `ui-v2/`.

**Uncommitted files excluded from the images** (`git status --porcelain -- data-service ui-v2`, 8 modified, 4 untracked, 574+/45−; none belongs to a 1308 plan):

```
 M data-service/cypher_allowlist.py
 M data-service/dg_context.py
 M data-service/tests/recognition_eval/repeat_sweep.py
 M data-service/tests/recognition_eval/report.py
 M data-service/tests/recognition_eval/test_provenance.py
 M data-service/tests/recognition_eval/test_repeat_sweep.py
 M data-service/tests/test_validation_run_immutability.py
 M ui-v2/tests/evidence/degram-verified.json
?? data-service/tests/test_ingest_atom_structure.py
?? data-service/tests/test_rule_conflict.py
?? ui-v2/tests/evidence/degram-commit-preflight.json
?? ui-v2/tests/evidence/degram-latest.json
```

**Containers before the rollout** (`docker inspect`; must be unchanged by this dry run):

| Container | Running image | Started (UTC) | Note |
|---|---|---|---|
| `data-service` | `sha256:f98c3b8e3709…` | 2026-10-13T17:03:26Z | untagged; the tag `design-grammar-system-data-service` points to `37e0b37a88ce` (built ~17:10Z, never deployed, provenance unrecorded) |
| `design-grammars` | `sha256:64cc2d37dcd4…` | 2026-10-13T20:09:29Z | equals the current tag; built during the SVOD session, provenance (export or working tree) unrecorded |
| `neo4j` | `sha256:5db2969455f4…` | 2026-10-13T14:04:16Z | running — no start needed |

Compose: `data-service` has `build: ./data-service`, `design-grammars` has `build: ./ui-v2`, no `image:` override; `docker compose config --images` resolves to the two tags below. The data-service Dockerfile copies the whole context (`COPY . .`), so `tests/` from HEAD ship in the image for the in-container suite.

**Commands to run after "rebuild ok"** (Git Bash, repo root):

```bash
# 0. gate: trees must still equal the approved ones
test "$(git rev-parse HEAD:data-service)" = b787ca846efa4c6554b7e38a74c14704e44de710
test "$(git rev-parse HEAD:ui-v2)"        = 9b2c05e425e3d0fafee1a8f4de22ac29ca5a98d4
# 1. build from the export only
docker build --no-cache -t design-grammar-system-data-service   C:/dgsrc1308/data-service
docker build --no-cache -t design-grammar-system-design-grammars C:/dgsrc1308/ui-v2
# 2. recreate only these two containers (neo4j already running)
docker compose up -d --no-build --no-deps data-service design-grammars
# 3. image-id equality and stale-image checks
docker inspect -f '{{.Name}} {{.Image}}' data-service design-grammars
MSYS_NO_PATHCONV=1 docker exec data-service grep -c "auth/connector-session" /app/app.py
#    served JS bundle on :8080 contains «Свод правил проекта»
# 4. unauthenticated probes (127.0.0.1:8000 and :8080/data-service) → 401 AUTH_REQUIRED
#    POST /auth/connector-session, GET /projects/x/summary, PUT /projects/x/members/u; GET :8080/ → 200
# 5. MSYS_NO_PATHCONV=1 docker exec data-service python -m pytest tests -q   (baseline: 1130 pass + 13 env failures, plus new 1308 tests)
```

Expected downtime: `data-service` and the UI on `:8080` restart, roughly 10–30 s each. No other service, volume, data or configuration is touched.

## Approval

_Pending — owner reply "rebuild ok"._

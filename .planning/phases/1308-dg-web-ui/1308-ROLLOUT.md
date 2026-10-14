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

Owner reply 2026-10-13 ~22:26Z: **"rebuild ok"** (plan as written above, no changes).

## Build (D-46) — 2026-10-13T22:26Z → 22:28Z

Gate at the start: `git rev-parse HEAD:data-service HEAD:ui-v2` = `b787ca84…` / `9b2c05e4…`, equal to the Build plan (HEAD had moved to `26fa79f`, the commit of this record only).

| Image | Built from | New image id | Container image id after `compose up --no-build --no-deps` | Started (UTC) |
|---|---|---|---|---|
| `design-grammar-system-data-service` | `C:/dgsrc1308/data-service` | `sha256:c1e018ee32566329483284e93508bbe167435228f80c830a42b311f18576d1e5` | same | 22:28:06Z |
| `design-grammar-system-design-grammars` | `C:/dgsrc1308/ui-v2` | `sha256:3b790ebbb5a19f8b50f46b630c1ccc1a41c9bd272c8c616ba51b22d2e2c19445` | same | 22:28:06Z |

`neo4j` was running throughout (start time unchanged, 14:04:16Z); no other container was touched.

**Stale-image checks.** `docker exec data-service grep -c "auth/connector-session" /app/app.py` = 5. The served UI chunk `/assets/PropertiesTable-DmQGXmWU.js` (HTTP 200) contains «Свод правил проекта» once; no served JS asset contains «Грамматика.». The entry `index-DJyq5RIH.js` does not hold the string (it lives in the lazily loaded i18n chunk).

## Probes (no credentials)

| Request | `127.0.0.1:8000` | `127.0.0.1:8080/data-service` |
|---|---|---|
| `POST /auth/connector-session` | 401 `AUTH_REQUIRED` | 401 `AUTH_REQUIRED` |
| `GET /projects/x/summary` | 401 `AUTH_REQUIRED` | 401 `AUTH_REQUIRED` |
| `PUT /projects/x/members/u` | 401 `AUTH_REQUIRED` | 401 `AUTH_REQUIRED` |
| `GET /` (UI on `:8080`) | — | 200 |

## Test baseline (in-container)

`docker exec data-service python -m pytest tests -q --continue-on-collection-errors` (a plain run stops at collection on `test_freeze_rule_ingest_prompts.py`, which reads the unmounted `/fixtures/golden/fixture.json`):

**13 failed, 5249 passed, 53 skipped, 8 deselected, 296 errors** in 184 s.

- **13 failed — all environmental, the known 13** (repo-root files not in the image): `test_cq3_attribute_of.py` ×10 (`/fixtures/golden/cq3-attribute-of/…`), `test_degram_relay.py` ×2 (`/spec/degram/OPERATIONAL-OUTCOMES.md`), `recognition_eval/test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields` (`/tools/de01/report_schema.json`).
- **296 errors — all environmental:** 295 setup errors `FileNotFoundError: 'dotnet'` in `test_evidence_raw_admission.py` (114), `test_gh_publish_wire.py` (71), `test_evidence_versions.py` (60), `test_evidence_unicode_containers.py` (50) — these tests drive the C# factory and need a .NET SDK, which the data-service image has never contained (Dockerfile unchanged since 2026-07-26; the tests were added 2026-09-30); plus 1 collection error (`/fixtures/golden/fixture.json`).
- The pass count outgrew the recorded baseline (1130) because the suite has grown since it was recorded; the rule "every failure is environmental" holds.
- **1308 test files** (28 files named in the 1308 plans and summaries, incl. `test_connector_session*.py`, `test_project_summary.py`, `test_member_roles.py`, `test_d49_store_cleanup.py`): **3234 passed, 3 skipped, 2 failed** — the two `test_degram_relay.py` environmental failures above.

**No regression.** Running stack = committed HEAD sources; the uncommitted files listed in the Build plan are not in either image.

## Cleanup dry run (D-47, plan 20) — 2026-10-13T22:39Z

**Backup (before any write).** All 19 `data-service/data/*.json` stores copied with `cp -p` to `C:/dgbackup1308/20261013T223918Z/` (outside the repository, not committed). Verified: 19 files in source and backup, `sha256sum -c` over all 19 equal; the checksum list is kept beside the copy as `SHA256SUMS.txt` (list digest `e612f12fe976dcb0…`). The container sees the same 19 files at `DG_DATA_DIR=/app/data` (bind mount). Inventory change since plan time: `connector-access.json` now exists (330 bytes).

**Neo4j (read-only, READ session through the data-service driver):** `MATCH (n) WHERE n.project = 'uat-pw-bd30ce' RETURN count(n)` → **0**.

**Script dry run** (reads only). The agent's `docker exec` was refused by the auto-mode classifier; the owner ran it from PowerShell (`docker exec data-service python d49_store_cleanup.py`) on 2026-10-14 and pasted the output:

| Store / item | Planned change |
|---|---|
| `credentials_to_retire` | **13** (get `revoked: true`, `revoked_at`, `retired: "D-49"`) |
| `credentials_already_revoked` | 11 (left byte-identical) |
| `users` | 1 (UAT user) |
| `memberships` | 1 (UAT user in UAT project) |
| `pairings` | 1 (retired pairing of the UAT user) |
| `connector_access_grants`, `connector_access_requests`, `connector_sessions`, `degram_grant_requests`, `degram_grants`, `delegated_tokens`, `export_policies`, `invites`, `project_companies`, `sessions` | 0 each |

Status `dry-run-ok`, exit 0. Against the plan-time inventory (22 credentials, 11 active): 24 credentials, 13 active — two connector credentials were issued since 2026-10-12 and are retired too (D-49 retires every `dgc_` credential). The UAT rows (1 user, 1 membership, 1 pairing) match the inventory; no other user or project is touched.

## Approval (cleanup)

The owner asked why the cleanup is needed and whether projects, graphs and validation runs survive (answer: the script reads and writes only the JSON stores, never Neo4j; targets are hard-coded to the UAT user and project; credentials are marked, not deleted), then ran `--apply` themselves from PowerShell on 2026-10-14 and pasted the output. That run is the approval of record (the agent's `docker exec` was refused by the auto-mode classifier, so it could not run the apply).

## Cleanup apply (D-47) — 2026-10-14, owner-run

Procedure (owner, PowerShell, repo root): `docker compose stop data-service` → `docker compose run --rm --no-deps data-service python d49_store_cleanup.py --apply` → `docker compose start data-service`. Output identical in counts to the dry run (13 credentials retired, 11 already revoked, 1 user, 1 membership, 1 pairing, every other store 0), status **`applied`**, exit 0. `data-service` restarted at 2026-10-14T08:13:39Z on the same image `sha256:c1e018ee…`; no `data-service-run` container left behind; `POST :8080/data-service/auth/connector-session` without credentials → 401.

**Verification (agent, read-only, from the host bind mount; only counts and field names printed):**

| Check | Result |
|---|---|
| `connector-credentials.json` | 24 records, **0 active**, 13 carry `retired: "D-49"` |
| Any store mentioning `uat-pw-bd30ce@dg.local` or `uat-pw-bd30ce` | **none** (all 19 files scanned) |
| `auth-users.json` | 2 users remain (was 3) |
| Neo4j nodes with `project = 'uat-pw-bd30ce'` | 0 (before the apply; the script never contacts Neo4j) |

Diff against the backup, by record: `auth-users` −1, `auth-memberships` −1, `degram-pairings` −1 (the script's removals), `connector-credentials` 13 marked (the script). Three other stores differ only by normal service activity between the backup (22:39Z) and the apply, not by the script: `auth-sessions` (`last_seen_at` on 1 row), `degram-grants` (`last_used` on 1 row), `auth-delegated-tokens` (newly issued delegated tokens: `issued_at`/`expires_at`/`token_hash`). No foreign row was removed.

**Post-apply script dry run** (expected `nothing-to-do`): the host-side checks above show the condition it tests (no active credential, no UAT row); the owner ran the script (`docker exec data-service python d49_store_cleanup.py`) on 2026-10-14 and confirmed `nothing-to-do` (UAT test 8, "pass").

Rollback, if ever needed: stop `data-service`, copy the 19 files back from `C:/dgbackup1308/20261013T223918Z/`, start it (note that this would also revert the later session activity listed above).

## Owner actions (D-48)

1. **Connector access for the editor.** On the Connectors screen of project `degram-uat-c`, grant connector access to editor `asiyagerey94@gmail.com` for each connector she uses (editors and viewers need a per-connector grant; owner and DG admin are exempt — D-04).
2. **Grasshopper plugin.** Rebuild (`dotnet build .\DG\DG.sln -c Release`) and install the add-in; re-wire canvases per `docs/RELEASE-NOTES-v13.0.md`. Old `dgc_` tokens no longer work anywhere (D-26): CONNECTOR signs in with Username/Password.
3. **Add-in live check (WEBUI-08, backstop):** CONNECTOR with Username/Password and Connect=true signs in; VALIDATOR publishes with `CONNECTOR.Session`; the Connectors screen shows «Вкл» for Grasshopper; Connect=false turns it to «Выкл».
4. **RU visual pass (backstop):** with RU selected, the landing (incl. summaries) and every screen read in Russian at 1280 px and 1920 px, light and dark, with no overlapping or clipped labels.

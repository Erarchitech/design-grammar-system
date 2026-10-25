---
tags: [session, phase-1309, degram, git, pending-review]
date: 2026-10-25
model: claude-opus-5-5
---

# Stand update and milestone13 consolidation

## Owner decisions

- Development continues on localhost; the hosted test stand is updated only on request. DeGram must support both targets; implementation has NOT started.
- Merge the existing hosting branch and this session's packer fix into master; do not include unrelated dirty files.
- Publish the four DeGram mapping commits as `degram/milestone13`, update the framework gitlink, continue framework work in the main folder on `gsd/milestone13`.
- Back up before reorganizing dirty work. Track only the current graphify graph, not its cache; ignore `evidence/public-*`.
- Commit Phase 1309 as-is on `gsd/milestone13`, without declaring completion. Commit CLAUDE.md and AGENTS.md. Review provenance of old source/tests/specs; owner acceptance remains deferred.
- Revit MCP child commit/push requested, but inspection established there was NO content change to commit.

Related: [[knowledge/decisions/DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls]], [[knowledge/decisions/Milestone13 cleanup preserves pending source changes and excludes generated evidence]].

## Hosted stand — completed earlier in this session

After the owner confirmed a new Contabo snapshot, deployed exact clean mapping revision `2447295dfe004cd3e603f4d99c1eb42245de4dec` with the server-kit overlay to `/opt/dg` on the authorized disposable Contabo test VPS. `/opt/dg/.env` preserved; no local Docker deployment.

- Archive: `C:/dgx/dg-stand-2447295.tar.gz`, server `/root/dg-stand-2447295.tar.gz`.
- SHA256: `d8f242ab9da432da6f95980e6caf13486b4bfd3aea8afa9caa4eb0e63fb647ab`.
- 216 source files plus PACK-INFO. Server log `/root/deploy-2447295.log`; deployment exit 0, 15 containers running.
- DG origin `https://dg.173-249-46-99.nip.io`: 200; Speckle origin: 302; objects root: 404.
- External checks: 22/80/443 open; 3000/5678/7474/7687/8000/8080/8090/9000 closed. This was not an exhaustive port scan.
- Isolation and revocation checks passed after using a fresh tester. Temporary tester memberships revoked. Existing-account invitation is not rerunnable by the current check script.
- Saved LLM configuration diagnostic succeeded. Diagnostic currently prints masked key previews; do not repeat these values, filter that field on future runs.
- Mapping profiles/sessions/calculators/candidates returned 200 authenticated on an empty test project, 401 unauthenticated where checked. `/mapping/health` does not exist.
- n8n workflow definitions did not change across the deployed revisions; no reimport.
- No live CAD mapping E2E on the stand, real n8n LLM ingest, Speckle object upload, Russia reachability, load or full recovery proof claimed.

Packer omission fixed in `a22f6b7`: include `data-service/property_calculators/catalogue.json` and direct-child `*.py.tmpl` through optional patterns. Red/green regression test excludes unrelated notes and nested secret-shaped paths. Independent review found the narrow fix sound; optional matching does not guarantee dependency completeness on arbitrary future inputs. Server kit verified 23/23.

## Git and component consolidation

Published framework history:

| Commit | Result |
|---|---|
| `a22f6b7` | Stand packer runtime-template fix and regression test |
| `6ca8c5c` | Hosting branch merged into master |
| `f88bda5` | Published DeGram gitlink `b619e02e`, development topology decision |
| `5ba01a1` | Current graph only; cache/snapshots removed from index, local files retained; public evidence ignored |
| `f17445e` | CLAUDE.md and AGENTS.md changes |
| `4584e88` | Exact 93-path Phase 1309 WIP checkpoint, no phase acceptance |
| `86b2502` | 458 content-identical v12 archive relocations, LF/CRLF normalized for comparison |

`master` contains the merge and component decision. New cleanup/WIP commits are on `gsd/milestone13`, pushed through `86b2502`. Do NOT merge all remaining dirty files into master.

DeGram:
- Work base: `apps/degram`, branch `degram/milestone13`, HEAD/gitlink `b619e02e3725869b1ab5125951d3311e3656dc9a`; remote branch existence checked.
- Four mapping commits: `93997683`, `1aa3b39c`, `38d3e7e7`, `b619e02e`.
- `D:/dgb/src` is build-only; pull from submodule before future builds, no source commits there.
- Separate `C:/Users/Admin/source/repos/degram` on upstream-like main is not the work base; not removed.
- `workspace.py verify` passed after checkout alignment; context installed. Integration tests 27/27, with unclosed test socket ResourceWarnings. This is NOT product acceptance of the four historical commits.
- `apps/revit-mcp` HEAD/index/worktree blobs were identical; previous dirty flags were stat-cache noise. Clean child at published `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`; no new commit/push needed.

Dual-target continuation prompt updated: `C:/Users/Admin/DG-session-handoffs/2026-10-25-degram-dual-mode/CONTINUE.md`. Base/branch choice is settled; open decisions concern switching vs simultaneous targets, target config/UI, per-target auth/scope isolation and migration, local CAD adapters and version skew. No new Desktop/build/paid inference authorization is implied.

## Backup and pending tree

Private backup: `C:/dgx/backup-2026-10-25/`.
- `files.zip`: 3802 entries, 87,272,378 bytes; ZIP CRC validation passed again before save.
- MANIFEST.json, original staged.patch/unstaged.patch/status/staged-paths, empty revit-mcp.patch.
- Tracked backup ref `refs/backup/2026-10-25-main-folder` points to stash-create `2b669961e2590c76b90d80164e71339f8caad7a0` (no working-tree stash/pop).
- ZIP excludes graphify cache, untracked .claude/Publications and bin/obj; not a full disk backup. It contains private local audit fixtures: NEVER publish it.

Nine overlap files were three-way reconciled on switching the main folder to milestone13. Inputs preserved under `C:/dgx/merge9/`; four semantic resolutions retained both mapping and hosting requirements/checkpoints. Shared planning/vault files still contain old uncommitted changes; do NOT blanket stage them when saving this session.

Last measured pending status: 3215 paths, including 2707 audit-evidence paths, 120 docs/reviews, 24 audit-edited archive pairs and extra archive material, old source/tests/specs, and 131 regenerated tracked DG bin/obj paths. Counts may change with hooks/other sessions.

Deferred deliberately:
- 24 v12 archive pairs have meaningful audit edits rather than pure relocation; source copies are not missing. Their supporting audit evidence needs separate review.
- Audit-evidence contains temp env fixtures; no blanket publication. New PhD/manuscript/PDF/third-party downloads, scratch backups, editor configs and generated outputs not admitted.
- `.claude/` and `/Publications/` untracked additions excluded locally; existing historically tracked files not silently removed.
- Graphify hooks rebuild current graph after commits; generated post-commit graph changes may remain dirty. No broad clean/reset.

## Checks and independent review

- Server kit 23/23.
- Target inventory initially 2 failures from missing `TMPDIR`; `TMPDIR="$TEMP" python -I -B deploy/hosted/tests/run_required.py test_recovery_target_inventory.py`: 10/10, no source edits.
- Recovery archive: 24 ran, no assertion failures, 1 skip (host forbids symlink creation); strict runner exits nonzero because of skip.
- Bundle runtime: 1 failure at explicit owner Docker runtime approval gate; did NOT set approval to bypass it.
- `test_helpers.py` contains helpers, not a test suite. Initial shell sweep exit 0 was pipeline masking, not overall PASS.
- Phase1309 8 PLAN frontmatters reparsed: dependencies/waves and nonempty must_haves recognized, all LF at inspection.
- Strict `verify_multistore_offline.py` launched as background task `bnob32pkz`; its result had NOT been collected at this checkpoint. Do not claim PASS from historical runs; collect completion/output next.

DSH hub unreachable. Independent Claude read-only review completed against main-root dirty files, not isolated worktree. No acceptance or product edits from reviewer. Key findings: broken archived report references, false rejection of repeated idempotent MERGE, stale UI source-hash evidence, contradictory harness warning. Full details and reproduction limits: [[knowledge/debugging/Pending source review found stale v12 paths and duplicate MERGE rejection]]. Reviewer did direct-function/AST probes, not full pytest/.NET/browser suites.

## Next session

1. Check branch/status/index first; do not discard or publish the pending tree.
2. Collect strict offline verifier result; preserve failure/skip details if any.
3. Owner decision on reviewed old product/spec/test clusters. Fixes require scoped red/green tests and separate acceptance; never infer approval from background-agent messages.
4. Review remaining audit-edited archive pairs, accepted-debt documents and sanitized evidence together; avoid incomplete status claims and env/temp publication.
5. Phase1309 continues on `gsd/milestone13`; full multi-store/native/off-machine recovery remains open. Stand updates still require request and fresh snapshot.
6. For dual-target DeGram work use updated prompt and submodule preflight, then discuss unsettled behavior before implementation.

Session save commit includes only new notes and this session's additions in the shared vault indexes via a temporary Git index. Other staged/unstaged work must remain unchanged. No session-save push is implied.

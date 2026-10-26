---
tags: [session, degram, phase-1301, dgmode]
date: 2026-10-26
---

# DeGram dual-mode offline acceptance and publication

## Scope

Continued the DGMODE Plan 1301-46 offline acceptance and executed the publication/integration checkpoint of Plan 1301-47 for Developer (`http://localhost:8080`) ↔ Demo (`https://dg.173-249-46-99.nip.io`) target switching.

## Completed

- Created a locked, Git-ignored `apps/degram/.venv` using `uv sync --locked --group dev --group test` after explicit owner authorization. It uses Python 3.14.2, pytest 9.1.1 and ruamel.yaml 0.18.16.
- Installed an engine-compliant Node LTS runtime: Node v24.22.1 / npm 11.19.1.
- Added/reviewed Plan 42–46 target selection, origin-derived environment/partition identity, profile separation, runtime switch/controller fencing, typed IPC, UI selector and actual-profile A→B→A coverage.
- Fixed the D-54 Russian catalogue guard by documenting allowed immutable protocol/product/input literals; normal Russian prose enforcement remains active.
- Recorded Plan 46 offline evidence in `1301-DGMODE-OFFLINE-EVIDENCE.md` and summary `1301-46-SUMMARY.md`.
- Published the component target-mode implementation:
  - component branch `degram/milestone13`
  - commit `846d67a54b1875984cc8122cfba1fb2db9ba5d1a`
  - remote `Erarchitech/degram` branch `degram/milestone13` verified at the same hash.
- Updated the framework gitlink and published private Plan 47 guide/evidence/acceptance documents:
  - framework branch `gsd/milestone13`
  - commit `4481fc75203fa6d41aef3762e9ea8e65ec9f356b`
  - remote `Erarchitech/design-grammar-system` branch `gsd/milestone13` verified at the same hash.

## Verification

- Component Python target-mode suite: **276 passed**.
- Desktop Electron suite: **306 passed, 1 skipped**.
- Desktop UI suite: **348 passed**.
- Desktop typecheck: passed.
- Framework workspace helpers: **27 passed**.
- `python tools/degram/workspace.py verify`: passed; component HEAD and framework gitlink are `846d67a…`, context installed.

Known non-blocking output: framework relay-probe tests report pre-existing `ResourceWarning` warnings about unclosed fixture sockets, but all 27 tests pass.

## Evidence and current boundaries

- [DGMODE test guide](../../.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DGMODE-TEST-GUIDE.md) provides the Russian owner procedure and stop/retry/rollback rules.
- [Live evidence matrix](../../.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DGMODE-LIVE-EVIDENCE.md) remains `not-run` for runtime rows.
- [Scoped acceptance](../../.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DGMODE-ACCEPTANCE.md) keeps DGMODE-01..04 Pending.
- Build, isolated installation, Desktop launch, test authentication and Developer → Demo → Developer rehearsal are authorised. They must use the published component revision through clean build-only `D:\dgb\src`.
- No paid inference, CAD/graph mutation, server/stand change, grant revocation or TLS bypass is authorised.
- DGMODE evidence does not close DGCL-01..07, HOST-04, HOST-05, hosted recovery, product acceptance or Phase 1301.

## Next

1. In `D:\dgb\src`, fetch/pull `degram/milestone13` at `846d67a…`; verify the build clone is clean and never develop there.
2. Follow `1301-DGMODE-TEST-GUIDE.md`: build a uniquely versioned artifact, record its SHA-256/metadata/packaged identity, then isolated install/launch.
3. Run and record only authorised Developer → Demo → Developer test-auth observations. Do not expose credentials/tokens/password panels and do not infer deployed versions from source commits.
4. Update live evidence row-by-row with observed results. Keep unexecuted negative/revocation/inference/CAD rows blocked or not-run.

## Related

- [[DeGram dual mode is an additive plan slice with explicit runtime gates]]
- [[DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls]]
- [[DeGram runtime generation must pass through both main wiring layers]]
- [[2026-10-26 DeGram plan 1301-45 renderer isolation complete]]

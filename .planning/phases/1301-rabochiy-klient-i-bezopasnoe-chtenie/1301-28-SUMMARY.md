---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 28
status: partial
component_commit: d2054ae59c0bad9d5bcf7feac3926eeda62f4444
framework_gitlink_commit: a041eb1
build_record_commit: 418cfc4
installer: D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.7.exe
---

# Plan 1301-28 Summary

## Completed

- Versioned and published DeGram 0.1.7, including plans 24, 26 and 27 plus Windows build-pipeline reliability fixes.
- Framework gitlink now references the published component commit `d2054ae59c0bad9d5bcf7feac3926eeda62f4444`; `python tools/degram/workspace.py verify` passes.
- Built `DeGram-Setup-0.1.7.exe` from clean `D:\dgb\src` at that commit using the clean `D:\dgb\revit-mcp-src` source at `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`.
- Recorded installer metadata and artifact checks in `1301-BUILD.md` (framework commit `418cfc4`).

## Verification

- Pre-build: Electron build/isolation 40 passed; lint 0 errors; typecheck passed; DeGram UI 218 passed; Electron DeGram 227 passed; Python DeGram 400 passed.
- Installer: 490,533,308 bytes; SHA-256 `2825491ced4bd045cf16179d09b8ca70490ab906393957993db74fabdbcb5b7d`; ProductVersion `0.1.7`.
- Artifact checks passed: committed Revit adapter markers, DeGram identity, `degram-select`, `host=degram`, and no adapter tests directory.
- D-32 hot patch remained live: `docker compose exec -T data-service grep -F D-32 /app/degram_policy.py` matched; data-service was not recreated by this plan.

## Pending owner checkpoint

- Owner installed 0.1.7 on PC1; `%LOCALAPPDATA%\Programs\DeGram\DeGram.exe` reports `ProductVersion` `0.1.7.0` and `FileVersion` `0.1.7` (read-only check 2026-10-10T18:40:22Z).

## Owner decision — deferred live recheck

- Owner explicitly chose on 2026-10-10 to skip and defer the 0.1.7 live recheck. The deferral does **not** mark any DGCL requirement passed and leaves Phase 1301 without live-acceptance exit evidence.
- Resume only on an explicit owner request, starting from the 0.1.7 recheck rows in `1301-UAT.md`. Phase 1302 may start independently.

---
tags: [session, degram, phase-1301, phase-1302]
date: 2026-10-10
---

# Session: 2026-10-10 — Phase 1301 gap closure, DeGram 0.1.7 and deferred live recheck

## Goal

Finish the Phase 1301 gap-closure build and installation path for DeGram 0.1.7, then record the owner's decision on the remaining live acceptance.

## What Was Done

- Executed and published the 1301 gap closure: host-mode DG Web, first-screen/project flow, persistent revoke notices, per-scope `session.list`, and 0.1.7 version/lint remediation.
- Fixed Windows packaging reliability issues: readonly payload cleanup and bounded frontend publication rename retry.
- Built `DeGram-Setup-0.1.7.exe` from a clean isolated checkout. SHA-256: `2825491ced4bd045cf16179d09b8ca70490ab906393957993db74fabdbcb5b7d`; installer size: 490,533,308 bytes.
- Published component commit `d2054ae59c0bad9d5bcf7feac3926eeda62f4444`, aligned the framework gitlink, and verified `python tools/degram/workspace.py verify`.
- Owner installed 0.1.7 on PC1. Read-only verification found `%LOCALAPPDATA%\Programs\DeGram\DeGram.exe` at ProductVersion `0.1.7.0`, FileVersion `0.1.7`.
- Updated `1301-UAT.md` and `1301-28-SUMMARY.md` with the installation and deferral decision.

## Decisions Made

- Owner explicitly skipped and deferred the 0.1.7 live recheck. No unobserved DGCL check is passed; Phase 1301 does not have live-acceptance exit evidence.
- Phase 1302 may begin independently. Resume 1301 UAT only on an explicit owner request.

## Issues Encountered

- Windows packaging initially failed on stale readonly output and transient frontend rename locks. The final build pipeline includes readonly-aware cleanup and bounded retry; the clean 0.1.7 build completed.

## Next Steps

- Begin Phase 1302: source-linked project rules, company vocabulary release, immutable revisions, history and lessons-learned transfer.
- If requested, resume the deferred 1301 UAT from the 0.1.7 recheck rows in `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md`.

## Related Notes

- [[knowledge/decisions/DeGram 0.1.7 live recheck deferred while Phase 1302 begins]]
- [[knowledge/decisions/DeGram keeps the DG sign-in and finishes Phase 1301 on one PC]]
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-BUILD.md`
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md`

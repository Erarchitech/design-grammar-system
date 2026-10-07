---
tags: [debugging, degram, phase-1301, kaspersky, installer, environment]
date: 2026-10-07
status: open (environment)
---

# Kaspersky on PC1 blocks the DeGram installer and the installed executable by path

## Symptoms

- 0.1.1 and 0.1.2 installs stopped at ~98,750 of 110,348 files, no uninstaller; the 0.1.1 installer file then disappeared from `D:\dgb`.
- Application log: `avp` event 4662 for `degram-setup-0.1.2.exe` in the same second the installer exited.
- With Kaspersky off the 0.1.2 install completed (~30 min; it looks hung while overwriting the earlier partial copy).
- Installed `%LOCALAPPDATA%\Programs\DeGram\DeGram.exe` could not reach DG (`ERR_CONNECTION_RESET`); the same binary under `D:\dgb\...\win-unpacked` connects. Probe: `ELECTRON_RUN_AS_NODE=1 DeGram.exe -e "http.get(...)"` → ECONNRESET vs 401.
- `tools\degram\relay_probe.py` run as a script: every connection reset; a byte-identical copy elsewhere, or `runpy`, connects.

## Diagnosis

Kaspersky Total Security 21.3 acts per executable path (heuristic for an unsigned 1.9 GB installer writing ~110k files; per-file network block after a traceback printed a Bearer header). Not a DeGram defect.

## Workaround / next

- Owner adds Kaspersky exclusions (trusted application, network allowed) for the installer, `DeGram.exe` and `resources\agent-payload\bin\degram.exe`; to be written into `docs/degram/CLEAN-INSTALL.md` as a prerequisite.
- Pilot runs the unpacked build meanwhile.

---
tags: [debugging, DeGram, v13.0, phase-1301, isolation, windows, path]
date: 2026-10-06
status: fixed (component 69eb9a1d, pushed); pilot PC cleaned
---

# DeGram first launch put its own `hermes` command first in the user PATH

## Symptom

After the 2026-10-06 DeGram launch, `HKCU\Environment\Path` started with `%LOCALAPPDATA%\DeGram\home\bin`, which held `hermes.cmd` and `hermes-acp.cmd` pointing at the build clone's `agent-payload`. Any new terminal's `hermes` ran DeGram's payload instead of the owner's Hermes. The isolation diff of the Hermes folders did not show it: the change was in the registry, not in a Hermes folder.

## Cause

Upstream `hermes_cli/_launchers.py::expose_cli` takes its Windows branch (`_expose_windows_user_bin`: stage launchers into `$HERMES_HOME\bin` and register that directory in the user PATH) **before** the `_is_bundled_payload` check that makes POSIX skip a desktop bundle. DeGram's pinned `HERMES_HOME` is its own home, so the launchers landed there and the directory was prepended to PATH.

Separately, upstream `tests/hermes_cli/test_hermes_home_shared_launchers.py` writes the real user PATH on Windows: earlier runs had left 8 `%TEMP%\hermes-pytest\…\bin` entries.

## Fix

- `expose_cli` returns `{"ok": true, "skipped": "degram-owns-no-command"}` when `HERMES_DEGRAM=1`, before any staging or registry write; tests `tests/degram/test_launchers_degram.py` (Windows, POSIX, stock path unchanged).
- PC cleanup (owner-approved): the DeGram PATH entry, the stale launchers and the 9 pytest entries removed, registry value type preserved.
- F-10 launch afterwards: user PATH and user `HERMES_HOME` byte-identical before/after, `home\bin` not created.

## Lesson

An isolation check must compare the user environment (PATH, `HERMES_HOME`, protocol handlers), not only folders. Never run the upstream launcher test suite on a pilot PC. Gena hit the same class of bug (its finish stage overwrote the user `HERMES_HOME`).

Related: [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes]], [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes]].

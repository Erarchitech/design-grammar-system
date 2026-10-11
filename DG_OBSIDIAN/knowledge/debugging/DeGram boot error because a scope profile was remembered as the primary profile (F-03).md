---
tags: [debugging, degram, phase-1301, electron, isolation]
date: 2026-10-11
---

# DeGram boot error because a scope profile was remembered as the primary profile (F-03)

## Symptom

DeGram 0.1.10 showed a toast on every start once a project had been opened before: «Не удалось запустить приложение — DeGram scope profile "scope-3a5ba019269a6038" no longer exists in this window (it is not the active scope)». The DG page and project selection still worked underneath.

## Evidence

- `desktop.log` 21:22:07, 21:41:00, 22:36:35: `[degram] refused to start the backend of a scope profile that is not the active scope`, then `[renderer error:main] … 'hermes:connection' …`.
- `%LOCALAPPDATA%\DeGram\userData\active-profile.json` = `{"profile": "scope-3a5ba019269a6038", "_migrated": true}`; `defaultRoute` empty.
- The primary backend then ran on that profile (its `state.db` was written while another DG user was signed in), so the bug also broke per-user separation.

## Root cause

1. Opening a project activates the scope profile in the renderer, and the inherited Hermes code remembers it as the startup profile: `src/store/profile.ts` :1017-1028 → `profile.remember(target)` → `active-profile.json` `profile`.
2. At boot `hermes:connection` without a profile falls back to `primaryProfileKey()` → `readActive()` → the scope profile (`electron/main.ts` :15814, :11064).
3. No scope is active yet, so the G-25 gate (`electron/degram/scope-gate.ts` :86) refuses it, and the boot catch shows the toast (`use-gateway-boot.ts` :1626).

The G-25 gate was right to refuse; the defect is that a DeGram scope profile could become the Hermes primary at all.

## Fix direction (plan 1301-37)

In variant degram a `scope-<16 hex>` profile is never remembered, a stored one reads as no preference (`default`), and the first launch of the fixed version rewrites it once. Regression test: cold boot with the old `active-profile.json`.

## Related

- [[knowledge/debugging/DeGram left-scope backend restarted by the renderer reconnect ladder (G-25)]]
- [[sessions/2026-10-11 DeGram 0.1.10 UAT and 0.1.11 fix round planned]]

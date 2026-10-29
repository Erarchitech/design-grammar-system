---
phase: quick-261029-cxc
plan: 01
type: execute
autonomous: true
files_modified:
  - apps/degram/apps/desktop/electron/degram/connector-install.ts
  - apps/degram/apps/desktop/electron/degram/connector-install.test.ts
  - apps/degram/apps/desktop/src/degram/i18n.ts
  - apps/degram/apps/desktop/electron-builder.config.cjs
  - docs/degram/CLEAN-INSTALL.md
---

# Install for Revit in DeGram → Connectors sets pyRevit Routes itself

## Problem

On the second test PC the Revit connector extension was installed from the Connectors tab, Revit was open and DG
sign-in worked, yet DeGram showed «Revit не отвечает», then «Маршруты pyRevit (Routes) доступны не только с этого
компьютера». The cause was one missing key: `%APPDATA%\pyRevit\pyRevit_config.ini` had `[routes] enabled = true` but
no `host`, so pyRevit listened on every interface and the adapter (by design, D-23 / SECURITY-BOUNDARY) refuses to
read. CLEAN-INSTALL step 3 told the user to add `host = "127.0.0.1"` by hand. The owner's rule: the user must not do
these settings or checks; **Install** in DeGram → Connectors must do them.

## Tasks (component repository: apps/degram, committed there; framework gets docs + this record)

1. `connector-install.ts` (component): `ensureRoutesLoopback(text)` — pure edit of `[routes]` (`host = "127.0.0.1"`,
   `enabled = true`; missing section/keys added, wrong values replaced, other lines, EOL and BOM kept). The Revit
   spec gets `settings.ok/apply`: `status` reads `install` while the settings are wrong (so the column offers
   Install again), `install` writes them after the files (temp file + rename), saving the previous ini under
   `connector-backups/revit-settings/<stamp>`; when only the settings are wrong the extension is left alone; a
   non-UTF-8 ini is never rewritten (install → `failed`). Confirmation dialog (ru/en) says so and asks for a Revit
   restart (a pyRevit reload does not restart the Routes server).
2. `i18n.ts` (component): the Routes-disabled / not-loopback / extension-not-loaded texts point to the Connectors
   tab and a Revit restart instead of a manual edit (existing test prefixes kept).
3. `connector-install.test.ts` (component): helper cases and install cases (section created, key added, wrong
   value replaced, file made when only pyRevit-Master exists, settings-only repair, non-UTF-8 untouched, Grasshopper
   unaffected). Desktop installer version 0.1.16.
4. `docs/degram/CLEAN-INSTALL.md` (framework): steps 2–4 and the failure table.

## Non-goals

No change to the adapter or to `dg_transport` (the loopback refusal stays). No push of the component, no gitlink
bump, no installer build, no launch of DeGram Desktop or Revit.

## Verify

`npx vitest run electron/degram src/degram` in `apps/degram/apps/desktop`; eslint on the changed files.

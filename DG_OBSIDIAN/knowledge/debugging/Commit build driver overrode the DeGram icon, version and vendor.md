---
tags: [debugging, DeGram, v13.0, phase-1301, installer, electron-builder]
date: 2026-10-06
status: fixed (component a9e56d7e, pushed); verified on DeGram-Setup-0.1.0.exe
---

# Commit build driver overrode the DeGram icon, version and vendor

## Symptom

The installer rebuilt from `69eb9a1d` passed every repo-level test, yet the packaged artifact showed:

- `resources\icon.ico` and the exe icon: upstream's **red commit-build icon with the Nous art and a `69eb9a1` badge** (every earlier DeGram build, plan 15 included, carried it);
- version `0.0.0` (installer `DeGram-Setup-0.0.0.exe`);
- CompanyName `Nous Research`, copyright `Copyright © 2026 DeGram`.

## Cause

All three in the build path, not in the committed files:

1. `scripts/bundles/desktop.py` runs upstream `scripts/generate_icons.py` for a commit build (`HERMES_BUILD_COMMIT` → red badge art) into `build/products/icons` and stages it over `apps/desktop/assets` while electron-builder runs (`flavored_assets`), restoring the committed files afterwards.
2. It always passes `-c.extraMetadata.version=<request version>` (0.0.0 for a commit build), which beats the config's `extraMetadata.version`.
3. electron-builder's AppInfo reads `author.name`; package.json's string author is normalized to an object on read, but an `extraMetadata.author` **string** is merged after that, so companyName became empty (CompanyName stayed from the rcedit stamp, copyright fell back to the product name).

## Fix

- `degram_icon_overlay(repo, icons)`: for variant degram, the committed DeGram icon files are laid over the render (list `DEGRAM_ICON_FILES`, pinned to the generator's outputs by a test).
- `package_version_args(variant, version)`: no version override for degram.
- `extraMetadata.author = { name: 'Erarchitech' }`.
- Rebuild from `a9e56d7e`: exe ProductName DeGram, CompanyName Erarchitech, version 0.1.0; `icon.ico` and the `app.asar` images byte-identical to the committed files.

## Lesson

Verify a product's identity on the packaged exe and `app.asar`, never on the repo files or unit tests alone (Gena learned the same: a dev run shows Electron's icon). Recorded as a rule in `spec/degram/WORKSPACE.md`.

Related: [[knowledge/decisions/DeGram product identity follows the Gena fork lessons]], [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes]].

---
tags: [session, degram, phase-1301, pairing, connectors, installer, branding, kaspersky]
date: 2026-10-07
---

# Session: 2026-10-06/07 — Phase 1301: DeGram pairing connector, agent reads the rules, 490 MB installer, no Hermes name

Model: claude-opus-5-5. Command: `/gsd-execute-phase 1301` (plans 16 and 17 remaining), executed inline on the owner's choice.

## Goal

Finish plan 17 (DeGram's credential from the DG Connectors tab), then fix what the owner found while using DeGram on PC1.

## What Was Done

- **Plan 17 — DeGram pairing connector (D-25, D-26, D-27), complete.**
  - Server: user-bound `dgp_` pairing token (hash-only store `degram-pairings.json`), DeGram card in Connectors (category Agents), `POST /auth/degram/exchange` mints the usual 15-minute `dgd_`; a `dgp_` on any other route answers 401 `PAIRING_NOT_A_PRINCIPAL`; revoke, password change or a deleted user end the pairing and every `dgd_` minted from it. Specs SECURITY-BOUNDARY §3.5 and API.md updated. Commits `6119979`, `de11958`, `e56b77c`.
  - DeGram: token stored as Electron `safeStorage` ciphertext, crosses IPC once, panel «Подключение к DG»; a refused pairing closes the project but keeps the DG sign-in. Component `e2fb6ffb`.
  - Live on PC1: create, exchange, renewal every 600 s, revoke → next turn closed the project, revoked state shown, sign-in kept (owner confirmed). `relay_probe.py` through the pairing: 4/4 cases with the owner's model `gena-mid` (MiMo not probed).
- **D-27** keep the DG sign-in, pairing never expires; **D-28** the reviewer-PC check moves to the last v13.0 phase, 1301 finishes on PC1. See [[knowledge/decisions/DeGram keeps the DG sign-in and finishes Phase 1301 on one PC|decision]].
- **G-1 — agent could not read the project's rules, closed live on 0.1.3 (12/12 rules).** Three layers: the `/graph` answer was 8.6 MB > the client's 8 MiB cap (server `?compact=true`, `bb036a1`); rules were only read after the graph (now independent, `5beb87d5`); the 256 KiB tool answer exceeded the agent's 100K-char result threshold and was spilled to a file DeGram cannot read (now ≤ 60 % of the threshold, rules first, `0614b41e`). See [[knowledge/debugging/DeGram graph tool answer was spilled to a file the agent cannot read|debug note]].
- **Installer size 1.9 GB → 490 MB (owner option 1, offline).** The degram payload keeps only Python and the pm-required tools, the core plus extras acp/cron/mcp/pty/vision/web, and a uv-cache of what is installed; F-11 (paths > 260 chars at the default dir) closed live. See [[knowledge/decisions/DeGram payload ships only what variant degram can use|decision]].
- **No "Hermes" name in DeGram.** Catalog + DOM rebrand, OS notifications, tray, DEGRAM wordmark (`c541b229`, approved on 0.1.4). Interface language now kept by DeGram itself; the locked `/api/config` is no longer used for it. See [[knowledge/decisions/DeGram rebrands Hermes at the catalog and the rendered interface|decision]].
- **Builds:** 0.1.1, 0.1.2, 0.1.3 (490 MB), 0.1.4 (approved, SHA-256 `5a5177f7…2fa307`). Records in `1301-BUILD.md`.

## Problems Found

- Kaspersky Total Security on PC1 terminates the installer, removed the 0.1.1 installer, and resets connections from the installed `DeGram.exe` and from `tools\degram\relay_probe.py` by path; the unpacked build under `D:\dgb` works. See [[knowledge/debugging/Kaspersky on PC1 blocks the DeGram installer and the installed executable by path|debug note]].
- A pasted pairing token was printed by `relay_probe` in a traceback; fixed (`c91d5a7`), the exposed pairing revoked.
- The installer looks hung for many minutes while it overwrites an earlier partial install; it is a slow copy, not a hang (~30 min for 0.1.2).

## Open

- Plan 16 (wave 9): DGCL-01..07 live checklist on PC1 (D-28), then plan 16 SUMMARY and phase verification.
- Installed copy of DeGram on PC1 cannot reach DG (Kaspersky per-path rule needed, owner).
- ffmpeg 427 MB still shipped (pm-required; a drift-skip for variant degram would drop ~120 MB of installer).
- Pilot project has no company assigned.

## Commits

Framework: `6119979` … `0d6b613` (pairing, specs, compact graph, UAT/BUILD records, gitlinks up to `970aee0`) and the session commit. Component `Erarchitech/degram` `degram/phase-1301`: `e2fb6ffb` … `c541b229`, all pushed; `workspace.py verify` passes.

---
tags: [decision, stand, speckle, security, hosting]
date: 2026-10-29
status: accepted (owner)
---

# Stand Speckle is set up from the server and its web UI stays closed at the edge

## Context

- The first Revit check from the demo PC that reached publishing failed with `SPECKLE_CONFIG_MISSING`.
- Publishing had never been configured on the stand:
  - Speckle had 0 users and open registration (`inviteOnly: false`);
  - the four `SPECKLE_*` keys in `/opt/dg/.env` were empty;
  - no DG project had an `IntegrationConfig`.
- The Speckle web UI (`/authn/*`, `/projects`, `/profile`) returns 404, because the edge Caddyfile allows only an
  explicit path list. `deploy/hosted/ORIGINS.md` says that opening Speckle publicly needs a separate tenancy decision.
- The V2 UI has no Speckle Settings card. The hint in the error text points at the archived legacy UI.

## Options

1. Set up Speckle from the server through its internal API, and keep the web UI closed.
2. Widen the edge allowlist to the Speckle web pages, and let the owner set up Speckle by hand.

## Decision (owner)

Option 1. The security boundary does not change, and results are viewed in the DG Model Viewer through the
data-service proxy.

## Result

- A service account `dg-service@dg-stand.invalid` (Speckle server admin), and Speckle `inviteOnly: true`.
- A write token (`streams:read`, `streams:write`, `profile:read`, `users:read`) and a read-only token
  (`streams:read`) in `/opt/dg/.env`.
- Speckle project `cb20909c46` with model `base` (`61dac1cfe2`). The model holds a placeholder version, because a
  publish needs a base version to overlay; Revit-native checks bring their own geometry.
- The project is bound only to `isolation-check-a`. There is no server-wide default, so other DG projects do not
  share it.
- The password and tokens are on the server only (`/opt/dg/.env`, `/root/dg-speckle-setup/`, mode 600). They were
  never shown in chat.
- Opening the Speckle web UI stays a separate, later decision.

## Related

- [[sessions/2026-10-29 Demo PC Revit check fixed end to end, stand Speckle set up (F-08, F-09)|session]]
- [[knowledge/decisions/Hosted stand first and recovery proof in parallel|stand first]]

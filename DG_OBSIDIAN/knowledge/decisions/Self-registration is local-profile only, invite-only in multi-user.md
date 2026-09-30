---
tags: [decision, security, auth, phase-1205]
date: 2026-09-30
---

# Self-registration is local-profile only, invite-only in multi-user

## Context

Phase 1205 D-05 removed the old localStorage Register form. It replaced it with server-side accounts: a bootstrap admin, then invite-only onboarding. During UAT the owner found no way to create a second account without learning the invite flow, and asked for the registration form back.

## Decision

Self-registration (`POST /auth/register`, `GET /auth/options`) is **on in the `local` profile and off in `multi-user`**.

- **Default:** the toggle `DG_ALLOW_SELF_REGISTRATION` follows the profile when blank. It can be set explicitly to override. `docker-compose.multi-user.yml` pins it to `false`.
- **Disabled route:** it answers 404, indistinguishable from an unknown route, before the CSRF check. Multi-user therefore shows no registration surface.
- **New accounts:** never admin, and no memberships. They see only projects they create or are invited to.
- **Hardening:** the same username rule, 12-character password policy, login throttle, dummy-scrypt timing and nginx rate limit as login.

## Why

- Local single-user development needs friction-free accounts (GATE12-05 does not block local work).
- The external multi-user evaluation keeps invite-only onboarding, so the GATE12-05 verdict is unaffected.
- Tenancy is unchanged either way, because membership, not account existence, is what authorizes.

## Consequences

- D-05 carries an "Amendment (2026-09-30)" line in `1205-CONTEXT.md`.
- `spec/SECURITY-BOUNDARY.md` lists both routes in its public-route block.
- There are 43 tests (`data-service/tests/test_self_registration.py`).
- Commits `6d8069d..b5179c4`.

---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 47
scope: DGMODE-01..04
status: pending-live-acceptance
independent_review: not-run
---

# DeGram: scoped acceptance — Developer / Demo modes

## Scope

This is a narrow acceptance report for DGMODE-01..04. It is not a release certificate and does not close any broader DeGram, hosted-recovery, security or Phase 1301 gate. The live matrix has been prepared but no live outcome is recorded yet: [1301-DGMODE-LIVE-EVIDENCE.md](1301-DGMODE-LIVE-EVIDENCE.md). Observed bounded offline results are separate: [1301-DGMODE-OFFLINE-EVIDENCE.md](1301-DGMODE-OFFLINE-EVIDENCE.md).

## Contract delta assessment

No normative change to [spec/SECURITY-BOUNDARY.md](../../../spec/SECURITY-BOUNDARY.md) is required for target selection as currently implemented/planned:

- no new route, principal type, published port, secret, delegated-token rule, connector grant rule or server-side permission is introduced;
- Developer is restricted to loopback, Demo to configured HTTPS, and `DEGRAM_DG_ORIGIN` is a target-matching launch override rather than arbitrary routing;
- remote TLS verification must remain enabled; target failure must not fall back to localhost;
- native/MCP boundaries remain local/stdio and Demo does not expose Bolt or add write authority;
- existing delegated token (`dgd_`) / grant rules continue to apply on every relevant request.

Consequently, no SECURITY-BOUNDARY machine inventory is amended by this framework-only Task 1. Any future route/principal/port/secret change requires a new contract review, the relevant inventory update and its named tests before release.

[spec/degram/WORKSPACE.md](../../../spec/degram/WORKSPACE.md) already verifies the relevant compatibility constraints: build only from `D:\dgb\src`; development only in `apps/degram` on `degram/milestone13`; DeGram’s separate runtime home/userData/app identity; no updater; and no `hermes update`. Task 1 has found no further verified behavior requiring a WORKSPACE amendment.

## Evidence basis

| Evidence | Status | What it establishes | Limitation |
| --- | --- | --- | --- |
| [1301-DGMODE-OFFLINE-EVIDENCE.md](1301-DGMODE-OFFLINE-EVIDENCE.md) | observed, complete-offline-evidence | Real profile CLI A→B→A in temporary homes, equal-ID profile separation, controller race/no-fallback behavior, renderer fencing, bounded Electron/UI/Python/typecheck suites | Does not establish a packaged Desktop, live target, TLS chain, login/grant, visual native bounds, deployed versions or stock-Hermes nonmutation |
| [1301-DGMODE-LIVE-EVIDENCE.md](1301-DGMODE-LIVE-EVIDENCE.md) | prepared; all primary observations not-run | Exact expected/actual slots for versioned Developer ↔ Demo rehearsal | No live result exists yet |
| [1301-DGMODE-TEST-GUIDE.md](1301-DGMODE-TEST-GUIDE.md) | prepared | Reproducible owner procedure, stop/retry/rollback and redaction boundary | A guide is not evidence |

## Requirement verdicts

| Requirement | Verdict | Grounding | Outstanding blockers |
| --- | --- | --- | --- |
| DGMODE-01 — explicit visible/persistent Developer/Demo selection | **Pending** | Offline config/controller/UI tests pass; live matrix rows LIVE-04, 10–12, 15–16 and 26 remain not-run | Exact installed artifact, local/stand observed versions, actual selector/native-window/restart observations |
| DGMODE-02 — origin/environment separation and A→B→A | **Pending** | Offline actual-profile CLI uses same disposable home with equal IDs and returns A without profile collision | Live auth/cookie/project/history/document separation across actual local/stand sessions remains not-run |
| DGMODE-03 — safe switching, no fallback, scoped native boundary | **Pending** | Offline controller race/TLS-shaped failure and renderer-generation fences passed | Actual busy/Stop/retry, live target failure/TLS/auth behavior, native boundary and late-response observation remain not-run; grant revocation is not authorized |
| DGMODE-04 — reproducible offline plus separately authorised live evidence | **Pending** | Offline Plan 46 matrix is recorded with versions and bounded green suites | Packaged client/local/stand version evidence, actual rehearsal, stock-Hermes boundary and owner review remain not-run |

## Authorizations and blockers

| Action | Current authorization/status |
| --- | --- |
| Child component commit | Owner-authorized and created: `846d67a54b1875984cc8122cfba1fb2db9ba5d1a` |
| Push to public `Erarchitech/degram` / `degram/milestone13` | Owner-authorized and completed; `origin/degram/milestone13` equals `846d67a54b1875984cc8122cfba1fb2db9ba5d1a` |
| Framework gitlink update | Now authorised by the commit/push instruction; record the exact pair with `workspace.py verify` before build/live acceptance |
| Build from clean `D:\dgb\src` | Explicitly authorized by owner; must still follow guide/preflight and use a recorded exact revision |
| Isolated install / Desktop launch | Explicitly authorized by owner; must preserve DeGram/Hermes runtime isolation and record artifact identity |
| Test auth + localhost → stand → localhost | Explicitly authorized by owner; credentials/grants remain redacted and environment-scoped |
| Paid inference / model relay | Not authorized |
| CAD/graph mutation, native write action | Not authorized |
| Server/stand config or deploy change | Not authorized |
| Expiry/revocation drill | Not authorized |
| TLS bypass / certificate override | Prohibited |

The Plan 47 ordering requires child commit then public push before a reproducible framework gitlink pair can be recorded. That publication prerequisite is now met at `846d67a54b1875984cc8122cfba1fb2db9ba5d1a`; the framework gitlink still needs its controlled update and `workspace.py verify`. Until that verification is recorded, any authorised live rehearsal remains an artifact-specific operational check, not proof of a completed framework/component integration pair.

## Independent review

No independent review has run. The controller’s document cross-check is self-review only and cannot change `independent_review: not-run`.

## Gates intentionally left open

- DGCL-01 through DGCL-07;
- HOST-04 and HOST-05, including hosted recovery;
- product acceptance and any Phase 1301 completion;
- server-side grant/revocation and permission semantics not explicitly exercised;
- any requirement checkbox in `.planning/REQUIREMENTS.md`.

## Next acceptance action

Use the guide to collect only the authorised build/install/launch/test-auth/local↔stand↔local evidence. Update each corresponding live row with an observed outcome, exact revisions/versions/hash/timestamps and redacted diagnostics. A missing, blocked or failed row remains visible; it must never be converted to Pass from an offline mock or build result.

---
tags: [debugging, degram, dgmode, concurrency]
date: 2026-10-26
---

# DeGram quiescence must reserve RPC work before enqueue

## Finding

During plan 1301-44 integration, the initial gateway barrier checked session flags and then assigned a barrier without a shared admission lock. Long native/mapping RPCs could already be queued without a running session. Requests without `_degram_environment`, or with another generation, bypassed the handler-level exact-match barrier. Main also attached metadata to calls whose closed contracts did not declare that transport envelope.

## Correction

- Gateway admission and quiesce share a process-owned lock and accepted-work count.
- Reserve before synchronous invocation or pool submission; release on handler completion, cancelled queued futures and enqueue failure.
- Refuse quiesce while accepted work or real session/compute-host activity exists. Unknown activity fails closed.
- Once frozen, reject new work independent of metadata. Allow only environment-control and credential clear/status; resume requires the exact frozen generation.
- Preserve existing capability lockdown before environment admission.
- Validate and remove the main-owned transport envelope before closed handler-contract validation.
- Scope opening/checking/renewing and uncertain retained backends veto switching. Strict cleanup releases a retained profile even after failed credential handoff; it never wipes partition storage.

## Verification and boundary

Fresh combined gateway/security/contracts/retirement selector: **196 passed**, including **11 environment tests**. Covers running work, deterministic idle/admission race, queued cancellation, enqueue failure, untagged/other-generation refusal and stock Hermes isolation. Electron DeGram: **302 passed**, typecheck passed.

An armed but unsubmitted Send is not backend work. Renderer preview/confirmation/streaming leases and source-generation callback checks remain plan 45; this fix does not claim live acceptance.

Related: [[sessions/2026-10-26 DeGram plan 1301-44 runtime composition complete]], [[knowledge/decisions/DeGram dual mode is an additive plan slice with explicit runtime gates]].

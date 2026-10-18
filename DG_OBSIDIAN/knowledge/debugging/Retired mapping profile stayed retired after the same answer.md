---
tags: [debugging, mapping, phase-1303]
date: 2026-10-18
status: fixed (ab04bb3), verified live
---

# Retired mapping profile stayed retired after the same answer

**Symptom (found before it bit).** For the cold restart on 2026-10-18 the two profiles of rehearsal 1 were set to `state = retired`. The same answer given again would have produced the same `profileId`, so `decide` found the retired profile among the existing ones. It copied it with all fields, raised `confirmations` and saved it, still retired. The next variant would then have been asked again instead of being mapped by the profile.

**Cause.** `profileId` hashes only platform, selector and roles. The update path in `decide` and `_item_profile` copied `state` unchanged.

**Fix (`ab04bb3`).** A human answer that produces an existing profile sets `state = active`. Test: `test_answer_reactivates_a_retired_profile`. In addition, `876e5d1` makes `GET /mapping/profiles` list only active profiles, so the Web UI table no longer shows retired ones.

**Verified live.** In rehearsal 2 the profile «Panels A → BottomTriangularPanel» (`P-7a2d45d381f1`), retired in the morning, became active again after the owner's answer.

**Lesson.** Retiring is reversible on purpose (an undo retires what an answer created), so every write path that touches an existing profile must decide its `state` explicitly.

Related: [[sessions/2026-10-18 Phase 1303 proposal cards, DeGram mapping sub-tab and live rehearsal through V2|session]].

---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 47
scope: DGMODE-01..04
status: pending-live-observation
---

# DeGram: матрица live evidence Developer ↔ Demo

## Правило заполнения

Все строки ниже имеют статус `not-run`, пока не будет получен наблюдённый redacted результат. Нельзя подменять `actual` результатом unit test, source commit, build success, предположением о deployed stand или успешным ответом другой программы. Полные инструкции, stop/retry и rollback: [1301-DGMODE-TEST-GUIDE.md](1301-DGMODE-TEST-GUIDE.md). Offline evidence зафиксирован отдельно: [1301-DGMODE-OFFLINE-EVIDENCE.md](1301-DGMODE-OFFLINE-EVIDENCE.md).

Никогда не вносить в этот документ пароль, cookie, `dgd_` token, pairing secret, API key, prompt/model content или screenshot password Panel. Для отказов записывать только безопасный код/класс ошибки и timestamp.

## Пакет версии и разрешений

| Field | Value |
| --- | --- |
| Framework revision | pending observation |
| Framework dirty-state summary | pending observation |
| Child revision / branch | `846d67a54b1875984cc8122cfba1fb2db9ba5d1a` / `degram/milestone13` |
| Child published remote revision | `846d67a54b1875984cc8122cfba1fb2db9ba5d1a`, verified at `origin/degram/milestone13` after owner-authorized commit/push |
| Framework gitlink equals published child | pending this framework update; verify immediately after the gitlink is staged |
| Build clone revision / clean state | pending observation |
| Client artifact path | pending observation |
| Client artifact version | pending observation |
| Client artifact SHA-256 | pending observation |
| Install path | pending observation |
| Local DG version/revision and source | pending observation |
| Demo DG version/revision and source | pending observation |
| Test window timestamps/time zone | pending observation |
| Runtime home/userData identity | expected `%LOCALAPPDATA%\DeGram\{home,userData}`; actual pending |
| Explicit runtime authorization | owner authorization for build, isolated install/launch, test auth, localhost ↔ stand ↔ localhost; no commit/push |
| Inference/CAD/server/revocation authorization | not authorized; these actions must not be used to satisfy any row |

## Preflight and artifact identity

| ID | Requirement link | Expected | Actual | Status | Redacted evidence |
| --- | --- | --- | --- | --- | --- |
| LIVE-00 | DGMODE-04 | `workspace.py verify` identifies the working pair and context; no silent pair substitution | not-run | not-run | pending |
| LIVE-01 | DGMODE-04 | Artifact metadata is DeGram / `com.erarchitech.degram`; SHA-256/version/path recorded before launch | not-run | not-run | pending |
| LIVE-02 | DGMODE-04 | Build clone is `D:\dgb\src`, at recorded selected revision and clean; no development occurs there | not-run | not-run | pending |
| LIVE-03 | DGMODE-04 | Existing Hermes stays running/unchanged according to control-window attribution; DeGram home/userData are isolated | not-run | not-run | pending |
| LIVE-04 | DGMODE-01 | Effective configured origins are Developer `http://localhost:8080` and Demo `https://dg.173-249-46-99.nip.io`; no unconfigured override | not-run | not-run | pending |

## Main local/hosted rehearsal

| ID | Requirement link | Expected | Actual | Status | Redacted evidence |
| --- | --- | --- | --- | --- | --- |
| LIVE-10 | DGMODE-01 | Existing/legacy local installation opens Developer without profile loss; selector displays mode and canonical origin before sign-in | not-run | not-run | pending |
| LIVE-11 | DGMODE-01 | Developer login/test company/project/grant operates against localhost; effective origin remains local | not-run | not-run | pending |
| LIVE-12 | DGMODE-01, DGMODE-03 | Developer → Demo changes selected/effective target to exact HTTPS Demo origin; no automatic localhost fallback | not-run | not-run | pending |
| LIVE-13 | DGMODE-02 | Demo requires independent auth/grant; no local cookie, delegated credential, selected project, document or history becomes Demo state | not-run | not-run | pending |
| LIVE-14 | DGMODE-02 | Equal user/company/project identifiers remain separate by origin/environment/partition | not-run | not-run | pending |
| LIVE-15 | DGMODE-01, DGMODE-02 | Demo → Developer restores its own valid local state only after environment-valid auth/membership; no Demo transient state/data leaks back | not-run | not-run | pending |
| LIVE-16 | DGMODE-01 | Restart with selected Developer restores Developer target; separate restart with selected Demo restores Demo target | not-run | not-run | pending |
| LIVE-17 | DGMODE-03 | During an active operation, switching is refused or safely stopped; explicit Stop/retry is required and old operation is not resent to new target | not-run | not-run | pending |
| LIVE-18 | DGMODE-03 | A late old-target response cannot update the newer target generation | not-run | not-run | pending |

## Failure and security boundary observations

| ID | Requirement link | Expected | Actual | Status | Redacted evidence |
| --- | --- | --- | --- | --- | --- |
| LIVE-20 | DGMODE-03 | Demo unavailable gives explicit selected-target failure; no localhost fallback or old runtime resurrection | not-run | not-run | pending |
| LIVE-21 | DGMODE-03 | Real TLS failure, if safely observable without bypass, remains an explicit target error; certificate validation is not disabled | not-run | not-run | pending |
| LIVE-22 | DGMODE-03 | Login/membership/grant refusal is explicit and does not fall back to weaker credential/cookie or another target | not-run | not-run | pending |
| LIVE-23 | DGMODE-03 | Expired/revoked delegated grant returns contract error only after separately authorized controlled test | not-run | blocked-not-authorized | no revocation authorization |
| LIVE-24 | DGMODE-03 | In Demo Mode native bridge remains loopback/stdio; no Bolt, public listener or new native write permission appears | not-run | not-run | pending |
| LIVE-25 | DGMODE-04 | DeGram launch/install does not modify stock Hermes profile, user PATH, updater config or non-control-window Hermes files | not-run | not-run | pending |
| LIVE-26 | DGMODE-04 | Owner-facing native bounds, focus, selector wrapping and accessibility are observed on actual Desktop window; no CSS overlay of WebContentsView | not-run | not-run | pending |

## Offline evidence mapping

| Offline row | Supports | Does not prove |
| --- | --- | --- |
| Actual profile CLI same-home A→B→A with equal IDs | DGMODE-02 partition/profile behavior | Client installation, real credentials/cookies, deployed Demo state or network behavior |
| Deterministic controller race and TLS-shaped failed Demo start | DGMODE-03 switch refusal/no fallback state machine | Real TLS chain/stand outage handling or Desktop renderer presentation |
| Renderer generation/store fencing | DGMODE-02/03 stale-response defense | Native WebContents bounds, live visual/focus behavior |
| Electron/UI/typecheck/Python green bounded suites | DGMODE-04 offline reproducibility prerequisite | Packaged artifact, launch, local/hosted login or stock-Hermes nonmutation |

## Result ledger

| DGMODE requirement | Current verdict | Required observations before a Pass verdict |
| --- | --- | --- |
| DGMODE-01 | Pending | LIVE-04, 10–12, 15–16, 26 with exact client/local/stand version evidence |
| DGMODE-02 | Pending | LIVE-13–16 and evidence of separated credentials/context for equal identifiers |
| DGMODE-03 | Pending | LIVE-12, 17–24, including only the failure cases actually authorized/observed |
| DGMODE-04 | Pending | LIVE-00–03, 25–26 plus this observed matrix and separately linked offline evidence |

This ledger does not close DGCL-01..07, HOST-04, HOST-05, hosted recovery, product acceptance or Phase 1301.

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
| Build clone revision / clean state | `D:\dgb\src`, detached `846d67a54b1875984cc8122cfba1fb2db9ba5d1a`, clean after build (observed 2026-10-27) |
| Client artifact path | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.11.exe`; unpacked `release\win-unpacked\DeGram.exe` |
| Client artifact version | exe ProductVersion `0.1.11.0`, FileVersion `0.1.11`; reused version, contrary to WORKSPACE.md unique installer patch rule; install/launch held |
| Client artifact SHA-256 | installer `E31491D74851393A68D138DED4DC48C714A39DEF6FADCE182B0AB9DD1F4345ED` (490656773 bytes); unpacked `resources\app.asar` `3E5C654A705880308BBC0D0C2C08381B3E878B291DA6F8C080A346C277659220` |
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
| LIVE-00 | DGMODE-04 | `workspace.py verify` identifies the working pair and context; no silent pair substitution | verifier exit 0; child HEAD = gitlink = `846d67a54b1875984cc8122cfba1fb2db9ba5d1a`; componentContextInstalled true; productAccepted false | pass-preflight-only | observed 2026-10-27 before install/launch |
| LIVE-01 | DGMODE-04 | Artifact metadata is DeGram / `com.erarchitech.degram`; SHA-256/version/path recorded before launch | ProductName DeGram, CompanyName Erarchitech; packaged main contains app ID and target selector/config markers; no resources/app-update.yml; hashes recorded above. Installer version 0.1.11 is reused; stamp base/displayVersion 0.0.0 | blocked-version-policy | stamp commit matches, dirty false, variant degram, payload bundled, updateMechanism external; install/launch not performed |
| LIVE-02 | DGMODE-04 | Build clone is `D:\dgb\src`, at recorded selected revision and clean; no development occurs there | exact selected commit, detached, clean after owner-run build | pass-build-preflight-only | owner-reported build exit 0 at 2026-10-27T08:03:19Z; stamp builtAt 2026-10-27T07:57:17.048Z; artifact independently inspected |
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

## Version-policy correction (2026-10-27)

The artifact metadata above describes the completed `846d67a…` build and is retained as historical evidence, not as the next install candidate. No installation or launch of that artifact occurred in this run.

- Owner requested the version correction in the canonical submodule and a build from the published new revision.
- Component `apps/desktop/electron-builder.config.cjs`: DeGram-only installer version `0.1.11` → `0.1.12`; no shared package version or runtime behavior changed.
- Published component commit: `aee247efc6bf92349aeff4161079e62133755cfb`, confirmed by `ls-remote origin refs/heads/degram/milestone13`. Only the one-line version change was committed/pushed.
- Framework gitlink staged to that published commit; workspace verifier passed on the exact pair. No framework commit/push performed.
- Build identity/isolation tests: initial default-timeout run 38 passed / 2 timed out at 5000 ms; repeat with explicit 30000 ms timeout 40/40 passed. Framework helper tests 27/27 passed, with socket ResourceWarnings.
- Build-only clone `D:\dgb\src` fetched from the canonical submodule and is clean/detached at `aee247efc6bf92349aeff4161079e62133755cfb`.
- Owner subsequently reported build exit 0 at `2026-10-27T08:26:50Z`. Independent artifact inspection at `2026-10-27T08:35:44Z` confirms the new build below. Earlier execution-permission denial was not bypassed; the build was owner-run.

### Verified 0.1.12 install candidate

This candidate supersedes the historical 0.1.11 artifact above for the next installation. LIVE-01's version-policy blocker is resolved for this candidate only; no runtime acceptance is implied.

| Field | Observed value |
| --- | --- |
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.12.exe` |
| Installer bytes / SHA-256 | `490659129` / `A08F838B172B09E4FB1C2405E020E115804054FA4983CD26C7DA4013799535A4` |
| Unpacked app.asar SHA-256 | `D9C8FB3D496BCCB3DE8A589F18FE0865B3754F769E5C892651E41DD42D5393F3` |
| ProductName / CompanyName / ProductVersion / FileVersion | `DeGram` / `Erarchitech` / `0.1.12.0` / `0.1.12` |
| Install stamp | commit `aee247efc6bf92349aeff4161079e62133755cfb`, dirty false, variant degram, payload bundled, updateMechanism external |
| Stamp builtAt | `2026-10-27T08:22:37.705Z` |
| Stamp upstream version fields | baseVersion/displayVersion remain `0.0.0`; actual exe metadata is `0.1.12.0` |
| Packaged main | contains `com.erarchitech.degram`, `persist:degram-dg-`, `activeDgTarget`, `DEGRAM_DG_ORIGIN` |
| Updater feed file | `resources/app-update.yml` absent |
| Build clone after build | clean, detached at `aee247efc6bf92349aeff4161079e62133755cfb` |
| Framework/component pair | workspace verify exit 0, gitlink = component HEAD = `aee247ef…`, componentContextInstalled true, productAccepted false |
| Installation / launch / target rehearsal | not performed or observed for 0.1.12 at this checkpoint |
- Git emitted a permission warning while pruning the old `dgp-t` worktree metadata during the component commit; no cleanup/bypass attempted. Commit/push and remote SHA verification succeeded.

## Result ledger

| DGMODE requirement | Current verdict | Required observations before a Pass verdict |
| --- | --- | --- |
| DGMODE-01 | Pending | LIVE-04, 10–12, 15–16, 26 with exact client/local/stand version evidence |
| DGMODE-02 | Pending | LIVE-13–16 and evidence of separated credentials/context for equal identifiers |
| DGMODE-03 | Pending | LIVE-12, 17–24, including only the failure cases actually authorized/observed |
| DGMODE-04 | Pending | LIVE-00–03, 25–26 plus this observed matrix and separately linked offline evidence |

This ledger does not close DGCL-01..07, HOST-04, HOST-05, hosted recovery, product acceptance or Phase 1301.

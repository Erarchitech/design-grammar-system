# Roadmap: Design Grammar System

## v13.0 — DeGram Agent

**Статус:** ACTIVE — owner scope revision 2026-10-04. Phase 1300 incomplete / scope revision; независимый read-only client slice 1301 в `ui-v2` — in progress, не готов к выпуску. Все 51 ID и ownership 1300–1307 сохранены; ни одна фаза не объявлена завершённой.

**Authority:** Последняя active revision имеет приоритет над историческими preparation/discussion/plan-check материалами. Архивный пакет не изменяется; frozen dossier hashes/receipts требуют явной перепривязки к изменённому scope и применимого независимого принятия, не autoaccept. Сравнение DeGram/current DG, baseline study и benefit thresholds исключены из milestone. Design State/pre-post/evaluator agreement/recognition regression и OPEN v12 D08 сохраняются как самостоятельные обязательства, не product benchmark. Directory slug `1300-kontrakty-baseline-i-ownership` сохранён только как стабильный путь.

**Цель milestone:** участник проводит проектное требование от доступного источника через утверждённую редакцию правила, точную native-привязку и измеренную проверку к принятому решению; другой участник восстанавливает контекст и доказательства без чата автора.

Основание: [контекст](milestones/v13.0-CONTEXT.md), [51 MVP requirement](REQUIREMENTS.md), [ownership ledger](milestones/v13.0-OWNERSHIP.md), сохранённое [исследование, §§5, 7–11](../docs/reviews/degram-framework-integration/DEGRAM-FRAMEWORK-INTEGRATION-REVIEW.md). Канонический repo-relative путь исследования: `docs/reviews/degram-framework-integration/DEGRAM-FRAMEWORK-INTEGRATION-REVIEW.md`.

Требования/ownership и этот roadmap утверждены в отдельных gates ответами владельца «Продолжи» после представления каждого пакета; запись сохранена в requirements/context/ownership. Историческое approval 2026-09-30 разрешало scoped documentation commit без активации. Активация разрешена отдельным запросом владельца 2026-10-02; новая Git/deploy авторизация из неё не следует. Исследование не повторяется. Номера **1300–1307** заданы владельцем и имеют приоритет над обычной нумерацией GSD; добавочных фаз нет. В `.planning/config.json` granularity и phase_id_convention не заданы; используется sequential-форма заголовков с явно зарезервированными номерами, без изменения общей конфигурации.

## Границы и ownership

**Принятое repository решение 2026-10-04:** официальный fork `Erarchitech/degram` от `NousResearch/hermes-agent` подключается как pinned submodule `apps/degram`. DeGram — часть framework; канонические `.planning` и `DG_OBSIDIAN` едины. Контекст двусторонний и явный, graphify — локальные индексы и общий framework merge. Реализация этого решения отдельно разрешает GitHub fork, clone/submodule registration и workspace files, но не публикацию внутренних материалов, произвольный commit/push, deployment или изменение установленного Hermes. Ни одна фаза/requirement этим не закрывается. Runbook: `spec/degram/WORKSPACE.md`.

- DeGram в целевом объёме — минимальный fork Hermes Desktop; первый increment — read-only workspace в существующем `ui-v2` для будущей reused-web интеграции, не Desktop delivery. DG владеет корпоративными данными, авторизацией и правами проектов; полный Model Viewer сохраняется, reviewer может работать только в web.
- Initial scope: local single-user Compose, текущий ПК, Revit 2024 / Rhino 8; единственная системная пара `genpro` / `mimo-v2.5-pro` скрыта от обычных пользователей. Reviewer/второй ПК подключаются для поздней независимой приёмки, а не как prerequisite identity/spec до разработки. Сейчас разрешены bounded client code/offline tests и read-only CAD/graph surface, без live calls, paid inference, Drive/external/native writes. Поздние mutation/publication capabilities 1302–1306 сохранены за своими владельцами и отдельно авторизуются.
- Ontograph отвечает за термины компании, Metagraph — за правила одного проекта и их applicability, ComputGraph — за script/model bindings, ValidGraph — за проверенные состояния и runs, SpecGraph — за источники и основания решений. Runtime casing и профиль фиксируются в 1300, а не переименовываются молча. CDE хранит документы/редакции и принятые материалы; шестой граф и вторая CDE не создаются.
- Разрешённое чтение не требует подтверждения каждой операции. Proposal не даёт права записи. Mutation/publication требуют точного scope, проверки полномочий и подтверждения; LLM предлагает и объясняет, но не устанавливает compliance verdict и не утверждает своё предложение.
- Lessons learned — разрешённая копия внутри компании, с новым ID, происхождением, адаптацией и свежими доказательствами назначения; не перенос исходного verdict и не автоматическая синхронизация копий.
- **v12** сохраняет ownership нормативного runtime-основания: canonical status/evidence, parser subset, identity/replay/security и closure GH wire в 1205.1. **v11** сохраняет ownership runtime/V8 compatibility и нормативных mapping/partition/semantic contracts, publication bundle и manuscript/dissemination. **v13** реализует новые product API/store/UI для source/rule revisions, company vocabulary releases и lessons learned, HTTP addin path, bindings, states/decisions и bounded editing. Исправление потребляемого основания возвращается его владельцу; второго engine и двойного delivery owner нет.
- Перенесённые результаты v9.1/v10 и ORCH/RING сверяются с ledger в 1300; transfer/superseded не означает completed. Full historical topology и arbitrary persisted-snapshot diff, cluster internals, slot synthesis, extended structure rules и расширенная consultation остаются вне v13 у v10. Tag-specific undo в 1303 не дублирует generalized batch editing в 1305.
- Исключены universal graph CRUD, arbitrary CAD/Python/C# execution из LLM, whole-definition synthesis, universal IFC/IDS/SWRL compiler, full DesignSpaceGraph/event sourcing, скрытая передача между компаниями, обязательные vector DB/GraphRAG/multi-agent и обещание distributed CAD+DG transaction или универсальной детерминированности LLM. Текущее приложение Hermes пользователя и его профили не изменяются.

## Gates активации и внешних зависимостей

**Историческая активация control plane 2026-10-02:** «Активируй Milestone v13.0 и запусти /gsd-discuss-phase 1300». Она разрешала только planning/discussion; v12 закрыт административно с `gaps_found` и OPEN debt, архивы сохранены. **Последняя авторизация 2026-10-04** дополнительно разрешает независимый read-only client code/offline tests 1301 без blanket 1300-complete gate. Deploy, live DB/CAD/LLM/CDE, secret rotation, Git commit/stage/push/stash/branch/install и активация v9.1/v10/v11 не разрешены. Влияющий долг остаётся gate зависимой возможности; см. `.planning/v13.0-ACTIVATION.md`.

Проверенные prerequisites этой активации (см. `v13.0-ACTIVATION.md`; зависимые capability gates сохраняются):

1. Иметь отдельные записи утверждения полного requirements/ownership и этого roadmap.
2. Прочитать точные финальные артефакты **1205.1 verification, v12 milestone audit и формального v12 closeout**, подготовленные их владельцем. Проверка выполнена: v12 закрыт административно с accepted OPEN debt и `gaps_found`; bounded PASS 1205.1 не подменяет verdict всего milestone.
3. Проверить **accepted residual debt** относительно каждой потребляемой возможности v13: security/tenancy и credentials, canonical non-verdict/evidence delivery, identity/replay, runtime version/hash completeness, live CAD и recognition limitations. Override closeout не отменяет обязательную возможность. Для каждого влияющего долга нужны точная ссылка, владелец и проверенное disposition; критический пробел блокирует зависимый slice, а не получает PASS.
4. Получить отдельное разрешение активации v13. Оно получено 2026-10-02; архив сохранён. Planning-only boundary той активации дополнен последней bounded implementation авторизацией выше, не разрешением dependent/live возможностей.

**v11 — capability gate, не blanket dependency на весь milestone.** G-01 требует approved consumed V8 runtime/semantic profile с версиями/хешами и независимым техническим/owner acceptance; v11/v12 сохраняют normative ownership. Критическая несовместимость блокирует semantic consumption, соответствующую live операцию и выход 1300, но не независимый read-only client code/offline tests. Полное завершение manuscript/publication v11 и v4 BOT не требуется.

## Phases

- [ ] **Phase 1300: Контракты, проверка и ownership** — владелец принимает границы MVP, контрактный профиль, функциональные/контрактные fixtures DeGram и Viewer compatibility; dependent capability gates сохраняются.
- [ ] **Phase 1301: Рабочий клиент и безопасное чтение** — участник входит в DG, выбирает свой проект и native document, безопасно читает через локальные adapters и reused web.
- [ ] **Phase 1302: Источник, словарь и утверждённая редакция** — автор управляет source-linked правилами, а steward — release словаря; история и lessons learned имеют отдельные доказательства.
- [ ] **Phase 1303: Правило ↔ GH ↔ объект** — пользователь получает точную native-привязку и inspect/trace с совместимыми tagging, recognition и publication.
- [ ] **Phase 1304: Design State, проверка и review** — участник сохраняет и сравнивает проверяемые состояния, reviewer видит evidence, человек отдельно принимает решение.
- [ ] **Phase 1305: Ограниченное GH intent editing** — автор подтверждает KB-валидированный patch, получает undo/rollback, реальный solve и восстановимую публикацию.
- [ ] **Phase 1306: Межплатформенная передача** — получатель на другом ПК проверяет Revit counterpart, значения, выбранную зависимость и основания принятого решения, затем разрешённую передачу в CDE.
- [ ] **Phase 1307: Приёмка и выпуск** — владелец принимает либо отклоняет выпуск DeGram по correctness/safety/traceability/recovery gates и реальным E2E evidence.
- [ ] **Phase 1308: DG Web UI: язык интерфейса, роли участников, политика экспорта, сводки главной** — язык EN/RU (D-38), смена ролей участников (D-36), экран политики экспорта только для админа (D-37), сводки на главном экране; вне клиента DeGram.

## Порядок и capability prerequisites

**Capability integration order:** `1300 → 1301 → 1302 → 1303 → 1304 → 1305 → 1306 → 1307`; это порядок зависимого потребления/приёмки, не blanket запрет независимой разработки.

Независимый bounded read-only `ui-v2` client slice 1301 может разрабатываться и offline-тестироваться сейчас параллельно незавершённому 1300. Он не потребляет непринятые semantic/runtime гарантии и не открывает live доступ. G-01/V8, security и независимое ownership acceptance проверяются перед соответствующим потреблением; интеграционный retest не создаёт второго владельца требования.

| Переход | Необходимая capability и отсутствие обратной зависимости |
|---|---|
| 1300 → 1301 | Initial auth/LLM/deployment scope задан выше; независимые code/offline tests разрешены сейчас. Принятый применимый V8/security профиль и отдельная live авторизация обязательны перед реальным Revit/GH handshake и зависимым semantic consumption, не перед созданием client surface. |
| 1301 → 1302 | Действуют company/project context и scoped access. Проверка и утверждение lessons-learned копии выполняются существующими v12 validators и/или явной человеческой проверкой в допустимом scope со свежим evidence назначения; UI 1304 не требуется. Human review не подменяет отсутствующий machine verdict: non-verdict сохраняется. |
| 1302 → 1303 | Есть immutable rule revision, vocabulary pin и typed command/risk/confirm contract. Tag/recognition confirms используют существующий native undo/shared annotation service; generalized batch primitive 1305 не является prerequisite. |
| 1303 → 1304 | Точные binding и source trace позволяют захватить осмысленный state, измерить population/inputs и показать evidence. Basic reused web surface доставляется уже в 1301; contextual parity и полный review workflow принадлежат 1304. |
| 1304 → 1305 | Доступны pinned states/rules, канонические outcomes, разделённые local/publish/validation состояния operationId и repeat-validation workflow. 1305 добавляет безопасное исполнение native batch, а не второй operation-state engine. |
| 1305 → 1306 | Проверенный bounded edit/solve/read-back даёт источник параметрического изменения для handover; ранний Revit bridge из 1301 уже доступен. Revit write slice отдельно ограничен решением 1300. |
| 1306 → 1307 | Существуют сквозной артефакт, независимый recipient review и отдельно разрешённый CDE receipt; E2E acceptance проверяет functional correctness/safety/traceability/recovery всего заявленного slice, не только tool success. |

## Общий verification contract

Каждая фаза должна предъявить evidence по **каждому назначенному ID**: воспроизводимые inputs/fixtures, версии сборок/CAD/plugins/contracts, scope/company/project/document, команду или human-checkpoint protocol, expected/actual outcome, ссылки на raw evidence и read-back. Functional correctness/safety/traceability/recovery criteria, точные команды и human checkpoints определяются **до соответствующей проверки**, а не подгоняются под результат. Предварительная идентификация reviewer/второго ПК не блокирует независимую разработку.

Contract/unit и negative tests необходимы, но не заменяют live CAD, multi-user проверки, два ПК и review человеком. Evidence отделяет operational outcome, completeness/freshness, evaluator verdict и human acceptance. Пропуск, unsupported, timeout и human-needed не превращаются в PASS. Тексты исследования, диаграммы, успешный tool call и принятый roadmap не являются completion evidence. Изменения схем/API в будущих планах должны соблюдать CLAUDE.md: schema propagation, normative mapping/partition, evidence, SWRL subset, reproducibility и security-boundary contracts, без второго словаря статусов.

## Phase Details

### Phase 1300: Контракты, проверка и ownership

**Goal**: Владелец может определить разрешённый MVP и принять контрактный профиль, DeGram functional/contract fixtures и Viewer compatibility, не опираясь на неустранённые несовместимости или неявные обещания других milestones.
**Depends on**: Нет внутренних фаз v13; внешние gates активации и выбранного профиля v11/v12 описаны выше.
**Requirements**: DGCN-01, DGCN-02, DGCN-03, DGCN-04
**Success Criteria**:

1. Владелец принимает versioned профиль runtime ontology, identity, canonical status/evidence, rule/state revision и source authority с версиями/хешами, ответственными компонентами и решениями по критическим несовместимостям; normative ownership v11/v12 не подменён v13. [DGCN-01]
2. Владелец находит для каждого переносимого результата v9.1/v10 и ORCH/RING debt item единственного delivery owner, disposition и ссылку; заменённый OpenClaw spike и перенесённые результаты не предъявляются как выполненные. [DGCN-02]
3. Владелец может воспроизвести DeGram functional/contract fixtures на выбранных моделях/definitions, проверить версии CAD/plugins/контрактов/источников, expected outcomes, negative cases, evidence/read-back protocol и матрицу совместимости полного reused Viewer без контрольного product-study arm. [DGCN-03]
4. Оператор по утверждённому decision register однозначно определяет LLM/data policy, login/SSO, steward/approvers, deployment, CAD corpus, bounded Revit read/measurement/dependency и при необходимости write slice, CDE destination/publication path; unresolved решение явно блокирует зависящую реализацию. [DGCN-04]

**Plans**: 8 active plans — scope revision in progress; 1300-07 withdrawn, not completed. The active roster is listed below; phase-local dependency/wave revisions must agree before execution. Historical independent plan-check iteration 2 PASS applies only to its old scope, not this revision. No phase acceptance is claimed.

Plans:
**Wave 1**

- [ ] 1300-01-PLAN.md — Documentary evidence admission, fail-closed validator and negative fixtures

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 1300-02-PLAN.md — Clause-level ownership and source dispositions
- [ ] 1300-03-PLAN.md — Full consumed V8 draft profile and frozen discrepancies

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 1300-04-PLAN.md — Operational decisions, authority and bounded orchestration

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 1300-05-PLAN.md — DeGram functional/contract fixtures and expected outcomes
- [ ] 1300-06-PLAN.md — Full active V2 Viewer inventory and parity protocol

**Wave 5** *(after applicable revised prerequisites; not withdrawn plan 07)*

- [ ] 1300-09-PLAN.md — Actual V8 runtime/GH evidence and independent profile acceptance

**Wave 6** *(after active prerequisites including plan 09)*

- [ ] 1300-08-PLAN.md — Functional acceptance/release criteria and final evidence admission

Withdrawn: `1300-07-PLAN.md` is retained only as a non-executable historical marker, never a completion or dependency. Latest owner scope revision governs conflicting `1300-CONTEXT.md` D-01..27/old plan-check clauses. G-01/V8 and applicable independent acceptance gates remain OPEN until real evidence/checkpoints; full Viewer scope remains required. Old check `phases/1300-kontrakty-baseline-i-ownership/1300-PLAN-CHECK-2.md` does not certify revised plans or hashes.

**Entry gate**: Requirements/ownership и roadmap утверждены, v13 отдельно активирован после проверки точных v12 final artifacts и влияния residual debt; active scope revision теперь приоритетна. Владелец нормативного контракта участвует в принятии обязательного V8 consumed profile; отсутствие полного v11 closeout само по себе не препятствие.

**Verification evidence**: Принятый contract manifest; сверка source-ID dispositions с ownership ledger; воспроизводимые DeGram functional/contract fixtures с expected/actual outcomes, raw evidence и раскрытым долгом; полный Viewer compatibility matrix; decision register с решениями и полномочиями утверждающих. Static/offline validity не заменяет live evidence или независимое принятие.

**Exit gate**: Критические контрактные конфликты разрешены с владельцами; G-01/V8 принят независимо; ownership однозначен; обязательные для downstream решения приняты. Зафиксированы functional/contract fixtures, Viewer compatibility и correctness/safety/traceability/recovery criteria до их проверки. Будущие SSO/расширения inference/Revit writes требуют отдельного scope и evidence. Независимый client slice 1301 может идти до этого выхода, но не закрывает его.

**Обязательный decision register 1300**:

- LLM: единственная системная пара `genpro` / `mimo-v2.5-pro`, скрытая от обычного пользователя, без personal providers/keys/selector/fallback; paid inference сейчас не разрешён. Разрешённые данные/transport и фактический user-facing chat/tool-calling path проверяются отдельно; внутренний `/llm/generate` не считается готовым таким интерфейсом. Local orchestration и retained n8n получают явные границы ошибок/стоимости.
- Login: существующие разрешённые DG accounts/invitations или обязательный SSO; не объявлять SSO готовым и не расширять service-only полномочия пользовательского клиента.
- Governance: steward и approvers, отдельные company/project права, миграция scope и процедуры vocabulary release/retirement.
- Runtime: версии/хеши выбранного semantic profile, владельцы нормативных изменений и сверка влияющего долга.
- Deployment/CAD: local single-user Compose, текущий ПК, Revit 2024 / Rhino 8; exact read-only property/measurement slice. Reviewer и второй ПК — поздняя приёмка. Native writes и arbitrary code не разрешены в первом increment; будущий bounded write scope отдельно утверждается.
- CDE: Drive/external writes сейчас запрещены; будущие конкретный target, доступ источников/получателя, publish confirmation и read-back receipt остаются в 1306 под отдельной авторизацией.
- Acceptance: plan-layout, urban-block и project-documentation functional/contract fixtures, expected/actual outcomes, negative cases, traceability/recovery и Viewer compatibility matrix. Никакого paired/counterbalanced product-study protocol или benefit gate.

### Phase 1301: Рабочий клиент и безопасное чтение

**Goal**: Участник на поддержанном ПК безопасно входит в свой проект, открывает существующий DG web и получает snapshot выбранного локального документа без скрытого контекста и сервисных полномочий.
**Depends on**: Phase 1300 only for dependent semantic consumption/live operations and final acceptance; independent bounded client code/offline tests may start now.
**Requirements**: DGCL-01, DGCL-02, DGCL-03, DGCL-04, DGCL-05, DGCL-06, DGCL-07
**Success Criteria**:

1. Участник устанавливает минимальный DeGram на чистом поддержанном ПК, входит разрешённым способом DG и выбирает только доступный проект; company/project, native document и bridge status видимы, смена контекста отражается в следующем запросе. Системная пара `genpro` / `mimo-v2.5-pro` скрыта от обычного пользователя, без provider/model selector. Первый `ui-v2` increment не является доказательством Desktop install. [DGCL-01, DGCL-02]
2. Участник открывает существующие DG web-экраны и Model Viewer через изолированную web surface со scoped доступом, без обхода security headers и без токена на все модели; logout, revoke membership/credential прекращают новые защищённые read/write через chat, web и tools, не раскрывая чужой scope. [DGCL-03, DGCL-05]
3. На каждом из двух ПК участник явно выбирает конкретный локальный Revit/GH document и получает read snapshot через typed adapter; busy/off bridge даёт диагностируемый operational outcome, а не молчаливую подмену документа. [DGCL-04]
4. Участник отменяет долгий запрос, продолжает работу при недоступном provider/сервере или timeout и восстанавливает соединение по конкретной диагностике; native UI остаётся отзывчивым, listener освобождается корректно. [DGCL-06]
5. До LLM-вызова участник видит состав selection context, ограничения/сокращения/отсутствующие данные; whole-definition требует явного подтверждения, snapshot использует существующий serializer DG. [DGCL-07]

**Plans**: 40/41 plans executed
**UI hint**: yes

Plans:
**Wave 1**

- [x] 1301-01-PLAN.md — Bounded reused-web read-only workspace `ui-v2/#degram` (executed, offline-verified)
- [x] 1301-02-PLAN.md — Owner authorization + lockfile restore + Desktop/agent test baseline
- [x] 1301-03-PLAN.md — Revit adapter fork registered as pinned submodule `apps/revit-mcp` (D-09)
- [x] 1301-05-PLAN.md — DG company attribute + delegated user-scoped token (D-06, D-08, D-20)
- [x] 1301-06-PLAN.md — GH bridge document identity + BUSY bounded wait (D-13, D-14, D-18)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 1301-04-PLAN.md — Desktop runtime isolation: identity, home, updater off, NSIS target (D-01..D-04)
- [x] 1301-07-PLAN.md — Revit fork read-only allowlist, document identity, loopback fail-closed (D-10, D-11, D-13, D-23)
- [x] 1301-08-PLAN.md — Streaming LLM relay with export policy, consent, provenance, cancel (D-16..D-18)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 1301-09-PLAN.md — Server-side Speckle proxy, no token in browser (D-21)
- [x] 1301-10-PLAN.md — Agent lockdown: in-memory credentials, pinned provider, registry allowlist, per-scope profiles (D-06, D-16, D-19, D-22)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 1301-11-PLAN.md — degram toolset, CAD adapters, context composer, cancellable reads (D-11, D-13..D-15, D-17, D-18)
- [x] 1301-12-PLAN.md — Electron main: partition sign-in, DG view, token mint/handoff, heartbeat/revoke (D-05..D-08, D-19)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 1301-13-PLAN.md — Renderer shell: theme, i18n, hidden surfaces, sign-in/boot states, DG page, scope strip, project picker

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 1301-14-PLAN.md — Renderer chat: document picker, bridge status, Context card, consent/deny, stop/retry

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 1301-15-PLAN.md — Installer build, clean-install protocol, first-launch isolation, authorized push + gitlink bump *(2026-10-06 audit-fix: rebuilt `DeGram-Setup-0.1.0.exe` from `a9e56d7e` with the DeGram icon/version/vendor; launch beside an open Hermes Desktop proven (F-10); both `degram/phase-1301` branches pushed, gitlinks bumped, `workspace.py verify` passes; see 1301-BUILD.md)*

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 1301-17-PLAN.md — DeGram connector in the Connectors tab: user-bound pairing token (dgp_) exchanged for dgd_ (D-25, D-26)

**Gap closure 2026-10-09** (0.1.5 live run on PC1, gaps G-3..G-17, D-29)

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 1301-18-PLAN.md — Chat follows the scope profile; credentials-missing copy; locked surfaces quiet; UI-SPEC gap-round amendment (G-3, G-5, G-6, G-7)
- [x] 1301-22-PLAN.md — revit-mcp fork: IronPython 3.4 loading, extension enabled by default, text/plain POST bodies committed; CLEAN-INSTALL enable check (G-8..G-12)

**Wave 10** *(blocked on Wave 9 completion)*

- [x] 1301-19-PLAN.md — DeGram copy on failed turns; preview deadlines below the RPC timeout (G-4, G-14)

**Wave 11** *(blocked on Wave 10 completion)*

- [x] 1301-20-PLAN.md — Purge by project on revoke + visible toast, honest DG-unreachable boot, sign-out entries; D-30 legacy profiles (G-15, G-16, G-17)

**Wave 12** *(blocked on Wave 11 completion)*

- [x] 1301-21-PLAN.md — One pinned document per bridge (D-29, G-13)

**Wave 13** *(blocked on Wave 12 completion)*

- [x] 1301-23-PLAN.md — DeGram 0.1.6: owner push, gitlink bumps, build with the committed revit-mcp adapter, install on PC1

**Wave 14** *(blocked on Wave 13 completion)*

- [x] 1301-24-PLAN.md — Release left scope backends, foreground spawn, backend-start failure notice; revoked pairing as access signal + start probe; provider-limit copy; UI-SPEC 0.1.7 amendment (G-18, G-21, G-24)
- [x] 1301-29-PLAN.md — Commit the D-32 export-policy default (seven files only; no image rebuild)

**Wave 15** *(blocked on Wave 14 completion)*

- [x] 1301-25-PLAN.md — ui-v2 host mode inside DeGram: hide Connectors, DG API Docs, Reasoner, AI Engine; announce the chosen project; rebuild design-grammars (G-22, G-23, D-33, D-34)

**Wave 16** *(blocked on Wave 15 completion)*

- [x] 1301-26-PLAN.md — One start screen: sign-in, token field, project from the Projects region; persistent notices (G-20, G-21, G-22, D-33, D-35)

**Wave 17** *(blocked on Wave 16 completion)*

- [x] 1301-27-PLAN.md — Per-scope session list over RPC (G-19, G-6, D-31)

**Wave 18** *(blocked on Wave 17 completion)*

- [x] 1301-28-PLAN.md — DeGram 0.1.7: owner push, gitlink bump, build, install on PC1

**Wave 19** *(blocked on Wave 18 completion)*

- [ ] 1301-16-PLAN.md — Live acceptance: relay capability probe + DGCL-01..07 UAT on PC1 (resumes on 0.1.7)

**Wave 20** *(0.1.10 gap round, owner comments 2026-10-11)*

- [x] 1301-30-PLAN.md — DeGram access grants issued by project owner/DG admin; session exchange; pairing retired; specs (D-39)
- [x] 1301-31-PLAN.md — CONNECTORS: grant issuing for owners/admins, trimmed DeGram view with «Запросить новый токен» (D-39, D-40; offline verified, live acceptance pending plan 36)
- [x] 1301-32-PLAN.md — DG host-mode ring centre: connecting sphere, new-session pill, host<->page channel, lang (D-41, D-44; offline verified, live acceptance pending plan 36)

**Wave 21** *(blocked on 1301-30)*

- [x] 1301-33-PLAN.md — DeGram opens projects through the grant-backed session exchange; token UI removed (D-39)

**Wave 22** *(blocked on 1301-32, 1301-33)*

- [x] 1301-34-PLAN.md — DeGram shell stays on the ring; sidebar set; pill opens chats; no «DEGRAM» heading; scoped pins (D-41, D-42, D-44)

**Wave 23** *(blocked on 1301-34)*

- [x] 1301-35-PLAN.md — «Модели» screen for document choice, status-only strip; stop re-dialing left scopes (D-43, G-25)

**Wave 24** *(blocked on 1301-30..35)*

- [x] 1301-36-PLAN.md — DeGram 0.1.10: owner push, service rebuild with consent, build, Russian test guide

**Wave 25** *(0.1.11 fix round from the 0.1.10 UAT, 2026-10-11; 37 and 40 touch disjoint files)*

- [x] 1301-37-PLAN.md — Scope profiles never primary (boot toast); grant check before releasing the open scope; DG page follows the open project (F-03, F-07, D-48)
- [x] 1301-40-PLAN.md — Per-connector access requests (viewer requests, owner approves) and the DeGram connectors table with Вкл/Выкл (D-45, D-46)

**Wave 26** *(blocked on 1301-37)*

- [x] 1301-38-PLAN.md — Session list refilled whenever a scope becomes ready (F-04)

**Wave 27** *(blocked on 1301-38)*

- [x] 1301-39-PLAN.md — One caption-less connecting sphere in the ring centre; no DeGram loader on top (F-05, D-47)

**Wave 28** *(blocked on 1301-37..40)*

- [x] 1301-41-PLAN.md — DeGram 0.1.11: owner push, service rebuild with consent, build, Russian test guide

**Entry gate**: Независимый read-only `ui-v2` client code/offline tests разрешён сейчас в local single-user scope, пока 1300 incomplete. Перед semantic consumption/live handshake применимые G-01/V8/security gates и independent ownership acceptance должны быть приняты; blanket завершение всего 1300 для независимой разработки не требуется. Reviewer/второй ПК нужны для поздних acceptance criteria, не для predevelopment identity/spec. Service-only endpoint не используется как обход отсутствующего user-facing path.

**Verification evidence**: Clean-install protocol; живые GH/Revit read snapshots с document identity; записи context switch и bounded LLM payload без секретов; backend/model-access deny cases при revoke/logout и межпроектном/межкорпоративном доступе; live web navigation; cancel/reconnect/listener lifecycle evidence. Native calls выполняются с требуемым UI-thread marshalling.

**Exit gate**: Все назначенные ID подтверждены, нет скрытого выбора документа/проекта и утечки scope. Basic существующая web surface доступна сейчас; расширенный contextual review/parity из 1304 не требуется для этого выхода и не подменяется заявлением, что он уже завершён.

### Phase 1302: Источник, словарь и утверждённая редакция

**Goal**: Автор создаёт управляемое source-linked проектное правило, steward выпускает словарь компании, а принимающий проект независимо проверяет и утверждает lessons-learned копию с сохранённой историей.
**Depends on**: Phase 1301
**Requirements**: DGKN-01, DGKN-02, DGKN-03, DGKN-04, DGKN-05, DGKN-06, DGKN-07, DGKN-08, DGKN-09, DGKN-10
**Success Criteria**:

1. Автор связывает requirement/intent с доступной CDE SourceRevision (URI/ID, редакция/хеш, фрагмент, applicability); неформализуемый intent сохраняет явную границу проверки. Правило действует ровно в одном проекте на выбранные классы/объекты/условия, а общий company class не распространяет правило в другой проект. [DGKN-01, DGKN-07]
2. Участник использует видимый immutable vocabulary release своей компании с происхождением терминов; private/project drafts не утекают. Только steward выпускает рассмотренное предложение; project editor без полномочия получает отказ, retirement используемого термина сохраняет исторические ссылки. [DGKN-02, DGKN-03]
3. Автор видит typed diff create/edit/retirement с source/applicability, проверяет формализацию и отдельно подтверждает редакцию; два редактора получают atomic expectedRevision conflict без потери изменения, а серверный audit показывает actor, before/after и outcome принятой операции. [DGKN-04, DGKN-05]
4. Проверяющий восстанавливает полный executable ruleset, vocabulary/source revisions старого run после изменения/retirement; затронутые bindings/states/runs требуют повторной проверки, исторический verdict сохранён. Через единый typed `/dg-` registry участник получает аргументы/risk/help, deterministic dispatch без LLM, ранний отказ неверных аргументов и confirmation точного mutation/publication scope. [DGKN-06, DGKN-10]
5. Участник с разрешением source transfer и destination write создаёт копию в другом проекте той же компании с новым независимым ID, source project/rule revision, условиями и основанием передачи; принимающий автор адаптирует её и активирует лишь после свежей проверки и утверждения назначения. Исходный run не служит destination compliance evidence, изменения копий независимы. [DGKN-08, DGKN-09]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Scoped access 1301 проверен; соответствующие source-authority, vocabulary и revision clauses профиля 1300 согласованы с v11/v12. Назначены steward/approvers и разрешённые CDE sources. Новые product endpoints/store/UI принадлежат только v13.

**Verification evidence**: Source-linked rule и vocabulary release read-back; concurrent-editor CAS/audit tests; pin/retirement/history reconstruction; два проекта одной компании и deny cases другой компании/private terms; command schema/confirmation tests; fresh destination validation record и human approval lessons learned с проверкой независимости копий.

**Exit gate**: По каждому ID предъявлены evidence и нужное human acceptance. Lessons-learned проверка не ждёт 1304: существующие v12 validators и/или ручная проверка человеком обеспечивают свежие destination evidence в объявленном scope, сохраняя unsupported/not-checked и границу machine verdict. Отсутствие доказательств блокирует активацию копии, а не переносится на будущую UI-фазу.

### Phase 1303: Правило ↔ GH ↔ объект

**Goal**: Пользователь DG addin прослеживает requirement до точного native input и объекта, безопасно подтверждает существующие annotations/recognition и публикует результат без потери совместимости reference definitions.
**Depends on**: Phase 1302
**Requirements**: DGBN-01, DGBN-02, DGBN-03, DGBN-04, DGBN-05, DGBN-06
**Success Criteria**:

1. Пользователь addin читает нужные company/project данные через авторизованный HTTP repository path без рабочего доступа к Bolt и без service-only полномочий; exact binding связывает rule revision и atom/property с document/definition, component instance, parameter/port и object identity, а ambiguity, одинаковые имена и stale target дают отказ. [DGBN-01, DGBN-02]
2. Участник проходит inspect/trace от requirement/rule revision через ComputGraph entity и native input к объекту и обратно к source; authored/tagged, recognized/inferred и user-confirmed связи различимы, пробелы раскрыты. [DGBN-03]
3. Автор mark/tag selection через общий с существующими компонентами сервис/annotation grammar получает идемпотентный, undoable результат, который разбирается существующим serializer без второго формата. [DGBN-04]
4. Автор запускает существующее распознавание, просматривает предложения, частично принимает/отклоняет их; unrecognized остаются видимыми, отдельное подтверждение публикации показывает target project, revision и реально записанный результат. [DGBN-05]
5. Пользователь открывает согласованные reference `.gh` с прежними компонентами/GUIDs и получает эквивалентные успешные tagging/publish результаты без новых missing-component placeholders; заранее известные исключения, включая CONNECTOR post-825, перечислены явно. [DGBN-06]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Выход 1302 даёт pin/revision и typed risk/confirm contract; профиль identity/mapping/security согласован. Выбраны реальные reference definitions и зафиксирован recognition baseline с открытым качественным долгом, а не предполагаемым PASS.

**Verification evidence**: HTTP authorization/denial tests; exact identity/port fixtures и live GH trace; same-name/duplicate/stale negative cases; serializer parity и tag undo на живом canvas; partial recognition confirm, publish read-back и regressions старых `.gh`/GUIDs. Качество распознавания сравнивается с принятым baseline без сокрытия unrecognized.

**Exit gate**: Цепочка source→rule→native input→object и назначенные ID проверены. Tag-specific confirmation/undo используют существующий механизм native/shared annotation service: generalized batch engine 1305 не нужен для выхода и не создаётся здесь повторно. Ownership старого recognition debt сохраняется; успешный workflow не объявляет его закрытым автоматически.

### Phase 1304: Design State, проверка и review

**Goal**: Автор и web-only reviewer видят полноту входов, проверяемые версии состояния и канонические evidence, сравнивают допустимые альтернативы и отдельно фиксируют человеческое принятие решения.
**Depends on**: Phase 1303
**Requirements**: DGST-01, DGST-02, DGST-03, DGST-04, DGST-05, DGST-06, DGST-07
**Success Criteria**:

1. Автор сохраняет неизменяемую capture revision с task/alternative context, document/definition identity, native snapshot/projection version, pinned ruleset и bindings; проверяющий видит expected/observed population и наличие/freshness входов, поэтому пустая выборка, пропущенные объекты и stale данные не выглядят полным успехом. [DGST-01, DGST-02]
2. Проверяющий получает от применимого evaluator канонический result/evidence с измеренными значениями/units, input versions и declared scope; unsupported/not-checked отличны от operational failure, а SHACL/OWL/tool success не подменяют compliance. [DGST-03]
3. По operationId участник видит раздельные local change, publication и validation outcomes; после timeout/failed publish выясняет фактическое состояние и безопасно продолжает без слепого повторения local mutation. [DGST-04]
4. Участник сравнивает варианты только в объявленных task/design-space и версии критериев, видит несовместимые snapshots/ruleset scopes; уполномоченный человек отдельно от verdict принимает вариант с rationale, доступными альтернативами, source/rule/state/run references и actor/approver/time. Временной порядок не выдаётся за reformulation, отсутствующее основание не выдумывается. [DGST-05, DGST-06]
5. Reviewer, включая web-only пользователя, в полном reused Model Viewer открывает нужные project/run/state, объекты, правила, evidence и сопоставимые альтернативы; вся утверждённая в 1300 матрица parity проходит без скрытой замены существующих функций read-only заглушками. [DGST-07]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Exact bindings и trace 1303 проверены; выбранные v12 evaluator/status/evidence и replay capabilities действительно доступны, долг по hash/projection scope оценён. Historical ruleset 1302 и Viewer parity matrix 1300 приняты.

**Verification evidence**: Versioned capture/read-back и distinct-definition cases; population/freshness negative tests; raw evaluator evidence по каноническому контракту, включая non-verdict; fault injection local/publish boundary и operationId status lookup на доступных операциях; comparison fixtures; human acceptance record; browser-only Viewer UAT по всей parity matrix.

**Exit gate**: Все назначенные ID проверены; отсутствуют silent pass при неполноте, смешение compliance/publication и фиктивное принятие LLM. Operation reconciliation проверен на уже доступных операциях и не зависит от будущего generalized editing 1305. Наличие task context не объявляется реализацией full DesignSpaceGraph или historical topology v10.

### Phase 1305: Ограниченное GH intent editing

**Goal**: Автор безопасно изменяет существующий visual block по intent, видит реальный результат solve и получает revisioned republish с доказательствами фактических изменений.
**Depends on**: Phase 1304
**Requirements**: DGED-01, DGED-02, DGED-03, DGED-04, DGED-05, DGED-06, DGED-07, DGED-08
**Success Criteria**:

1. Автор проверяет реальные GUID/ports/types/access/defaults компонента в versioned KB согласованного corpus; отсутствующий компонент/capability явно unsupported, несовместимый connection/value отклоняется до canvas change, разрешённая операция сохраняет KB provenance без заявления compliance. [DGED-01, DGED-02]
2. Автор получает ограниченный old→new patch существующего блока с add/remove/rewire/value/group operations, затронутыми элементами и сохраняемыми инвариантами, видит preview на canvas; writes по умолчанию off, apply возможен лишь после включения и подтверждения, cancel не меняет definition. Whole-definition synthesis не предлагается как поддержанная. [DGED-03, DGED-04]
3. Подтверждённый batch создаёт один undo record, ошибка возвращает полный pre-state без изменения нецелевых элементов; stale document/revision/target даёт structured refusal, повтор operationId сначала разрешает неопределённый outcome и не применяет batch второй раз. [DGED-05, DGED-06]
4. После apply автор получает реальный solve/read-back величин и ошибок, а связанные правила проходят повторную проверку; успех native patch сам по себе не считается вычислением или compliance. [DGED-07]
5. Автор отдельно подтверждает revisioned republish с pre/post snapshots и exact applied-change record; publisher-owned stale bindings reconciled, чужие связи сохранены, failed publish восстановим, локальный Undo не стирает опубликованную историю. [DGED-08]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Выход 1304 подтверждает state/evidence/reconciliation workflow; KB corpus, permitted native writes, инварианты и revision preconditions утверждены. Transferred CKBS/BWRT/SEDT outcomes имеют одного владельца v13 согласно ledger.

**Verification evidence**: KB/component inventory с реальными native metadata; schema/type/access negative tests; live preview/cancel/apply/undo; injected mid-batch failure с pre-state comparison и non-target invariants; stale/retry/no-double-apply cases; live solve/read-back + повторная проверка; publish failure/retry/read-back и проверка сохранности чужих edges/истории.

**Exit gate**: Все назначенные ID доказаны на bounded existing-block corpus. Generalized batch guarantee доставлен здесь, consuming risk contract 1302 и operation-state seam 1304. Минимальные operation/pre-post evidence не называются WPER arbitrary historical diff, distributed transaction или поддержкой SGEN/cluster internals.

### Phase 1306: Межплатформенная передача

**Goal**: Получатель на ПК B с реальным Revit независимо восстанавливает объект, проверяет согласованный параметрический slice и основания решения из проектного артефакта, после чего подтверждает разрешённую публикацию в CDE.
**Depends on**: Phase 1305
**Requirements**: DGHN-01, DGHN-02, DGHN-03, DGHN-04, DGHN-05
**Success Criteria**:

1. Получатель на ПК B разрешает выбранный native counterpart GH-объекта с ПК A через identity registry и source/document provenance; duplicate document, missing counterpart и ambiguity дают явный outcome вместо случайного совпадения имени. [DGHN-01]
2. Получатель читает согласованный typed property/measurement slice с исходными и нормализованными units; конфликт GH/Revit сохраняет оба source-attributed значения до решения уполномоченного человека. [DGHN-02]
3. На live модели получатель проверяет ожидаемую реакцию выбранной зависимости на изменение параметра и сохранность согласованных инвариантов; unsupported зависимости исключены явно, mapping или совпадение геометрии сами по себе не доказательство сохранённого intent. [DGHN-03]
4. Другой участник без исходного chat transcript восстанавливает source, rule, applicability, выбранный вариант, rationale и evidence из проектного артефакта; результат подтверждает получатель, а не авторский пересказ. [DGHN-04]
5. Уполномоченный участник подтверждает передачу принятого артефакта в выбранную CDE destination и видит revision/read-back receipt; ошибка публикации видима, доступ получателя сохраняется, DeGram не становится второй системой документов. [DGHN-05]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Предыдущие фазы приняты; реальные GH ПК A/Revit ПК B и разрешённые источники доступны. В 1300 утверждены exact measurement/dependency/invariant slice, режим ручных либо bounded Revit writes, CDE target и полномочия. Нельзя расширять Revit write scope только ради прохождения теста.

**Verification evidence**: Live двухкомпьютерные identity/read-back records; duplicate/missing/ambiguous counterexamples; исходные и нормализованные units; pre/post measurements и независимая проверка инвариантов; recipient reconstruction protocol без чата автора; CDE receipt и read-back прав получателя, включая отказ/сбой публикации.

**Exit gate**: Все назначенные ID проверены получателем в объявленном slice. Невыполненный live dependency test не заменяется registry demo или synthetic API response; нерешённый конфликт значений не скрывается. Успех handover не расширяет support за пределы согласованной зависимости.

### Phase 1307: Приёмка и выпуск

**Goal**: Владелец принимает либо отклоняет выбранную сборку DeGram по E2E correctness/safety/traceability/recovery gates, а оператор воспроизводит безопасную установку, обновление и откат на двух ПК.
**Depends on**: Phase 1306
**Requirements**: DGRL-01, DGRL-02, DGRL-03, DGRL-04
**Success Criteria**:

1. Владелец получает воспроизводимый DeGram E2E acceptance report по утверждённым plan-layout, urban-block и project-documentation fixtures: functional/contract correctness, false-pass/false-fail/non-verdict, traceability, handover и recovery; expected/actual outcomes, raw evidence и неудачные попытки сохранены без второго product-study arm. [DGRL-01]
2. Оператор предъявляет live governance/security/recovery evidence для двух компаний и двух проектов одной компании, concurrent editors, revoked access, source/scribble injection, missing population, stale patch и timeout после apply/до publish; скрытых неразрешённых side effects нет. [DGRL-02]
3. Оператор устанавливает, обновляет и откатывает выбранные DeGram/DG adapters на двух поддержанных ПК по compatibility manifest, сохраняя проектный контекст и не раскрывая credentials в поставке/логах. [DGRL-03]
4. Владелец принимает либо отклоняет выпуск по заранее утверждённым correctness/safety/traceability/recovery gates, raw evidence, known limitations и remaining debt; tool success не заменяет gate, незавершённая проверка не получает PASS. Порог сравнительной пользы не требуется. [DGRL-04]

**Plans**: TBD
**UI hint**: yes

**Entry gate**: Заявленные release capabilities 1300–1306 имеют phase evidence и human checkpoints; functional/contract fixtures, Viewer compatibility и correctness/safety/traceability/recovery criteria заморожены до E2E acceptance. Изменения protocol/scope требуют новой привязки hashes/receipts и повторной применимой проверки, не post-hoc PASS.

**Verification evidence**: Raw DeGram E2E runs с versioned backend/rules/models/contracts, expected/actual outcomes и всеми failure attempts; recipient evidence; отдельно разрешённая live security/recovery matrix; compatibility/build manifests, clean install/update/rollback на двух ПК и secret checks; owner release decision со ссылками на каждый gate и долг. Контрольный current-DG arm и benefit metrics отсутствуют.

**Exit gate**: Evidence pack и решение владельца полны; положительный выпуск разрешён только при выполнении заранее утверждённых gates. Неуспешная E2E приёмка даёт no-go, а не ложное закрытие acceptance. Необработанный human-needed/FAIL остаётся открытым. Фактическая публикация/активация сборки — отдельное разрешённое действие.

## Progress

| Phase | Plans Complete | Status | Completed |
|---|---|---|---|
| 1300. Контракты, проверка и ownership | 0/8 active | Incomplete — scope revision; 1300-07 withdrawn, not complete; acceptance OPEN | — |
| 1301. Рабочий клиент и безопасное чтение | 40/41 | In Progress|  |
| 1302. Источник, словарь и утверждённая редакция | 0/TBD | Not started | — |
| 1303. Правило ↔ GH ↔ объект | 0/TBD | Not started | — |
| 1304. Design State, проверка и review | 0/TBD | Not started | — |
| 1305. Ограниченное GH intent editing | 0/TBD | Not started | — |
| 1306. Межплатформенная передача | 0/TBD | Not started | — |
| 1307. Приёмка и выпуск | 0/TBD | Not started | — |

## Coverage и передача управления

Единственный delivery mapping задаётся строкой **Requirements** каждой фазы и совпадает с traceability в active `REQUIREMENTS.md`. Исторический `milestones/v13.0-REQUIREMENTS.md` не переопределяет active revision. Ссылки в Success Criteria — проверка покрытия, не повторное назначение владельца; поздние retests потребляют прежний результат.

| Phase | Требований | Success Criteria |
|---|---|---|
| 1300 | 4 | 4 |
| 1301 | 7 | 5 |
| 1302 | 10 | 5 |
| 1303 | 6 | 5 |
| 1304 | 7 | 5 |
| 1305 | 8 | 5 |
| 1306 | 5 | 5 |
| 1307 | 4 | 4 |

**Проверяемые инварианты roadmap:** ровно 8 фаз 1300–1307; все 51 MVP ID назначены ровно один раз; ни одного нового/пропущенного ID; назначение совпадает с requirements; у каждой фазы 2–5 наблюдаемых критериев, вместе ссылающихся на все её IDs; внутренний dependency graph ацикличен. Это структурная проверка планирования, не выполнение 51 требований.

**Текущий gate:** 1300 incomplete / scope revision; 1300-07 withdrawn, не completed. Независимый read-only client slice 1301 in progress; не Desktop delivery и не release-ready. G-01/V8, independent ownership acceptance и OPEN debt остаются capability gates для semantic consumption/live work. Исторические PASS/hashes не переносятся на изменённый scope автоматически.

**Открытые риски:** accepted v12 debt может блокировать конкретный slice. V8 runtime evidence/independent acceptance, security readiness, fixture/Viewer evidence и будущие отдельно разрешаемые write/CDE/handover capabilities остаются непроверенными. Initial system pair/local deployment/CAD choices заданы выше, не открываются заново. Research findings и исторические PROJECT/MILESTONES записи не доказывают устранение проблем; reviewer подключается для поздней независимой приёмки.

### Phase 1308: DG Web UI: язык интерфейса, роли участников, политика экспорта, сводки главной

**Goal:** администратор и участники проекта работают с DG Web UI на выбранном языке (EN/RU), админ управляет политикой экспорта проекта, владелец меняет роли участников, а главный экран показывает сводные данные модулей; вынесено из live-приёмки 1301 (решение владельца 2026-10-10, не часть клиента DeGram).
**Requirements**: WEBUI-01, WEBUI-02, WEBUI-03, WEBUI-04, WEBUI-05, WEBUI-06, WEBUI-07, WEBUI-08, WEBUI-09, WEBUI-10, WEBUI-11
**Depends on:** Phase 1301 (находки live-приёмки: D-36, D-37, D-38, образ data-service с D-32)
**Plans:** 15/24 plans executed

Plans:
**Wave 1**

- [x] 1308-01-PLAN.md — settle owner WIP on files 1308 edits (D-49, decision checkpoint)
- [x] 1308-02-PLAN.md — data-service: PUT member role (last-owner guard) + GET project summary, spec rows
- [x] 1308-03-PLAN.md — data-service: dgk_ connector session store + owner/admin exemption helpers (TDD)
- [x] 1308-04-PLAN.md — DG.Core ConnectorSessionClient (account sign-in, dgk_ prefix, templates)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 1308-05-PLAN.md — ui-v2 i18n core driven by DeGram (#degram-lang / ?lang=) or primary browser language, no control; coverage rules and raw-text guard
- [x] 1308-06-PLAN.md — data-service: dgk_ resolver + POST/DELETE /auth/connector-session, fixture seam, spec
- [x] 1308-07-PLAN.md — Grasshopper CONNECTOR account sign-in (new GUID, gate), Session → VALIDATOR/COMPUTGRAPH PUBLISH
- [x] 1308-08-PLAN.md — d49_store_cleanup.py (token retirement + UAT account removal, dry-run default, TDD)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 1308-09-PLAN.md — data-service: owner/admin exemption everywhere + 410 on credentials (reversibility gate)
- [x] 1308-10-PLAN.md — ui-v2 Projects: role Select + admin-only Project settings (export policy)
- [x] 1308-12-PLAN.md — ui-v2 translation: Graph area
- [x] 1308-16-PLAN.md — ui-v2 translation: Reasoner, LLM model (title rename), API docs chrome, DeGram grants panel, lib messages
- [x] 1308-23-PLAN.md — ui-v2 landing translated (owner-fixed hero strings, LLM model label, live relayout on dg-lang)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 1308-11-PLAN.md — ui-v2 landing summaries + shared run grouping
- [x] 1308-13-PLAN.md — data-service: legacy-token tests moved to dgk_, heartbeat/capture on sessions, legacy prefix refused, spec blocks

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 1308-14-PLAN.md — ui-v2 translation: Model area
- [ ] 1308-24-PLAN.md — data-service: session-based connector status, legacy helpers removed, D-33 cascades incl. invite paths

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 1308-15-PLAN.md — ui-v2 Connectors screen, DeGram-hosted table and API docs without tokens

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 1308-22-PLAN.md — ui-v2 translation: App shell, DeGram host workspace, primitives + completeness gate and font check

**Wave 8** *(blocked on Wave 7 completion)*

- [ ] 1308-17-PLAN.md — DeGram sidebar «Projects»: ui-v2 host signal + component commit (authorization checkpoint)

**Wave 9** *(blocked on Wave 8 completion)*

- [ ] 1308-19-PLAN.md — live: D-32 closure, rebuild from git archive HEAD (human-verify)
- [ ] 1308-21-PLAN.md — DeGram: one language setting (Русский/English only, live #degram-lang to the DG page, RU catalog complete), component commit

**Wave 10** *(blocked on Wave 9 completion)*

- [ ] 1308-18-PLAN.md — owner pushes the fork; gitlink bump + workspace verify
- [ ] 1308-20-PLAN.md — live: backup, dry run, apply cleanup (human-verify), owner actions

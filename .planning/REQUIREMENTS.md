# Requirements: v13.0 DeGram Agent

**Подготовлено:** 2026-09-30
**Статус:** ACTIVE — scope revised 2026-10-04 по последнему запросу владельца. Phase 1300 остаётся incomplete / scope revision; независимый read-only slice Phase 1301 в `ui-v2` — in progress, не готов к выпуску. Ни одно требование не закрыто.
**Core value:** участник проводит проектное требование от источника до проверенного и принятого решения, а получатель восстанавливает его контекст и доказательства без истории чата автора.

Основание: [согласованный контекст](milestones/v13.0-CONTEXT.md), [распределение ownership](milestones/v13.0-OWNERSHIP.md) и сохранённое исследование, указанное в контексте. Чекбоксы обозначают реализацию с доказательствами; утверждение этого документа не закрывает ни одного требования.

**Authority:** Последняя ревизия active control plane имеет приоритет над историческим preparation package, прежними решениями discussion и plan-check PASS. Архив не переписывается; прежние frozen dossier hashes/receipts требуют явной перепривязки к изменённому scope и повторного принятия затронутых обязательств, а не autoaccept. Сравнение DeGram с current DG, baseline study и benefit thresholds исключены из v13. Сравнение Design States, pre/post, evaluator agreement и recognition regression, включая OPEN v12 D08, сохраняется: это не product benchmark.

## Границы MVP

- Целевая оболочка — минимальный fork Hermes Desktop; первый реальный increment — read-only workspace в существующем `ui-v2` для будущей reused-web интеграции, не сам Desktop. Корпоративные данные/права — DG; полный Model Viewer сохраняется.
- Начальный deployment scope: local single-user Compose, текущий ПК, Revit 2024 / Rhino 8. Reviewer и второй ПК — поздняя независимая приёмка, не prerequisite идентичности/спецификации перед разработкой. Единственная системная пара `genpro` / `mimo-v2.5-pro` скрыта от обычного пользователя; без selector/private keys/fallback и без paid inference в текущей работе.
- Сейчас разрешены только независимые client code/offline tests и CAD/graph read surface; live вызовы, Drive/external writes и native mutations не разрешены. Поздние write/publication возможности требований сохранены за их phase owners и требуют отдельной авторизации; read-only increment не закрывает их.
- Общий словарь компании; проектные правила и проектная применимость. Права пользователя и область применения правила — разные проверки.
- Lessons learned между проектами одной компании: разрешение → копия с происхождением → адаптация → проверка → утверждение. Исходные проверки не переносятся как доказательство соответствия нового проекта.
- Пять графов сохраняют ответственность; CDE хранит документы/редакции и принятые материалы, а не заменяется DeGram.
- Read выполняется в разрешённой области; proposal сам по себе не разрешает запись. LLM не устанавливает compliance verdict и не утверждает собственное предложение.
- Исторические ограничения v9/v12 и исследовательские наблюдения проверяются применимыми functional/contract/regression fixtures, а не объявляются уже устранёнными.

## MVP requirements

### Контракты, проверка и ownership — DGCN

- [ ] **DGCN-01**: Владелец может принять версионированный контрактный профиль, который указывает версии/хеши runtime ontology, identity, status/evidence, rule/state revision и source-authority контрактов, ответственный компонент каждой границы и решение по каждой критической несовместимости с v11/v12.
- [ ] **DGCN-02**: Владелец может проверить единственного delivery owner каждого переносимого результата v9.1/v10 и каждого ORCH/RING debt item; перенесённый или заменённый результат имеет disposition и ссылку, а не ложную отметку completed.
- [ ] **DGCN-03**: Владелец может утвердить воспроизводимые функциональные и контрактные fixtures DeGram: задания, модели/definitions, версии CAD/plugins/контрактов, источники, expected outcomes и negative cases, evidence/read-back protocol и матрицу совместимости полного reused Model Viewer; проверка не требует контрольной группы или метрик сравнительной пользы.
- [ ] **DGCN-04**: Оператор может определить разрешённую конфигурацию MVP по утверждённому decision register: LLM/data policy, login/SSO, steward/approvers, поддержанные Revit operations, CDE publication path и ограничения deployment; unresolved решение блокирует зависящую от него реализацию.

### Рабочее место и безопасное чтение — DGCL

- [ ] **DGCL-01**: Участник может установить минимальный DeGram Desktop на чистом поддержанном ПК, войти существующим разрешённым способом DG и выбрать только доступный ему проект. Plan 1301-30 supplies the server-side grant/session-exchange path; client installation and owner acceptance remain pending.
- [ ] **DGCL-02**: Участник видит действующие company/project, native document и bridge status; смена контекста явно отражается в следующем запросе, без переиспользования скрытого контекста другого проекта. Единственная системная пара `genpro` / `mimo-v2.5-pro` управляется оператором и скрыта от обычного пользователя; пользователь не выбирает provider/model и не вводит private keys.
- [ ] **DGCL-03**: Участник может открыть в DeGram существующие DG web-экраны и Model Viewer через изолированную web surface с разрешённым доступом; обход iframe/security headers или расширение токена до всех моделей не требуется.
- [ ] **DGCL-04**: Участник на каждом из двух ПК может выбрать конкретный локальный Revit/GH document и получить read snapshot через локальный typed adapter; выключенный/занятый bridge выдаёт диагностируемый operational outcome, другой документ не выбирается молча.
- [ ] **DGCL-05**: После logout, отзыва membership или credential участник теряет возможность новых защищённых чтений/записей; клиент, backend и model access проверяют company/project scope и не возвращают данные недоступного проекта через чат, web surface или tools. Plan 1301-30 enforces the backend grant/session revocation leg; client, relay, model-access, and live acceptance evidence remain pending.
- [ ] **DGCL-06**: Участник может отменить долгий запрос и продолжить работу; недоступный provider/сервер, timeout и lifecycle reconnect дают конкретную причину и способ восстановления, сохраняя отзывчивость native UI и корректное освобождение локального listener.
- [ ] **DGCL-07**: Участник видит состав и ограничение отправляемого LLM selection context; whole-definition scope требует явного подтверждения, сокращение/отсутствие данных раскрывается, а чтение selection использует существующую сериализацию DG.

### Источники, компания, проект и lessons learned — DGKN

- [ ] **DGKN-01**: Автор может связать requirement/intent с доступной CDE SourceRevision: URI/идентификатор, редакция/хеш, фрагмент и applicability; неформализуемый intent сохраняется с явной границей проверки вместо выдуманного исполняемого правила.
- [ ] **DGKN-02**: Участник проекта может использовать выбранный неизменяемый release словаря своей компании; release и происхождение термина видимы, private/project draft terms не раскрываются другому проекту или компании без разрешения.
- [ ] **DGKN-03**: Уполномоченный steward может рассмотреть и выпустить предложение изменения корпоративного словаря; editor проекта без этого полномочия получает отказ, а используемый термин выводится из обращения с сохранением исторических ссылок.
- [ ] **DGKN-04**: Автор может предложить создание, изменение или retirement проектного правила как typed diff с source/applicability, проверить его формализацию и отдельно подтвердить новую редакцию; действующая редакция меняется только через разрешённую операцию.
- [ ] **DGKN-05**: Два редактора получают определённый результат optimistic concurrency: запись с устаревшим expectedRevision отклоняется без потери чужого изменения; серверный audit связывает принятую операцию, actor, before/after revisions и outcome.
- [ ] **DGKN-06**: Проверяющий может восстановить полный исполняемый ruleset, vocabulary release и source revision старой проверки после последующего изменения/retirement правила; новая редакция показывает затронутые bindings/states/runs как требующие повторной проверки, сохраняя исторический verdict.
- [ ] **DGKN-07**: Автор может задать область правила внутри ровно одного проекта по выбранным классам, объектам и условиям; общность класса компании не делает проектное правило действующим в других проектах.
- [ ] **DGKN-08**: Участник с разрешением передачи источника и записи назначения может создать lessons-learned копию правила в другом проекте той же компании; фиксируются source project/rule revision, условия применения, основание передачи и новый независимый идентификатор.
- [ ] **DGKN-09**: Автор принимающего проекта может адаптировать копию и активировать её только после проверки и утверждения в этом проекте; исходный run не используется как подтверждение соответствия назначения, а последующие изменения любой копии не меняют другую.
- [ ] **DGKN-10**: Участник может выполнить опубликованную typed `/dg-` команду через единый реестр аргументов/риска/help без LLM-dispatch; read выполняется сразу, mutation/publication показывает точный scope и требует подтверждения, неверные аргументы отклоняются до исполнения.

### Правило ↔ GH ↔ объект — DGBN

- [ ] **DGBN-01**: Пользователь DG addin может читать необходимые корпоративные/project данные через авторизованный HTTP repository path без доступа рабочего места к Bolt и без выдачи пользовательскому клиенту service-only полномочий.
- [ ] **DGBN-02**: Автор может привязать конкретный rule revision и atom/property к точному native parameter/port с company/project, document/definition, component instance и object identity; одинаковые имена, неоднозначность или stale target дают отказ вместо произвольной привязки.
- [ ] **DGBN-03**: Участник может пройти inspect/trace от требования и редакции правила к ComputGraph entity, native input и объекту, а обратно — к источнику; ответ различает authored/tagged, recognized/inferred и user-confirmed связи и указывает пробелы.
- [ ] **DGBN-04**: Автор может mark/tag selection через команды, использующие общий с существующими компонентами сервис и annotation grammar; результат идемпотентен, undoable и разбирается существующим serializer без второго формата.
- [ ] **DGBN-05**: Автор может вызвать существующее распознавание, просмотреть и частично принять/отклонить предложения; unrecognized элементы остаются видимыми, а подтверждённая публикация показывает целевой проект, revision и фактически записанный результат.
- [ ] **DGBN-06**: Пользователь может открыть существующие reference `.gh` с прежними компонентами/GUIDs и получить эквивалентные успешные tagging/publish результаты; исключения совместимости явно перечислены, новые missing-component placeholders не вводятся.

### Состояния, проверка и принятие решения — DGST

- [ ] **DGST-01**: Автор может сохранить Design State с task/alternative context, document/definition identity, native snapshot/projection version, pinned ruleset и bindings; новая capture revision не подменяет предыдущую и не смешивается с состоянием другого definition.
- [ ] **DGST-02**: Проверяющий видит expected/observed population и наличие/freshness входов для заданной задачи/стадии; пустая выборка, пропущенные объекты или stale данные не отображаются как полный успешный результат.
- [ ] **DGST-03**: Проверяющий получает канонический result и evidence от применимого evaluator с измеренными значениями/units, input versions и declared scope; unsupported/not-checked и operational failure сохраняют различие, SHACL/OWL/tool success не подменяют design compliance.
- [ ] **DGST-04**: Участник видит отдельно состояние локального изменения, публикации и проверки для operationId; после timeout/failed publish может выяснить фактическое состояние и безопасно продолжить без повторного слепого применения local mutation.
- [ ] **DGST-05**: Участник может сравнить варианты в явно заданном task/design-space и версии критериев; несовместимые snapshots/ruleset scopes обозначаются, временной порядок capture не выдаётся за семантическую эквивалентность или reformulation.
- [ ] **DGST-06**: Уполномоченный человек может отдельно от verdict принять вариант и сохранить краткое rationale, рассмотренные альтернативы при наличии, source/rule/state/run references, actor/approver/time; отсутствующее основание не генерируется как факт.
- [ ] **DGST-07**: Reviewer может в полном reused Model Viewer, в том числе web-only, открыть соответствующий проект/run/state, проверить объекты, правила, evidence и сопоставимые альтернативы; утверждённая в 1300 матрица parity существующих функций проходит без скрытых замен read-only заглушками.

### Ограниченное GH intent editing — DGED

- [ ] **DGED-01**: Автор может проверить наличие компонента и его фактических GUID/ports/types/access/defaults в versioned KB для согласованного набора reference definitions; отсутствующая возможность обозначается unsupported, а не выдумывается LLM.
- [ ] **DGED-02**: Автор получает отказ до изменения canvas для несовместимого connection/value по KB и schema; разрешённая операция сохраняет provenance версии KB, не выдавая KB validity за compliance.
- [ ] **DGED-03**: Автор может по intent получить ограниченный old→new patch существующего visual block: add/remove/rewire/value/group operations с перечислением затронутых элементов и сохраняемых инвариантов; whole-definition synthesis не предлагается как поддержанная операция.
- [ ] **DGED-04**: Автор может просмотреть patch на canvas и подтвердить его только при включённых native writes (по умолчанию off); отмена оставляет definition неизменным, даже если LLM предложила действие.
- [ ] **DGED-05**: Подтверждённый batch применяется одним undo record; ошибка внутри batch восстанавливает pre-state без частично изменённого блока, а нецелевые элементы остаются неизменными.
- [ ] **DGED-06**: Автор получает structured refusal для stale document/revision/target; повтор operationId сначала разрешает неопределённый outcome и не выполняет native batch второй раз.
- [ ] **DGED-07**: Автор после изменения видит результат реального solve и read-back величин/ошибок; успешное применение patch не заменяет вычисление и повторную проверку связанных правил.
- [ ] **DGED-08**: Автор может подтвердить revisioned republish с pre/post snapshot и exact applied-change record; stale publisher-owned bindings reconciled, чужие связи сохранены, сбой публикации явно восстанавливаем, локальный Undo не стирает опубликованную историю.

### Межплатформенная передача — DGHN

- [ ] **DGHN-01**: Получатель на ПК B с реальным Revit может разрешить выбранный native counterpart объекта из GH на ПК A по identity registry и source/document provenance; дубликат документа, missing counterpart или неоднозначность даёт явный результат, а не случайное совпадение имени.
- [ ] **DGHN-02**: Получатель может прочитать согласованный typed property/measurement slice с исходными и нормализованными units; конфликт GH/Revit значений сохраняет оба source-attributed значения до решения уполномоченного человека.
- [ ] **DGHN-03**: Получатель может проверить на live модели ожидаемую реакцию согласованной зависимости на изменение параметра и сохранность заданных инвариантов; неподдержанные зависимости явно исключены, mapping или одинаковая геометрия сами по себе не считаются сохранением intent.
- [ ] **DGHN-04**: Другой участник может восстановить источник, правило, applicability, выбранный вариант, rationale и evidence по проектному артефакту без доступа к исходному chat transcript; проверка проводится получателем, а не автором пересказа.
- [ ] **DGHN-05**: Уполномоченный участник может подтвердить передачу принятого артефакта в согласованную CDE destination с revision и read-back receipt; ошибка публикации видима, права получателя сохраняются, DeGram не создаёт вторую систему документов.

### Приёмка и выпуск — DGRL

- [ ] **DGRL-01**: Владелец получает воспроизводимый DeGram E2E acceptance report на утверждённых plan-layout, urban-block и project-documentation fixtures: functional/contract correctness, false-pass/false-fail/non-verdict, traceability, recipient handover и recovery с raw evidence, expected/actual outcomes и всеми неудачными попытками. Приёмка проверяет DeGram, а не two-arm study.
- [ ] **DGRL-02**: Оператор может предъявить live evidence governance/security/recovery испытаний: две компании и два проекта одной компании, concurrent editors, revoked access, injection в источнике/scribble, missing population, stale patch и timeout после apply/до publish; скрытых неразрешённых side effects нет.
- [ ] **DGRL-03**: Оператор может установить, обновить и откатить выбранную сборку DeGram/DG adapters на двух поддержанных ПК по документированному compatibility manifest, без потери проектного контекста и без credentials в поставке/логах.
- [ ] **DGRL-04**: Владелец может принять либо отклонить выпуск по заранее утверждённым correctness, safety, traceability и recovery gates, raw evidence, known limitations и remaining debt; tool success не заменяет gate, незавершённая проверка не получает PASS. Benefit threshold для выпуска не требуется.

### DG Web UI (Phase 1308, вне 51 MVP ID) — WEBUI

Источник: `1308-SEED.md`, решения D-32/D-36/D-37/D-38/D-49 (`1301-CONTEXT.md`), рекомендации `1308-RESEARCH.md`, утверждённые владельцем 2026-10-12. Не входят в счёт 51 MVP ID и не меняют инварианты roadmap.

- [x] **WEBUI-01**: Язык интерфейса выбирается из двух вариантов — «Русский» и «English». В DeGram — одна настройка Settings → Appearance → Language; смена применяется к открытой странице DG без перезагрузки, на встроенной странице DG своего переключателя нет. В обычном браузере вне DeGram у DG Web UI есть собственный список «Русский / English» вверху справа; выбор запоминается, по умолчанию — язык браузера (поправка владельца на UAT 2026-10-13, D-07/D-08/D-53; текст обновлён 2026-10-14).
- [x] **WEBUI-02**: При выбранном RU весь DG Web UI отображается по-русски (глоссарий D-38 и фиксированные переводы владельца), ошибки сервера переводятся по `code`; тест покрытия ключей держит EN/RU в синхроне.
- [x] **WEBUI-03**: Владелец проекта или админ DG меняет роль существующего участника (`PUT /projects/{project}/members/{username}`); последний владелец не понижается (409 `LAST_OWNER`); действие доступно в панели участников.
- [x] **WEBUI-04**: Админ DG (и только он) видит и меняет политику экспорта проекта (`providerExportAllowed`, `wholeDefinitionAllowed`) в панели настроек проекта.
- [x] **WEBUI-05**: Пункты главного экрана показывают сводки под подписью (Graph Viewer, Model Viewer, «LLM model», Connectors, Reasoner); «AI Engine» переименован в «LLM model».
- [x] **WEBUI-06**: В боковой панели DeGram под «Models» / «Модели» есть пункт «Projects» / «Проекты», открывающий экран DG PROJECTS.
- [x] **WEBUI-07**: Доступ к коннектору — только грантом на каждый коннектор (владелец и админ освобождены, editor/viewer — по гранту); токены коннекторов заменены сессией входа коннектора; `POST /connectors/{id}/credentials` выведен (410); статус «Вкл» означает живую сессию входа.
- [x] **WEBUI-08**: Аддин Grasshopper входит под учётной записью пользователя (CONNECTOR, VALIDATOR, COMPUTGRAPH PUBLISH) без токена коннектора.
- [x] **WEBUI-09**: Экран Connectors в Web UI, таблица коннекторов в DeGram и документация API больше не содержат сценария токенов.
- [x] **WEBUI-10**: `spec/SECURITY-BOUNDARY.md` (и API/GRASSHOPPER/DEPLOYMENT, release notes) и инвентарь маршрутов отражают все изменения маршрутов и принципалов.
- [x] **WEBUI-11**: Живое развёртывание: проверка D-32, пересборка образов из закоммиченного кода, вывод `dgc_` токенов, удаление UAT-учётки `uat-pw-bd30ce` — каждое за контрольной точкой.

### Автоматизированный меппинг GH/Revit → DG (MVP-срез Phase 1303, вне 51 MVP ID) — DGMAP

Источник: приоритет и решения владельца 2026-10-17 (`phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`), исследование `docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md`. Не входят в счёт 51 MVP ID и не меняют инварианты roadmap; демо 2026-10-19 — demo-grade, не приёмка DGBN.

- [ ] **DGMAP-01**: Пользователь отправляет набор элементов проекта из Grasshopper или из Revit (сначала только чтение; с 2026-10-18 по решению владельца — через Revit-коннектор DG с записью, 1303 D-45) как дескрипторы — платформа, native id, источник/категория/семейство/тип, геометрические признаки, параметры, IFC-класс при наличии — и получает для каждого элемента кандидаты классов DG с уверенностью и объяснением по источникам свидетельств; кандидат не становится привязкой без подтверждения человеком или применимого профиля.
- [ ] **DGMAP-02**: Система группирует элементы по сигнатуре признаков и упорядочивает группы по неопределённости × влиянию (число элементов × число затронутых правил проекта); для неоднозначной группы вопрос формулируется через последствия для правил проекта, включая различение «ошибка меппинга / ошибка проекта», с вариантами «класс X», «класс Y», «обе роли», «разделить по признаку», «ни один».
- [ ] **DGMAP-03**: Ответ на вопрос о группе сохраняется как MappingDecision (автор, время, вопрос, показанные свидетельства и последствия, ответ) и порождает проверяемый MappingProfile (селектор признаков → роли, поддержка, подтверждения/опровержения); ручной меппинг (подключение в GH, категория + параметры в Revit) хранится тем же объектом с `source=authored`.
- [ ] **DGMAP-04**: Профили применяются детерминированно к следующим импортам того же проекта и переносятся между платформами по общим признакам; автоматически применяется только профиль выше порога уверенности, остальные элементы попадают в очередь; повторный импорт тех же дескрипторов даёт тот же результат.
- [ ] **DGMAP-05**: Элемент может иметь несколько ролей; роли, объявленные несовместимыми (`owl:disjointWith`), вместе не применяются и порождают вопрос; применённые роли дают по одному ObjState на роль и проходят существующий VALIDATOR без изменения его логики.
- [ ] **DGMAP-06**: Пользователь видит в DG Web UI очередь групп, карточку вопроса с последствиями, прогресс (подтверждено / авто по профилю / неоднозначно / без меппинга) и список профилей (RU/EN); в Rhino элементы окрашиваются по состоянию меппинга. На фасаде `v12-hexagonal-facade-01` (V1, 376 элементов, эталон известен) демонстрируются холодный старт GH, повтор на V2/V3 и живая Revit-модель с протоколом числа вопросов и precision/recall против эталона.

### Проверка боксов отверстий ИОС → КР (срез Phase 1303, вне 51 MVP ID) — DGOPN

Источник: приоритет владельца 2026-10-20 (`todos/pending/2026-10-20-check-mep-opening-boxes-in-revit-against-structural-rules.md`), план `1303-15`. Кейс: инженеры ИОС ставят боксы (Generic Model) на пересечениях коммуникаций с конструкциями; конструкторы копируют боксы в модель КР и ставят отверстия только там, где это допускают правила. Demo-grade, не приёмка DGBN.

- [ ] **DGOPN-01**: Правила КР для отверстий вводятся на естественном языке через обычный конвейер DG (NL → SWRL → Neo4j) в отдельном проекте: R1 запрет в балках, R2 запрет в колоннах, R3 запрет над дверными/оконными проёмами, R4 не ближе 300 мм к границе проёма; каждое правило ссылается на DataProperty бокса, вычислимую по модели Revit.
- [ ] **DGOPN-02**: DG сама генерирует скрипт расчёта этих свойств по правилам проекта (каталог проверенных калькуляторов Revit/Rhino.Inside, выбор и параметризация по DataProperty правил) и сама размещает его на GH-канвасе вместе с цепочкой OBJECT STATE / PROPERTY STATE / VALIDATOR; пользователь не пишет и не вставляет код, он только запускает и проверяет результат.
- [ ] **DGOPN-03**: VALIDATOR вычисляет R1–R4 для каждого бокса без вызова LLM; боксы с нарушениями подсвечиваются в активном виде Revit (красный / зелёный, одна отменяемая транзакция) и получают список нарушенных правил в параметре; результат публикуется в ValidGraph.
- [ ] **DGOPN-04**: На локальной копии реальной модели КР владельца (оригинал не открывается на запись) результат проверки совпадает с эталоном, который подтвердил владелец (precision/recall по боксам и правилам), и записан в протоколе «Акт 4» вместе со временем прогона.
- [ ] **DGOPN-05**: Калькулятор свойства, сгенерированный LLM, попадает в общий каталог компании (Neo4j) только после того, как оператор в Web UI увидел его код, значения на боксах и вердикты прогона и подтвердил его; после этого его свойство входит в словарь ingest, и следующие правила и проекты компании используют его без вызова LLM. Отклонённый калькулятор не воскрешается повторной генерацией; отозванный исчезает из разрешения и словаря. Решения D-54…D-59, планы `1303-16`…`1303-18`.

## Future / retained elsewhere

| Возможность | Единственный владелец / disposition |
|---|---|
| Полная per-node historical topology и произвольный diff двух persisted snapshots | v10 WPER-01..04; v13 хранит только минимальный operation/pre-post seam |
| Cluster internals, генерация новых блоков в slots, расширенная структура правил | v10 CLIN/SGEN/SRUL |
| Расширенная consultation через новые SRUL/SGEN и новые экраны | v10 остаточные CONS; базовая consultation/reused UI — v13 |
| Publication bundle, нормативная V8 миграция, manuscript/dissemination | v11; v13 потребляет согласованный профиль |
| SSO, дополнительные LLM/CDE providers, расширенные Revit writes | Только выбранный в DGCN-04 вариант MVP; расширения — отдельный scope |
| Скрытие legacy GH компонентов | Deferred; успешная совместимость обязательна, hiding не нужен MVP |

## Out of scope

Universal graph CRUD; arbitrary Revit/Python/C# execution из LLM; universal IFC/IDS/SWRL compiler; whole-definition synthesis; full DesignSpaceGraph/event sourcing; отдельная CDE/шестой граф; скрытая передача знаний между компаниями; автоматическое распространение lessons-learned revisions; перенос compliance проекта A в B; обязательные GraphRAG/vector DB/multi-agent; обещание универсальной детерминированности LLM или distributed CAD+DG transaction. Текущее приложение Hermes пользователя и его профили этим milestone не изменяются.

## Verification contract

У каждого требования должны появиться phase evidence и результат проверки. Contract/unit tests нужны для схем и negative cases, но не заменяют поздние отдельно разрешённые live CAD, multi-user, двухкомпьютерный handover и человеческое принятие. Exact fixtures, commands, expected outcomes и human checkpoints фиксируются до соответствующей проверки. Независимый bounded client implementation/offline tests 1301 не ждёт завершения всего 1300; G-01/V8, независимое техническое принятие/ownership и security gates сохраняются для потребления semantic contracts, live операций и phase acceptance. Research prose и согласованная диаграмма не являются PASS evidence.

## Traceability

Утверждённое распределение по phase slots независимо проверено против roadmap. У каждого ID ровно один delivery phase; поздний integration test не создаёт второго владельца.

| Requirement | Phase | Status |
|---|---|---|
| DGCN-01 | 1300 | Pending |
| DGCN-02 | 1300 | Pending |
| DGCN-03 | 1300 | Pending |
| DGCN-04 | 1300 | Pending |
| DGCL-01 | 1301 | Pending (server grant/session leg delivered in 1301-30; client/live acceptance pending) |
| DGCL-02 | 1301 | Pending |
| DGCL-03 | 1301 | Pending |
| DGCL-04 | 1301 | Pending |
| DGCL-05 | 1301 | Pending (backend grant/session revocation leg delivered in 1301-30; end-to-end evidence pending) |
| DGCL-06 | 1301 | Pending |
| DGCL-07 | 1301 | Pending |
| DGKN-01 | 1302 | Pending |
| DGKN-02 | 1302 | Pending |
| DGKN-03 | 1302 | Pending |
| DGKN-04 | 1302 | Pending |
| DGKN-05 | 1302 | Pending |
| DGKN-06 | 1302 | Pending |
| DGKN-07 | 1302 | Pending |
| DGKN-08 | 1302 | Pending |
| DGKN-09 | 1302 | Pending |
| DGKN-10 | 1302 | Pending |
| DGBN-01 | 1303 | Pending |
| DGBN-02 | 1303 | Pending |
| DGBN-03 | 1303 | Pending |
| DGBN-04 | 1303 | Pending |
| DGBN-05 | 1303 | Pending |
| DGBN-06 | 1303 | Pending |
| DGST-01 | 1304 | Pending |
| DGST-02 | 1304 | Pending |
| DGST-03 | 1304 | Pending |
| DGST-04 | 1304 | Pending |
| DGST-05 | 1304 | Pending |
| DGST-06 | 1304 | Pending |
| DGST-07 | 1304 | Pending |
| DGED-01 | 1305 | Pending |
| DGED-02 | 1305 | Pending |
| DGED-03 | 1305 | Pending |
| DGED-04 | 1305 | Pending |
| DGED-05 | 1305 | Pending |
| DGED-06 | 1305 | Pending |
| DGED-07 | 1305 | Pending |
| DGED-08 | 1305 | Pending |
| DGHN-01 | 1306 | Pending |
| DGHN-02 | 1306 | Pending |
| DGHN-03 | 1306 | Pending |
| DGHN-04 | 1306 | Pending |
| DGHN-05 | 1306 | Pending |
| DGRL-01 | 1307 | Pending |
| DGRL-02 | 1307 | Pending |
| DGRL-03 | 1307 | Pending |
| DGRL-04 | 1307 | Pending |

**Coverage:** 51 MVP requirements; 51 mapped; 0 unmapped. Первый read-only client slice 1301 в работе; server-side D-39 grant/session-exchange leg delivered in 1301-30, but no DGCL requirement is confirmed fully until client and live acceptance evidence exist.

**Вне 51 MVP ID:** WEBUI-01…11 → 1308 (Complete); DGMAP-01…06 → 1303, MVP-срез (приоритет владельца 2026-10-17, демо 2026-10-19), Pending. DGOPN-01…04 → 1303-15 (приоритет владельца 2026-10-20, демо в тот же день), Pending. DGOPN-05 → 1303-16…18 (решения D-54…D-59, 2026-10-20/21), Pending.

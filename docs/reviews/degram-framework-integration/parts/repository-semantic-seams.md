# DeGram Agent: аудит семантических границ хранения и управления

## Вывод

**Условный GO для тонкого типизированного DG-адаптера; NO-GO для обещания уже готовой общей корпоративной семантической платформы, полного воспроизведения Design State или безопасной многопользовательской записи в CAD.** В репозитории есть существенная основа: проектная авторизация, отдельные графовые разделы, registry идентичности, подтверждение предложений, канонические статусы, отдельные JSON-снимки и адресуемые результаты. Но это не единая система версий источника → правила → вычисления → результата.

Главное ограничение — не отсутствие очередного orchestration framework, а неодинаковые контракты существующих путей записи/чтения. Замена оболочки на Hermes не исправит их автоматически. Разумный минимальный объём: сохранить серверную DG-политику, дать адаптеру узкие операции и сведения об их фактических ограничениях; закрыть конкретные CAS/revision/provenance/freshness-границы. **Не превращать организационный словарь в общий граф простым удалением `project` из запросов.**

## Граница и метод

- База просмотра: ветка `master`, HEAD `37450d4e6ec6763ff1c35953a560cbfcec767dc6`; последний коммит относится к Phase 1205, а не закрытию 1205.1. Рабочее дерево уже содержало изменения planning, CLAUDE, сборочных и Graphify-артефактов. Выводы относятся к прочитанному рабочему дереву, не к чистому checkout.
- `.planning/STATE.md:3–17,24–33` явно показывает **v12.0, phase 1205.1, executing, wave 1**. Одновременно `stopped_at` и `last_activity_desc` ещё говорят о завершении 1205: это не основание объявлять milestone закрытым. `.planning/ROADMAP.md:320–344` содержит незакрытые планы 1205.1.
- Прочитаны CLAUDE и профильный skill; проверены адресные spec/runtime/ontology/test/planning-файлы. Источником выводов служат код и точные строки ниже. Publication/manuscript-файлы и `DG_OBSIDIAN/dissemination/` не открывались; научные тексты не использованы. Домашние vault-index/priorities просмотрены только как навигационные документы и не используются как доказательство возможностей.
- Graphify не применён: его общий индекс в этом дереве содержит конвертированные материалы исключённой области; вместо расширения доступа использован прямой адресный source-read. Live Neo4j, Docker, n8n, Speckle, CAD и LLM не вызывались. Схемы реально развёрнутой БД, migration history и её текущие constraints неизвестны.
- Статусы: **I** — реализовано в прочитанном коде; **T-src** — есть адресные тесты, но они здесь не выполнялись; **V-offline** — непосредственно проверено безопасной локальной пробой; **P** — явно запланировано; **U** — не установлено. Наличие теста, SHACL shape или зарегистрированного connector не означает live-поддержку.

## Матрица границ

| Граница | Фактически реализовано / доказательства | Проверка, план и ограничение |
|---|---|---|
| Организационный словарь ↔ проект | **I:** context и GH читают проектный OntoGraph: `data-service/dg_context.py:317–359`; `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs:10–25`. **I:** membership-политика именованных graph/rule routes: `data-service/route_policy.py:115–123`. | Корпоративные namespace/release/import permissions в этих путях **U**. Удаление фильтра смешает авторизованные проекты; общий `SpecClass` hub — не корпоративный словарь (`data-service/app.py:1282–1302`). |
| TBox ↔ runtime schema | **I:** reasoner по умолчанию грузит V7 (`dg-reasoner/reasoning.py:94`); OWL объявляет 7.0 и динамический domain vocabulary (`ontology/DesignGrammar-V7.owl:30–49`). Runtime — LPG плюс blob payloads, не буквальная материализация всех OWL-классов. | **P:** версия/профиль и V7→V8 согласование принадлежат v11: `.planning/milestones/v11.0-ROADMAP.md:110–150`. Нельзя считать это выполненным по наличию v12. |
| Revision storage | **I:** `ValidationRun` защищает только `rulesJson/statePayloadJson/createdAt` через `ON CREATE SET` (`data-service/app.py:685–743`); SpecNote/Computgraph/SharedProperty обновляются на месте. | **T-src:** immutability-тест проверяет emitted Cypher, не транзакции БД (`data-service/tests/test_validation_run_immutability.py:12–18,78–88`). Универсальной immutable revision history **не показано**. |
| Rule source ↔ правило ↔ результат | **I:** supersession, prompt/actor и session logs; `ATTRIBUTE_OF` и `sourceRuleId` у принятого кандидата. | Это части трассы, не end-to-end provenance. Источник с revision/hash/fragment, утверждённая редакция SWRL и полный corpus snapshot в publish result **не обеспечены просмотренным путём**. Подробнее ниже. |
| Design State comparison | **I/V-offline:** каноническая сортировка и хеширование; хеш чувствителен к времени capture и StateId, геометрия исключена (`data-service/design_state_projection.py:144–175,196–231`). | «Равное содержание в разные моменты → равный hash» противоречит фактической проекции. Membership design-space/partition отсутствует в `DesignState` (`DG/src/DG.Core/Models/DesignState.cs:3–19`). Семантическая сравнимость **U**, побайтовая сравнимость ограниченной проекции — **I/V-offline**. |
| Capture/replay/freshness | **I:** HTTP capture, debounce/coalesce, ParamState apply guards; повторное чтение domains перед accept. | Capture явно simulated-client (`data-service/app.py:2752–2755`); два wire-shape под `version=2` остаются несогласованными. Валидность свежести по версии canvas/rules/geometry не доказана. |
| Native representation ↔ dgId | **I:** project-bound hash, labeled mint, sequential anti-rebind guard (`data-service/dg_identity.py:90–102,254–271,294–354`). | **T-src:** in-memory tests. **U:** конкурентная гарантия «один native key → один владелец» и live Revit. Нет document/model scope в representation key. |
| Published graph ↔ актуальный canvas | **I:** GH перечитывает canvas; сервер атомарно выполняет publish MERGEs (`DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs:125–154`; `data-service/computgraph_publish.py:96–119`). | Нет replace-snapshot/revision compare. Старые nodes только перечисляются, старые edges не удаляются; конкурентные публикации не имеют expected revision. Snapshot/version diff — **P** v10 Phase 41. |
| Capability / deployment / evidence | **I:** REST write-auth, local-only Bolt, перечень connectors/heartbeat. | Connector presence/heartbeat не доказывает read/write/replay capability. GH direct-Bolt multi-user unsupported — нормативно и в коде. Каноническая production-wire доставка — текущий owner **v12 1205.1**, не завершённая возможность. |

## 1. Общий словарь нельзя получать расширением проектных выборок

### Что реально отделено

Статический meta-schema и динамические проектные термины уже различаются: `spec/LPG-OWL-MAPPING.md:24–41` отделяет `dg/dgm/dgv/dgs/dgc` от `ex:`; `ontology/DesignGrammar-V7.owl:30–49,258–283` подтверждает это в фактическом OWL. `dg_context` собирает статический набор сведений, versioned catalog и текущие проектные сущности (`data-service/dg_context.py:458–494`). Это полезная основа, но не управление организационным vocabulary release.

В экспортёре `ex:Building` расширяется в единый `EX[local]`, независимо от проекта, тогда как Rule/Var получают project-scoped IRI (`dg-reasoner/ontology_export.py:32–35,109–133`). Изолированный export одного проекта не обязательно ошибочен. Однако **слияние экспортов разных проектов при одинаковом `ex:` имени не доказывает одинаковое значение термина**. Серверная tenant-изоляция и semantic namespace — разные задачи.

Есть конкретный read-contract drift: GH `Neo4jOntoGraphRepository` ищет `ObjProperty/DataProperty` (`DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs:16–25`), context/export — `ObjectProperty/DatatypeProperty` (`data-service/dg_context.py:142–150,317–323`; `dg-reasoner/ontology_export.py:43–48`). Без live данных нельзя заключить, какие alias реально заполнены; но нельзя переносить этот репозиторий в REST и объявлять parity без fixtures для обеих форм.

### Минимальное решение

1. Оставить project-guard для всех project-owned сущностей и операций.
2. Начать с read-only **версированного пакета словаря**: namespace, release ID, digest, список terms и источник; проект явно pin-ит нужный release. Допустим первоначально file-backed manifest в Git — отдельный ontology service не обязателен.
3. Отдельно определить ownership терминов, явный import в проект и локальные overrides. Project-private term никогда не становится организационным только потому, что пользователь прочитал его из другого проекта.
4. До физического shared storage доказать на двух проектах: одинаковое имя с разной семантикой не сливается; обновление общего release не меняет старый run; чтение общего пакета не открывает private metadata; импорт выполняется с явной provenance.

## 2. Существуют разные виды «версии», их нельзя смешивать

### SpecGraph: актуальный текст, но не реестр редакций источников

`SpecNote` идентифицируется хешем `project:source_path` (`data-service/app.py:1261–1263`), re-ingest делает SET текущего title/content/source/tags и updatedAt (`data-service/app.py:3365–3385`). PUT также перезаписывает текст, DELETE физически удаляет узел (`data-service/app.py:3460–3504`). `SpecSession` хранит prompt и строковый result; confirm сохраняет лишь список затронутых названий, урезанный до 2000 символов (`data-service/app.py:4209–4221`).

**Источник-путь ≠ исходный документ конкретной редакции.** Здесь нет обязательного source digest, fragment locator, исходного before/after, immutable revision и автора каждой текстовой правки. Повторный ingest изменившегося файла уничтожает прежнюю версию content. `source` может продолжать указывать на файл, хотя последующий LLM/ручной PUT уже создал производный текст.

Three-step match → propose → confirm действительно есть; propose возвращает updatedAt, confirm отказывает при отличии (`data-service/app.py:4113–4167,4184–4196`). Но read и write — отдельные вызовы, WHERE записи **не содержит ожидаемый updatedAt**, а цикл пишет по одному note до создания session (`data-service/app.py:4197–4233`; helpers: `data-service/app.py:509–522`). Следовательно:

- проверка ловит уже случившееся изменение, но не закрывает race между read и write;
- конфликт на втором note может оставить первый уже обновлённым;
- crash между update и session теряет audit-запись.

Это source-derived риски, не воспроизведённые здесь live-дефекты. Тесты покрывают stale timestamp и три вызова записи, не двух конкурентных клиентов/rollback (`data-service/tests/test_update_flow.py:73–109`). Note-by-ID routes не следует ошибочно объявлять неавторизованными из-за отсутствия project в локальном MATCH: resource resolver и route policy существуют (`data-service/app.py:4272–4281`; `data-service/route_policy.py:188–191`).

**Минимум:** атомарный compare-and-set по expected revision; immutable previous content/digest для изменяемых notes; revision ID в session. Для batch либо одна transaction, либо честная per-item response с partial completion. Полный event-sourcing всех графов для этого не требуется.

### Rule edit и supersede — два разных жизненных цикла

Новый ingest имеет conflict dialog и после записи вызывает supersede/accept-overlap. UI выбирает первый конфликт при нескольких, fail-open при недоступности conflict check и выполняет provenance запись отдельным шагом (`ui-v2/src/screens/GraphScreen.jsx:661–726`). Это **клиентский workflow**, не универсальная серверная гарантия на любую запись правила.

Отдельный edit-mode всё ещё посылает `edit Rule_Id: ...` (`ui-v2/src/screens/GraphScreen.jsx:500`). Его n8n `Prepare Graph Payload` удаляет ARG/REFERS_TO/body/head/старое правило и заново пишет граф; cleanup + новые statements объединены в одну Neo4j HTTP transaction (`n8n/workflows/rules-to-metagraph.json:134,147–168`). То же destructive guidance остаётся в context (`data-service/dg_context.py:216–251`). Значит **«Replace никогда не удаляет» нельзя распространять на все способы редактирования**.

Supersede имеет полезную защиту publishability replacement и authenticated actor (`data-service/app.py:3804–3859,3871–3883`). Однако:

- комментарий обещает idempotent повтор, но любой уже-superseded old даёт 409 (`data-service/app.py:3892–3894,3938–3944`);
- new проверяется на существование и shape, но не на собственный outgoing SUPERSEDED_BY (`data-service/app.py:3946–3958`), вопреки более широкому комментарию `3770–3773`;
- check и MERGE раздельны (`data-service/app.py:3925–3974`): конкурентная замена старого правила двумя редакциями не блокируется shown compare-and-set;
- GH active corpus исключает superseded (`DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31–43`), но input binding loader не исключает (`data-service/cg_input_bindings.py:292–303`), как и LPG→RDF queries (`dg-reasoner/ontology_export.py:50–61`). Это различие scope потребителей, не доказательство того, что HermiT исполняет бизнес-правила.

**Минимум:** одна серверная операция `revise/activate` с expected active revision, атомарной активацией и сохранённой старой редакцией; legacy edit явно помечать destructive до перевода. Existing SUPERSEDED_BY можно сохранить — новый generic workflow engine не нужен. Acceptance: retry той же операции возвращает тот же результат; две competing revisions не обе становятся active; все consumer scopes согласованы либо явно исторические.

### Run snapshot не является полным executable artifact

`rulesJson` неизменяем после первой записи, но содержит только ruleId/name/description/passed, **не SWRL/atoms/корпус редакции** (`data-service/app.py:1072–1085,708–724`). Изменение/удаление Rule после run поэтому не оставляет достаточного материала для повторной оценки по одной этой записи.

EvidenceEnvelope допускает schema/ontology/rule/shape versions (`data-service/evidence_contract.py:223–273`), но production builder передаёт project, **run_id как definition_id**, service/version/stage/rows, не заполненные версии правил и input hashes (`data-service/app.py:2591–2598`). Поле в schema — это возможность хранения, не факт provenance completeness.

## 3. Трассировка source → Rule → Parameter → measured result

### Реальный прогресс

- `ATTRIBUTE_OF` реально производится, это не только предложение: publish использует общий классификатор `inputBindings`; ребро имеет derivedFromRuleId/source/determinability (`data-service/computgraph_publish.py:138–164,819–855`).
- Unknown binding по умолчанию `geometry-required`; threshold считывается из SWRL atoms, не дублируется в binding config (`data-service/cg_input_bindings.py:273–303,376–409`). `spec/RULE-PARTITION-POLICY.md:96–119` прямо запрещает превращать generation в новый compliance evaluator.
- `reinstateParameterId` выводится из фактических wires к PARAMETER STATE; неоднозначный target исключается (`data-service/computgraph_publish.py:167–184,193–247`). Это лучше угадывания по display name.
- Есть tests derivation, обеих направлений запроса и project isolation (`data-service/tests/test_computgraph_publish.py:843–1044`; `data-service/tests/test_cq3_attribute_of.py:135–207`). CQ3 graph fixture отдельно от реального GH solver; это не solver equivalence.

### Остаточная граница

`inputBindings` — **repo-wide файл без project scope**, ограничение признаёт сам publisher (`data-service/computgraph_publish.py:138–147`). Совпадающий Rule_Id разных проектов ещё не доказывает, что одинаковое имя параметра означает одну и ту же величину. `_attribute_of_from_bindings` индексирует параметры только по name; одинаковые имена молча вытесняются последней записью (`data-service/computgraph_publish.py:521–535`). Writer связывает **все body DataPropertyAtom данного правила** с найденным Parameter, не конкретный property predicate (`data-service/computgraph_publish.py:841–848`). Для многосвойственного правила это потенциально более широкий bridge, чем доказанное соответствие.

`ATTRIBUTE_OF` — структурная связь, не record оценки. В `ValidationEntity` persistence пишутся ruleId/dgEntityId/displayName/status, а не замер, единицы и цепочка вычисления (`data-service/app.py:745–791`). PropState сохраняет ruleIri/dataPropertyIri/objectRef/value в payload (`data-service/design_state_projection.py:178–193`), но это ещё не source-document revision или computation provenance.

`DesignRuleSession` хранит mode/prompt/result[:2000] с временем, без typed links к Rule revisions и authenticated actor (`data-service/app.py:4072–4095`). Session полезен для истории беседы, но не заменяет audit trail изменения доменного артефакта.

**Минимум:** `sourceRevisionId + fragment`, immutable rule revision/hash, привязка к конкретному atom/property и parameter identity (`project/definitionId/cgId`), измеренное typed value + unit + producer/run reference. Первое внедрение — один понятный vertical slice, например правило высоты: исходный пункт → утверждённая SWRL revision → selected parameter → solve → per-object result. Не требуется немедленно импортировать всю PROV-O/SOSA как новые runtime nodes.

## 4. Design State: сохранение, сравнение и воспроизведение

### Нельзя подменять три разных отношения одним hash

Нужны отдельно: (a) тот же capture event, (b) те же данные в объявленной проекции, (c) сравнимые варианты внутри одного design space. Текущий `DesignState` содержит StateId, label, три списка и capture timestamp, но не пространство/partition/тип альтернативы (`DG/src/DG.Core/Models/DesignState.cs:3–19`). Поэтому diff двух состояний не доказывает смену замысла или семантически сопоставимые альтернативы.

`DesignStateIdGenerator` декларирует отдельную event identity и «одинаковое содержание при разных временах — одинаковый canonicalStateHash» (`DG/src/DG.Core/Services/DesignStateIdGenerator.cs:12–34`). Но projection включает root stateId/capturedAtUtc и timestamps ObjState/ParamState (`data-service/design_state_projection.py:144–175,214–222`). **V-offline:** одна только замена root capturedAtUtc меняет hash; порядок объектов его не меняет; добавление геометрии его не меняет. Поэтому текущий hash годен как fingerprint конкретного ограниченного envelope, но не как general content-equivalence key между captures.

Геометрия исключена намеренно (`data-service/design_state_projection.py:21–24,148–156`); версия geometry artifact в этой проекции не участвует. `canonicalStateHash` в view вычисляется по сохранённому payload на чтении (`data-service/app.py:1122–1132,1214`), что также требует явного projection-version контракта при будущих изменениях.

**Минимум:** не менять молча существующий hash. Назвать его область; отдельно согласовать versioned comparison projection (без event IDs/times, с нужными geometry/rule/unit references) или отказаться пока от обещания equivalence. Сравнение разрешать только при совместимых schema/vocabulary/rule/configuration и явно указанном design-space scope. В MVP достаточно компактного metadata block, не DesignSpaceGraph как новой платформы.

### Два v2 wire-shape — подтверждённая несовместимость, не завершённый replay

Accepted-candidate writer пишет `numberValue/integerValue/booleanValue`, а C# serializer — `type/value` (`data-service/cg_paramstate_store.py:131–143`; `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs:97–111`). Inline repository reader прямо признаёт, что concise values станут null (`DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:339–437`). Регрессии **намеренно утверждают различие**, включая потерю typed value (`DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs:278–333`). Это T-src документированной non-alignment, а не тест успешного универсального восстановления.

ParamState accept дополнительно имеет отдельный identity algorithm: hash от `sourceRuleId + sorted(parameterId,value)`, без definitionId (`data-service/cg_paramstate_store.py:73–95`). MERGE key — `StateId+project`, затем безусловный SET provenance, definitionId и acceptedAt (`data-service/cg_paramstate_store.py:314–347`). **V-offline:** одинаковые values/rule при разных provenance.definitionId дают тот же StateId. Следовательно два definitions внутри одного проекта могут схлопнуться в одну accepted candidate запись, переписывая attribution. Это логический key collision, не криптографическая коллизия.

**Минимум:** reader, принимающий оба исторических shape без silent null, и явный producer/schema discriminator новых данных; candidate identity должна быть согласована с definition scope, а принятие — сохранять source candidate/provenance, не принимать клиентскую attribution за проверенный факт. Реальный Revit/geometry round-trip остаётся отдельной задачей.

### Freshness присутствует локально, но не end-to-end

Положительные guards: GH publish извлекает свежий canvas (`DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs:125–154`); accept перечитывает **опубликованные** domains и проверяет values (`data-service/cg_paramstate_store.py:296–312`); reinstatement проверяет target/type/range/ambiguity и атомарно отказывает при sibling failure (`DG/src/DG.Core/Services/DesignStateReinstatementService.cs:37–87,90–159`).

Но опубликованные domains могут отставать от canvas; revalidation не доказывает совпадение rule revision, topology, solver config и model version. Same-StateId guard возвращает Unchanged до проверки текущих targets (`DG/src/DG.Core/Services/DesignStateReinstatementService.cs:17–35`), поэтому повторное применение после ручного изменения targets требует отдельной оговорки/теста.

HTTP capture имеет новый server UUID/time, не freshness comparison с producer revision (`data-service/app.py:2805–2821`). Watcher coalesce сгруппирован по **проекту**, не definition/client (`data-service/dsav_watcher.py:158–185`); значит разные открытые definitions одного проекта могут вытеснять captures друг друга при latest-wins. Guardrails process-local и сбрасываются после restart (`data-service/dsav_watcher.py:384–413`); distributed claim/lease в показанном poll отсутствует (`data-service/dsav_watcher.py:479–515`). Его SHACL verdict нельзя объявлять SWRL compliance (`spec/RULE-PARTITION-POLICY.md:27–33`).

**Минимум для нового агента:** proposal carries base definition revision/hash, ruleset revision, model reference и capture time; confirm проверяет их заново и возвращает typed stale/conflict, а не «успех». Разделить watcher stream по `(project, definitionId, producer)`; до горизонтального масштабирования либо явно single-worker, либо атомарный claim. Дорогой distributed orchestration здесь преждевременен.

## 5. Mapping и конкурентные публикации

### Representation key

Реальный ключ `(nativeId, platform, project)`; `nativeIdKind` и connector только ON CREATE provenance (`data-service/dg_identity.py:274–291,335–354`). Model/document ID, occurrence/instance scope и версия mapping отсутствуют. Platform и nativeIdKind валидируются **независимо**, а не как совместимая пара (`data-service/dg_identity.py:158–180`). Нормативное «Revit → UniqueId» пока сильнее runtime проверки (`spec/DG-ID.md:169–178`).

Anti-misbinding реализован read-before-write несколькими `session.run`; route открывает session, не передаёт один explicit transaction (`data-service/dg_identity.py:312–354`; `data-service/app.py:2299–2315`). Это последовательная защита, не гарантия против двух конкурентных bind. Даже unique constraint на Representation key сам по себе не запрещает два incoming HAS_REPRESENTATION от разных entities. Constraints в просмотренных migrations не найдены; реальные live constraints **U**.

Tests используют `FakeGraph`, где `single()` берёт первый row и op=BIND моделирует одну запись (`data-service/tests/test_dg_identity.py:62–170`), а cross-platform scenario — simulated (`spec/DG-ID.md:24–26`). Нельзя переносить это evidence на реальные Revit links, document copies и concurrent binds.

SharedProperty — string value API плюс last-write-wins с заменой producer/time (`data-service/dg_identity.py:199–205,463–482`; `spec/DG-ID.md:228–230`). Нет units, per-result revision, authority priority или immutable previous value. Identity API authorizes member, но attribution platform/connector берёт из запроса (`data-service/route_policy.py:159–166`; `data-service/app.py:2341–2358`): происхождение заявлено клиентом, не аттестовано платформой.

**Минимум:** explicit source-model scope в native key там, где требуется; valid platform-kind pairs; atomic ownership check/bind с конфликтом; actual actor отдельно от declared source connector. Проверить реальные uniqueness/cardinality guarantees двумя конкурентными транзакциями на disposable DB позже, не в этом аудите. Не обещать пока bidirectional reconciliation всех BIM платформ.

### Computgraph publish — atomic upsert, не revisioned snapshot

Публикация атомарна внутри одной `execute_write`, но rule classifications прочитаны до transaction (`data-service/computgraph_publish.py:88–117`). Nodes/Algorithm.contextJson обновляются SET (`data-service/computgraph_publish.py:628–672,733–789`), edges только MERGE (`data-service/computgraph_publish.py:716–723,802–848`). `staleEntityIds` вычисляет лишь отсутствующие cgIds, без удаления nodes/edges (`data-service/computgraph_publish.py:859–877`).

Следствия: удалённая wire/перемещённая принадлежность/изменённый binding могут оставить историческое ребро в текущем graph; старый ATTRIBUTE_OF после смены bindings не автоматически retired. Две публикации из stale canvases могут последовательно перезаписать данные без explicit conflict. FakeGraph publish tests полезны для emit semantics, но не доказывают contention; даже fake typed node key не содержит definitionId (`data-service/tests/test_computgraph_publish.py:70–113`).

`dgId` привязан к cgId, а rename по контракту re-mints (`spec/DG-ID.md:98–111`); следовательно «durable identity» не означает survival всех переименований. Это должно быть видно в UI-agent mapping preview.

**Минимум:** publish revision + expectedRevision, один активный snapshot per definition, reconciliation только publisher-owned edges, явный stale report. Полную per-node wire history/diff не дублировать: её будущий owner — v10 Phase 41 (`.planning/milestones/v10.0-ROADMAP.md:32–50`).

## 6. Runtime ontology и слой чтения: не использовать graph viewer как semantic API

Фактический V7 OWL описывает DesignState как disjoint union трёх видов (`ontology/DesignGrammar-V7.owl:1151–1184`); C# aggregate содержит одновременно три коллекции, а live runs физически хранятся в ValidationRun payload (`DG/src/DG.Core/Models/DesignState.cs:3–19`; `data-service/app.py:708–712`). Это разные представления, их соответствие требуется описывать, а не объявлять все узлы одной универсальной ontology model.

В `dg_context` сохранилось безусловное «Design states are NOT separate graph nodes» (`data-service/dg_context.py:174–212`), но standalone accepted DesignState уже пишется (`data-service/cg_paramstate_store.py:331–347`). Context читает лишь 25 ValidationRun и summary counts (`data-service/dg_context.py:410–450`), поэтому отсутствие candidate в таком контексте нельзя объяснять как отсутствие его в проекте. Выражение «та же заявка всегда даёт byte-identical context» также условно: запрос зависит от живой БД (`data-service/dg_context.py:466–482`).

`GET /graph/{project}` возвращает до 2000 nodes / 8000 edges; reads раздельны, нет pagination/completeness token, relationship properties отброшены (`data-service/app.py:4619–4625,4688–4705`). Поэтому адаптер не может использовать этот viewer snapshot как полное доказательство: теряются HAS_BODY.order, ARG.pos, ATTRIBUTE_OF provenance. Для semantic reads нужны typed endpoints с полным pair/atom/edge contract и явной completeness, а не universal Cypher доступ модели.

SHACL Representation/SharedProperty shapes реально существуют (`ontology/dg-shapes.ttl:188–249`), но shape-файл сам по себе не доказывает их достижимость текущим exporter. Политика прямо фиксирует отсутствие Computgraph RDF projection и отдельные Cypher checks (`spec/RULE-PARTITION-POLICY.md:75–92`); опубликованные shape definitions нельзя продавать как исполненную проверку всех registry nodes.

## 7. Capabilities и граница GH-клиента

- GH Rule/Onto repositories реально открывают direct Bolt (`DG/src/DG.Core/Data/Neo4jRuleRepository.cs:73–99`; `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs:28–37`). Multi-user heartbeat не выдаёт connection bundle (`data-service/app.py:1602–1613`); unsupported статус нормативно закреплён (`spec/SECURITY-BOUNDARY.md:50`). Типизированный REST DG adapter нужен не только Hermes: GH read repositories тоже требуют соответствующего авторизованного пути, если заявляется remote multi-user workflow.
- GH publish уже HTTP + connector token, не нужно переписывать всё (`DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs:28–60`). Но BuildRequest копирует legacy boolean/lists и geometry, не богатый canonical pair package (`DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs:115–160`). Python fallback может восстановить только то, что дошло (`data-service/app.py:2532–2598`). Это ровно **текущий blocker-owner 1205.1**, а не новый v13 status protocol.
- Server GH bridge — глобальный host/port и ограниченные команды context/selection/preview (`data-service/gh_bridge.py:27–51,108–134`). Local MCP per PC архитектурно снимает часть routing проблемы, но не доказывает свежесть, source identity, undo и execution safety.
- Connector registry — статический список названий (`data-service/connectors.py:28–55`); active/stale определяется heartbeat, а не проверкой операций (`data-service/connectors.py:306–324,343–383`). Не считать перечисление Revit/Dynamo и active heartbeat capability manifest.

**Минимальный capability result для адаптера:** operation ID, supported schema/profile, principal/deployment allowance, instance/document, read/write/preview mode, evidence class, requires confirmation, ограничения replay и freshness. Сначала это может быть небольшая версия JSON-контракта рядом с существующей route policy, без самостоятельного capability marketplace/service.

## 8. Проверка и качество evidence

### Выполнено непосредственно

Попытки `python` и `python3` запустить только projection/canonical JSON tests с `--noconftest -p no:cacheprovider` остановились до collection: **`ModuleNotFoundError: No module named 'pytest'`**. Dependencies не устанавливались; container suite и C# build не запускались, чтобы не мешать текущей 1205.1 и не трогать внешние системы.

Вместо объявления tests green проведена отдельная **stdlib-only probe** (`python -B -c`, из корня репозитория): импорт pure `design_state_projection/canonical_json`, AST-выделение `_shared_vector_payload` из существующего теста и двух pure-функций candidate ID без импорта app. Финальный запуск: **exit 0, 6 assertions PASS**:

1. Реальная проекция совпала с существующим golden hash `4A4CAB67B35F6F9B3A0E42BA56C5A366673675CBC871DFA302058977CC34E09E` (`data-service/tests/test_design_state_projection.py:25,35–110`).
2. Перестановка ObjState не меняет hash.
3. Изменение только root capturedAtUtc меняет hash.
4. Добавление geometry не меняет hash.
5. `canonical_json.hash_scalar_tuple('a|b','c','d') == hash_scalar_tuple('a','b|c','d')`: legacy helper сохраняет delimiter collision (`data-service/canonical_json.py:59–78`; известное исключение: `spec/DG-ID.md:64`). Это **не** обвинение нового `compute_dg_id` в той же коллизии.
6. `compute_param_state_id` одинаков при одинаковых rule/parameter values и разных provenance.definitionId (`data-service/cg_paramstate_store.py:73–95`).

Первый запуск AST-probe остановился на отсутствующем `Any` в локальном namespace; после явного добавления typing.Any выполнен весь набор. Ни app, ни DB/CAD клиент не импортировались; `-B` запрещал bytecode writes. Это узкая проверка pure Python, не полный pytest и не C# parity execution.

### Что проверяют существующие тесты — и чего нет

| Источник | Фактический вид доказательства | Не доказывает |
|---|---|---|
| `data-service/tests/test_dg_identity.py:62–170,479–529,638–720` | Stateful FakeGraph: bind/resolve, последовательный конфликт, property sharing | Neo4j concurrent uniqueness, real Revit, document-scoped native identity |
| `data-service/tests/test_computgraph_publish.py:1–12,70–113,568–616,843–1044` | Op-tag simulation, provenance и ATTRIBUTE_OF, idempotent повтор | Реальный Cypher rollback/race, удаление stale edges, несколько definitions с одинаковыми cgId |
| `data-service/tests/test_update_flow.py:73–109` | Mock stale token + write/session calls | Атомарный CAS, multi-note rollback, durable before/after revisions |
| `data-service/tests/test_rule_conflict.py:53–79,87–223` | Mock publishability refusal и success | Конкурентное supersede, retry после успешного supersede, полная редакционная история |
| `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs:278–333` | Явные divergence assertions обоих v2 readers | Универсальное lossless replay; тесты, утверждающие потерю значения, не означают исправление |
| `data-service/tests/test_cg_paramstate_store.py:150–242` | Accept/domain/provenance requirements, сужение published domain | Correspondence provenance настоящему provider/canvas, detection устаревшего неопубликованного canvas |
| `spec/REPRODUCIBILITY.md:20–59,126–148` | Нормативное разделение measured/model-dependent/unmeasured и replay | Нельзя переносить DE-01 fixed fixture на live GH solver или LLM determinism |

## 9. Владельцы работ и минимальный порядок

| Пакет | Уже назначенный owner / evidence | Что допустимо предложенному v13 |
|---|---|---|
| Production canonical statuses / GH wire | **v12.0 1205.1 executing**, `.planning/STATE.md:24–33`; `.planning/ROADMAP.md:320–344` | Потреблять после независимого closure evidence. Не менять контракты параллельно, не объявлять gate уже пройденным. |
| V7/V8 runtime/spec/ontology и semantics propagation | **Future v11 1104–1106**, `.planning/milestones/v11.0-ROADMAP.md:110–170` | Согласовать version/profile prerequisite для адаптера; не переносить полную ontology migration в desktop/product milestone. |
| Historical/live GH UAT и project inputs у capture | Phase 40 / existing owners; `spec/DG-ID.md:124–137`; `.planning/ROADMAP.md:310–311` | Не считать отсутствие обязательного capture project решённым серверным project filter. Новая remote integration может добавить отдельный acceptance gate, не закрывая старый UAT заочно. |
| Wire substrate/diff, component KB, bridge writes/edit | **Future v10**, `.planning/milestones/v10.0-ROADMAP.md:5–24,32–50,56–96` | При одобренном переносе явно переназначить outcomes/requirements/test gates. Сейчас «порт KB/BWRT/SEDT» — предложение о реализации planned capability, не перенос готового модуля. |
| Тонкий REST adapter, локальная host routing, operation metadata | Новая product-интеграция; утверждённого v13 в просмотренных planning MD не найдено | Предлагаемый v13: узкий vertical slice, явная policy delegation DG server, reuse существующего ModelViewer. |
| Revision/CAS/source-link и comparison scope | Частично пересекается с v11 provenance/replay contracts и v10 snapshot work | Сначала contract-owner decision, затем bounded implementation. Не дублировать версии/статусы ещё одним DeGram control plane. |

**Порядок без scope creep:**

1. Зафиксировать, какие возможности доступны на текущем профиле, и дождаться доказанного 1205.1 closure для canonical outcomes.
2. Согласовать с v11 минимальный version/profile/provenance контракт, не активируя весь milestone по умолчанию.
3. Вертикальный read/propose/confirm slice одного правила, одного definition и одного accepted state. Сохранять source/rule/definition revisions и отказ на stale confirmation.
4. Закрыть конкретные CAS/key/reader inconsistencies, препятствующие этому slice; двухпроектные и двухклиентные негативные тесты на disposable fixtures.
5. Только затем переносить planned GH write/edit capability с отдельными safety/undo/live UAT gates.

**Не нужно сейчас:** новая общая база онтологий только ради общего dropdown; полный event sourcing всех nodes; новый rules engine вместо SWRL/Cypher/SHACL partition; новый identity spine вместо dgId; custom workflow kernel вместо n8n; единый «universal graph CRUD» для LLM. Существующие n8n deterministic domain workflows можно сохранить, но их входные scope, active revision и output evidence должны быть такими же строгими, как у прямого adapter call.

## 10. Acceptance gates и неизвестное

Перед заявлением готовности DeGram Agent должны быть показаны:

- Two-project vocabulary isolation плюс explicit shared-release import и immutable pin; ни одного расширенного private MATCH ради общей vocabulary.
- Rule source revision → конкретная rule revision → binding/parameter → `(rule,object)` result traversable без догадок по названию; mutation исходника не меняет historical explanation.
- Повтор supersede безопасен, competing activation конфликтует; confirmed batch knowledge update либо атомарен, либо явно partial; source history переживает повторный ingest.
- Два definitions с одинаковыми parameter values не перезаписывают accepted state attribution; representation key корректен для нескольких source models; concurrent bind не создаёт двусмысленного владельца.
- Новый publish удаляет/retire-ит только свои stale edges; stale publisher не перезаписывает current snapshot без решения пользователя.
- Оба исторических v2 shape читаются без silent null или дают явное unsupported-format; replay не обещает восстановление исключённой геометрии.
- Hash сравнения имеет объявленную область и версию; различаются equivalence содержимого, capture identity и design-space comparability.
- Production GH serialization сохраняет canonical non-verdicts; evidence gate относится к настоящему wire path, а не к hand-built Python payload. Это проверяется владельцем 1205.1.
- Capability ответ отличает installed/registered, reachable, authorized, verified, planned; heartbeat не даёт разрешения на write/replay.

**U / недостающие входы:** утверждённая v13 ownership migration; организационная политика словарей; требуемые юридические/регуляторные source metadata; реальные Neo4j constraints; ожидаемая concurrency и worker count; актуальная версия deployed workflows; реальные GH/Revit model identity/clone semantics; свежие live replay/solver/host-routing доказательства. Это не причины изобретать новый framework; это решения и измерения, которые нужно ограниченно получить.

## Изменения аудита

Создан только этот отчёт. Исходный код, ontology/spec/planning, vault, зависимости и runtime не изменялись; миграции, commits, live CAD и тесты с внешними побочными эффектами не выполнялись. Все архитектурные/семантические предложения — **manual decision**, не auto-fix.

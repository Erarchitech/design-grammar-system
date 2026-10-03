# Phase 1300: Контракты, baseline и ownership — Context

**Gathered:** 2026-10-03
**Discussion:** 2026-10-02 — 2026-10-03
**Status:** Ready for planning
**Authority:** владелец последовательно выбрал варианты и разрешил сформировать итоговый контекст и журнал ответом «1». Это завершение discuss, а не completion Phase 1300 или допуск product implementation.
**Scope:** DGCN-01, DGCN-02, DGCN-03, DGCN-04.

<domain>
## Phase Boundary

Phase 1300 готовит принятый versioned V8-профиль для выбранного DeGram MVP, однозначную ownership/disposition сверку, воспроизводимый baseline текущего DG, учебный corpus/expert gold и утверждённый decision register. Владелец принимает разрешённые границы и доказательства до зависимой реализации Phases 1301–1307.

- **DGCN-01:** версии/хеши ontology/mapping, identity, canonical status/evidence, rule/state revision и source authority; реальные компоненты, их владельцы и разрешение критических несовместимостей.
- **DGCN-02:** единственный delivery owner, disposition и ссылки по каждому переносу v9.1/v10 и ORCH/RING debt. Transferred/adapted/superseded — не completed. Полный ledger сохраняется; обсуждение не назначает второй implementation owner.
- **DGCN-03:** учебные задания plan-layout, urban-block, project-documentation; fixtures/gold, CAD/plugin версии, participant/counterbalance protocol, raw current-DG baseline, Viewer matrix и заранее утверждённые correctness/traceability/benefit gates.
- **DGCN-04:** конфигурация данных/LLM/login/roles, deployment и доступ двух ПК, exact Revit read/measurement/dependency/write slice и Google Drive source/publication path. Неразрешённое решение блокирует зависимую capability.

### Унаследованные утверждённые boundaries

- Минимальный DeGram Desktop fork на ПК участника; DG владеет корпоративными данными, правами и авторизацией. Переиспользуются DG web и полный V2 Model Viewer, включая web-only reviewer.
- Пять графов: Ontograph — термины; Metagraph — правила одного проекта/applicability; ComputGraph — script/model bindings; ValidGraph — проверенные состояния/runs; SpecGraph — источники и основания решений. Runtime casing/profile фиксируется по принятому контракту, без молчаливого переименования.
- Company vocabulary и project rules различаются по scope и полномочиям. Lessons learned — разрешённая независимая копия с новым ID/provenance, адаптацией и свежей destination проверкой/утверждением; исходный verdict не переносится.
- Read выполняется в разрешённой области; LLM предлагает и объясняет. Typed mutation/publication подтверждает человек, applicable evaluator формирует scoped verdict, человек отдельно принимает проектное решение.
- v11 владеет V8 runtime/normative mapping/partition и publication; v12 — существующим status/evidence/parser/identity/replay/security и 1205.1 wire closure. v13 доставляет новые product endpoints/store/UI и потребляет основание, а не создаёт competing engine.
- Произвольный код из LLM, universal graph CRUD, whole-definition synthesis, шестой граф, новая CDE, общий bidirectional CAD sync, distributed CAD+DG transaction и универсальная детерминированность LLM/live canvas остаются вне MVP.

### Уровень готовности

v13 активен; v12 административно CLOSED_WITH_ACCEPTED_DEBT, technical verdict `gaps_found` и OPEN debt сохранены. В 1205.1 round-3 PASS имеет bounded scope. Обсуждение не объявляет долг устранённым, V8 готовым, Docker test server развёрнутым или baseline выполненным. Prepared versioned v13 package и outgoing v12 evidence остаются неизменными.

</domain>

<decisions>
## Принятые решения

### Контрактный профиль и ownership

- **D-01:** V8 как обязательное основание. До реализации зависимых возможностей DeGram согласовать и проверить V8 runtime с владельцем v11. Начало зависимой реализации может отложиться до готовности профиля; завершение рукописи и всего публикационного milestone v11 не требуется.
  - Gate — принятый V8-профиль. Текущий V7 не утверждён как fallback; выбор V8 не активирует v11 и не доказывает его готовность.

- **D-02:** Продолжать подготовку Phase 1300: определить LLM/data policy, доступ, CAD/CDE и задания пилота; измерить исходный baseline текущего DG. Baseline служит сравнению, а не допуску текущего runtime в DeGram. Зависимая реализация остаётся за V8 gate.
  - Исходный baseline текущего DG хранится отдельно с раскрытыми версиями. Сравнение DG/DeGram позже выполняется на одном согласованном основании.

- **D-03:** Полный профиль для выбранного MVP: проверяются все потребляемые DeGram контракты — ontology/mapping, identity, статусы/evidence, revisions и совместимость согласованных GH definitions. Профиль содержит точные версии, хеши, доказательства и ограничения. Возможности вне MVP не задерживают допуск.
  - MVP-профиль охватывает все потребляемые контракты, включая rule/state revision и source authority; критический конфликт блокирует зависимую capability.

- **D-04:** Независимая техническая проверка и утверждение владельца: автор изменений готовит профиль и доказательства; проверяющий, не участвовавший в их подготовке, сверяет совместимость, покрытие и ограничения; владелец принимает профиль по результатам проверки.
  - Автор профиля и независимый технический проверяющий разделены; эта независимость сохраняется при совмещении операторских ролей D-08.

### LLM, доступ и управление

- **D-05:** Провайдер и модели контролируются системой. Пользователи используют предоставленные системой LLM, а не собственные providers, аккаунты или API-ключи.
  - Это revision 2 после явной коррекции владельца. Режим личных providers и обязанность участников оплачивать личные вызовы отменены; история отмены хранится только в журнале.

- **D-06:** Ограниченный рабочий контекст по утверждённой политике: необходимые для задачи параметры выбранных объектов, правила и фрагменты источников. Система проверяет права и допустимость передачи конкретному provider; пользователь видит состав контекста. Обычные разрешённые запросы выполняются без повторных подтверждений. Передача whole-definition требует отдельного подтверждения и разрешения политики.
  - Доступ к данным DG и разрешение их передачи конкретному provider — разные проверки. Подтверждение пользователя не снимает policy deny; mutation/publication требуют своих подтверждений.

- **D-07:** Существующие DG-аккаунты и приглашения: переиспользуются вход DG и серверная проверка прав компании/проекта. DeGram и встроенный web работают от имени пользователя, без сервисных полномочий. Совместимость с Desktop, logout и отзыв доступа проверяются в Phase 1301. Корпоративный SSO не становится обязательным условием MVP.
  - Desktop, chat, встроенный web и tools проверяют действующие server-side company/project права; logout/revoke прекращают новые защищённые операции. Service-only/connector права не подменяют user access.

- **D-08:** Раздельные полномочия с возможностью совмещения ролей: одному человеку можно явно назначить несколько ролей. Оператор системы управляет доступными LLM и политикой передачи данных; steward компании утверждает изменения общего словаря; утверждающий проекта принимает редакции проектных правил и проектные решения. Каждое утверждение фиксирует, кто действовал и в какой роли. Права редактора проекта сами по себе не дают права выпускать корпоративный словарь.
  - Явные назначения company/project roles и actor/role каждой операции обязательны. Общий словарь не выпускается на основании одних прав project editor.

- **D-09:** Система назначает модель по типу задачи. Оператор задаёт модели для чата, подготовки правил и других разрешённых задач. Пользователь работает без ручного выбора, но видит фактические provider/model. Маршрутизация следует заданной конфигурации, а не произвольному решению LLM.
  - Маршрут задаётся операторской конфигурацией, не LLM. Requested и provider-attested served model различаются; неизвестный served model не выдумывается.

- **D-10:** Остановить LLM-запрос и предложить повторить: пользователь получает понятную причину — timeout, недоступность provider или исчерпание лимита. Доступные DG/web/CAD-функции продолжают работать. После восстановления пользователь повторяет запрос; ранее выполненные изменения не применяются повторно.
  - Автоматического fallback на другую модель/provider нет. После неопределённого результата начатой операции сначала reconciliation, затем разрешённое продолжение без повторной mutation.

- **D-11:** Учёт расходов и предупреждения, без автоматической остановки: оператор видит расход и получает уведомления. Запросы продолжаются, пока оператор вручную не ограничит доступ. Конкретные суммы и пороги задаются после выбора моделей и объёма пилота.
  - Budget advisory, manual access restriction. Provider quotas, auth/data policy и технические safety bounds сохраняются; оценочная стоимость маркируется как оценочная.

- **D-12:** Данные, права доступа и LLM контролируются через Web Design Grammars. Существующая Docker-система должна быть размещена на отдельном тестовом сервере. DeGram Desktop и локальные Revit/GH adapters остаются на ПК участников и потребляют централизованно управляемые данные, права и LLM.
  - Одна Web Design Grammars surface управления; enforcement выполняет backend. Тестовый сервер не означает обязательную локальную LLM; remote-server доступ к двум local CAD bridges ещё нужно спроектировать и проверить.

### CAD/Revit и CDE slice

- **D-13:** Чтение, измерения и проверка зависимостей плюс ограниченные подтверждаемые записи. Заранее определяется точный перечень изменяемых параметров и допустимых операций. DeGram показывает изменение и целевые объекты, получает подтверждение, выполняет операцию и проверяет фактический результат. В план включаются проверки отказов и отката; произвольный код и универсальное редактирование модели исключены.
  - Typed allowlist, exact scope, authority, preview/confirm, live read-back, rollback/undo и reconciliation обязательны. Произвольный CAD/Python/C# execution и обещание distributed CAD+DG transaction исключены.

- **D-14:** Параметры экземпляров и типов: дополнительно к согласованным параметрам выбранных экземпляров разрешены согласованные изменения типа, которые могут затронуть несколько экземпляров. Перед подтверждением DeGram показывает все затрагиваемые объекты; результат проверяется для всей области изменения. Конкретные параметры, допустимые значения, зависимости и инварианты фиксируются на выбранных пилотных моделях до исполнения.
  - Изменение типа включает всю затрагиваемую область, не только selection. Создание/удаление элементов, duplicate types и Family Editor этим решением не разрешены.

- **D-15:** Оба сценария: размеры параметрического элемента → геометрия и измерения; отметки и смещения → положение и размеры зависимых элементов. Корпус покрывает согласованные изменения параметров экземпляров и типов, ожидаемую реакцию связанных объектов и сохранность заранее заданных инвариантов.
  - Оба сценария получают отдельные pre/post evidence. Нужны реальные IDs, units, параметры, expected effects и invariants; совпадение имени/геометрии не доказывает сохранение intent.

- **D-16:** Одна фиксированная комбинация версий Windows, Revit, Rhino/GH и DG adapters. На обоих ПК одинаковые версии тех приложений, которые используются на каждом из них. Остальные версии пока не заявляются поддержанными. Точные номера версий фиксируются после проверки доступных пилотных ПК.
  - Фиксируется одна compatibility combination; версии общего приложения совпадают на двух ПК, но установка всех CAD на оба ПК не требуется.

- **D-17:** В существующем Google Drive компании: используется выбранное проектное пространство, его редакции документов и права доступа. DG хранит ссылки на источник, редакцию/хеш и фрагмент; после подтверждения публикует принятый материал и проверяет результат и доступ получателя.
  - Google Drive выбран, folder/source/destination/auth path ещё открыты. DG membership не предоставляет Drive permission. Выбор Drive не аттестует полный стандартный CDE workflow.

- **D-18:** Отдельная папка пилота внутри существующего проектного пространства Google Drive компании: выделяются разрешённые копии источников и место для принятых результатов. Рабочие материалы проекта сохраняются отдельно.
  - Учебный corpus D-19 — основной. Любая копия существующего источника требует разрешения и provenance; рабочие материалы не изменяются ради пилота.

- **D-19:** Специально подготовленные учебные модели: компактный, контролируемый набор GH/Revit-файлов с заранее известными зависимостями и ожидаемыми результатами. Выводы о пользе ограничиваются этим учебным набором. Отдельно сохраняется обязательная проверка совместимости существующих reference .gh. Конкретные файлы и ожидаемые результаты утверждаются до измерений.
  - Оба Revit сценария, instance/type cases, negative cases и plan-layout/urban-block/project-documentation сохраняются. Legacy reference .gh/GUID regression — отдельный обязательный evidence, а не замена учебного corpus.

- **D-20:** Отдельный комплект для каждой принятой редакции: в папке пилота появляется новый явно обозначенный комплект с карточкой решения, результатами проверки и ссылками на точные версии моделей и источников. Предыдущие принятые комплекты сохраняются, чтобы получатель восстановил основания конкретного решения.
  - Каждая принятая редакция получает отдельный publication package; старые комплекты не перезаписываются. Receipt и доступ получателя проверяются, authoritative записи остаются в графах.

- **D-21:** Все данные Design Grammars хранятся в серверных графах как полноценные записи словаря, правил, привязок, состояний, измерений, evidence, решений и истории, а не только ссылки. Исходные документы и бинарные .gh/.rvt-файлы хранятся отдельно в Google Drive и рабочей CAD-среде; графы фиксируют их идентичность, версии/хеши и необходимые данные. Комплекты в Google Drive являются публикационными представлениями серверных записей.
  - Сохраняются пять graph responsibilities. Desktop/Drive не являются вторым authoritative store DG; полные binary .gh/.rvt не требуется помещать в графы. Реальное соответствие текущей persistence ещё проверяется.

### Baseline, пилот и Viewer parity

- **D-22:** Сквозные задания: участник проходит источник → правило → привязка → изменение модели → проверка → принятие → передача другому участнику и публикация. Результат измеряется целиком и по этапам, чтобы оценить пользу DeGram для всей цепочки работы, а не только отдельной команды.
  - Paired/counterbalanced задания, одинаковое согласованное backend/rules/models/LLM основание, раздельный setup/training и сохранение failed attempts. В current-DG arm честно раскрываются ручные этапы и отсутствующие функции.

- **D-23:** Автор корпуса и независимый предметный эксперт: автор готовит задания и ожидаемые результаты; эксперт, не участвовавший в подготовке, проверяет их по источникам и моделям. Владелец утверждает пакет до измерений.
  - Gold готовится до измерений по источникам/native моделям; ответы LLM и DG не эталон автоматически. Неразрешённые expected-result разногласия блокируют включение задания.

- **D-24:** Снижение общей трудоёмкости сквозного задания. Основной показатель — затраты на всю цепочку, включая исправления, проверку и передачу получателю. Ускорение автора не считается выигрышем, если оно увеличивает работу проверяющего или получателя.
  - Измеряется трудоёмкость всей цепочки автора/reviewer/получателя плюс rework. Скорость не компенсирует correctness, traceability, security или перенос нагрузки на других.

- **D-25:** Небольшой пилот с двумя участниками на двух ПК: они выполняют сопоставимые учебные задания через текущий DG и DeGram и меняются ролями автора и получателя. Порядок инструментов чередуется; задания различаются, чтобы участник не повторял уже известный ответ. Выводы ограничиваются этим составом и корпусом без обобщения на всех пользователей.
  - Два человека — ограниченный учебный pilot, не population effect. Разные эквивалентные задания и смена порядка/ролей ограничивают learning carry-over; эксперт D-23 и verifier D-04 сохраняются отдельно.

- **D-26:** Матрица функций, автоматизированные проверки и живой UAT. Перечень сверяется с существующим полным Viewer; для каждой функции фиксируется ожидаемый результат. Повторяемые проверки покрываются регрессионными тестами, реальные сценарии проверяются в браузере и внутри DeGram, web-only reviewer работает без Desktop. Известные проблемы исходного Viewer фиксируются отдельно.
  - В 1300 принимается полный inventory/parity matrix с baseline defects и expected outcomes; 1304 доказывает contextual parity, 1307 retest. Web-only review и browser/Desktop UAT не заменяются automated tests.

- **D-27:** Обоснованный пакет после исходного baseline, затем утверждение владельца. По учебному корпусу, экспертному эталону и измерениям текущего DG подготавливаются минимальный выигрыш общей трудоёмкости, допустимые отклонения измерений и критерии корректности, требования к полноте traceability и восстановлению решения, число заданий, повторов и правила анализа. Предметный эксперт проверяет обоснованность критериев, владелец утверждает пакет до сравнительных испытаний DeGram.
  - Сейчас числовых targets нет. Их подготовка/предметная проверка/утверждение — Phase 1300 gate; сравнение DeGram не используется для post-hoc выбора порога. Если baseline pre-V8, переносимость на единое сравниваемое основание обосновывается до серии.

### Полномочия ассистента

Отдельного делегирования спорных product choices «реши сам» не было. Research/planning выбирают технический HOW внутри утверждённых boundaries; новые scope, thresholds, реальные principals/модели/CAD/сервер/Drive targets требуют предусмотренного согласования. Отмена личных providers отражается только текущим D-05 revision 2; финальный контекст не использует отменённый режим.

</decisions>

<open_gates>
## Открытые уточнения, владельцы и условия допуска

Все строки ниже — **OPEN**. Это оставшаяся работа Phase 1300 и зависимых планов, а не выполненные acceptance. Названия ролей описывают ответственность; конкретные люди и полномочия ещё не назначены. Планирование разрешено; dependent implementation/release не получают автоматический допуск.

| Gate | Что подготовить и проверить | Владелец / обязательная приёмка | Что блокируется |
|---|---|---|---|
| G-01 V8 MVP profile | Exact ontology/mapping/identity/status/evidence/revision/source contracts, версии/хеши, capability coverage, GH regression и критические incompatibilities. Реальное V8 loading вместо текущего default V7 | v11 normative/runtime owner совместно с v12 contract owner; отдельный technical verifier D-04; финальное утверждение владельца | Принятие DGCN-01, exit 1300 и зависимая capability до её приёмки; whole v11 manuscript closeout не требуется |
| G-02 Ownership/debt reconciliation | Сверить каждый source ID и split clause v9.1/v10, ORCH/RING; признанное superseded отдельно от completion. Ссылки на evidence/disposition потребляемого v12 долга | Phase 1300 control-plane owner + существующие v9.1/v10/v11/v12/debt owners; приёмка владельцем | DGCN-02 и дублирующие/конфликтующие dependent plans |
| G-03 Управляемые LLM | Конкретные providers/models по task, user-facing chat/tool-calling path, served-model provenance, разрешённые компании/проекты/данные/transport, операторские права и отсутствие automatic fallback. Облачный/собственный inference ещё не выбран | Оператор системы / владельцы DG Web и backend; policy approval владельцем; evidence 1301, pilot retest 1307 | Неоднозначная конфигурация DGCN-04; dependent LLM task до разрешённого и проверенного пути |
| G-04 Cost accounting | Кто оплачивает общий доступ, actual/estimated usage method, числовые warning thresholds и manual restriction procedure. Plan-budget advisory D-11 сохраняется | Оператор системы и владелец | Запуск пилота без объявленного учёта; не добавлять автоматический budget-stop вопреки D-11 |
| G-05 Назначения и user access | Named operator/steward/project approvers, company/project memberships, migration/release/retirement authority. Desktop/Web/chat/tools logout/revocation и scoped model access | DG authorization/governance owner и назначенный оператор; owner approval; security evidence 1301/1302/1307 | Принятие конфигурации 1300 и операции до действующего authority; обязательный SSO не добавлен |
| G-06 Test server | Адрес/ОС/ресурсы, доступ, Docker manifests, persistence/backup/recovery и разрешённый deploy/rollback; безопасный HTTP/TLS путь с двух ПК, секреты и изоляция internal ports | Оператор deployment с DG backend owner; существующий security owner v12; отдельное runtime разрешение | Multi-user/test-server допуска до проверки security gates; отсутствие живого сервера не маскируется local-profile PASS |
| G-07 Два ПК / local bridges | Exact Windows/Revit/Rhino/GH/plugin/adapters manifest; process/document identity и capability handshake; remote Web сервер не выбирает localhost автора вместо конкретного ПК | DG native adapter owners и оператор двух рабочих мест; acceptance 1301 | Dependent live read/write/handover; схема безопасного per-PC routing должна быть доказана |
| G-08 Учебный corpus и Revit writes | GH/Revit/reference файлы и hash; точные type/instance параметры, ranges/units, expected pre/post effects обоих сценариев, неизменяемые invariants, affected scope, negative cases, preview/confirm/read-back/undo и recovery | Автор корпуса + независимый предметный эксперт D-23; native adapter owners; финальное утверждение владельца | DGCN-03/04, dependent writes и 1306 acceptance; model validity не предполагается |
| G-09 Google Drive path | Реальные folder/source/destination IDs, типы исходных файлов, revision/hash/fragment mechanism, разрешённый auth/publication path, distinct revision packages, read-back и recipient permissions | Оператор проектных документов/Drive и source/publication product owner v13; confirmation уполномоченного человека | Source workflow и CDE publication до доступа/receipt; DG account сам по себе не Drive permission |
| G-10 Серверное graph storage | Сопоставить все DG domain records с пятью графами, immutable revisions/provenance/history, server read-back и восстановление без author chat. Native/source binaries остаются отдельными | v13 product store/API owners; v11/v12 normative owners по потребляемому foundation | DGCN-01/04 и dependent domain writes; текущая persistence не объявляется соответствующей по одному выбору architecture |
| G-11 Gold/baseline/pilot protocol | Проверенные fixtures/gold, два named participants/experience, training и измеряемые задания отдельно, task variants/counterbalance, repetitions/time accounting, raw current-DG failures. Pre-V8 baseline и единое V8 основание сравнения разделены | Автор корпуса/protocol + независимый предметный эксперт; владелец утверждает | Принятие baseline DGCN-03 и comparative measurement до фиксированного протокола |
| G-12 Numeric acceptance | Benefit threshold общей трудоёмкости, correctness/measurement margins, traceability/handover targets, analysis/failure rules. Подготовка после baseline, независимая предметная проверка, утверждение до DeGram comparative series | Автор протокола + независимый предметный эксперт D-23; окончательное утверждение владельца | Соответствующий exit 1300 и pilot/release; числа не выдумывать и post-hoc не подгонять |
| G-13 Viewer matrix | Full active V2 inventory, baseline outcomes/defects, expected results по всем функциям и contextual review; automated + browser/Desktop/web-only UAT protocol | DG Viewer owner + независимый reviewer/владелец для утверждения matrix; integration доказательства 1304, retest 1307 | Принятие matrix 1300, contextual parity и release; archived legacy renderer не используется как второй product UI |

### Влияющий v12 долг

По `.planning/v13.0-ACTIVATION.md` и accepted-debt register остаются отдельные gates: runtime row provenance/hashes и replay exclusions; независимый evaluator/determinism baseline (включая retained D08 FAIL), incomplete historical LLM provenance; n8n credential rotation и whole-UI/security acceptance; identity/canonical scalar encoding и geometry/projection limitations; live CAD/recognition/provider-switch/Phase40 и 824/825 evidence. У каждого сохраняется исходный owner. Planning disposition и ограниченный PASS 1205.1 не закрывают эти долги; критический пробел блокирует соответствующую capability.

### Последовательность подготовки для planning

1. Inventory и discrepancy register V8/ownership/debt без миграции на веру; получить проверенный MVP-профиль по D-01..04.
2. Зафиксировать операционный decision register и реальные authority/environment targets, затем учебный corpus, live-measurement plan, gold и Viewer matrix.
3. До сравнительной серии предъявить raw current-DG baseline и numeric protocol по D-27; подтвердить одинаковое основание сравнения и переносимость pre-V8 baseline, если оно отличается.
4. Независимая проверка evidence и owner checkpoints принимают реальные результаты DGCN-01..04. Этот контекст только задаёт решения для этих работ.

</open_gates>

<canonical_refs>
## Канонические ссылки

Downstream researcher/planner сверяют relevant documents до планирования; перед implementation читают нормативные контракты применимой поверхности. Все пути относительно корня репозитория. Исторические документы preparation/archives не переопределяют текущие выбранные решения или milestone status.

### Управление milestone и основание решений
- `.planning/ROADMAP.md` — Phase 1300, DGCN-01..04, последовательность 1300–1307 и phase gates.
- `.planning/REQUIREMENTS.md` — Утверждённые 51 MVP requirements и единственный delivery mapping; completion требует evidence.
- `.planning/PROJECT.md` — Активный v13.0, core value, общие boundaries.
- `.planning/v13.0-ACTIVATION.md` — Реальная активация и влияющий OPEN debt; разрешение control-plane, не deployment certification.
- `.planning/milestones/v13.0-CONTEXT.md` — Исторически утверждённый подготовительный пакет; его Not active/isolation notices относятся к подготовке, текущий статус задают active records.
- `.planning/milestones/v13.0-OWNERSHIP.md` — Единственные владельцы и source-ID dispositions v9.1/v10/v11/v12 и ORCH/RING.
- `.planning/milestones/v11.0-REQUIREMENTS.md` — V8 runtime и normative ownership; D-01..04 выбирают обязательный MVP-профиль, а не завершение всего v11.
- `DG_OBSIDIAN/knowledge/decisions/DeGram approved process and company-project rule scope.md` — Утверждённый бизнес-процесс, company/project scope, пять графов и авторитет DG.
- `docs/reviews/degram-framework-integration/DEGRAM-FRAMEWORK-INTEGRATION-REVIEW.md` — Сохранённое исследование, §§5, 7–11; findings не являются implementation evidence.
- `CLAUDE.md` — Правила репозитория, schema propagation и normative boundary owners.

### Исходный v12 evidence и остаточный долг
- `.planning/milestones/v12.0-ACCEPTED-DEBT.md` — Accepted OPEN debt, прежние владельцы и resume gates.
- `.planning/milestones/v12.0-MILESTONE-AUDIT.md` — Сохранённый gaps_found audit; administrative closeout не заменяет runtime acceptance.
- `.planning/audit-evidence/v12.0-closeout/closeout.json` — Формальный override_closeout / closed_with_accepted_debt.
- `.planning/milestones/v12.0-phases/1205.1-canonical-status-gh-publish-closure/1205.1-VERIFICATION-3.md` — Bounded round-3 PASS canonical GH publish closure, не full milestone certification.

### Нормативные контракты и безопасное размещение
- `spec/DG-ID.md` — Identity, binding/replay и ограничения канонизации.
- `spec/EVIDENCE-CONTRACT.md` — Canonical status/evidence и версия envelope; отдельная граница operational outcome.
- `spec/SWRL-SUBSET.md` — Фактически поддержанный parser/evaluator subset и non-verdict outcomes.
- `spec/RULE-PARTITION-POLICY.md` — Разделение evaluator ownership, SHACL и design compliance.
- `spec/REPRODUCIBILITY.md` — Фиксированные inputs/configs/provenance; без универсальной детерминированности LLM/live CAD.
- `spec/SECURITY-BOUNDARY.md` — User/connector/service principals, tenancy, local/multi-user и credentials/rotation gates.
- `spec/LPG-OWL-MAPPING.md` — LPG/RDF/OWL mapping; текущие V7 references — вход для V8 сверки, а не разрешённый fallback.
- `spec/DEPLOYMENT.md` — Существующий Docker stack, порты, TLS и multi-user gate; hosted test deployment ещё требуется.
- `spec/API.md` — Существующие HTTP endpoints и их authorization boundaries.
- `spec/DATABASE.md` — Существующие graph properties, state/run/evidence persistence и schema surfaces.
- `spec/GRASSHOPPER.md` — Serializer/plugin integration, connector scope и direct-Bolt limitations.

### Проверенные code seams для дальнейшего исследования
- `dg-reasoner/reasoning.py` — По умолчанию DG_OWL_PATH указывает V7; проверять реальный выбранный runtime, не объявлять V8 готовым.
- `data-service/evidence_contract.py` — Strict EvidenceEnvelopeV2, ruleResults и resource-bounded JSON admission.
- `data-service/llm_gateway.py` — Provider adapters/settings, requested model и served_model; внутренний generate не готовый chat/tool orchestration.
- `data-service/gh_bridge.py` — Старый bounded TCP bridge, default host.docker.internal; не готовый per-PC remote-server routing.
- `ui-v2/src/lib/auth.js` — DG login/invitations, /auth/me, memberships и logout.
- `ui-v2/src/screens/ModelScreen.jsx` — Активный V2 Model Viewer; starting point inventory/parity, не доказательство live readiness.
- `graph-viewer/model-viewer/src/App.jsx` — Legacy Viewer reference. По CLAUDE.md отдельный legacy app архивирован; второй renderer не создаётся.

</canonical_refs>

<code_context>
## Существующий код и reusable seams

### Reusable Assets

- `ui-v2/src/lib/auth.js`: существующие `/auth/login`, `/auth/accept-invite`, `/auth/me`, memberships и `/auth/logout`. Это code seam, не выполненный Desktop/production acceptance.
- `data-service/evidence_contract.py`: `EvidenceEnvelopeV2` и `parse_envelope_model` сохраняют canonical contract и strict validation. New workflow потребляет его, не придумывает второй vocabulary outcomes.
- `data-service/llm_gateway.py`: существующие provider adapters, requested/served model provenance. Его file-backed settings упомянуты в текущем коде; D-21 требует inventory реальной storage boundary, а не предположения, что все DG domain records уже графовые. Secret storage не переносится в graph без отдельного security решения.
- `ui-v2/src/screens/ModelScreen.jsx`: active V2 functions/run-state grouping/object-rule inspection и остальные surfaces — исходный материал полного inventory. `graph-viewer/model-viewer/src/App.jsx` legacy reference, не target нового renderer.

### Established Patterns

- User/connector/service auth и company/project scoping, immutable source/rule/state references, canonical evidence/non-verdict, typed confirmations и operationId reconciliation остаются отдельными boundaries.
- Существующий GH serializer/annotation grammar/GUID compatibility переиспользуются. Dependent source/API/schema extension распространяется по CLAUDE.md и согласуется с normative owners; this discuss не меняет схему.
- Authoritative domain records находятся на сервере (D-21), исходные документы/CAD binaries — отдельно; права Drive, права DG, data-export policy и human acceptance не сливаются в одну проверку.

### Integration Points / известные несовпадения, требующие исследования

- `dg-reasoner/reasoning.py:94`: default ontology path V7. Фактический selected deployment/profile проверяется до допуска V8; suffix файла не доказательство semantic compatibility.
- `data-service/gh_bridge.py:27`: default `host.docker.internal`/socket bridge описывает local host topology. Отдельный remote test server и два ПК требуют explicit safe per-PC/process/document routing, а не сетевого раскрытия произвольного CAD listener.
- Внутренний `/llm/generate` и existing server n8n services не аттестуют user-facing multi-turn chat/tool-calling. Один local Desktop orchestrator и retained bounded server services сохраняют роли; второй rule compiler/agent engine не создаётся.
- Revit MCP availability/read/write support и two-PC runtime ещё не подтверждены. Typed adapters должны выполнять native UI-thread, exact scope, permitted operations и read-back; универсальный execute-code обход не выбирается.
- Google Drive source/publication adapter ещё не проверен; OAuth/access/revision/read-back mechanism исследуется на выбранных типах файлов. CDE receipt связан с server graph records, не с предположением об upload success.

</code_context>

<specifics>
## Предметные ориентиры владельца

- Web Design Grammars в Docker управляет данными, правами и системными LLM; общая система размещается на отдельном тестовом сервере.
- DeGram использует системные LLM с task routing оператора, без user model selector, личных ключей и автоматического fallback. Cost controls — advisory warnings и ручной контроль.
- Revit writes охватывают согласованные instance/type parameters; оба dependency сценария обязательны. Общий type impact раскрывается до подтверждения.
- Учебные GH/Revit-файлы, одна фиксированная CAD-комбинация, два участника/два ПК. Голд проверяет независимый предметный эксперт; V8 имеет отдельного technical verifier.
- Google Drive компании, отдельная папка пилота и отдельный комплект каждой принятой редакции. Полноценные DG domain records и история — в пяти серверных графах; документы и бинарные CAD исходники — отдельно.

</specifics>

<deferred>
## Вне текущего объёма

Новых идей на отдельную фазу в обсуждении не добавлено. Открытые G-01..13 остаются обязательными phase/dependency gates, а не discarded backlog. Сохраняются ранее утверждённые exclusions: full topology/historical arbitrary diff/cluster internals/slot synthesis/extended rules принадлежат v10; normative V8/publication/manuscript — v11; существующий foundational debt — исходным owners. SSO, multi-version CAD support, личные providers, automatic model fallback, универсальные Revit writes, новая CDE и внедрение второго renderer этим контекстом не добавлены.

</deferred>

## Граница текущей авторизации

Создание CONTEXT и DISCUSSION-LOG и обновление GSD session state разрешены последним ответом владельца «1». Product implementation, executable PLAN, activation других milestones, commit/tag/push, deploy/restart, secret reads/rotation, database/CAD/Drive mutations и paid inference не выполняются автоматически. Внутренние planning-файлы не являются runtime certification.

**Следующий workflow:** `/gsd-plan-phase 1300` — отдельно, на основании этого контекста. Phase 1300 остаётся незавершённой до проверенного evidence и owner acceptance её требований.

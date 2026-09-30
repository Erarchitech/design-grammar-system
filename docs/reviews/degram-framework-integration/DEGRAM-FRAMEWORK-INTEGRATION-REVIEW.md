# DeGram Agent в экосистеме Design Grammars

## Критическая проверка нового milestone по ptBIM, ITcon, литературе и реализации

**Дата:** 30 сентября 2026. **Статус:** исследовательское предложение, не утверждённый roadmap. **Решение:** условный GO с изменением приоритетов. Исходные публикации, продуктовый код и GSD planning этим исследованием не редактировались; коммитов, миграций и live CAD-вызовов нет.

## 1. Executive assessment

**DeGram полезен как единое рабочее приложение для управляемого изменения проектного знания и локальной модели. Одного desktop-чата с MCP недостаточно для цели Design Grammars.** Основная ценность — сохранить и сделать доступной другому участнику цепочку «источник требования → утверждённое правило → объект/параметр → конкретное состояние → проверка → принятое решение». Удобство вызова Revit/GH — средство, не конечный критерий.

Рекомендуемое название milestone: **v13.0 DeGram Agent — Governed Design-Intent Workspace**. Сохранить thin fork Hermes Desktop, локальные MCP, существующий DG backend и полный `ui-v2`/Model Viewer. Изменить предметную постановку: обычный CRUD заменить управляемыми предметными операциями; общую vocabulary отделить от проектных данных; версии источников/правил/состояний и краткое rationale включить в основной вертикальный сценарий, а не оставить косметическим audit trail. GH intent-based editing остаётся в MVP в ограниченном наборе поддерживаемых компонентов; генерация произвольных definitions, универсальный solver, полноценная межорганизационная ontology federation и непрерывная двусторонняя синхронизация моделей — позднее.

**Порядок:** закрытие v12.0/1205.1 → минимальные совместно согласованные v11 контракты, необходимые продукту → v13.0 → оставшаяся v10 Script Intelligence. v9.1 как отдельный Eto-chat superseded после утверждения переноса функций. Полный publication/manuscript scope v11 не является обязательной задержкой Desktop; отсутствие согласованной версии семантики, напротив, блокирует зависящие от неё записи.

## 2. Evidence and method

### 2.1 Прочитанные пользовательские материалы

| Код | Точный файл | Объём | Роль |
|---|---|---:|---|
| P | `Publications/ptBIM2026_Evgenii_Ermolenko_UMinho_R2.pdf` | 10 физических PDF-страниц | Основная статья о framework и трёх практических сценариях |
| T | `Publications/T1_ITcon_DG_ErmolenkoE_Submission.pdf` | 30 физических PDF-страниц | Онтологический контракт, CQ1–CQ4 и границы доказанного |
| S | `Publications/01_ptBIM26_R6.pdf` | 24 слайда | Дополнительная презентация, не замена P |

Все ссылки на P/T ниже используют **физическую PDF-страницу**, включая титульные листы T. Полные тексты, bibliography и annexes прочитаны основным агентом. Рукописи не передавались исследовательским субагентам: их работа ограничена публичными источниками и адресным чтением кода. Текст извлечён PyMuPDF; SHA-256 и source paths — `evidence/paper-metadata.json`. Чтение таблиц по PyMuPDF устранило ошибки автоматического PDF→Markdown, например `75.0` вместо ошибочно извлечённого `75A0`.

Визуальный анализ изображений трижды завершился timeout; для ключевых схем S выполнен локальный RapidOCR. Его текст не является независимой визуальной проверкой направлений стрелок и мелких подписей. Основные выводы опираются на полный P/T prose, а не реконструкцию схем.

### 2.2 Уровни доказательств

- **Source-verified:** прочитаны код/спецификация/полный первоисточник. Это не live-проверка развёртывания.
- **Offline-verified:** реально выполнена узкая локальная проба с сохранённым результатом.
- **Reported:** результат сообщён авторами публикации; здесь не воспроизведён.
- **Planned/conceptual:** явно проектируемая возможность.
- **Unknown/partial access:** full text или runtime evidence не получены.

Исходный HEAD: `37450d4e6ec6763ff1c35953a560cbfcec767dc6`, ветка master, dirty tree; текущая 1205.1 выполняется параллельно. На последнем чтении STATE: **executing, plan 02 of 06**, не complete. Source audit — снимок во времени; новые изменения соседней сессии могут устранить отдельные finding и должны быть повторно сверены до implementation planning.

### 2.3 Состав пакета

- `parts/paper-framework-analysis.md` — полный анализ P/T/S и требований к продукту.
- `parts/public-agentic-literature.md` — агентная BIM/GraphRAG/LLM литература.
- `parts/public-design-literature.md` — intent/rationale, DCM, co-evolution, LOT, SHACL, reuse.
- `parts/public-ptbim-literature.md` — references оригинала P, ошибки identity и актуальные продолжения.
- `parts/repository-semantic-seams.md` — source-backed проверки реализации и ownership.
- `evidence/integration-findings.json` — 18 уникальных DGINT findings, action и acceptance.
- Собственные evidence и tools находятся рядом с отчётом. Публичные PDF/metadata трёх literature-streams находятся **в `evidence/public-agentic/`, `evidence/public-design/`, `evidence/public-ptbim/` от корня репозитория**, а не внутри каталога этого отчёта. Это различие путей проверено.

## 3. Что следует из статей — и что из них не следует

### 3.1 Роль приложения в framework

P §2.1–2.3, с. 3–5 разделяет **Model Domain** и **Grammar Domain**, связывая их shared knowledge core и API/MCP. T §3.2, с. 12–14 задаёт пять графов; §4, с. 18–20 добавляет организационную семантическую интеграцию, четыре входных канала и управляемые изменения.

DeGram — прикладной communication/integration client и пользовательская оркестрация между этими доменами. Он **не шестой граф, не новый reasoner, не источник истины для геометрии и не замена CDE**. Не смешивать «пять сервисных слоёв» S с «пятью графами» T: это разные оси архитектуры.

P §2.3 допускает специализированные storage domains и прямо ограничивает current implementation центральным graph repository. Поэтому не требуется переносить всю геометрию, файлы, timeseries и документы в Neo4j. Единая семантическая идентичность совместима с разными авторитетными источниками и неизменяемыми evidence snapshots.

### 3.2 Граница доказанного

T §2.4, с. 11 прямо исключает из доказанного user-level interoperability, cross-organisation governance, identity conflict resolution и reliability of LLM-assisted authoring. CQ1–CQ4 проверяют конкретные graph queries и reasoning outputs, а не многопользовательский Desktop. P §3.3, с. 8 сообщает предварительные academic metrics; §4 называет production/scalability validation будущей работой.

Следовательно DeGram — возможность **проверить ранее предложенную операционную архитектуру**, а не упаковка уже доказанной экосистемы. Обещать сокращение затрат, полную интероперабельность и сохранение всего intent до испытаний нельзя.

### 3.3 Продуктовая единица — решение с контекстом

Вместо «пользователь редактирует узлы графа» основной сценарий: «изменилось требование; какие объекты и вычисления затронуты; как изменить модель; на чём основан новый результат; кто выбрал вариант». T CQ1–CQ3 дают навигационные операции, T Session/SpecGraph — место provenance/rationale. P §2.5 и §3 различает domain expert и computational designer и сохраняет архитектора ответственным за решения.

## 4. Критическая матрица всех аспектов первоначального milestone

| Аспект | Решение | Улучшение и ожидаемая польза | Что не добавлять |
|---|---|---|---|
| Hermes Desktop fork | Сохранить | Thin fork branding/install/security surface; DG package использует существующий agent runtime. Нужен pinned upstream и upgrade regression | Второй chat engine, fork всей предметной логики |
| Корпоративный вход | Сохранить | Пользовательская DG identity, explicit permissions, expiry/revocation; роли UI не заменяют server enforcement | Service token на каждом ПК; обязательный SSO до подтверждения потребности |
| Активация проекта | Уточнить | Контекст включает endpoint/user/project, vocabulary/rules revision, native document и snapshot. Это устраняет stale-target и cross-project действия | Mutable server-global active project |
| Ontograph CRUD | Переработать | Project proposals + steward approval + организационный vocabulary release + project pin; shared read policy отделена от private data | Снятие `project` filters, бесконтрольный LLM mint, универсальный ontology marketplace |
| Metagraph CRUD | Переработать | Source-linked typed rule lifecycle, immutable accepted revision, atomic activate/supersede; retirement использованных правил | Разрушение atoms/history, universal Cypher write |
| SpecGraph CRUD | Повысить приоритет | Source revision/fragment, derived note отдельно от источника, короткая карточка решения, CAS | Копирование всего CDE или всего личного transcript в граф |
| Чтение всех графов | Сохранить | Typed object/task queries, paging, exact argument order, completeness и provenance. Graph visualization — экспертный режим | Выгрузка всей БД в prompt, вывод «нет» из ограниченного snapshot |
| Model Viewer | Сохранить полностью | Reuse `ui-v2`; реальные ссылки rule↔object↔state↔source, stale/coverage context; изоляция web surface и Speckle access | Второй renderer и общие client credentials |
| GH MCP | Обязательная основа | Локальный bridge per PC, explicit process/document, capability handshake, HTTP repositories вместо корпоративного Bolt | LAN listener с arbitrary host URL, второй serializer |
| DG addin nodes | Сохранить | Реальные GUID/ports, общие handlers с командами Agent, legacy regression | Удаление рабочих нодов ради единственного DG CHAT |
| GH structure consult | Сохранить | Existing parser/context/checkers; вопрос по выделению и объяснение доказанной трассы | Обещание, что recognition уже качественно надёжен |
| GH visual editing | Сохранить ограниченно | Intent→small patch→diff→approve→UI-thread apply→solve/readback; approved component set, invariant checks | Полная synthesis definition, произвольный code execution/plugin install в базовой поставке |
| DG mapping | Усилить | Exact atom/property→parameter identity; control input отдельно от emergent measurement; unit/direction/source | Mapping только по name, трактовка ATTRIBUTE_OF как доказательства причинности |
| Revit MCP | Сохранить с узким обменом | Real document-scoped identity + typed read/analysis/mapping + проверяемый перенос выбранной информации | Claim «GUID = interoperability», общий bidirectional model sync |
| Design State | Добавить в ядро MVP | Capture event, comparable content и выбранная альтернатива различены; pinned rules/mapping/geometry source | Полный DesignSpaceGraph или вывод о reformulation по двум hashes |
| CDE | Добавить минимально | Import/reference документа с version/hash/fragment; новый документ создаёт proposal и impact view | Новый CDE и коннекторы ко всем вендорам |
| LLM+n8n | Сохранить границы | Один пользовательский orchestrator, existing server pipelines как bounded domain services, corporate inference broker при выбранном режиме | Новый многоагентный оркестратор без ablation; дублированный rule compiler |
| Подтверждения | Уточнить | Один meaningful change set; различать authorization, commit, check outcome и human design acceptance | Approval на каждое чтение, несколько противоречивых чатов |
| Многопользовательский pilot | Усилить | Два реальных ПК и сравнительная проверка времени/качества/handover против current DG | `tools/list` или красивое демо как доказательство пользы |

Матрица включает исходные MVP функции; «новые» provenance/governance требования не повод молча вычеркнуть запрошенное GH editing. Если срок требует уменьшения объёма, это отдельное продуктовое решение.

## 5. Минимальные семантические контракты

### 5.1 Shared vocabulary без потери project security

T §3.2 утверждает организационный Ontograph, тогда как текущие `dg_context` и GH repositories фильтруют проектные термины (`data-service/dg_context.py:317–359`). Это реальный architecture seam.

Минимальный переход: один опубликованный организационный vocabulary package (namespace, release ID, digest, terms, provenance), явная зависимость проекта и приватный proposal/local extension. Физически можно начать file-backed manifest/release, не создавая отдельный ontology microservice. Предложения create/edit/delete доступны из DeGram, но опубликованное изменение утверждает steward; используемый термин deprecate/retire, а не незаметно удалить. Расширение shared storage — контролируемая миграция с проверкой двух проектов, не обход tenancy.

LOT обосновывает итеративные requirements/implementation/publication/maintenance и участие domain experts; это процесс, а не автоматическая гарантия качества словаря.[13]

### 5.2 Requirement, rationale, operation и evidence

**Requirement/intent:** чего необходимо добиться, applicability, source и критерий. **Rationale:** почему выбран этот способ/вариант и какие альтернативы рассмотрены. **Operation:** какие изменения реально выполнены. **Evidence:** каким методом получен результат для каких входов. Эти сущности связаны, но не взаимозаменяемы; такой вывод согласуется с Wyke & Lindhard, чья работа является обзором определений, не причинной оценкой внедрения.[8]

Минимальная карточка принятого решения: `intent/sourceRevision`, `selected alternative`, `reason`, `considered alternatives` при наличии, `affected objects/rules`, `actor/approver/time`, `state/run references`. Часть полей заполняется автоматически из operation envelope; rationale формулирует/утверждает человек. Не сохранять выдуманное объяснение отсутствующего основания и не требовать внутреннюю chain-of-thought модели.

### 5.3 Provenance chain

Целевая цепочка:

**SourceRevision/fragment → Requirement → RuleRevision → vocabulary release → точный binding → native snapshot → measured value/unit → evaluator version → canonical result → accepted decision.**

Это контракты и ссылки, а не требование немедленно создавать по новому graph-node на каждое поле. Переиспользовать существующие SpecNote/Session, Rule/SUPERSEDED_BY, evidence envelope и identity registry. PROV-O — полезный язык соответствия для долгосрочного обмена, не обязательная новая runtime ontology для MVP.[4]

`DesignRuleSession` сейчас сохраняет prompt и усечённый result, но не заменяет typed revision audit (`data-service/app.py:4072–4095`). Immutable `rulesJson` run содержит краткие сведения, а не полный executable ruleset (`app.py:1072–1085`): сохранённого ruleId недостаточно после destructive rule edit.

### 5.4 State и версии

Различать: тот же capture event; эквивалентные данные в объявленной проекции; варианты, которые допустимо сравнить. T §6, с. 26 прямо требует design-space membership для интерпретации переходов. Минимум MVP — task/alternative context и версия критериев, не автоматическая классификация мыслительного процесса автора.

Локальная probe подтвердила: capture timestamp меняет текущий state hash, геометрия исключена; candidate ID при разных definitionId может совпасть. Это не аргумент немедленно менять все исторические hashes. Нужно объявить область существующей проекции, versioned comparison contract и исправить только обязательные для нового workflow key/reader seams. Evidence: `evidence/offline-verification.json`.

### 5.5 Publication не является общей транзакцией CAD+graph

Одна операция несёт `operationId`, project/document/revision preconditions, ожидаемые изменения, result/status и ссылки на read-back. `applied_local`, `pending_publication`, `published` — операционные состояния, не замена канонических validation statuses. Повтор после timeout сначала уточняет status; не исполняет изменение заново вслепую. GH Undo восстанавливает локальный документ, но не удаляет автоматически опубликованные сведения. Нужны понятная reconciliation и retry, а не ложное обещание распределённой ACID-транзакции.

### 5.6 Проверка и полнота

Нужны отдельно target/applicability, completeness/freshness, solver/evaluator execution, canonical outcome и approval. SHACL проверяет shape относительно data graph; его conformance не подтверждает, что в граф попали все ожидаемые объекты.[1]

Реальные synthetic probes в этом исследовании:

- `sh:targetClass ex:Building` + `height minCount=1`: пустой граф **Conforms True**, имеющийся Building без height **False**;
- авторский Hagedorn R1/V2: element без GUID **True**, с GUID и без task **False**;
- авторский R3/V2 без вычислительных входов **True**.

Это не дефект SHACL и не воспроизведение DG production regression: это демонстрация необходимости population/input coverage. Полноту контролировать по согласованной задаче/стадии; ранний эскиз не обязан иметь все данные construction model. При неопределённости использовать уже принятый DG non-verdict vocabulary, не новый набор статусов. Hagedorn различает inference и validation, а benchmark не обосновывает универсальную полноту.[14]

## 6. Что литература меняет в решении

### 6.1 Generative assistance не равна compliance

Heimig-Elschner et al., arXiv v2: один ReAct-agent, шесть задач по пять повторов. При 100% tool success Model Success в двух случаях составляет 40% и 48,9%; эта метрика не равна вероятности полностью правильного здания. Container isolation не подтверждает tenant security или защиту от malicious commands. Их evidence ограничено IfcOpenShell backend; перенос на live Revit/GH необходимо проверять отдельно.[9]

Madireddy et al. оценивают получение работающих Revit scripts, а processing time сообщают сами модели. Это не точность verdict по экспертному корпусу. Chen et al. сообщают 0,97 для классификации сложности текста, не end-to-end compliance.[11][12] Iversen & Huang доступен только по metadata/indexed abstract, поэтому размеры/состав benchmark и подробные conclusions не приписаны непрочитанному full text.[19]

**Решение для DeGram:** сохраняя constrained interpretation, измерять отдельно семантическую корректность, извлечение величин, tool execution, coverage и итог. Формулировка T «интерпретация больше не bottleneck» не может быть acceptance assumption продукта.

### 6.2 Multi-agent — опция после измерения

Gusarov et al. показывают улучшение Text-to-Cypher QA при feedback/verification, но сравнение не отделяет число агентов от дополнительных проверок и compute. В IFC appendix ответ содержит 76465,52 м³ при ожидаемых 76,47 м³ и оговорку об необычной величине: предупреждение не исправляет unit error.[10]

**Решение:** один orchestrator + typed tools + deterministic checks. Не добавлять GraphRAG/vector DB/семь агентов только ради state-of-art label. Для graph context сначала существующие индексы и точные traversal; добавлять retrieval complexity после теста недостающей полноты.

### 6.3 Семантика не заменяет solver

Lin DCM показывает представление критериев и ограничивает автоматическое получение удовлетворяющих решений. Геометрическое отношение нуждается в соответствующем алгоритме; имя `privacy`/`adjacency` не исполняет проверку.[29] P plan-layout case прямо опирается на GH/Kangaroo, а не на SWRL как геометрический генератор.

DeGram предлагает и изменяет bounded visual program; GH/Revit/специализированный analysis вычисляют; DG связывает критерии и evidence. `ATTRIBUTE_OF` не показывает, какой independent input обязательно исправит нарушение. Semantic declaration, measurement adapter и generative procedure должны быть различимы. SWRL conclusion о PatternNode сам по себе не создаёт объект CAD.[5]

### 6.4 Intent сохранён только если проверено поведение/контекст

Wu conference version восстанавливает grid-based spatial dependencies; отдельное журнальное продолжение 2025 уже описывает Revit-плагин и восемь моделей, с экспертной оценкой одиннадцати участников. Следовательно «IFC только статичен, Desktop впервые возвращает изменяемость» — неверное противопоставление. Но это не универсальное восстановление rationale или любых зависимостей; ручное время в сравнении оценено экспертами, не полностью измерено controlled experiment.[24][22]

IDI follow-up Kyratzi/Azariadis раскрывает связи intent/meta-constraints в MCAD; перенос на building regulations требует новой проверки.[25] CPBI даёт BIM precedent representation, но исследование 19 студентов без control group не доказывает промышленную эффективность.[23]

**Решение:** проверять после изменения параметра сохранённые инварианты, а не только совпадение исходной геометрии/числа ID. Помечать связь authored/imported/inferred/user-confirmed. Reconstructed plausible dependency — не гарантированно исходный авторский intent.

### 6.5 Стандарты и governance

- BOT официальный LBD источник обозначает как **Community Group Report**, а не W3C Recommendation; это важно для точности positioning, не причина отказаться от vocabulary.[2][3]
- IDS включает applicability, requirements, cardinality и значения/диапазоны; его нельзя сводить к проверке наличия properties. Geometry/computed cross-object checks имеют явные границы. Не строить универсальную автоматическую IDS→SWRL конверсию в MVP; отдельные supported mappings требуют тестов.[18]
- Co-evolution у Dorst & Cross объясняет, почему меняются и критерии, и решения; не даёт алгоритма, который по двум snapshots определяет психологическую reformulation.[16]
- Palihakkara — обзор reuse/ontology mapping, а не benchmark нашего продукта; его поиск ограничен апрелем 2023, несмотря на публикацию 2025.[15]

### 6.6 Ошибки и ограничения references оригинала ptBIM

В P, с. 10:

| Позиция | Указано в P | Проверено |
|---|---|---|
| «Knowledge-based OpenBIM data exchange for building design», 105144 | Sacks, Bloch, Katz, Yosef | **Khudhair, Li, Ren**, DOI `10.1016/j.autcon.2023.105144`.[20] |
| «Graph-based inter-domain consistency maintenance for BIM models», 104979 | Preidel, Borrmann, Mattern, König, Schapke | **Wang, Ouyang, Sacks**, DOI `10.1016/j.autcon.2023.104979`.[21] |

Подтверждено непосредственным Crossref lookup основного агента. Авторы исправляются отдельно по разрешению пользователя; исходная статья не менялась. Названия релевантны, но детали их систем здесь ограничены metadata/indexed abstract — не full-text выводы.

Core–periphery hypergraphs — математическая модель иных datasets, не доказательство BIM architecture quality.[26] Abrishami 2015 — generative workspace context; доступный abstract не доказывает современный LLM/SWRL pipeline.[27] Semjén/Szép — полезная мотивация интеграции; получен abstract, а не полноценная проверка всех выводов обзора.[28]

## 7. Текущее состояние реализации и минимальная работа

| Проверенный участок | Риск для DeGram | Минимальная реакция |
|---|---|---|
| `/mcp` внутренний и service-only; descriptors без inputSchema | Не готовый пользовательский MCP API | Локальный typed REST-backed adapter; внутренний endpoint не ломать |
| GH repositories direct Bolt; multi-user unsupported | Рабочие места не смогут полноценно читать DG через существующий CONNECTOR | HTTP-backed repository contract с user/delegated scopes; сохранить готовые HTTP publish paths |
| `gh_bridge.py:27–51` global host | Сервер не определяет нужный пользовательский canvas | Live tools локально; сервер получает snapshot |
| `computgraph_publish.py:521–535,841–848` name mapping и все body DataPropertyAtoms | Неоднозначная/слишком широкая привязка | Exact atom/property + parameter identity и ambiguity refusal |
| SpecNote confirm read-check/write отдельно | Race и partial update | Atomic expectedRevision CAS, before/after revision и явный batch outcome |
| Разные destructive edit/supersede paths | Историческая формализация теряется | Общий backend revision/activation contract и legacy disposition |
| `rulesJson` summary, Session prompt/result | Неполный execution provenance | Frozen ruleset reference/content и source revision chain |
| Hash и candidate ID probes | Capture equivalence и definition scope не обеспечены | Отдельная comparison projection; explicit definition identity |
| Computgraph edges MERGE, stale IDs только отчёт | Current graph может сохранять устаревшие зависимости | Revisioned publish + reconcile только publisher-owned edges |
| Speckle shared read token, iframe DENY | Корпоративная изоляция и embed не «готовы из коробки» | Isolated native web surface и scoped access/proxy decision |

Полная source trace и ограничения тестов — `parts/repository-semantic-seams.md`. Большинство risks выявлены source inspection, а не воспроизведены на live DB. Шесть offline assertions повторены основным агентом: golden hash, order invariance, timestamp sensitivity, geometry exclusion, known legacy scalar helper delimiter collision и definition-agnostic candidate ID. Это **не шесть исправленных ошибок** и не полный pytest pass.

## 8. Улучшенный бизнес-процесс

### Роли

- **Domain expert / ведущий архитектор:** формулирует и утверждает проектные требования, выбирает вариант.
- **Computational designer:** отвечает за native definition, измерения и допустимые локальные изменения.
- **Vocabulary steward / BIM-методолог:** управляет общими терминами и compatibility releases. В малой команде это тот же человек с отдельным полномочием, не новая штатная единица.
- **Проверяющий / заказчик:** изучает evidence и отвечает по решению; может использовать web UI без CAD/desktop installation.
- **DeGram:** собирает контекст, предлагает, вызывает разрешённые операции и связывает результат. Не обладает отдельной предметной властью утверждать смысл или нормативное соответствие.

### Сквозной сценарий изменения ограничения

1. Ведущий архитектор получает новую редакцию brief; фиксируются source URI/hash/fragment, изменённый пункт и applicability.
2. DeGram показывает существующую формализацию и её зависимости, предлагает редакцию. Неформализуемые пожелания сохраняются как intent, а не превращаются в выдуманный SWRL.
3. Термины разрешаются против pinned vocabulary. Новый общий термин проходит steward gate; локальный проектный draft не публикуется всему предприятию автоматически.
4. Автор подтверждает rule revision. Impact view показывает mappings, состояния и проверки, для которых прежний outcome больше не актуален. История сохраняется.
5. Computational designer на своём ПК выбирает документ и вариант. DeGram предлагает ограниченный GH patch или помогает выполнить ручное изменение; показывает affected objects и expected invariant.
6. После подтверждения adapter проверяет revision, применяет patch, запускает solver и считывает действительные значения/ошибки. Вычисленные параметры не подменяются желаемыми порогами.
7. Capture получает pinned context; проверяются inputs/population, запускаются appropriate evaluators; canonical results сохраняются независимо от operational publish status.
8. В reused Model Viewer участники сравнивают сопоставимые варианты и видят почему/по каким данным получен verdict. Руководитель отдельно принимает вариант и кратко фиксирует основание.
9. Второй сотрудник получает проектный артефакт, а не пересказ первого чата. Revit mapping/измерение проверяются по native document и units; при расхождении сохраняются обе source-attributed величины до решения владельца.

**Цикл лаконичен:** источник → предложение → согласованное изменение → вычисление/проверка → выбранный результат. Ветвления vocabulary/revision/security происходят только там, где есть риск. Для обычного чтения согласование не нужно; весь workflow не превращается в форму из десятков обязательных полей.

## 9. Пересмотренный v13.0: вертикальные результаты вместо списка подсистем

Числовые идентификаторы — предложение в принятой milestone-derived схеме, не изменение `.planning/`.

| Фаза | Результат и scope | Условие завершения |
|---|---|---|
| **1300 — Контракты, baseline и ownership** | Одобрить scope MVP, runtime/V8 profile, vocab ownership, rule/state revisions, source authority; зафиксировать baseline tasks из P | Нет конфликтующих владельцев; input/output/status contracts согласованы с v11/v12; пилотный corpus и критерии определены |
| **1301 — Рабочий клиент и безопасный read slice** | Thin fork, DG login/project, локальные read MCP, early Revit/GH handshake, полный reused web surface | Чистая установка, два проекта/два ПК, document selection, logout/revocation; основные web-функции работают |
| **1302 — Требование, словарь и утверждённая редакция** | Source-linked SpecGraph, vocabulary proposals/release pin, typed rule CRUD/retirement, CAS, server audit | Новая редакция не меняет старый результат; конфликт редакторов определён; private terms не утекли |
| **1303 — Правило ↔ GH ↔ объект** | HTTP repositories addin, actual GUID/ports, точный binding, consult/trace, reuse tagging/confirm/publish | Доказанная цепочка одного требования через реальный definition до адресуемого объекта; неоднозначность отклонена |
| **1304 — Design State, validation и review** | Minimal snapshot/revision/freshness, coverage, pinned rules, selectable alternatives/rationale; полная Viewer parity | Missing population не даёт full pass; старый run объясним после изменений; принятие решения отделено от verdict |
| **1305 — Bounded GH intent editing** | Перенесённые CKBS/BWRT/SEDT outcomes, safe patch/diff, undo/rollback, solve/readback и republish | Поддержанный visual block реально изменяется по intent; нецелевые элементы сохранены; stale patch/retry безопасны |
| **1306 — Реальный межплатформенный handover** | Реальный Revit mapping и выбранные typed properties/dependencies; source/document identity, units/conflicts | Пользователь B восстанавливает заданный смысл/контекст без чата A; native changes имеют ожидаемое поведение либо explicit unsupported |
| **1307 — Comparative pilot и выпуск** | Задачи P + governance/concurrency/security; effect против current DG, distribution/update/rollback | Correctness/traceability gates и заранее согласованные benefit criteria проверены; ограничения опубликованы |

1301 проверяет Revit/GH deployment рано, чтобы не обнаружить непригодный bridge лишь в конце. 1306 проверяет предметную пользу interop, а не впервые наличие Revit в registry. Полный web Viewer не откладывается за рамки MVP: early embed в 1301, contextual parity и проверка функций в 1304.

### Ownership изменений других milestone

- **v9.1:** CHTW отдельная оболочка superseded; CTXS/SCMD/TAGX/RCMD и lifecycle outcomes переадресуются v13; DEPR-01 compatibility сохраняется, DEPR-02 hiding legacy необязательно. Не отмечать superseded как completed.
- **v10:** CKBS/BWRT/SEDT и базовые CONS переходят в v13 после утверждения; WPER full per-node historical topology, CLIN, SGEN, SRUL и расширенная consultation остаются v10. Для SEDT-03 договориться о минимальном revisioned publish/pre-post snapshot seam сейчас; не обещать полноценный WPER diff без реализации.
- **ORCH/RING:** устранить ownership gap; RING outcomes включить в authoring, ORCH decision пересмотреть под local Hermes + retained server n8n. OpenClaw spike не считается выполненным.
- **v12/1205.1:** canonical GH wire closure остаётся у текущего исполнителя; не править параллельно.
- **v11:** версии V7/V8, normative mappings/status/evidence и semantic governance decisions — существующий/согласованный владелец. V13 потребляет контракт и реализует operator UX/API slice; одинаковые backend deliverables назначать единственному владельцу явно.
- **v4:** не prerequisite Desktop. Пересмотреть остаточный scope относительно deposited BOT alignment и v11 перед отдельной активацией; не возрождать дублирующее alignment из устаревшего плана.

## 10. Как доказать эффективность и пользу

### 10.1 Исходные показатели P — не обещание DeGram

P §2.5/§3.3: около 15 минут для первого height-rule, около двух часов guided GH onboarding, оценка дня ontology setup; Table 1 — ~45→~15 минут authoring, ~30→<2 минут propagation, 3–5→12–20 alternatives, self-reported ~95% retained intent. Это informal/controlled academic evidence с ограниченной разметкой выборки. Не выдавать за гарантированную экономию DeGram и не считать большее число вариантов доказательством лучшего решения.

### 10.2 Сравнение

**A:** актуальный DG web + DG addin. **B:** те же backend, правила, модели и LLM через DeGram. **C, если бюджет позволяет:** DeGram typed commands/forms без NL-agent — отделяет пользу общей среды от LLM. Для interop при заявлении преимуществ сравнивать выбранный класс зависимостей не только с простым IFC export, но и с применимым enriched IFC/native baseline; иначе сравнение заведомо слабое.[22]

Использовать paired/counterbalanced tasks, фиксировать опыт участников, training/setup отдельно, сохранять неудачные попытки. Выборку, допустимые margins и критерии owner утверждает до пилота; этот отчёт не подставляет выдуманный statistical power.

### 10.3 Три практических кейса P и новые негативные испытания

1. **Plan layout:** существующий spatial program + GH/Kangaroo; bounded change, исходные adjacency/circulation constraints и независимые измерения.
2. **Urban block:** правило → exact binding → два варианта → проверка; обновить правило и убедиться, что история не переписалась.
3. **Project documentation:** получить источник/обоснование, согласованно отредактировать knowledge, передать другому участнику.
4. **Governance:** одинаковое имя/разный смысл, change of shared vocabulary, проект на старом release.
5. **Interop:** настоящий GH PC A / Revit PC B, units, document copies, identity conflict, missing native counterpart.
6. **Failure recovery:** timeout после local apply, failed publish, revoke permission, concurrent edits, prompt injection в note/scribble, missing population.

### 10.4 Метрики

| Критерий | Измерение |
|---|---|
| Пользовательская эффективность | Wall-clock и human-active time до правильного принятого результата, включая review/rework; setup отдельно |
| Authoring correctness | Доля правильно формализованных atomic requirements: scope, units, exceptions, quantifiers; экспертный gold |
| Проверка | False-pass, false-fail, justified non-verdict, coverage/omission; не только aggregate accuracy |
| Traceability | Возможность пройти source→rule revision→mapping→state→result; независимое восстановление другим участником |
| Handover | Что получатель восстановил правильно без доступа к transcript; ручные уточнения/время |
| Parametric preservation | Правильная реакция на известное изменение и сохранность согласованных инвариантов |
| Review burden | Исправления предложений, ошибочные approvals, время capture rationale и fatigue |
| Эксплуатация | Update/reconnect/recovery, лишние side effects, scope isolation, реальная latency/cost |

Success gate не сводится к «стало быстрее»: correctness и traceability не должны ухудшаться сверх заранее допустимой границы. Нулевая ошибка в небольшом пилоте не означает нулевого промышленного риска. Tool calls, токены и количество созданных variants — диагностические показатели, не самостоятельная полезность.

## 11. Приоритеты, риски и missing inputs

### Блокирующие перед соответствующим release

- Canonical status delivery и non-verdict preservation — closure 1205.1.
- Корпоративная user/delegated authorization, HTTP addin path, scoped model access.
- Согласованный vocabulary/runtime profile и rule revision/provenance contract.
- Exact document/parameter binding, stale-write/concurrency и read-back для writes.
- Population/inputs coverage и историческая объяснимость результата.

### Высокая польза при умеренной сложности

- Short decision record на событие принятия, source pointers.
- Object-centered inspect/trace вместо обучения всех пяти графам.
- Deterministic forms/commands для частых операций плюс NL для формулирования/объяснения.
- Minimal released vocabulary package и project pin вместо глобального редактирования.
- Определённый reference-definition component set и reuse existing generators.

### Отложить

Universal graph CRUD; general solver; full event sourcing; новая vector memory; обязательная multi-agent organization; произвольный Revit code execution; все CDE-коннекторы; universal IFC/SWRL compiler; full DesignSpaceGraph; автономные модели, непрерывно синхронизирующиеся без владельца.

### Требуются решения владельца

1. Revit: read/analysis/mapping достаточно или нужны модельные writes в MVP?
2. LLM: corporate inference или личные providers? Corporate inference требует совместимого user-facing chat/tool-calling пути; внутренний `/llm/generate` не готовая замена.
3. SSO обязателен или используются существующие accounts/invitations?
4. Кто steward общей vocabulary и какие проектные изменения он обязан утверждать?
5. Какие definitions/CAD versions и какой information-exchange slice входят в pilot?
6. Разрешается ли web-only участие reviewer/client без обязательного Desktop?

**Audit-fix classification:** архитектура, semantics, ownership, manuscript references и lifecycle policy — manual-only. Узкие implementation flaws маршрутизируются в утверждённые планы с fixtures после scope confirmation. Во время исследования код не исправлялся. Выявленные references не редактировались в PDF.

## 12. Итог

**Сохраняю рекомендацию строить DeGram, но меняю основание и порядок разработки.** Harness должен сделать операционными сильные стороны DG — долговечное, проверяемое проектное знание — и доказать пользу на тех же трёх сценариях P. Desktop без source/revision/rationale становится ещё одним местом потери intent; semantics без локальных CAD tools остаётся оторванной от модели. Минимальное работоспособное соединение этих сторон — цель v13.

Следующий шаг — согласовать ownership и product decisions, затем оформить изолированный future milestone package. Активный v12 не переключать до его проверенного закрытия.

## Sources

[1] https://www.w3.org/TR/2017/REC-shacl-20170720
[2] https://w3c-lbd-cg.github.io/bot
[3] https://w3c-lbd-cg.github.io/lbd
[4] https://www.w3.org/TR/prov-o
[5] https://www.w3.org/submissions/SWRL
[8] https://www.itcon.org/papers/2025_26-ITcon-Wyke.pdf
[9] https://arxiv.org/pdf/2601.00809v2
[10] https://arxiv.org/pdf/2511.08274v1
[11] https://mdpi-res.com/d_attachment/electronics/electronics-14-02146/article_deploy/electronics-14-02146.pdf
[12] https://mdpi-res.com/d_attachment/buildings/buildings-14-01983/article_deploy/buildings-14-01983.pdf
[13] https://lot.linkeddata.es
[14] https://pure.tue.nl/ws/files/317339893/1-s2.0-S0926580523003667-main.pdf
[15] https://www.itcon.org/papers/2025_49-ITcon-Palihakkara.pdf
[16] https://sites.cc.gatech.edu/computing/classes/AY2013/cs7601_spring/papers/Dorst_Cross2001.pdf
[18] https://raw.githubusercontent.com/buildingSMART/IDS/development/Documentation/UserManual/specifications.md
[19] https://api.openalex.org/works/https://doi.org/10.1016/j.autcon.2025.106707
[20] https://api.crossref.org/works/10.1016/j.autcon.2023.105144
[21] https://api.crossref.org/works/10.1016/j.autcon.2023.104979
[22] https://mediatum.ub.tum.de/doc/1785697/g0tmslxc39zgchdo8dq11q4j6.2025_WU_EnrichIFC.pdf
[23] https://mdpi-res.com/d_attachment/buildings/buildings-15-01287/article_deploy/buildings-15-01287.pdf
[24] https://mediatum.ub.tum.de/doc/1749096/wkcbb1pjs0u9nzajsslaqt44b.2024_WU_IFC.pdf
[25] https://archives.aristeia.aegean.gr/Publications/e-Aegean_CulTour/2.1/08.%20CAD23_143-148.pdf
[26] https://arxiv.org/abs/2206.00783
[27] https://api.crossref.org/works/10.1108/CI-07-2014-0036
[28] https://doaj.org/api/articles/1422949dd8f74727b939c19826c1b030
[29] https://doi.org/10.1080/16864360.2015.1131551

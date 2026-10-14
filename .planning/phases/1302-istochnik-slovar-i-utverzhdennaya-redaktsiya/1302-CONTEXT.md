# Phase 1302: Источник, словарь и утверждённая редакция - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning (dependent entry gates remain open)

<domain>
## Phase Boundary

Автор создаёт source-linked проектное правило с ограниченной применимостью, company steward выпускает неизменяемые редакции словаря, а принимающий проект независимо проверяет и утверждает lessons-learned копию. Phase 1302 отвечает за DGKN-01..10: источник и scope, словарь, управляемые редакции и историю, независимый перенос и typed `/dg-` commands. Сервер DG остаётся authority данных и прав. Обсуждение и offline-планирование возможны независимо от отложенной live-проверки 1301, но зависимая реализация и acceptance требуют доказанного entry gate.

Удалённое по `1300-SCOPE-REVISION.md` сравнение DeGram с текущим DG не возвращается как prerequisite. Вне границы: изменение native GH/Revit binding (1303), state/review Viewer parity (1304), CAD writes/editing (1305), CDE publication (1306), новый CDE или перенос исходного verdict как доказательства соответствия назначения.

</domain>

<decisions>
## Implementation Decisions

### Источник и применимость правила
- SourceRevision сохраняет URI/ID, закреплённую редакцию или хеш, точный фрагмент и происхождение. Доступ к источнику проверяется отдельно; DG membership не означает CDE permission.
- Неформализуемый intent сохраняется как явно неисполняемый, с причиной и границей проверки; machine verdict для него не выдумывается.
- Правило закреплено ровно за одним проектом; классы, объекты и условия определяют scope внутри него. Общий company class не расширяет действие правила на другие проекты.
- До утверждения конкретных разрешённых CDE sources допускаются проектирование контракта и тесты на локальных фикстурах. Реальное чтение и активация source-linked правила зависят от gate источника и прав.

### Выпуск и границы словаря
- Проект закрепляет конкретный неизменяемый release словаря своей компании; версия release и происхождение терминов видимы.
- Project editor может предложить изменение, но только явно назначенный company steward рассматривает и выпускает его. Сервер проверяет полномочия для обеих операций; project-editor право не даёт steward authority.
- Private drafts видны только уполномоченным участникам своей области; project drafts не становятся доступны другим проектам или компаниям через общий словарь.
- Retirement прекращает новое применение термина в следующих release, сохраняя его и ссылки в исторических release, правилах и проверках.

### Редакции правил и история проверок
- Для create/edit/retirement автор видит typed diff с источником и применимостью, отдельно проверяет результат формализации и отдельно подтверждает новую редакцию. Применение не следует автоматически из результата LLM или проверки.
- Мутация требует `expectedRevision`: атомарно отклонить stale запись, вернуть конфликт и актуальную редакцию для нового сравнения, не перезаписывая работу другого автора. Серверный audit фиксирует actor, before/after revisions и outcome принятой операции.
- Для старого run восстанавливаются полный исполняемый ruleset, vocabulary release и source revisions после любых последующих edit/retirement. Исторический verdict не переписывается.
- Новая редакция отмечает затронутые bindings, states и runs как требующие новой проверки; старый verdict не считается проверкой новой редакции.

### Lessons learned и typed-команды
- Копия допускается между проектами одной компании после отдельных проверок права передачи источника и права записи назначения. Она получает новый независимый ID и сохраняет source project/rule revision, условия и основание переноса.
- Принимающий автор адаптирует копию; активация требует свежей проверки в scope назначения и отдельного утверждения назначения. Исходный run не является destination compliance evidence; последующие изменения копий независимы.
- Опубликованные `/dg-` команды используют единый типизированный registry аргументов, risk и help с детерминированным dispatch без LLM. Некорректные аргументы отклоняются до исполнения.
- Read выполняется сразу; mutation/publication сначала показывает точную цель, проект, редакцию и последствия, затем требует подтверждения и повторной серверной проверки полномочий. Общее подтверждение на сессию недостаточно.

### Claude's Discretion
- В пределах решений выше исследовать схему хранения, транзакции, API и UI и выбрать реализацию в существующих DG seams. Не трактовать существующие unversioned ingest/delete paths как уже соответствующие DGKN.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data-service/app.py` содержит существующие project-scoped reads, delete-preview, conflict/supersede и rule-ingest relay. `data-service/route_policy.py` перечисляет route-level auth и проектные/делегированные principals.
- `ui-v2/src/lib/graphApi.js` содержит fetchRules, delete preview, conflict, ingest и delete transport; `ui-v2/src/screens/GraphScreen.jsx` содержит rule console/edit flow. Это точки интеграции, а не подтверждение immutable revision или CAS.
- `data-service/evidence_contract.py` и `spec/EVIDENCE-CONTRACT.md` задают canonical evidence/non-verdict semantics; `spec/SECURITY-BOUNDARY.md` — principals/route policy. Графовая схема и source authority требуют проверки по `spec/DATABASE.md`, `training/dataset_schema.json` и `cypher_template.txt` до расширения.

### Established Patterns
- Все DG domain records и governance должны иметь серверный authority; исходные документы и CAD binaries остаются отдельно. Компания, проект, CDE, export и approval представляют разные проверки.
- Current graph UI уже имеет read/preview/explicit action patterns, но n8n rule-ingest edit пересоздаёт atoms и не обеспечивает здесь заявленного immutable, atomic expectedRevision и historical reconstruction. Не утверждать обратное без тестов.

### Integration Points
- Разработку новых v13 API/store/UI держать в рамках Phase 1302; для нового route/relationship обновить соответствующие normative specs, policy inventory, SHACL/schema surfaces и тесты согласно `CLAUDE.md`.
- При планировании проверить, можно ли атомарно закрепить rule/source/vocabulary revisions и run pins в выбранном server-side store, как достигаются tenant isolation и audit, и где ставится server-side confirm boundary. `apps/degram` остаётся pinned submodule с отдельным repository/permission gate; не внедрять в него изменения без preflight и согласованной задачи.

</code_context>

<specifics>
## Specific Ideas

- Владелец принял все 16 предложенных ответов в четырёх областях без изменений.
- По решению начать с 1302 отложенный live recheck 1301 не становится автоматически пройденным; план может содержать offline increments и явные блокирующие acceptance gates.
- Entry gate `ROADMAP.md`: проверенный scoped access 1301; согласованные с v11/v12 source-authority/vocabulary/revision clauses 1300; назначенные steward/approvers и разрешённые CDE sources. `workspace.py verify` прошёл 2026-10-14, но сообщил `productAccepted: false`; это проверка структуры workspace, не подтверждение продуктового gate.
- Exit gate: evidence для каждого DGKN ID и human acceptance; активация destination-копии требует свежей destination проверки и отдельного утверждения. Отсутствие evidence блокирует активацию, не переносится автоматически на 1304.

</specifics>

<deferred>
## Deferred Ideas

Новых возможностей за пределами 1302 в обсуждении не добавлено. Открытые entry/exit gates не закрыты созданием этого документа. Реальный CDE доступ/публикация, live service/graph mutation, paid inference, CAD operations, package installs, Desktop launch и cross-repository push остаются предметом отдельных разрешений и проверок. Сравнение DeGram с текущим DG исключено из активного scope решением `1300-SCOPE-REVISION.md`; это не отменяет проверки correctness, security, provenance и recovery.

</deferred>

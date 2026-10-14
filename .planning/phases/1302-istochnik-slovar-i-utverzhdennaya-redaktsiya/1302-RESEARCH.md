# Phase 1302: Источник, словарь и утверждённая редакция — предварительное исследование

**Дата:** 2026-10-14

**Статус:** inline, предварительно; независимый GSD researcher/checker не запускался. Это не PLAN, PASS, разрешение на выполнение или подтверждение entry gate.

**Область:** DGKN-01..10; только локальное чтение framework-кода и контрактов, без обращения к CDE, Neo4j или работающим сервисам.

## Вывод

Существующие чтение и изменение правил — удобные точки интеграции, но не версия 1302: текущие `Rule`/`Atom` не образуют неизменяемый управляемый снимок, supersession выполняется после отдельного ingest, а старый `ValidationRun.rulesJson` не закрепляет полный исполняемый корпус и его исходники. Проект→компания пока только атрибут доступа; корпоративный steward, release словаря и двойное разрешение переноса отсутствуют. Нельзя объявлять обычный GraphScreen edit, SUPERSEDED_BY или существующую историю run достаточными для DGKN-04..09.

**Рекомендация для будущего планирования (не утверждённая реализация):** сначала определить server-owned immutable revision/pin contract и разрешения; затем атомарную запись с CAS и полной историей; затем привязку исполняемого корпуса и validation run; затем управляемый UI и перенос; typed `/dg-` dispatch лишь поверх тех же серверных операций. Пока реальные CDE sources и их ACL не определены, использовать локальные фикстуры и не активировать source-linked правила.

## Наблюдения по коду и контрактам

| Утверждение | Основание | Следствие |
|---|---|---|
| У компании есть только project→company assignment в JSON, а не tenancy/governance layer | `data-service/company.py:1-16,52-94`; `spec/SECURITY-BOUNDARY.md:118-127` | Для DGKN-02/03 нужны отдельно назначаемые company steward и проверка области; `editor` проекта недостаточен. При смене компании нужно исключить старые release/draft/copy из нового scope. |
| Route policy deny-by-default, но её `min_role` выражает только проектную роль | `data-service/route_policy.py:47-91,284-299`; `data-service/auth.py:1146-1222`; `data-service/tests/test_route_inventory.py` | Классифицировать каждый новый route, проверять company/source-transfer/destination-write/steward в серверном handler/store и тестировать оба уровня. `filtered` ответы обязаны сами фильтровать строки; resource IDs другого проекта должны быть неразличимы от неизвестных. Не расширять автоматически `dgd_`/`dgk_`. |
| Relay отправляет `rules_text` в n8n асинхронно и отвечает execution ID; edit в GraphScreen всё ещё отправляет `edit Rule_Id: ...` | `data-service/app.py:3651-3683`; `ui-v2/src/screens/GraphScreen.jsx:624-669,790-844`; `n8n/workflows/rules-to-metagraph.json` | Старый ingest/edit нельзя считать publish-командой с CAS. Нужна граница, исключающая обход управляемой редакции старым write-путём для управляемых правил, включая n8n и прямые legacy операции; проверить живую версию n8n отдельно перед любым rollout. |
| Preview и DELETE разделены; DELETE удаляет Rule/Atoms, audit/ревизии не сохраняются | `data-service/app.py:3910-4003`; `data-service/route_policy.py:284-291` | Managed retirement — отдельная недеструктивная операция. Старые delete/bulk-delete и generic property-edit необходимо закрыть для managed records; preview сам по себе не даёт атомарности подтверждения. |
| Conflict preview read-only, supersession выполняется после ingest, отдельными чтениями и записью `SUPERSEDED_BY` | `data-service/app.py:4112-4133,4243-4362`; `spec/DATABASE.md:593-600` | Publishability guard не является CAS и не гарантирует атомарное создание replacement+pin+audit. Существующий `SUPERSEDED_BY` оставляет старую Rule, но не фиксирует полный снимок её атомов и исходников. |
| C# SWRL corpus фильтрует superseded Rule по проекту, читает атомы отдельным запросом | `DG/src/DG.Core/Data/Neo4jRuleRepository.cs:23-64`; `spec/SECURITY-BOUNDARY.md:49` | Выбор активной управляемой редакции и закрепление полного corpus/run должны учитывать двухзапросное чтение и локальный direct-Bolt boundary; иначе проверка может увидеть разные редакции. Реальное изменение этого пути потребует проверки C# и отдельной совместимости со старыми Rule. |
| ValidationRun `rulesJson`/`statePayloadJson` записываются только при CREATE, но `rulesJson` — результат `build_rules_summary` (ruleId/name/description/status/warnings/detail), а не исполняемый снимок | `data-service/app.py:782-840,892-916,1169-1187,3142-3215`; `spec/DATABASE.md` раздел ValidGraph | D-15 сохраняет существующий summary от переписывания, но для DGKN-06 нужны полный исполняемый ruleset, vocabulary release, source revision/fragment и идентичность применённой конфигурации в момент исполнения. Не добавлять реконструкцию через нынешний HEAD rules. |
| Rule list/detail возвращает id, text и отдельные поля; ни revision, ни pin не экспонируются | `data-service/app.py:5372-5379,5522-5546` | Новый read-back API нужен для typed diff, conflict и исторического просмотра; не выдавать существующий список за version history. |
| Canonical source/vocabulary/revision требования уже обозначены, но независимого SourceRevision/VocabularyRelease/RuleRevision контракта в `spec/*.md` целевым поиском не обнаружено | `.planning/REQUIREMENTS.md:43-52`; `.planning/ROADMAP.md:289-309`; `DG_OBSIDIAN/knowledge/decisions/DeGram approved process and company-project rule scope.md:15-23` | Согласовать профиль 1300 с v11/v12 и определить формат, идентичность, ACL и pin до graph/schema реализации; отсутствие поискового совпадения не доказывает отсутствие внешнего CDE механизма. |

## Контрактные вопросы для плана

1. **Идентичность и хранение.** Развести стабильный project rule ID, immutable RuleRevision и mutable head; хранить точные исходные refs/фрагменты, applicability, результаты формализации и ссылки на immutable vocabulary release. Историческая редакция должна реконструироваться без повторного вызова LLM/CDE. Решить, хранится ли снимок атомов и корпус в Neo4j или в отдельном server-owned version store; показать один authority и проектные ключи. `SpecNote` не является SourceRevision автоматически.
2. **CAS и публикация.** В одной транзакции заблокировать/recheck ожидаемую head revision, записать новую неизменяемую редакцию, переключить активную проекцию и audit. Проверить конкурентными тестами ровно один success, stale conflict с актуальной версией, отсутствие частичных рёбер/атомов/audit и корректный retry. Нельзя полагаться на раздельные `read_single`/`write_query` или UI preview. Способ Neo4j lock/constraint/retry подтвердить интеграционным тестом, не принимать его на веру.
3. **Совместимость старого ingestion и evaluator.** Нельзя допустить, чтобы n8n edit, DELETE/bulk-delete, generic node-property update или прямой legacy клиент переписали управляемый rule head/атомы; при переходе не ломать действующий проектный corpus. Отдельно определить, как validator выбирает одну active revision и как в момент запуска фиксирует тот же набор, который фактически исполняет. Сохранить unsupported/not-checked, не преобразовывать их в pass.
4. **Компания и источник.** Роли steward/approver назначаются явно и перепроверяются сервером; project membership, DeGram grant и CDE permission независимы. Для source reference требуются allowlisted provider/object/revision/fragment, право чтения/transfer и отказ при непроверяемом pin. Source URI нельзя разыменовывать как произвольный URL. Company reassignment, revoked steward, private drafts и смена ACL должны иметь fail-closed поведение и тесты.
5. **Run/history.** Уточнить immutable manifest с полным исполняемым corpus, порядком атомов, provenance/version источников и словаря, digest и статусом доступности исходника. Зафиксировать его до/во время реального evaluator run, а не выводить из свежего графа после факта. Старые runs без pins честно показывать как legacy/unknown; старые verdict не менять. Recheck markers — отдельное состояние текущих bindings/states, не ретроактивная правка evidence.
6. **Копия и подтверждение.** Транзакция переноса проверяет тот же company для обоих проектов, source-transfer и destination-write, создаёт новый ID и не наследует ни активность, ни verdict. Destination evidence должно быть новым по проекту/области/редакции и пройти человеческое утверждение; source run — только provenance. Определить отказ при отзыве права между preview и confirm.
7. **Команды и UI.** Единственный typed registry для `/dg-` именует аргументы/risk/help, отбрасывает неизвестные аргументы до вызова handler, не даёт LLM исполнять свободный текст. Mutation показывает точные цель/проект/revision/последствия и требует одноразового подтверждения с повторной auth/CAS на сервере. Уточнить интеграцию с DeGram после component preflight и отдельного cross-repository плана; текущий `1302-UI-SPEC.md` — draft, без checker sign-off.

## Возможная разбивка offline-работы (не GSD PLAN)

- Контракты и adversarial фикстуры: DGKN↔storage/auth/evaluator matrix; согласовать v11/v12 и 1300; gate реальных CDE sources/steward/approvers оставить явно открытым.
- Серверная immutable vocabulary/source/rule schema и чтение, policy inventory, source ACL; отдельные тесты изоляции.
- Atomic rule revision/CAS/audit и fencing старых mutation paths; конкурентный интеграционный тест с доступным Neo4j, без притворного PASS по mock.
- Run manifest/evaluator read pin и историческая реконструкция, retirement/recheck, C# regression.
- Lessons-learned copy и destination evidence/approval с cross-project deny matrix.
- UI typed diff/история/копия/command registry, RU/EN и accessibility; DeGram seam отдельно по repository ownership; полная security/schema propagation и UAT.

Порядок выше — гипотеза для будущего GSD planner; у каждой работы должны быть собственные критерии, зависимости, files_modified, тесты, репозиторий и человеческие permission checkpoints. Пока нет независимого researcher/planner/checker, `ROADMAP.md` остаётся с `Plans: TBD`.

## Открытые gates и пределы проверки

- `ROADMAP.md:305-309`: подтверждённый scoped access 1301; согласованные clauses 1300 с v11/v12; назначенные steward/approvers; разрешённые CDE sources; затем DGKN evidence и human acceptance. Старт offline-исследования не закрывает их.
- `python tools/degram/workspace.py verify` 2026-10-14 вернул согласованные gitlinks и `componentContextInstalled: true`, но также `productAccepted: false`, pending `desktop-runtime-isolation` и `product-integration-and-acceptance`. Это структурный preflight, не продуктовый PASS.
- `1302-UI-SPEC.md` — черновик; checker и ui-consideration probe отсутствуют. AI-SPEC и формальный GSD PLAN не созданы.
- Исследование не тестировало живую БД, CDE, n8n, DeGram Desktop или конкурирующие транзакции. Целевой поиск по `spec/*.md` ограничен именами SourceRevision/VocabularyRelease/RuleRevision; архитектурный вывод о полном отсутствии механизма за пределами этих файлов делать нельзя.
- Новые graph nodes/relationships/properties или routes потребуют перечня Schema Change Propagation из `CLAUDE.md`, `spec/SECURITY-BOUNDARY.md` и машинных проверок. `spec/EVIDENCE-CONTRACT.md`, `spec/RULE-PARTITION-POLICY.md` и `spec/REPRODUCIBILITY.md` проверить до смены verdict/partition/LLM boundary. После реальных code changes обновить graphify.

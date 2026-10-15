# Phase 1302: Источник, словарь и утверждённая редакция — карта паттернов

**Mapped:** 2026-10-14
**Классифицировано:** 27 кандидатов изменения/создания, включая условные propagation surfaces; 6 ключевых возможностей не имеют полного аналога.
**Статус:** сопоставление исходников для планирования, не реализация и не подтверждение entry/exit gate. Имена новых модулей ниже — **кандидаты**, а не принятая схема API/хранилища. Только framework-репозиторий; дочерний `apps/degram` не исследовался как источник кода и не включён в задания на запись.

## File Classification

| Новый/изменяемый файл (кандидат) | Роль | Поток данных | Ближайший отслеживаемый аналог | Качество / граница |
|---|---|---|---|---|
| `data-service/dgkn_source.py` (новый, имя уточнить) | service, adapter | request-response, transform | `data-service/company.py`, `data-service/connector_access.py` | частичный: project/company и право доступа есть, CDE SourceRevision/ACL нет |
| `data-service/dgkn_vocabulary.py` (новый) | service, store | CRUD, file-I/O либо транзакция после выбора хранилища | `data-service/degram_grants.py`, `data-service/connector_access.py` | роль: request→authorized issuance, но release/steward/retirement ещё нет |
| `data-service/dgkn_revisions.py` (новый) | service, store | transactional CRUD, transform | `data-service/computgraph_publish.py` | частичный: одна Neo4j-транзакция, **не** CAS/immutable history |
| `data-service/dgkn_history.py` (новый или часть revision store) | service | request-response, snapshot | `data-service/app.py` (run write/read), `data-service/evidence_contract.py` | частичный: persisted summary не равен executable manifest |
| `data-service/dgkn_copy.py` (новый или часть revision store) | service | transactional CRUD | `data-service/connector_access.py`, `data-service/company.py` | частичный: выдача права и компания, не transfer/approval |
| `data-service/app.py` (изменение) | controller, route | request-response | `data-service/app.py` (rule preview, publish route, actor) | точный для тонкого маршрута и ошибок; старые операции НЕ copy as-is |
| `data-service/route_policy.py` (изменение) | middleware/config | request-response | `data-service/route_policy.py` | точный для route classification; steward/source checks поверх неё |
| `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` (условное изменение) | repository | batch read, transform | тот же файл | точный для нынешнего чтения; его two-query skew надо устранить/доказать |
| `ui-v2/src/lib/graphApi.js` (изменение либо узкий `dgknApi.js`) | transport utility | request-response | `ui-v2/src/lib/graphApi.js`, `ui-v2/src/lib/connectorsApi.js` | точный для scoped API/CSRF, не для authority |
| `ui-v2/src/screens/GraphScreen.jsx` (изменение либо отдельный экран) | component | event-driven, request-response | `ui-v2/src/screens/GraphScreen.jsx` | частичный preview/dialog; legacy ingest fail-open непригоден |
| `ui-v2/src/lib/dgCommands.js` (новый, если registry живёт в web-слое) | utility/config | deterministic dispatch | `ui-v2/src/lib/graphApi.js` | **нет аналога** типизированного `/dg-` registry; место runtime-адаптера решает план |
| `data-service/tests/test_dgkn_source.py` (новый) | test | request-response | `data-service/tests/test_company_scope.py`, `data-service/tests/test_rule_deletion.py` | роль: fixtures/scoped read, реальная CDE ACL проверка отдельно |
| `data-service/tests/test_dgkn_vocabulary.py` (новый) | test | request-response, file-I/O | `data-service/tests/test_company_scope.py`, `data-service/tests/test_route_inventory.py` | роль: deny matrix и isolated store |
| `data-service/tests/test_dgkn_revision.py` (новый) | test | request-response | `data-service/tests/test_rule_deletion.py`, `data-service/tests/test_computgraph_publish.py` | роль: preview read-only и transactional fake; mock не доказывает CAS |
| `data-service/tests/test_dgkn_concurrency.py` (новый) | test | concurrent transactional CRUD | `data-service/tests/test_auth_store.py`, `data-service/tests/test_computgraph_publish.py` | частичный: thread barrier JSON-store / fake transaction; нужен реальный isolated Neo4j |
| `data-service/tests/test_dgkn_history.py` (новый) | test | snapshot, batch read | `data-service/tests/test_computgraph_publish.py`, `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs` | частичный: нужен equality с фактическим corpus |
| `data-service/tests/test_dgkn_scope.py` (новый) | test | request-response | `data-service/tests/test_route_inventory.py`, `data-service/tests/test_company_scope.py` | роль: foreign/unknown/role denial |
| `data-service/tests/test_dgkn_copy.py` (новый) | test | request-response, CRUD | `data-service/tests/test_company_scope.py`, `data-service/tests/test_route_inventory.py` | частичный: двухпроектная authorization и свежая destination evidence ещё не реализованы |
| `data-service/tests/test_dgkn_commands.py` (новый) | test | request-response | `data-service/tests/test_route_inventory.py` | частичный: registry не существует; server deny/recheck |
| `ui-v2/tests/dgkn-review.test.js` (новый; расширение `.mjs` согласно текущему `node --test`) | test | event-driven | `ui-v2/tests/connector-access-api.test.mjs` | частичный: transport test, не полноценный modal/focus test |
| `ui-v2/tests/dgkn-commands.test.js` (новый; `.mjs` согласно текущему стилю) | test | deterministic dispatch | `ui-v2/tests/connector-access-api.test.mjs` | частичный: нет command parser/dispatcher аналога |
| `DG/tests/DG.Tests/` — целевой тест reader/manifest (условно) | test | batch read | `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs` | частичный: unit fixture, не consistency транзакции |
| `spec/DATABASE.md` (изменение) | normative config/schema | document transform | `spec/DATABASE.md` | точный структурный образец; новая модель пока не выбрана |
| `spec/SECURITY-BOUNDARY.md` (изменение при новых routes/principals) | normative config | document transform | тот же файл + `data-service/route_policy.py` | точный route-policy inventory; не право CDE |
| `spec/EVIDENCE-CONTRACT.md` / `spec/evidence-contract.schema.json` (по необходимости) | normative config/schema | document transform | те же файлы + `data-service/evidence_contract.py` | точный для outcome/schema, не записывать исторический verdict повторно |
| `training/dataset_schema.json`, `cypher_template.txt`, `ontology/dg-shapes.ttl`, `spec/LPG-OWL-MAPPING.md` (условно при graph schema) | config/schema | document transform | `training/dataset_schema.json`, `cypher_template.txt`, `spec/DATABASE.md` | аналог для propagation, **не** шаблон свободного LLM-записывания revision |
| `n8n/workflows/`, `config.template.js`, `llm/structure_rules.json`, readers/templates/tests (условно при graph schema) | config/consumer | transform, batch | `cypher_template.txt`, `spec/DATABASE.md` | перечислены как propagation surfaces в `CLAUDE.md:245-259`; сначала инвентаризировать конкретные файлы, не переписывать всё |

`1302-RESEARCH.md:129-130,244-257` задаёт области и предложенные имена тестов, **не утверждает** имена production-модулей. Все существующие пути-аналогии в таблице и выдержках проверены по индексу Git framework checkout (tracked); gitignored зеркала/архивы не используются. Никаких path в дочернем репозитории здесь не назначено.

## Pattern Assignments

### Source/scope, vocabulary и копия — серверный state и две независимые проверки

**Источники:** `data-service/company.py:53-62,76-95` (project→company), `data-service/connector_access.py:13-21,207-233` (per-project право) и `data-service/app.py:4981-4996,5022-5039` (разделены requester/issuer). Повторить квалификацию по проекту и брать actor из principal, а не из тела. Пример фактического кода:

```python
# data-service/company.py:53-62
with auth._STORE_LOCK:
    for row in auth._load(_file(), _KEY):
        if row.get("project") == project:
            value = row.get("company")
            return value if isinstance(value, str) and value else None
# data-service/connector_access.py:213-220
return any(
    g.get("username") == normalized
    and g.get("project") == project
    and g.get("connector_id") == connector_id
    and _is_active(g)
    for g in grants
)
```

`data-service/connector_access.py:67-99` сохраняет grants+requests одним atomic replace под `auth._STORE_LOCK`, полезно **только** если выбран файловый store в однопроцессной границе; это не доказательство cross-process CAS/Neo4j. `data-service/company.py:1-17` прямо говорит, что company map — не tenancy/governance. Для DGKN-01/02/03/07/08/09 новые checks: разрешённый provider + CDE object/revision ACL, явное steward appointment, draft visibility, одинаковая компания, transfer source **и** write destination, fresh destination proof. Аналога CDE-проверки в этих файлах нет. Нельзя приравнивать membership/DeGram grant к source/approval authority.

### Governed revision API/store: отделить preview от атомарного commit

**Источник тонкого маршрута:** `data-service/app.py:2118-2145`; **источник транзакционного shape:** `data-service/computgraph_publish.py:28-45,72-117`:

```python
# data-service/app.py:2118-2137
@router.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    try:
        with driver.session() as session:
            return computgraph_publish.publish_structure(
                session, payload.project, payload.cgContext
            )
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cgContext shape (cgContextJson v1 envelope).",
            "COMPUTGRAPH_PUBLISH_REQUEST_INVALID",
            422,
        )
# data-service/computgraph_publish.py:96-117 (сокращённый последовательный фрагмент)
def _write(tx: Any) -> None:
    if params["object"] is not None:
        _publish_object(tx, params)
        _publish_behavior(tx, params)
    # ... остальные связанные tx.run() внутри той же функции ...
session.execute_write(_write)
```

Скопировать **границу одной транзакции и parameterized Cypher**, не существующую семантику MERGE. Новый commit должен в транзакции сравнить `expectedRevision`, сохранить immutable revision, передвинуть project-qualified head, записать audit actor/before/after/outcome; stale возвращает разрешённую актуальную редакцию без записи. `data-service/app.py:4251-4263` — образец authenticated actor (body actor игнорируется):

```python
principal = getattr(request.state, "principal", None)
kind = getattr(principal, "kind", None)
if kind == "user" and principal.username:
    return principal.username
```

`data-service/app.py:3910-3960` даёт project-scoped read-only preview; `data-service/app.py:3963-4003` **удаляет** Rule/Atoms, `4266-4354` supersede привязывает edge **после** отдельного ingest, а `4550-4588` knowledge confirm делает read timestamp и detached write. Это антианалоги: **не** использовать ни один как CAS/atomic revision. `data-service/app.py:605-620` открывает отдельную session для каждого `read_single`/`write_query` — тоже не транзакционный commit. В `data-service/app.py:3670-3683` ingest отвечает 202 и идёт через n8n; не считать это подтверждённой редакцией.

### Authorization и ошибки — закрытая policy плюс resource-level check

**Источник:** `data-service/route_policy.py:48-85,284-299`, `data-service/tests/test_route_inventory.py:1-22,25-53`:

```python
# data-service/route_policy.py:48-66,80-85
@dataclass(frozen=True)
class RoutePolicy:
    principals: frozenset[str]
    project_source: str | None = None
    min_role: str | None = None

def register_resource_resolver(name: str, resolve: ResolverFn, not_found: NotFoundFn) -> None:
    RESOURCE_RESOLVERS[name] = (resolve, not_found)
# data-service/route_policy.py:285-291 — существующие правила, не предлагаемые DGKN routes
("GET", "/rules/{project}/{rule_id}/delete-preview"): _p(_MEM, source="path", role="viewer"),
("DELETE", "/rules/{project}/{rule_id}"): _p(_MEM, source="path", role="editor"),
```

Каждый новый endpoint включить в bidirectional inventory и `spec/SECURITY-BOUNDARY.md` (его fenced machine-checked blocks, `:1-11`). `member/editor` не означает steward/source-transfer/approver. Для непрозрачного id использовать серверное определение проекта + одинаковый not-found для foreign и unknown (`route_policy.py:69-85`). Возврат typed error:

```python
# data-service/app.py:3952-3960
if preview is None:
    raise _structured_error_response(
        f"Rule '{rule_id}' not found in project '{project}'.",
        "Check the Rule_Id; it is case-sensitive.",
        "RULE_NOT_FOUND",
        404,
    )
```

Этот текст legacy может разглашать project/rule hints в новой resource-route: для DGKN заменить на одинаковое нейтральное сообщение для неизвестного/чужого id. При confirm повторно проверить policy, company/steward/source rights, head/CAS и только потом мутировать.

### Run pin/evaluator — образец read, но не полноценного снимка

`DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-65,73-86` использует project-scoped, упорядоченные RulesQuery/AtomsQuery, но **две отдельные выборки**:

```csharp
private const string RulesQuery = """
    MATCH (r:Rule {graph:'Metagraph', project:$project})
    WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
    // ... ORDER BY id
    """;
private const string AtomsQuery = """
    MATCH (r:Rule {graph:'Metagraph', project:$project})-[rel:HAS_BODY|HAS_HEAD]->(a:Atom {graph:'Metagraph', project:$project})
    // ... ORDER BY ruleId, relationType, atomOrder, argPos
    """;
// :78-86: LoadRulesAsync(...), затем LoadAtomsAsync(...)
```

Это **иллюстративное сокращение с комментариями**, не дословно компилируемый блок: точные запросы и `PopulateVariables` смотреть в файле (`:31-86,116-259,268-321`). Manifest должен фиксировать именно упорядоченные исполняемые rules/atoms вместе с source/vocab pins на границе run, исключить read skew и сохранить старый verdict. `data-service/app.py:803-840` показывает существующий write-once `ON CREATE SET run.rulesJson`, но `:1169-1187` показывает, что этот JSON содержит только ruleId/name/description/passed/optional canonicalStatus и warnings — **не** atoms/source/vocab. Legacy run без pin обозначать явно unpinned, не реконструировать из текущего HEAD. Outcome — `data-service/evidence_contract.py:52-84,108-117`: `unsupported`, `not_evaluated` и прочие non-pass не становятся `passed`; обратное выведение canonical status из legacy bool запрещено. При изменении C# reader тестовый базовый стиль `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs:8-32,45-64`, но нужен дополнительный integration test фактического corpus.

### UI и typed `/dg-` dispatch

**Transport:** `ui-v2/src/lib/graphApi.js:7-20,48-68`, `ui-v2/src/lib/connectorsApi.js:20-49`; единый `apiFetch` (`ui-v2/src/lib/apiClient.js:72-100`) отправляет cookie+CSRF и сохраняет typed `ApiError.status/code/hint`. Пример:

```javascript
// ui-v2/src/lib/graphApi.js:57-68
export function fetchRuleDeletePreview(project, ruleId) {
  return apiFetch(`${dataServiceBase()}/rules/${enc(project)}/${enc(ruleId)}/delete-preview`);
}
export function deleteRule(project, ruleId) {
  return apiFetch(`${dataServiceBase()}/rules/${enc(project)}/${enc(ruleId)}`, { method: "DELETE" });
}
```

**UI preview:** `ui-v2/src/screens/GraphScreen.jsx:1048-1099,1650-1743` показывает список, только затем вызывает delete, busy/error и refetch. `:1017-1039,1755-1816` держит suspended decision в React state и отображает ограничения. Однако `:813-819` продолжает ingest при ошибке conflict-check (**fail-open**), а `:821-863` делает post-ingest provenance best-effort: **не копировать** для DGKN confirm. Новая форма должна показывать typed before/after source/applicability, separate formalization review, exact project/revision/consequences, stale re-diff без потери черновика. `ui-v2/src/components/surfaces/Dialog.jsx:4-65` — стиль, но нет доказанного `role=dialog`, focus trap и возврата focus: UX/accessibility-тесты обязательны.

Для `/dg-` настоящего аналога deterministic typed registry в framework нет. `graphApi.js:171-216` — async **workflow** с n8n, не command dispatcher. План должен определить место registry (web/typed adapter), schema аргументов, risk/help, reject-before-handler, per-action confirm и server re-auth, не модельный free-text dispatch и не generic CRUD. В child писать только при отдельном preflight/repo permission gate; текущая карта не назначает child path.

### Тестовый стиль и пределы доказательства

```python
# data-service/tests/test_rule_deletion.py:79-86
writes: list = []
_wire(monkeypatch, captured=writes)
client.get(f"/rules/{PROJECT}/{RULE}/delete-preview")
assert writes == []
# data-service/tests/test_auth_store.py:565-585 — barrier и one-winner для JSON auth store
barrier = threading.Barrier(8)
# ... восемь threads вызывают create_project_if_unclaimed ...
assert sum(1 for r in results if r) == 1
```

`data-service/tests/test_computgraph_publish.py:330-375` использует FakeGraph/FixtureSession/execute_write для offline failure paths. Это годится для fixture-first, **не** засчитывать как живой Neo4j CAS, одновременность двух редакторов или evaluator consistency. `data-service/tests/test_route_inventory.py:1-22,240-267` проверяет policy↔registered routes в обе стороны; расширить deny matrix на foreign/unknown IDs, private drafts, revocation и company reassignment. `ui-v2/tests/connector-access-api.test.mjs:1-56` даёт transport-тест с mock fetch/URL encoding/CSRF; UI focus и end-to-end confirmation потребуют отдельного теста.

## Shared Patterns

- **Authority:** `route_policy.py:106-112,284-299` + `app.py:4981-5039`: server route classification и независимая роль при approve, а не кнопка UI как проверка прав. Для source/CDE добавляется отдельный authority, которого тут нет.
- **Project isolation:** `company.py:53-62`, `Neo4jRuleRepository.cs:31-65`, `route_policy.py:69-85`: project-qualified identity/read, никакой выдачи чужих drafts/source URI в списке/conflict/history.
- **Transactional write:** `computgraph_publish.py:28-45,96-117`: один `execute_write` и параметры вместо строкового Cypher; CAS/constraints/audit должны быть доказаны отдельно. Не копировать `app.py:617-620` в новый multi-step commit.
- **Outcome:** `evidence_contract.py:52-84,108-117` и `spec/EVIDENCE-CONTRACT.md:51-64`: не переименовывать `unsupported`/`not_evaluated` в pass; не использовать source-run как destination evidence.
- **Schema propagation:** `CLAUDE.md:245-259`, `spec/DATABASE.md:593-617`, `training/dataset_schema.json:1-38`, `cypher_template.txt:10-32`: изменение graph relationship/route/outcome синхронизирует нормативные и machine-check surfaces. Шаблон n8n — legacy rule ingestion, а не полномочие для новой редакции.

## No Analog Found

| Capability / предполагаемый target | Причина |
|---|---|
| Approved CDE source adapter/ACL/transfer (`dgkn_source.py`) | Нет проверенного провайдера, allowlist, CDE revision или выдачи transfer permission; source gate открыт. |
| Immutable vocabulary release + steward appointment + private draft (`dgkn_vocabulary.py`) | Existing grants/company — только аналог role и scoping; не release versioning/retirement. |
| Atomic `expectedRevision` CAS + actor audit (`dgkn_revisions.py`) | Есть общий transactional shape, но нет двухписательского head/revision constraint протокола. |
| Полный executable run manifest (`dgkn_history.py`, C# reader) | `rulesJson` — summary, evaluator читает Rule и Atom раздельно; no pin equality proof. |
| Independent destination approval/evidence (`dgkn_copy.py`) | Нет transfer+write double authorization, новой независимой ID lineage и fresh destination verdict. |
| Typed `/dg-` registry (`dgCommands.js` либо адаптер) | Нет schema/risk/help/deterministic dispatch с per-action confirm. |

## Metadata и gates

**Область поиска:** адресно `data-service/` и `tests/`, `ui-v2/src/lib/`, `src/screens/`, `src/components/surfaces/`, `ui-v2/tests/`, `DG/src/DG.Core/Data/` и `DG/tests/DG.Tests/`, а также названные нормативные файлы `spec/`, `training/`, `cypher_template.txt`. Graphify query использован только для навигации (старый node-ID scheme); факты и выдержки сверены по tracked source. Число просмотренных аналогов: 17 исходников кода/тестов плюс нормативные surfaces; explicit `test_rule_conflict.py` обнаружен локально, но **не tracked**, поэтому аналогом не назначен. Поиск в submodule, live CDE/DB/проверки, Git actions и исполнение тестов не проводились. Структурный workspace preflight ранее прошёл с `productAccepted: false`; 1301/1300 entry gates, назначение steward/approvers/CDE sources и acceptance DGKN-01..10 остаются открытыми.

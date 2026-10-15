# Phase 1302: Источник, словарь и утверждённая редакция — Research

**Researched:** 2026-10-14
**Domain:** source authority, vocabulary governance, immutable rule revisions, historical evidence, destination approval
**Confidence:** MEDIUM — contracts and code inspected; live CDE/DB/evaluator/Desktop untested. Research, not approval or PLAN.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
Новых возможностей за пределами 1302 в обсуждении не добавлено. Открытые entry/exit gates не закрыты созданием этого документа. Реальный CDE доступ/публикация, live service/graph mutation, paid inference, CAD operations, package installs, Desktop launch и cross-repository push остаются предметом отдельных разрешений и проверок. Сравнение DeGram с текущим DG исключено из активного scope решением `1300-SCOPE-REVISION.md`; это не отменяет проверки correctness, security, provenance и recovery.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md) | Research Support |
|---|---|---|
| DGKN-01 | Автор может связать requirement/intent с доступной CDE SourceRevision: URI/идентификатор, редакция/хеш, фрагмент и applicability; неформализуемый intent сохраняется с явной границей проверки вместо выдуманного исполняемого правила. | Source pin/ACL and non-verdict; Pattern 1 |
| DGKN-02 | Участник проекта может использовать выбранный неизменяемый release словаря своей компании; release и происхождение термина видимы, private/project draft terms не раскрываются другому проекту или компании без разрешения. | Release/visibility; Pattern 2 |
| DGKN-03 | Уполномоченный steward может рассмотреть и выпустить предложение изменения корпоративного словаря; editor проекта без этого полномочия получает отказ, а используемый термин выводится из обращения с сохранением исторических ссылок. | Appointment/retirement; Pattern 2 |
| DGKN-04 | Автор может предложить создание, изменение или retirement проектного правила как typed diff с source/applicability, проверить его формализацию и отдельно подтвердить новую редакцию; действующая редакция меняется только через разрешённую операцию. | Proposal/confirm; Pattern 3 |
| DGKN-05 | Два редактора получают определённый результат optimistic concurrency: запись с устаревшим expectedRevision отклоняется без потери чужого изменения; серверный audit связывает принятую операцию, actor, before/after revisions и outcome. | Transaction/concurrent test; Pattern 3 |
| DGKN-06 | Проверяющий может восстановить полный исполняемый ruleset, vocabulary release и source revision старой проверки после последующего изменения/retirement правила; новая редакция показывает затронутые bindings/states/runs как требующие повторной проверки, сохраняя исторический verdict. | Run manifest; Pattern 4 |
| DGKN-07 | Автор может задать область правила внутри ровно одного проекта по выбранным классам, объектам и условиям; общность класса компании не делает проектное правило действующим в других проектах. | Scoped identity; Pattern 1 |
| DGKN-08 | Участник с разрешением передачи источника и записи назначения может создать lessons-learned копию правила в другом проекте той же компании; фиксируются source project/rule revision, условия применения, основание передачи и новый независимый идентификатор. | Double authorization; Pattern 5 |
| DGKN-09 | Автор принимающего проекта может адаптировать копию и активировать её только после проверки и утверждения в этом проекте; исходный run не используется как подтверждение соответствия назначения, а последующие изменения любой копии не меняют другую. | Fresh destination evidence; Pattern 5 |
| DGKN-10 | Участник может выполнить опубликованную typed `/dg-` команду через единый реестр аргументов/риска/help без LLM-dispatch; read выполняется сразу, mutation/publication показывает точный scope и требует подтверждения, неверные аргументы отклоняются до исполнения. | Registry/server check; Pattern 6 |
</phase_requirements>

## Summary

[VERIFIED: .planning/ROADMAP.md:289-309; .planning/REQUIREMENTS.md:43-52] The ten requirements demand source authority, steward governance, concurrency, historical executable corpus and independent destination evidence. Entry gates remain: verified 1301 scoped access, 1300/v11/v12 clauses, appointments and permitted CDE sources. Offline fixtures/design can proceed without implying acceptance. `workspace.py verify` returned `productAccepted: false` (2026-10-14): structural preflight only.

[VERIFIED: data-service/app.py:3670-3683,3963-4003,4266-4354,782-840,1169-1187; DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-86] Existing ingest is async n8n relay, DELETE removes rule/atoms, supersede follows separate ingest, validator reads rules and atoms separately, and `rulesJson` is a result summary, not full executable snapshot. These are integration seams, **not** DGKN-04..06 implementation. Favor one server-owned revision authority with project-qualified reads, atomic CAS/audit, and a manifest pinned to actual evaluator input. Prove the transaction and isolation boundary before locking storage details.

**Primary recommendation:** Contract/ACL/fixtures first, transactional revision and validator pin second, UI/copy/commands over the same server authority; live source and human acceptance remain explicit gates. No new package or install recommended.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Source identity/read/transfer | DG API/source adapter | permitted CDE | DG membership does not grant source permission |
| Vocabulary/release and drafts | DG API/governed storage | UI | Steward appointment and tenant isolation server-side |
| CAS/revision/audit | DG API/transactional store | UI | Client cannot serialize writers |
| Executable corpus/run pin | evaluator + DG backend/store | graph | Snapshot must match what executed |
| Diff/confirmation/recheck | UI | DG API | Presentation not authorization |
| Destination copy/approval | DG backend/store | reviewer | Separate permissions and evidence |
| `/dg-` parse/dispatch | typed adapter | DG API | Deterministic dispatch, server final authority |

## Standard Stack

### Core
| Component | Declared version | Purpose | Boundary |
|---|---|---|---|
| FastAPI, Neo4j Python driver, pytest, Pydantic | Pydantic `>=2.7,<3`, others unpinned [VERIFIED: data-service/requirements.txt:1-11] | DTO/API/store/tests | Deployment versions unknown |
| Neo4j | 5 [VERIFIED: spec/DATABASE.md:1-15] | Existing project-scoped graph | CAS/constraint integration test required |
| React/Vite/Node test runner | React `^18.3.1`, Vite `^5.4.14`, `node --test` [VERIFIED: ui-v2/package.json:1-21] | UI/fixtures | Ranges not installed-version proof |
| C# Neo4j driver | [VERIFIED: DG/src/DG.Core/Data/Neo4jRuleRepository.cs:1-8,73-86] | Evaluator read seam | Direct Bolt trusted-local boundary |

### Supporting
Reuse route policy, canonical evidence contract, `graphApi.js`, GraphScreen and UI tokens [VERIFIED: data-service/route_policy.py:1-11,48-85; data-service/evidence_contract.py:1-28,52-84; 1302-UI-SPEC.md:16-26]. DeGram slash adapter is a separate component-repo seam [VERIFIED: apps/degram/apps/desktop/src/AGENTS.md:36-63]. **No new external package:** package-legitimacy gate not triggered; no registry-latest or publish-date claim for existing deps.

### Alternatives Considered
| Standard | Alternative | Tradeoff |
|---|---|---|
| Neo4j-local immutable records/head | Separate version store | May ease governance but complicates atomic graph/evaluator coordination; owner decision after prototype |
| Governed API | Reuse n8n edit | Familiar flow, but async ingest and legacy writes cannot prove CAS/pins |

## Project Constraints (from CLAUDE.md)

[VERIFIED: CLAUDE.md:13-39,153-182,188-259,430-438] One framework `.planning/`, one `DG_OBSIDIAN/`; indexes first, no broad child/archive sweep. DeGram workspace preflight and child/Desktop AGENTS/DESIGN before component work; never edit generated `.hermes.md`, publish private material, launch against installed profile or run `hermes update`. Child and framework changes belong to separate repositories. All graph changes propagate through `cypher_template.txt`, `training/dataset_schema.json`, n8n prompts, `spec/DATABASE.md`, LPG-OWL, SHACL, relevant readers/templates/tests; new routes/principals update SECURITY-BOUNDARY and policy inventory; outcomes follow EVIDENCE-CONTRACT, partitions RULE-PARTITION-POLICY, constructs SWRL-SUBSET, determinism REPRODUCIBILITY. Graphify update follows actual code changes, not research. Current owner scope forbids live DB/CDE/CAD/LLM/deploy, package installs, Desktop launch and Git stage/commit/push [VERIFIED: .planning/STATE.md:707-715; spec/degram/WORKSPACE.md:3-5]. GSD init `commit_docs: true` is overridden by explicit no-commit instruction.

## Architecture Patterns

### System Architecture Diagram

```text
author + allowed source reference -> DG API: membership ∧ source ACL ∧ project scope
                                       | denied/unpinned -> no activation
                                       v
                               proposal + formalization preview
                                       | separate confirm, re-auth, CAS
                                       v
                         immutable revision + head + audit
                                       |             |
project editor -> proposal -> steward -> immutable vocabulary release
                                       |             |
                                       +-- pinned source/vocab + executable manifest
                                                           |
                                      evaluator actual corpus -> run evidence
                                                           |
      transfer + destination write checks -> independent destination draft
                                                           |
                             fresh destination check + approval -> activation
```

CDE, Neo4j, n8n, evaluator and DeGram are separate service/trust boundaries [VERIFIED: spec/SECURITY-BOUNDARY.md:15-24].

### Recommended Project Structure
Candidate seams, not asserted new files: `data-service/` governed DTO, policy and store; `data-service/tests/` auth/concurrency/history; `ui-v2/src/lib/graphApi.js`, `ui-v2/src/screens/GraphScreen.jsx`, `ui-v2/tests/`; `DG/src/DG.Core/Data/` and `DG/tests/DG.Tests/` if evaluator changes; `spec/` propagation. Component adapter only after separate approval under `apps/degram/apps/desktop/src/`; specify committing repository for each task [VERIFIED: CLAUDE.md:163-182].

### Pattern 1: Source and single-project identity
Recommend stable project-qualified rule ID separate from immutable revision and mutable head; source pin includes provider/object URI or ID, revision/hash, exact fragment/provenance/applicability. Allowlisted provider and current ACL must validate before real read/activation/transfer. Non-formalizable intent stores reason/boundary without executable atoms or machine verdict; company-wide class cannot expand project rule scope [VERIFIED: 1302-CONTEXT.md:18-23; spec/DATABASE.md:1-15]. This is a proposed model, not existing feature.

### Pattern 2: Company vocabulary
Separate draft visibility from released terms; release append-only, project pins exact company release and origin; only explicitly appointed steward publishes. Retirement bars future use, retains old release/pins. Revocation and company reassignment must fail closed [VERIFIED: 1302-CONTEXT.md:24-28; data-service/company.py:1-17,53-95]. Company map explicitly is **not** tenancy/governance.

### Pattern 3: Transactional proposal/confirmation
Typed create/edit/retirement diff and formalization review precede separate human confirmation. At confirmation recheck auth/source/company/head; one transactional authority compares `expectedRevision`, writes immutable revision, updates head and actor-derived audit, or rolls all back and returns authorized current revision. Unique project-qualified constraint and real two-writer test required: `MERGE` alone does not guarantee node uniqueness concurrently [CITED: https://neo4j.com/docs/cypher-manual/current/clauses/merge/]. Managed Python driver callback retries transient errors and must be idempotent [CITED: https://neo4j.com/docs/python-manual/current/transactions/]. Avoid external CDE side effects inside retriable callback. Exact Neo4j CAS mechanics remain unproved; no mock-only PASS.

### Pattern 4: Pin the executed corpus
Immutable run manifest should contain complete ordered rules/atoms, their rule revision IDs, source revisions/fragments, vocab release, applicability, digest and actual evaluator inputs. `rulesJson` currently records summary (`ruleId`, `ruleName`, `ruleDescription`, `passed`, optional `canonicalStatus`/warnings/detail), not atoms [VERIFIED: data-service/app.py:1169-1187,782-840]. C# currently runs separate `RulesQuery` and `AtomsQuery` [VERIFIED: DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-86]; test read consistency under concurrent edit. Write pin at run boundary, not reconstructed later from HEAD. Old runs lacking pins remain labelled legacy/unpinned; affected current bindings/states/runs get recheck markers, historic verdict unchanged [VERIFIED: 1302-CONTEXT.md:31-34].

### Pattern 5: Copy is not compliance evidence
Transaction checks same-company, source transfer and destination write separately, creates independent destination ID and immutable lineage. Adaptation is destination-owned; fresh destination-scoped check plus distinct human approval precede activation. Original run stays provenance, never destination verdict; unsupported/non-executable is not pass [VERIFIED: .planning/REQUIREMENTS.md:50-52; .planning/ROADMAP.md:299-309]. Test later edits to each copy do not cross-mutate.

### Pattern 6: Typed command registry
One registry owns command name/argument schema/risk/help/handler; reject unknown/invalid args before handler; read immediate, mutation/publication exact target/project/revision/consequence preview then per-action confirm with server re-auth/CAS. DeGram's documented generic extension dispatch may submit skill text as a model prompt, thus is **not** a safe mutation dispatch [VERIFIED: apps/degram/apps/desktop/src/AGENTS.md:36-63]. Use narrowly typed DG API adapter, no generic graph CRUD.

### Anti-Patterns to Avoid
- Legacy n8n `edit Rule_Id`, supersede or delete as governed revision: relay 202 precedes ingestion, supersede follows separate ingest, DELETE removes rule/atoms [VERIFIED: data-service/app.py:3670-3683,3946-4003,4266-4354; ui-v2/src/screens/GraphScreen.jsx:624-669]. Fence old delete/bulk-delete/property edit/n8n/direct Bolt writes to managed records.
- `SUPERSEDED_BY` as full snapshot: edge alone does not pin old atoms/source/vocab [VERIFIED: spec/DATABASE.md:593-617].
- DG membership/DeGram grant as source or steward authority [VERIFIED: spec/SECURITY-BOUNDARY.md:119-131].

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Actor/tenant check | Client role/session-wide consent | `require_principal` + route/resource policy, supplementary steward/source/company checks [VERIFIED: data-service/route_policy.py:1-11,48-85] | Server authority |
| Outcomes | Boolean/LLM guess | Canonical evidence contract [VERIFIED: data-service/evidence_contract.py:21-28,52-84] | Reverse boolean mapping forbidden |
| Concurrency | Preview-read plus detached writes | Managed transaction, constraint, concurrent test [CITED: https://neo4j.com/docs/python-manual/current/transactions/; https://neo4j.com/docs/cypher-manual/current/clauses/merge/] | Retry/uniqueness |
| Source resolution | Arbitrary URI fetcher | Approved provider, verified ACL/pin [CITED: https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x10-V1-Encoding-and-Sanitization.md] | SSRF and leaks |
| Command routing | Free-text model interpretation | Typed registry + server recheck [VERIFIED: .planning/REQUIREMENTS.md:52] | No LLM authority |

## Common Pitfalls

1. **Preview/confirm race:** steward/source rights or head changes; server recheck, stale conflict preserving draft and no losing audit.
2. **Legacy bypass:** old DELETE, bulk-delete, generic update, n8n edit or direct Bolt overwrites managed atoms; inventory all writers and test block/routing; direct Bolt is trusted-local boundary [VERIFIED: spec/SECURITY-BOUNDARY.md:19-24].
3. **Read skew/history laundering:** two-query evaluator sees mismatched rule/atoms; run summary mistaken for executable manifest; measure actual evaluator input and leave unpinned legacy runs explicitly limited [VERIFIED: DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-86; data-service/app.py:1169-1187].
4. **Tenant leak:** list/conflict/history/private drafts/URI expose another project; filtered responses and equal unknown/foreign-ID denial [VERIFIED: data-service/route_policy.py:69-85; data-service/tests/test_route_inventory.py:1-22].
5. **False destination PASS:** original run or human review treated as machine compliance; require fresh destination evidence and separate approval [VERIFIED: .planning/ROADMAP.md:305-309; spec/EVIDENCE-CONTRACT.md:81-103].
6. **False determinism:** typed dispatch is design intent, not `deterministic-measured` without cross-process fixture repeats [VERIFIED: spec/REPRODUCIBILITY.md:15-29].
7. **UI/accessibility:** styled Dialog not proven accessible modal; distinct draft/checked/approved/active/recheck, RU/EN, focus tests; UI-SPEC sign-off still pending [VERIFIED: 1302-UI-SPEC.md:22-26,74-104,132-141].

## Code Examples

Observations/test shape, not invented API or passing result:

```python
# Existing source: data-service/route_policy.py:69-85; tests/test_route_inventory.py:1-22
# Test foreign and unknown resource IDs yield indistinguishable not-found.
# FastAPI TestClient/pytest: https://fastapi.tiangolo.com/tutorial/testing/
# Two real writers: assert exactly one head success, one stale conflict,
# exactly one accepted audit and no orphan revisions after retry.
```

```text
# Existing source: DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-86
# RulesQuery and AtomsQuery are separate. Instrument actual corpus
# and assert complete pinned manifest equals what evaluator consumed.
```

## State of the Art

| Existing path | Phase target | Why |
|---|---|---|
| Async n8n ingest + later supersede | Governed proposal/CAS/audit | Separate writes cannot ensure head/manifest [VERIFIED: data-service/app.py:3670-3683,4266-4354] |
| `ValidationRun.rulesJson` summary | Executable manifest/source/vocab pins | Summary lacks atoms [VERIFIED: data-service/app.py:1169-1187] |
| Project→company attribute | Steward appointment and source ACL | Assignment is not governance [VERIFIED: data-service/company.py:1-17] |

**Deprecated for governed workflow only:** old edit/delete are legacy paths, not an assertion they are globally removed.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | [ASSUMED] Neo4j single transaction can own all required head/revision/audit/run pin writes in chosen shape; no prototype run. | Pattern 3–4 | Split brain; store decision may change |
| A2 | [ASSUMED] Approved CDE adapter will expose immutable revision/hash and transferable permission. | Pattern 1,5 | Activation/transfer blocked |
| A3 | [ASSUMED] Existing v12 validator or scoped human review can produce fresh destination evidence for every intended fixture; corpus unavailable. | Pattern 5 | Acceptance blocked; human review cannot manufacture machine verdict |

## Open Questions (RESOLVED for planning only; product gates remain open)

The resolutions below assign each unknown to an explicit decision or verification boundary. They do **not** assert that the external evidence, authority or live tests already exist; a negative or missing answer pauses the dependent work.

1. **RESOLVED — planning disposition:** Phase 1300/v11/v12 clauses, 1301 scoped-access evidence, steward/approver appointments and permitted CDE providers/objects/transfer rights must be independently evidenced and accepted at `1302-08-PLAN.md` Task 2 **before** plans 01–07/09–10 start product implementation. `1302-07-PLAN.md` Tasks 1 and 3 recheck the gate at acceptance. Entry remains open [VERIFIED: .planning/ROADMAP.md:305-309].
2. **RESOLVED — planning disposition:** Store transaction/CAS/uniqueness and evaluator-consistent manifest are not assumed proven. `1302-03-PLAN.md` Task 1 is an owner decision checkpoint for identity/store/isolated target; Task 2 requires actual concurrent-writer and rollback proof. `1302-10-PLAN.md` Tasks 1–2 and `1302-04-PLAN.md` Tasks 1–3 require the actual evaluator→publisher→backend corpus pin and historical equality. If the chosen store cannot provide these, pause and revise the design; do not infer support or perform a migration.
3. **RESOLVED — planning disposition:** `1302-09-PLAN.md` Tasks 1–2 enumerate legacy runs and tracked graph consumers/writers, including deployed n8n and direct Bolt reachability, and require compatibility evidence or in-phase propagation before downstream plans 10/04. Unfenced direct access blocks rollout; no retroactive verdict edit.
4. **RESOLVED — planning disposition:** `1302-05-PLAN.md` Task 1 requires the owner to appoint the destination approver and decide transfer, evidence freshness and source ACL proof rules before activation; Task 3 demands a fresh destination check and distinct human approval. No distinct-actor assumption or compliance/retention policy is invented; absence leaves the copy inactive.
5. **RESOLVED — planning disposition:** `1302-07-PLAN.md` Tasks 2–3 require UI consideration review and independent UI sign-off before product acceptance. `1302-08-PLAN.md` bars DeGram product work without authorization; plans 01–10 target framework files, not the component. Public ALNST licensing remains a separate distribution gate outside Phase 1302's implementation authority [VERIFIED: 1302-UI-SPEC.md:132-141; .planning/STATE.md:37-44].

## Environment Availability

| Dependency | Required by | Observed | Fallback / limit |
|---|---|---|---|
| Python/pytest | offline API tests | `python3` 3.13.7, `python` 3.14.7, `python -m pytest` 9.0.2 [VERIFIED: local CLI probe 2026-10-14] | Specify interpreter/environment |
| Node/npm | UI tests | Node v26.7.0, npm 11.19.0 [VERIFIED: local CLI probe 2026-10-14] | Declared ranges not installed compatibility proof |
| .NET SDK | C# tests | 10.0.301 [VERIFIED: local CLI probe 2026-10-14] | No evaluator tests run |
| DeGram workspace | preflight | verify exit 0, context installed, `productAccepted: false` [VERIFIED: local CLI probe 2026-10-14] | Structural only |
| Neo4j/CDE/live evaluator/Desktop | final acceptance | not probed under current authorization | Mock/fixture cannot replace live evidence |

No new package/install. `ctx7` CLI unavailable; official Neo4j/FastAPI/OWASP sources discovered via web search excerpts; direct extraction backend unavailable. No conclusion about live service availability.

## Validation Architecture

[VERIFIED: .planning/config.json:1-6] `workflow.nyquist_validation` absent, thus enabled. Commands below are **proposed for later authorized work**, not executed tests. New files are Wave 0 gaps.

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (host 9.0.2), FastAPI TestClient; `node --test` per `ui-v2/package.json:6-11`; DG.Tests .NET on corpus changes [VERIFIED: data-service/tests/test_route_inventory.py:25-43] |
| Config file | `ui-v2/package.json`; focused Python test files to create |
| Quick run | `python -m pytest data-service/tests/test_route_inventory.py -q` (existing); later `python -m pytest data-service/tests/test_dgkn_revision.py -q` |
| Full suite | `python -m pytest data-service/tests -q`; `npm --prefix ui-v2 test`; `dotnet test DG/tests/DG.Tests/` in suitable isolated environment |

### Phase Requirements → Test Map
| Req ID | Behavior | Test type | Proposed automated command (focused; duration not measured) | File exists? |
|---|---|---|---|---|
| DGKN-01 | Pin/ACL/non-executable intent | API fixture + manual approved CDE | `python -m pytest data-service/tests/test_dgkn_source.py -q` | ❌ Wave 0 |
| DGKN-02 | Release immutable/draft isolation | API/security | `python -m pytest data-service/tests/test_dgkn_vocabulary.py -q` | ❌ Wave 0 |
| DGKN-03 | Steward review/deny/retire history | API/security | `python -m pytest data-service/tests/test_dgkn_vocabulary.py -q` | ❌ Wave 0 |
| DGKN-04 | Diff/formalization/separate confirmation | API/UI | `python -m pytest data-service/tests/test_dgkn_revision.py -q`; `node --test ui-v2/tests/dgkn-review.test.js` | ❌ Wave 0 |
| DGKN-05 | Two writers/stale conflict/audit atomicity | **real isolated Neo4j** integration | `python -m pytest data-service/tests/test_dgkn_concurrency.py -q` | ❌ Wave 0; gated |
| DGKN-06 | Corpus pin/history/recheck/verdict | API/evaluator integration | `python -m pytest data-service/tests/test_dgkn_history.py -q`; `dotnet test DG/tests/DG.Tests/` | ❌ Wave 0; gated |
| DGKN-07 | One-project class/object/conditions | API/security | `python -m pytest data-service/tests/test_dgkn_scope.py -q` | ❌ Wave 0 |
| DGKN-08 | Same company + transfer/write, independent ID | API/security | `python -m pytest data-service/tests/test_dgkn_copy.py -q` | ❌ Wave 0 |
| DGKN-09 | Fresh destination check/approval/no source reuse | API/integration + human UAT | `python -m pytest data-service/tests/test_dgkn_copy.py -q` | ❌ Wave 0; human gate |
| DGKN-10 | Registry args/risk/help/confirm/re-auth | Node/UI + API | `node --test ui-v2/tests/dgkn-commands.test.js`; `python -m pytest data-service/tests/test_dgkn_commands.py -q` | ❌ Wave 0 |

Missing paths are proposed, not existing. Add deny matrix for revocation, company change, private drafts, foreign/unknown IDs, stale no-side-effect, unsupported/non-verdict and retries. Existing route inventory enforces bidirectional classification [VERIFIED: data-service/tests/test_route_inventory.py:1-22].

### Sampling Rate
- Per offline task: focused affected tests + existing route inventory, **no commit implied**.
- Per integration wave: relevant Python/UI/C# suite in authorized isolated environment.
- Phase gate: evidence per DGKN-01..10, authorized real CAS/source/destination verification and human acceptance before `/gsd:verify-work`; no suites run in this research.

### Wave 0 Gaps
- [ ] Add focused source/vocab/revision/scope/history/copy/command test files and two-project/foreign-company/revoked-source fixtures.
- [ ] Real isolated Neo4j concurrent harness and actual evaluator-manifest equality test; mocks do not earn DGKN-05/06.
- [ ] Legacy writer/route inventory; protect prior tests.
- [ ] Approved CDE/steward/approver evidence and fresh destination record + human sign-off for DGKN-09.

## Security Domain

[VERIFIED: .planning/config.json:1-6] `security_enforcement` not disabled. OWASP ASVS **5.0.0** chapter numbering differs from older role template; avoid pretending V2 is Authentication [CITED: https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release; https://github.com/OWASP/ASVS].

### Applicable ASVS Categories
| Category | Applies | Control |
|---|---|---|
| V6 Authentication; V7 Session Management (ASVS 5) | yes | Existing principal/session/delegation and revocation [VERIFIED: spec/SECURITY-BOUNDARY.md:119-131] |
| Access Control (chapter number not asserted here) | yes | Project/company/steward/source checks, route/resource deny [VERIFIED: data-service/route_policy.py:48-85] |
| V2 Validation and Business Logic | yes | Server schema/expectedRevision and ordered approval [CITED: https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x11-V2-Validation-and-Business-Logic.md] |
| V1 Encoding/Sanitization | yes | Parameterized Cypher, source allowlist/SSRF defense [CITED: https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x10-V1-Encoding-and-Sanitization.md] |
| Cryptography | yes for hashes/tokens | Reuse existing primitives, no custom secret scheme [VERIFIED: spec/SECURITY-BOUNDARY.md:119-127] |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---|---|---|
| Cross-tenant list/conflict/source leak | Information disclosure | Server filtering/equal unknown-foreign denial |
| Forged steward/actor or post-preview revocation | Spoofing/Elevation | Explicit appointment, authenticated actor, commit-time recheck |
| Arbitrary source URI/redirect | Information disclosure/SSRF | Allowlisted connector/object/revision, verified ACL |
| Stale editor/duplicate retry | Tampering | Transaction/CAS/constraint/idempotence and concurrency test |
| Old delete or LLM command bypass | Tampering/Elevation | Managed-record fencing, typed dispatch, server confirm |
| Missing evidence treated as pass | Integrity | Canonical non-verdict and destination-scoped approval |

## Sources

### Primary: inspected local contracts/code (HIGH for what these files declare)
- `.planning/ROADMAP.md:289-309`; `.planning/REQUIREMENTS.md:43-52`; `1302-CONTEXT.md:6-78`; `CLAUDE.md:153-259`; `spec/degram/WORKSPACE.md:3-54` — scope/gates.
- `data-service/app.py:782-840,1169-1187,3651-3683,3910-4003,4243-4362`; `data-service/company.py:1-17,53-95`; `data-service/route_policy.py:1-111`; `DG/src/DG.Core/Data/Neo4jRuleRepository.cs:31-86`; `spec/DATABASE.md:1-45,593-617`; `spec/SECURITY-BOUNDARY.md:15-24,119-131`; `spec/EVIDENCE-CONTRACT.md:81-103`; `spec/REPRODUCIBILITY.md:15-29` — seams.
- `ui-v2/package.json:1-21`; `data-service/requirements.txt:1-11`; `data-service/tests/test_route_inventory.py:1-22`; `apps/degram/apps/desktop/src/AGENTS.md:36-63`; `1302-UI-SPEC.md:10-141` — test/UI.

### Official docs: search excerpts, not full-page extraction (MEDIUM)
- https://neo4j.com/docs/python-manual/current/transactions/ — retries/idempotence; publication date not visible in excerpt.
- https://neo4j.com/docs/cypher-manual/current/clauses/merge/ — uniqueness/constraints; publication date not visible.
- https://fastapi.tiangolo.com/tutorial/testing/ — TestClient/httpx/pytest; publication date not visible.
- https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release — dated 2025-05-30 in release excerpt; https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x11-V2-Validation-and-Business-Logic.md; https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x10-V1-Encoding-and-Sanitization.md.

## Metadata

**Confidence breakdown:** stack HIGH for declared repo ranges, LOW for deployed versions; architecture MEDIUM (proposed CAS not prototyped); pitfalls HIGH for inspected legacy behavior, MEDIUM for mitigations. Valid until ~2026-11-13 or any 1300/1301/permissions/driver change. Preliminary research replaced; no PLAN, live tests, Git action or gate closure.

# Шаг 3c — ввод правил и сверка с Neo4j

Проверка после каждого ввода (Cypher через `cypher-shell` в контейнере `neo4j`, проект `v12-hexagonal-facade-01`). Критерии — [RULES.md](RULES.md), раздел «Критерии приёмки ввода».

Вычислитель использует **только тело** правила (`RuleEvaluator` берёт `BodyAtoms`; голова в привязке не участвует), поэтому голова, отличающаяся от эталона `violation(?x)`, допустима.

## Сводка

| # | Ожидаемый Rule ID | Записанный Rule ID | Тело (класс / свойство / builtin / порог) | Голова | Итог |
|---|---|---|---|---|---|
| R1 | `R_FAC_ASPECT_MIN_13_V` | `R_GLASS_ASPECTRATIO_MIN_1.3_V` | `GlassPanel(?g)` / `hasAspectRatio(?g, ?a)` / `lessThan(?a, 1.3 xsd:decimal)` ✓ | `aspectRatioBelowMin(?g, true)` (новое DatatypeProperty) | ✅ принято, ID другой |
| R2 | `R_FAC_ASPECT_MAX_6_V` | `R_GLASS_ASPECTRATIO_MAX_6_V` | `GlassPanel(?e)` / `hasAspectRatio(?e, ?val)` / `greaterThan(?val, 6 xsd:decimal)` ✓ | `aspectRatioBelowMin(?e, true)` (переиспользовано, название не по смыслу) | ✅ принято, ID другой, отдельное правило |
| R3 | `R_FAC_LEVELOFFSET_MAX_001_V` | `R_GEO_HEXUNIT_LEVELOFFSET_MAX_0_01_V` | `HexagonalUnit(?u)` / `hasLevelOffsetM(?u, ?v)` / `greaterThan(?v, 0.01 xsd:decimal)` ✓ | `levelOffsetExceedsMax(?u, true)` (новое) | ✅ принято, ID другой |
| R5 | `R_FAC_VERTEXCOUNT_EQ_3_V` | `R_BTP_HASVERTEXCOUNT_REQ_3_V` | `BottomTriangularPanel(?e)` / `hasVertexCount(?e, ?val)` / `notEqual(?val, 3 xsd:integer)` ✓ | `vertexCountInvalid(?e, true)` (новое) | ✅ принято, ID другой |
| R6 | `R_FAC_PLANARITY_MAX_0005_V` | `R_GLASS_PLANARITYDEVIATION_MAX_0p005_V` | `GlassPanel(?p)` / `hasPlanarityDeviationM(?p, ?d)` / `greaterThan(?d, 0.005 xsd:decimal)` ✓ | `planarityDeviationExceedsMax(?p, true)` (новое) | ✅ принято, ID другой |
| R7 | `R_FAC_WIDTH_MIN_45_V` | `R_GP_WIDTH_MIN_4.5_V` | `GlassPanel(?g)` / `hasWidthM(?g, ?w)` / `lessThan(?w, 4.5 xsd:decimal)` ✓ | `widthBelowMin(?g, true)` (новое) | ✅ принято, ID другой |
| R8 | `R_FAC_HEIGHT_MAX_120_V` | `R_FACADE_TOTALHEIGHT_MAX_120_V` | `Facade(?f)` / **`hasTotalHeightM`**`(?f, ?h)` / `greaterThan(?h, 120 xsd:decimal)` ✓ | `totalHeightExceedsMax(?f, true)` (новое) | ✅ принято; **без подсказки класса/свойства**; свойство названо `hasTotalHeightM`, не `hasHeightM` |
| R9 | `R_FAC_HEXGAPS_MAX_0_V` | `R_HEX_HASGAPCOUNT_MAX_0_V` | **`HexagonalUnit`**`(?e)` (распознан из «hexagonal module») / `hasGapCount(?e, ?count)` / `greaterThanOrEqual(?count, 0)` **+** `greaterThan(?count, 0)` (integer) | `outlineGapCountExceedsMax(?e, true)` (новое) | ✅ принято; лишний, но безвредный атом `≥ 0` (4 атома тела вместо 3) |
| R10 | `R_FAC_GROUNDGAPS_MAX_0_V` | `R_OUTLINE_HASGAPCOUNT_MAX_0_V` | ✗ **`HexagonalUnit`**`(?e)` вместо нового класса 1-го этажа / `hasGapCount` (переиспользовано ✓) / `greaterThan(?val, 0)` | `outlineGapCountExceedsMax(?e, true)` | ❌ **не принято** — ложное распознавание: «ground floor module» → существующий `HexagonalUnit`; дублирует R9 |
| R10 (повтор) | `R_FAC_GROUNDGAPS_MAX_0_V` | `R_GFU_HASGAPCOUNT_MAX_0_V` | `GroundFloorUnit(?e)` (явный класс) / `hasGapCount(?e, ?val)` (переиспользовано ✓) / `greaterThan(?val, 0 xsd:integer)` ✓ | `outlineGapCountExceedsMax(?e, true)` (переиспользовано) | ✅ принято |
| R11 | `R_FAC_VERTEXCOUNT_EQ_5_V` | `R_GF_HASVERTEXCOUNT_REQ_5_V` | **`GroundFloorUnit`**`(?u)` (распознан) / **`hasVertexCount`**`(?u, ?v)` (распознано) / `notEqual(?v, 5 xsd:integer)` ✓ | `vertexCountInvalid(?u, true)` (переиспользовано) | ✅ принято; **без подсказок** — оба термина распознаны |
| R12 | `R_FAC_VERTEXCOUNT_EQ_6_V` | `R_HEX_HASVERTEXCOUNT_REQ_6_V` | `HexagonalUnit(?e)` (распознан) / `hasVertexCount(?e, ?val)` (распознано) / `notEqual(?val, 6 xsd:integer)` ✓ | `vertexCountInvalid(?e, true)` (переиспользовано) | ✅ принято; без подсказок |

## R1 — 2026-10-05

```text
SWRL: GlassPanel(?g) ^ hasAspectRatio(?g, ?a) ^ swrlb:lessThan(?a, "1.3"^^xsd:decimal) -> aspectRatioBelowMin(?g, true)
kind: violation
HAS_BODY 1  _A1  ClassAtom         GlassPanel         -> Class            args 1:?g
HAS_BODY 2  _A2  DataPropertyAtom  hasAspectRatio     -> DatatypeProperty args 1:?g 2:?a
HAS_BODY 3  _A3  BuiltinAtom       lessThan           -> Builtin          args 1:?a 2:1.3 (xsd:decimal)
HAS_HEAD 1  _H1  DataPropertyAtom  aspectRatioBelowMin-> DatatypeProperty args 1:?g 2:true (xsd:boolean)
project nodes: Rule 1, Atom 4, Var 2, Literal 2, Builtin 1, Class 1 (GlassPanel), DatatypeProperty 2, DesignRuleSession 1
```

- Тело совпадает с эталоном: один ClassAtom, свойство — DatatypeProperty с переменной в позиции 2, `lessThan` с порогом 1.3. Все узлы с `project = v12-hexagonal-facade-01`.
- LLM **не взяла** явный Rule ID из текста, а сгенерировала свой (с точкой в пороге) — находка F9.
- Голова — придуманное свойство `aspectRatioBelowMin` (попадает в OntoGraph проекта как DatatypeProperty). На вычисление не влияет; в PROPERTY STATE выбирать `hasAspectRatio`, не его.

## R2 — 2026-10-05

```text
SWRL: GlassPanel(?e) ^ hasAspectRatio(?e, ?val) ^ swrlb:greaterThan(?val, "6"^^xsd:decimal) -> aspectRatioBelowMin(?e, true)
HAS_BODY 1  _A1  ClassAtom         GlassPanel      args 1:?e
HAS_BODY 2  _A2  DataPropertyAtom  hasAspectRatio  args 1:?e 2:?val
HAS_BODY 3  _A3  BuiltinAtom       greaterThan     args 1:?val 2:6 (xsd:decimal)
HAS_HEAD 1  _H1  DataPropertyAtom  aspectRatioBelowMin args 1:?e 2:true
project: Rule 2 (по 3 body + 1 head у каждого), Atom 8, orphan atoms 0, DatatypeProperty [hasAspectRatio, aspectRatioBelowMin]
```

- Отдельное правило, с R1 не слилось (F6 не сработал). Тело верное.
- Голова переиспользует `aspectRatioBelowMin` — для верхнего порога название не по смыслу; на вычисление не влияет.

## R3 — 2026-10-05

```text
SWRL: HexagonalUnit(?u) ^ hasLevelOffsetM(?u, ?v) ^ swrlb:greaterThan(?v, "0.01"^^xsd:decimal) -> levelOffsetExceedsMax(?u, true)
project: Rule 3 (3 body + 1 head у каждого), orphan atoms 0
Class: GlassPanel, HexagonalUnit
DatatypeProperty: hasAspectRatio, aspectRatioBelowMin, hasLevelOffsetM, levelOffsetExceedsMax
```

- `HexagonalUnit` создан как Class; `hasLevelOffsetM` — DatatypeProperty; «nearest level plane» лишнего атома не дал. Порог 0.01 в ID записан как `0_01` (без точки — в отличие от R1).

## R5 — 2026-10-05

```text
SWRL: BottomTriangularPanel(?e) ^ hasVertexCount(?e, ?val) ^ swrlb:notEqual(?val, "3"^^xsd:integer) -> vertexCountInvalid(?e, true)
project: Rule 4 (3 body + 1 head у каждого), orphan atoms 0
Class: GlassPanel, HexagonalUnit, BottomTriangularPanel
DatatypeProperty: hasAspectRatio, aspectRatioBelowMin, hasLevelOffsetM, levelOffsetExceedsMax, hasVertexCount, vertexCountInvalid
```

- Направление верное (`notEqual`, не `equal`); литерал 3 — `xsd:integer`. `hasVertexCount` создан один раз — R11/R12 должны переиспользовать его с другими классами.

## R6 — 2026-10-05

```text
SWRL: GlassPanel(?p) ^ hasPlanarityDeviationM(?p, ?d) ^ swrlb:greaterThan(?d, "0.005"^^xsd:decimal) -> planarityDeviationExceedsMax(?p, true)
project: Rule 5 (3 body + 1 head у каждого), orphan atoms 0, duplicate classes 0
Class (3): GlassPanel, HexagonalUnit, BottomTriangularPanel
DatatypeProperty (8): + hasPlanarityDeviationM, planarityDeviationExceedsMax
```

- Класс `GlassPanel` переиспользован (дубликатов нет); порог 0.005 сохранён точно. В ID порог — третья форма записи (`0p005`; ранее `1.3` и `0_01`).

## R7 — 2026-10-05

```text
SWRL: GlassPanel(?g) ^ hasWidthM(?g, ?w) ^ swrlb:lessThan(?w, "4.5"^^xsd:decimal) -> widthBelowMin(?g, true)
project: Rule 6 (3 body + 1 head у каждого), orphan atoms 0
Class (3): GlassPanel, HexagonalUnit, BottomTriangularPanel
DatatypeProperty (10): + hasWidthM, widthBelowMin
```

- «at least 4.5» → `lessThan 4.5` (схема нарушения) — верно; `GlassPanel` переиспользован. Префикс домена в ID снова другой (`GP`; ранее `GLASS`).
- Для R8 в OntoGraph проекта нет ни `Facade`, ни свойства высоты (в других проектах есть: `v8-ui-smoke` — `Facade`/`hasHeightM`, `v9-final-uat` — `Building`/`height`). Онтология изолирована по проекту, так что R8 будет создавать свои термины.

## R8 — 2026-10-05 (без подсказки класса и свойства)

Текст: `The total height of the facade must not exceed 120 meters.`

```text
SWRL: Facade(?f) ^ hasTotalHeightM(?f, ?h) ^ swrlb:greaterThan(?h, "120"^^xsd:decimal) -> totalHeightExceedsMax(?f, true)
project: Rule 7 (3 body + 1 head у каждого), orphan atoms 0
Class (4): + Facade
DatatypeProperty (12): + hasTotalHeightM, totalHeightExceedsMax
```

- Термины придуманы осмысленно и в стиле проекта (суффикс единицы `M`, как у `hasWidthM`), структура тела верная.
- **В Grasshopper:** OBJECT STATE — класс `Facade`, PROPERTY STATE — свойство **`hasTotalHeightM`** (не `hasHeightM` из RULES.md).

## R9 — 2026-10-05 (без подсказки класса и свойства)

Текст: `The outline of each hexagonal module must be closed: the number of gaps in its outline must not exceed 0.`

```text
SWRL: HexagonalUnit(?e) ^ hasGapCount(?e, ?count) ^ swrlb:greaterThanOrEqual(?count, "0"^^xsd:integer) ^ swrlb:greaterThan(?count, "0"^^xsd:integer) -> outlineGapCountExceedsMax(?e, true)
project: Rule 8, orphan atoms 0
Class (4): без новых — HexagonalUnit переиспользован
DatatypeProperty (14): + hasGapCount, outlineGapCountExceedsMax
```

- **Распознавание сработало**: «hexagonal module» сопоставлен существующему классу `HexagonalUnit`, дубликата `HexagonalModule` нет.
- Свойство придумано как `hasGapCount` (целое) — **в Grasshopper для R9 выбирать `hasGapCount`**, не `hasOutlineGapCount`.
- В теле лишний атом `greaterThanOrEqual(?count, 0)`. Вычислитель идёт по атомам тела как по конъюнкции (`RuleEvaluator.EvaluateBody`): при `count = 0` первый атом выполняется, второй (`> 0`) — нет → passed; при `count ≥ 1` выполняются оба → failed. Результат совпадает с эталоном `> 0`, правило оставлено как есть (находка F11).

## R10 — 2026-10-05 (без подсказки) — НЕ ПРИНЯТО

Текст: `The outline of each ground floor module must be closed: the number of gaps in its outline must not exceed 0.`

```text
SWRL: HexagonalUnit(?e) ^ hasGapCount(?e, ?val) ^ swrlb:greaterThan(?val, "0"^^xsd:integer) -> outlineGapCountExceedsMax(?e, true)
project: Rule 9, orphan atoms 0; Class (4) — нового класса нет
```

- Распознавание терминов **переусердствовало**: «ground floor module» сопоставлен существующему `HexagonalUnit` (общее слово «module»), хотя это другой класс объектов (пятиугольники 1-го этажа). Свойство `hasGapCount` переиспользовано правильно.
- Последствие: правило — смысловой дубль R9, пятиугольники 1-го этажа не охвачены (находка F12).
- Исправление: удалить `R_OUTLINE_HASGAPCOUNT_MAX_0_V` (Graph → Edit, «delete R_OUTLINE_HASGAPCOUNT_MAX_0_V» — ID без точки, F10 не мешает) и ввести заново с явным классом.

## R10 — попытка исправления 2026-10-05 13:00 — правило ИСПОРЧЕНО

По журналу `DesignRuleSession`: удаления не было. В **режиме ingest** ушла строка `R_OUTLINE_HASGAPCOUNT_MAX_0_V` (без слова delete и без текста правила). LLM сочинила правило по одному ID и `MERGE` записала его поверх существующего правила с тем же `Rule_Id`:

```text
SWRL (перезаписан): Facade(?f) ^ hasGapCount(?f, ?val) ^ swrlb:greaterThan(?val, 0) -> outlineGapCountExceedsMax(?f, true)
_A1 ClassAtom   REFERS_TO -> Facade  И  HexagonalUnit       ARG 1 -> f, ?e
_A2 DataProp    REFERS_TO -> hasGapCount                    ARG 1 -> f, ?e ; ARG 2 -> val, ?val
_A3 Builtin     REFERS_TO -> greaterThan                    ARG 1 -> val, ?val ; ARG 2 -> 0
_H1 DataProp    REFERS_TO -> outlineGapCountExceedsMax      ARG 1 -> f, ?e ; ARG 2 -> true
новые Var без «?»: f, val
```

Остальные 8 правил не затронуты; Class (4), повторного ввода с `GroundFloorUnit` не было.

## R10 — очистка через UI (Graph → Edit → delete) 2026-10-05

```text
Rule 8 (R_OUTLINE_HASGAPCOUNT_MAX_0_V удалено), атомы R_OUTLINE_* — 0, orphan atoms 0, orphan Var/Literal — нет
Var: 14 → 12 (удалены f, val — использовались только испорченным правилом); Atom: 37 → 33
R_HEX_HASGAPCOUNT_MAX_0_V не задет: A1 → HexagonalUnit, A2 → hasGapCount, A3 → ≥, A4 → >
```

Штатное удаление (`DELETE /rules/{project}/{ruleId}`) очистило и смешанное правило полностью: атомы с двойными `REFERS_TO`/`ARG` удалены, общие аргументы сохранены. Удаление в журнал `DesignRuleSession` не пишется (последняя запись — ingest 13:00).

## R10 — повторный ввод 2026-10-05 (класс указан явно, свойство — нет)

Текст: `The outline of each ground floor module (class GroundFloorUnit) must be closed: the number of gaps in its outline must not exceed 0.`

```text
SWRL: GroundFloorUnit(?e) ^ hasGapCount(?e, ?val) ^ swrlb:greaterThan(?val, "0"^^xsd:integer) -> outlineGapCountExceedsMax(?e, true)
project: Rule 9, orphan atoms 0, атомов с ≠1 REFERS_TO — нет
Class (5): + GroundFloorUnit
DatatypeProperty (14): без новых — hasGapCount и outlineGapCountExceedsMax переиспользованы
```

- Новый класс создан по явному указанию; существующее свойство `hasGapCount` распознано без подсказки; ID отличается от R9 — слияния нет.

## R11 — 2026-10-05 (без подсказки класса и свойства)

Текст: `Each ground floor module is a pentagon with a flat bottom and must have exactly 5 vertices.`

```text
SWRL: GroundFloorUnit(?u) ^ hasVertexCount(?u, ?v) ^ swrlb:notEqual(?v, "5"^^xsd:integer) -> vertexCountInvalid(?u, true)
project: Rule 10, orphan atoms 0; Class (5) и DatatypeProperty (14) — без новых
```

- Распознавание сработало там, где в R10 ошиблось: при наличии обоих классов «ground floor module» сопоставлен `GroundFloorUnit`, а не `HexagonalUnit`. Свойство `hasVertexCount` переиспользовано; «pentagon with a flat bottom» лишних атомов не дал.

## R12 — 2026-10-05 (без подсказки класса и свойства)

Текст: `Each hexagonal module must have exactly 6 vertices.`

```text
SWRL: HexagonalUnit(?e) ^ hasVertexCount(?e, ?val) ^ swrlb:notEqual(?val, "6"^^xsd:integer) -> vertexCountInvalid(?e, true)
```

## Итог шага 3c — 2026-10-05

Проверки целостности проекта после R12: Rule 11, у каждого атома ровно один `REFERS_TO`, повторных `ARG` на одной позиции нет, orphan atoms 0, узлов без `graph` 0, узлов Rule/Atom в `default-project` 0. Class 5, DatatypeProperty 14 (7 «рабочих» свойств тела + 7 придуманных свойств головы).

### Таблица для шага 5 (OBJECT STATE / PROPERTY STATE)

В PROPERTY STATE выбирать правило по **ID в графе** и свойство **тела** (столбец «Свойство»), не свойство головы.

| # | Наш ID (RULES.md) | ID в графе | Класс (OBJECT STATE) | Свойство (PROPERTY STATE) | Нарушение | Выход скрипта | Объекты (вход скрипта) |
|---|---|---|---|---|---|---|---|
| R1 | `R_FAC_ASPECT_MIN_13_V` | `R_GLASS_ASPECTRATIO_MIN_1.3_V` | `GlassPanel` | `hasAspectRatio` | `lessThan 1.3` | `AR` | `PB` |
| R2 | `R_FAC_ASPECT_MAX_6_V` | `R_GLASS_ASPECTRATIO_MAX_6_V` | `GlassPanel` | `hasAspectRatio` | `greaterThan 6` | `AR` | `PB` |
| R3 | `R_FAC_LEVELOFFSET_MAX_001_V` | `R_GEO_HEXUNIT_LEVELOFFSET_MAX_0_01_V` | `HexagonalUnit` | `hasLevelOffsetM` | `greaterThan 0.01` | `LO` | `HU` |
| R5 | `R_FAC_VERTEXCOUNT_EQ_3_V` | `R_BTP_HASVERTEXCOUNT_REQ_3_V` | `BottomTriangularPanel` | `hasVertexCount` | `notEqual 3` | `VC` | `PA` |
| R6 | `R_FAC_PLANARITY_MAX_0005_V` | `R_GLASS_PLANARITYDEVIATION_MAX_0p005_V` | `GlassPanel` | `hasPlanarityDeviationM` | `greaterThan 0.005` | `PD` | `PB` |
| R7 | `R_FAC_WIDTH_MIN_45_V` | `R_GP_WIDTH_MIN_4.5_V` | `GlassPanel` | `hasWidthM` | `lessThan 4.5` | `W` | `PB` |
| R8 | `R_FAC_HEIGHT_MAX_120_V` | `R_FACADE_TOTALHEIGHT_MAX_120_V` | `Facade` | `hasTotalHeightM` | `greaterThan 120` | `H` | `F` |
| R9 | `R_FAC_HEXGAPS_MAX_0_V` | `R_HEX_HASGAPCOUNT_MAX_0_V` | `HexagonalUnit` | `hasGapCount` | `greaterThanOrEqual 0 ∧ greaterThan 0` | `HG` | `HU` |
| R10 | `R_FAC_GROUNDGAPS_MAX_0_V` | `R_GFU_HASGAPCOUNT_MAX_0_V` | `GroundFloorUnit` | `hasGapCount` | `greaterThan 0` | `GG` | `GU` |
| R11 | `R_FAC_VERTEXCOUNT_EQ_5_V` | `R_GF_HASVERTEXCOUNT_REQ_5_V` | `GroundFloorUnit` | `hasVertexCount` | `notEqual 5` | `GV` | `GU` |
| R12 | `R_FAC_VERTEXCOUNT_EQ_6_V` | `R_HEX_HASVERTEXCOUNT_REQ_6_V` | `HexagonalUnit` | `hasVertexCount` | `notEqual 6` | `HV` | `HU` |

OBJECT STATE — 5 штук, по одному на класс: `GlassPanel` (PB), `HexagonalUnit` (HU), `GroundFloorUnit` (GU), `BottomTriangularPanel` (PA), `Facade` (F). PROPERTY STATE — 11, по одному на правило; одна величина в двух/трёх правилах (AR → R1, R2; HV/GV/VC → R12, R11, R5; HG/GG → R9, R10) подаётся в каждый PROPERTY STATE отдельно.

Отличия терминов графа от RULES.md: `hasTotalHeightM` (было `hasHeightM`), `hasGapCount` (было `hasOutlineGapCount`).

Наблюдения по распознаванию без подсказок (R8–R12): существующие термины распознаны в R9, R11, R12 и для свойства в R10; ложное совпадение класса — R10 (F12); новые термины осмысленны (R8). Rule ID ни разу не взят из текста (F9).

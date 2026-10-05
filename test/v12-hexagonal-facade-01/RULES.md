# v12-hexagonal-facade-01 — утверждённый набор правил

**Статус:** утверждено 2026-10-03; **пороги откалиброваны по V1 2026-10-05** (R1, R2, R7, R8 — от V1 с запасом ~8%); дополнено 2026-10-04 (модули 1-го этажа, замкнутость, R6 → контрольное), 2026-10-05 — **R4 (симметрия) исключено**. Калибровка: замер V1 №7 в [3a-V1-summary.txt](3a-V1-summary.txt).
**В графе (2026-10-05):** Rule ID и часть терминов LLM записала по-своему (`hasTotalHeightM`, `hasGapCount`) — для Grasshopper использовать таблицу в [3c-ingest.md](3c-ingest.md), не ID этого файла.
**Машиночитаемая копия:** [rules-approved.json](rules-approved.json) — используется для сверки с тем, что LLM-конвейер реально записал в Neo4j.

## Ограничения вычислителя, которые определили форму правил

Проверено по коду DG v12 (`DG.Core/Services/DesignStateBindingService.cs`, `DG.Core/Validation/RuleEvaluator.cs`, `spec/SWRL-SUBSET.md`):

1. **Одна объектная переменная на правило.** Каждый ObjState даёт свою строку привязки; правила, связывающие два объекта, дают `unknown`/`unsupported`.
2. **Тело правила — только конъюнкция (И).** SWRL не имеет «ИЛИ», поэтому диапазон `2 ≤ x ≤ 4` записывается **двумя** правилами-нарушениями (`x < 2` и `x > 4`).
3. **Значения — только число / целое / boolean.** Строковые значения (например `"TriangularBottom"`) PROPERTY STATE передать не может → `unknown`. Литерал внутри атома свойства не сравнивается; сравнение — только через `swrlb:*`.
4. **Связи между объектами (ObjectProperty)** распознаются, но вычисляются как `unsupported` (честный отказ, не «passed»).
5. **Класс объекта** приходит только из `OntologyClass` (выход METAGRAPH Objects) → один OBJECT STATE на класс; имена классов в правилах должны совпадать буква в букву.
6. **Схема нарушения:** тело правила выполнилось → объект `failed`.

## Основной набор (11 правил, 5 классов; номер 4 не используется)

| # | Rule ID (ожидаемый) | Источник | Класс | Свойство | Нарушение, если | Ед. |
|---|---|---|---|---|---|---|
| 1 | `R_FAC_ASPECT_MIN_13_V` | D1 (нижний порог) | `GlassPanel` | `hasAspectRatio` | `< 1.3` | — |
| 2 | `R_FAC_ASPECT_MAX_6_V` | D1 (верхний порог) | `GlassPanel` | `hasAspectRatio` | `> 6.0` | — |
| 3 | `R_FAC_LEVELOFFSET_MAX_001_V` | B1 (адаптировано), **контрольное** | `HexagonalUnit` (эт. 2+) | `hasLevelOffsetM` | `> 0.01` | м |
| ~~4~~ | ~~`R_FAC_SYMMETRY_MAX_001_V`~~ | B2 — **исключено 2026-10-05** | — | — | — | — |
| 5 | `R_FAC_VERTEXCOUNT_EQ_3_V` | C1 (адаптировано) | `BottomTriangularPanel` | `hasVertexCount` | `≠ 3` | шт |
| 6 | `R_FAC_PLANARITY_MAX_0005_V` | новое (драйвер V4) | `GlassPanel` | `hasPlanarityDeviationM` | `> 0.005` | м |
| 7 | `R_FAC_WIDTH_MIN_45_V` | новое | `GlassPanel` | `hasWidthM` (уже есть в OntoGraph) | `< 4.5` | м |
| 8 | `R_FAC_HEIGHT_MAX_120_V` | новое, **контрольное** | `Facade` (уже есть в OntoGraph) | `hasHeightM` (уже есть) | `> 120` | м |
| 9 | `R_FAC_HEXGAPS_MAX_0_V` | замкнутость (2026-10-04) | `HexagonalUnit` (эт. 2+) | `hasOutlineGapCount` | `> 0` | шт |
| 10 | `R_FAC_GROUNDGAPS_MAX_0_V` | замкнутость (2026-10-04) | `GroundFloorUnit` (эт. 1) | `hasOutlineGapCount` | `> 0` | шт |
| 11 | `R_FAC_VERTEXCOUNT_EQ_5_V` | исключение 1-го этажа (2026-10-04) | `GroundFloorUnit` (эт. 1) | `hasVertexCount` | `≠ 5` | шт |
| 12 | `R_FAC_VERTEXCOUNT_EQ_6_V` | (2026-10-04) | `HexagonalUnit` (эт. 2+) | `hasVertexCount` | `≠ 6` | шт |

**Модули 1-го этажа (дополнение 2026-10-04).** На первом этаже модули пятиугольные (снизу плоские) — это исключение, а не дефект. Они выделены в отдельный класс `GroundFloorUnit` (25 шт.); `HexagonalUnit` — только этажи 2+ (100 шт.). Отдельный класс, а не один класс с номером этажа, потому что вычислитель не делает вывода по подклассам и сравнивает класс буква в букву: так R3 (уровни) не применяется к пятиугольникам, а у каждого OBJECT STATE ровно один класс. **Все модули должны быть замкнутыми** — правило записано отдельно для каждого класса (R9, R10), потому что общего надкласса вычислитель не знает. `hasOutlineGapCount` — число разрывов контура (0 = замкнут), целое.

**R4 исключено (решение владельца 2026-10-05).** Требование симметрии сот снято целиком. Замеры V1 показали, что все 68 плоских модулей симметричны точно, а все 32 модуля, сложенные через углы здания, несимметричны (до 4.83 м по развёртке, до 4.14 м в 3D) — угловые соты в модели по построению несимметричны. Номер 4 не переиспользуется, чтобы не перенумеровывать артефакты; правило в граф не вводится.

**Калибровка порогов (решение владельца 2026-10-05).** Пороги привязаны к базовому варианту V1 с запасом ~8% и **не подгоняются** под ожидаемые провалы: проваливающиеся варианты V2–V4 получаются выбором значений слайдеров.

| Правило | Было | Стало | V1 (замер №7) | Запас |
|---|---|---|---|---|
| R1 соотношение сторон, мин. | 2.0 | **1.3** | min 1.419 | 8% |
| R2 соотношение сторон, макс. | 4.0 | **6.0** | max 5.480 | 9% |
| R7 ширина панели, мин. | 0.9 м | **4.5 м** | min 4.927 м | 9% |
| R8 высота фасада, макс. | 50 м | **120 м** | 114.275 м | 5%; контрольное — высота от слайдеров не зависит |

Rule ID отражают новые пороги. Во все тексты для ввода добавлен явный Rule ID (см. находку F6 в README).

**R6 — рабочее, R3 — контрольное (решение 2026-10-05).** На V1 панели B плоские (`hasPlanarityDeviationM` = 0), поэтому R6 сначала было помечено контрольным. Развёртка наклона сот показала обратное: при любой паре наклонов, кроме базовой −1 / +1, 14–54 панели скручиваются (до 3.6 м) — R6 и есть правило, которое ловит «искажённые соты» (V4). Вершины сот при этом остаются на уровнях во всех сочетаниях, поэтому R3 проходит во всех вариантах и стало контрольным. Подробно: [3b-variants.md](3b-variants.md).

### Тексты для ввода (Graph → Ingest, по одному)

```text
R1  Rule R_FAC_ASPECT_MIN_13_V: the aspect ratio of each glass panel (class GlassPanel, property hasAspectRatio) must be at least 1.3.
R2  Rule R_FAC_ASPECT_MAX_6_V: the aspect ratio of each glass panel (class GlassPanel, property hasAspectRatio) must not exceed 6.0.
R3  Rule R_FAC_LEVELOFFSET_MAX_001_V: the maximum vertical offset of the vertices of each hexagonal unit (class HexagonalUnit, property hasLevelOffsetM) from the nearest level plane must not exceed 0.01 meters.
R5  Rule R_FAC_VERTEXCOUNT_EQ_3_V: each bottom triangular panel (class BottomTriangularPanel, property hasVertexCount) must have exactly 3 vertices.
R6  Rule R_FAC_PLANARITY_MAX_0005_V: the planarity deviation of each glass panel (class GlassPanel, property hasPlanarityDeviationM) must not exceed 0.005 meters.
R7  Rule R_FAC_WIDTH_MIN_45_V: the width of each glass panel (class GlassPanel, property hasWidthM) must be at least 4.5 meters.
R8  Rule R_FAC_HEIGHT_MAX_120_V: the total height of the facade (class Facade, property hasHeightM) must not exceed 120 meters.
R9  Rule R_FAC_HEXGAPS_MAX_0_V: each hexagonal unit (class HexagonalUnit, property hasOutlineGapCount) must have a closed outline, so the number of gaps in its outline must not exceed 0.
R10 Rule R_FAC_GROUNDGAPS_MAX_0_V: each ground floor unit (class GroundFloorUnit, property hasOutlineGapCount) must have a closed outline, so the number of gaps in its outline must not exceed 0.
R11 Rule R_FAC_VERTEXCOUNT_EQ_5_V: each ground floor unit (class GroundFloorUnit, property hasVertexCount) is a pentagon with a flat bottom and must have exactly 5 vertices.
R12 Rule R_FAC_VERTEXCOUNT_EQ_6_V: each hexagonal unit (class HexagonalUnit, property hasVertexCount) must have exactly 6 vertices.
```

Rule ID задан в тексте явно (сначала только в R9–R12, с 2026-10-05 во всех): конвейер пишет правило через `MERGE (r:Rule {Rule_Id, project})`, и при совпадении ID два правила замкнутости молча слились бы в одно.

### Ожидаемый SWRL (эталон для проверки после ввода)

```text
R1  GlassPanel(?p) ^ hasAspectRatio(?p, ?r) ^ swrlb:lessThan(?r, 1.3)            -> violation(?p)
R2  GlassPanel(?p) ^ hasAspectRatio(?p, ?r) ^ swrlb:greaterThan(?r, 6.0)         -> violation(?p)
R3  HexagonalUnit(?u) ^ hasLevelOffsetM(?u, ?d) ^ swrlb:greaterThan(?d, 0.01)    -> violation(?u)
R5  BottomTriangularPanel(?p) ^ hasVertexCount(?p, ?n) ^ swrlb:notEqual(?n, 3)   -> violation(?p)
R6  GlassPanel(?p) ^ hasPlanarityDeviationM(?p, ?e) ^ swrlb:greaterThan(?e, 0.005) -> violation(?p)
R7  GlassPanel(?p) ^ hasWidthM(?p, ?w) ^ swrlb:lessThan(?w, 4.5)                 -> violation(?p)
R8  Facade(?f) ^ hasHeightM(?f, ?h) ^ swrlb:greaterThan(?h, 120)                 -> violation(?f)
R9  HexagonalUnit(?u) ^ hasOutlineGapCount(?u, ?g) ^ swrlb:greaterThan(?g, 0)     -> violation(?u)
R10 GroundFloorUnit(?u) ^ hasOutlineGapCount(?u, ?g) ^ swrlb:greaterThan(?g, 0)   -> violation(?u)
R11 GroundFloorUnit(?u) ^ hasVertexCount(?u, ?n) ^ swrlb:notEqual(?n, 5)          -> violation(?u)
R12 HexagonalUnit(?u) ^ hasVertexCount(?u, ?n) ^ swrlb:notEqual(?n, 6)            -> violation(?u)
```
Для R9/R10 допустим и `swrlb:notEqual(?g, 0)` — результат тот же.

Критерии приёмки ввода каждого правила (проверяются в Neo4j):
- ровно один `ClassAtom` с переменной в позиции 1, и имя класса совпадает с таблицей;
- свойство записано как `DatatypeProperty` (не `ObjectProperty`), значение — переменная в позиции 2;
- порог стоит в `swrlb:` builtin из разрешённых шести, с правильным направлением сравнения;
- `project = 'v12-hexagonal-facade-01'` на всех созданных узлах;
- `Rule_Id` не совпадает ни с одним ранее введённым правилом проекта, у правила ровно один `HAS_HEAD` и ожидаемое число `HAS_BODY` (признак того, что MERGE не слил два правила).

## Что считать в Grasshopper (модель в **мм** → длины делить на 1000)

| Свойство | Объекты | Расчёт |
|---|---|---|
| `hasAspectRatio` | панели группы B | средняя длина вертикальных рёбер / средняя длина горизонтальных (в модели уже есть группа «Group B Panel Ratio» — сверить определение) |
| `hasPlanarityDeviationM` | панели группы B | `Plane Fit` по 4 углам → max `Distance` угла до плоскости, ÷1000 |
| `hasWidthM` | панели группы B | средняя длина горизонтальных рёбер, ÷1000 |
| `hasLevelOffsetM` | шестигранные модули (эт. 2+); уровни `LZ` включают отметку парапета 114.275 м | для каждой вершины min \|z − z_уровня\|, затем max по вершинам модуля, ÷1000 |
| `hasVertexCount` | панели группы A; модули 1-го этажа; модули эт. 2+ | число вершин контура (целое) |
| `hasOutlineGapCount` | модули 1-го этажа; модули эт. 2+ | число открытых кусков, в которые склеиваются линии модуля (0 = замкнут) |
| `hasHeightM` | фасад (1 объект) | высота bounding box фасада, ÷1000 |

Одна величина, используемая в двух правилах (`hasAspectRatio` → R1 и R2), подаётся в **два** PROPERTY STATE: PropState привязан к конкретному правилу. То же для `hasVertexCount` (R5, R11, R12 — три разных класса) и `hasOutlineGapCount` (R9, R10).

Все величины считает [gh-measure-rules.cs](gh-measure-rules.cs); пороги в нём продублированы блоком `THRESHOLDS`.

## Вне основного набора

| Правило | Статус | Причина |
|---|---|---|
| A1 Create pattern control points | контрольное, после основного цикла | порождающее; `hasUpperVertex` — ObjectProperty → ожидаемый статус `unsupported` (проверка честного отказа v12) |
| A2 Create facade modules | не вводится | порождающее, не формализовано; место — Computgraph (OBJECT MARKER / ENTITY TAG) |
| C1 в исходной форме | не вводится | строковый литерал в атоме не сравнивается → ложные `failed` на всех панелях; заменено правилом R5 |
| `R_FAC_TRIANGLEANGLE_MIN_15_V` (min угол треугольной панели ≥ 15°) | резерв | включить при необходимости дополнительной нагрузки на группу A |

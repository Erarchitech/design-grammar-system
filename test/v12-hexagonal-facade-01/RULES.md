# v12-hexagonal-facade-01 — утверждённый набор правил

**Статус:** утверждено 2026-10-03. Пороги помечены *предварительными* до калибровки на базовом варианте V1 (см. [README.md](README.md), шаг 3a).
**Машиночитаемая копия:** [rules-approved.json](rules-approved.json) — используется для сверки с тем, что LLM-конвейер реально записал в Neo4j.

## Ограничения вычислителя, которые определили форму правил

Проверено по коду DG v12 (`DG.Core/Services/DesignStateBindingService.cs`, `DG.Core/Validation/RuleEvaluator.cs`, `spec/SWRL-SUBSET.md`):

1. **Одна объектная переменная на правило.** Каждый ObjState даёт свою строку привязки; правила, связывающие два объекта, дают `unknown`/`unsupported`.
2. **Тело правила — только конъюнкция (И).** SWRL не имеет «ИЛИ», поэтому диапазон `2 ≤ x ≤ 4` записывается **двумя** правилами-нарушениями (`x < 2` и `x > 4`).
3. **Значения — только число / целое / boolean.** Строковые значения (например `"TriangularBottom"`) PROPERTY STATE передать не может → `unknown`. Литерал внутри атома свойства не сравнивается; сравнение — только через `swrlb:*`.
4. **Связи между объектами (ObjectProperty)** распознаются, но вычисляются как `unsupported` (честный отказ, не «passed»).
5. **Класс объекта** приходит только из `OntologyClass` (выход METAGRAPH Objects) → один OBJECT STATE на класс; имена классов в правилах должны совпадать буква в букву.
6. **Схема нарушения:** тело правила выполнилось → объект `failed`.

## Основной набор (8 правил, 4 класса)

| # | Rule ID (ожидаемый) | Источник | Класс | Свойство | Нарушение, если | Ед. |
|---|---|---|---|---|---|---|
| 1 | `R_FAC_ASPECT_MIN_2_V` | D1 (нижний порог) | `GlassPanel` | `hasAspectRatio` | `< 2.0` | — |
| 2 | `R_FAC_ASPECT_MAX_4_V` | D1 (верхний порог) | `GlassPanel` | `hasAspectRatio` | `> 4.0` | — |
| 3 | `R_FAC_LEVELOFFSET_MAX_001_V` | B1 (адаптировано) | `HexagonalUnit` | `hasLevelOffsetM` | `> 0.01` | м |
| 4 | `R_FAC_SYMMETRY_MAX_001_V` | B2 (адаптировано) | `HexagonalUnit` | `hasSymmetryDeviationM` | `> 0.01` | м |
| 5 | `R_FAC_VERTEXCOUNT_EQ_3_V` | C1 (адаптировано) | `BottomTriangularPanel` | `hasVertexCount` | `≠ 3` | шт |
| 6 | `R_FAC_PLANARITY_MAX_0005_V` | новое | `GlassPanel` | `hasPlanarityDeviationM` | `> 0.005` | м |
| 7 | `R_FAC_WIDTH_MIN_09_V` | новое | `GlassPanel` | `hasWidthM` (уже есть в OntoGraph) | `< 0.9` | м |
| 8 | `R_FAC_HEIGHT_MAX_50_V` | новое | `Facade` (уже есть в OntoGraph) | `hasHeightM` (уже есть) | `> 50` | м |

### Тексты для ввода (Graph → Ingest, по одному)

```text
R1  The aspect ratio of each glass panel (class GlassPanel, property hasAspectRatio) must be at least 2.0.
R2  The aspect ratio of each glass panel (class GlassPanel, property hasAspectRatio) must not exceed 4.0.
R3  The maximum vertical offset of the vertices of each hexagonal unit (class HexagonalUnit, property hasLevelOffsetM) from the nearest level plane must not exceed 0.01 meters.
R4  The symmetry deviation of each hexagonal unit (class HexagonalUnit, property hasSymmetryDeviationM) about its own axis through its top and bottom vertices must not exceed 0.01 meters.
R5  Each bottom triangular panel (class BottomTriangularPanel, property hasVertexCount) must have exactly 3 vertices.
R6  The planarity deviation of each glass panel (class GlassPanel, property hasPlanarityDeviationM) must not exceed 0.005 meters.
R7  The width of each glass panel (class GlassPanel, property hasWidthM) must be at least 0.9 meters.
R8  The total height of the facade (class Facade, property hasHeightM) must not exceed 50 meters.
```

### Ожидаемый SWRL (эталон для проверки после ввода)

```text
R1  GlassPanel(?p) ^ hasAspectRatio(?p, ?r) ^ swrlb:lessThan(?r, 2.0)            -> violation(?p)
R2  GlassPanel(?p) ^ hasAspectRatio(?p, ?r) ^ swrlb:greaterThan(?r, 4.0)         -> violation(?p)
R3  HexagonalUnit(?u) ^ hasLevelOffsetM(?u, ?d) ^ swrlb:greaterThan(?d, 0.01)    -> violation(?u)
R4  HexagonalUnit(?u) ^ hasSymmetryDeviationM(?u, ?s) ^ swrlb:greaterThan(?s, 0.01) -> violation(?u)
R5  BottomTriangularPanel(?p) ^ hasVertexCount(?p, ?n) ^ swrlb:notEqual(?n, 3)   -> violation(?p)
R6  GlassPanel(?p) ^ hasPlanarityDeviationM(?p, ?e) ^ swrlb:greaterThan(?e, 0.005) -> violation(?p)
R7  GlassPanel(?p) ^ hasWidthM(?p, ?w) ^ swrlb:lessThan(?w, 0.9)                 -> violation(?p)
R8  Facade(?f) ^ hasHeightM(?f, ?h) ^ swrlb:greaterThan(?h, 50)                  -> violation(?f)
```

Критерии приёмки ввода каждого правила (проверяются в Neo4j):
- ровно один `ClassAtom` с переменной в позиции 1, и имя класса совпадает с таблицей;
- свойство записано как `DatatypeProperty` (не `ObjectProperty`), значение — переменная в позиции 2;
- порог стоит в `swrlb:` builtin из разрешённых шести, с правильным направлением сравнения;
- `project = 'v12-hexagonal-facade-01'` на всех созданных узлах.

## Что считать в Grasshopper (модель в **мм** → длины делить на 1000)

| Свойство | Объекты | Расчёт |
|---|---|---|
| `hasAspectRatio` | панели группы B | средняя длина вертикальных рёбер / средняя длина горизонтальных (в модели уже есть группа «Group B Panel Ratio» — сверить определение) |
| `hasPlanarityDeviationM` | панели группы B | `Plane Fit` по 4 углам → max `Distance` угла до плоскости, ÷1000 |
| `hasWidthM` | панели группы B | средняя длина горизонтальных рёбер, ÷1000 |
| `hasLevelOffsetM` | шестигранные модули | для каждой вершины min \|z − z_уровня\|, затем max по вершинам модуля, ÷1000 |
| `hasSymmetryDeviationM` | шестигранные модули | ось через верхнюю и нижнюю вершины; `Mirror` вершин через плоскость оси → max расстояния до ближайшей исходной вершины, ÷1000 |
| `hasVertexCount` | панели группы A | число вершин контура (целое) |
| `hasHeightM` | фасад (1 объект) | высота bounding box фасада, ÷1000 |

Одна величина, используемая в двух правилах (`hasAspectRatio` → R1 и R2), подаётся в **два** PROPERTY STATE: PropState привязан к конкретному правилу.

## Вне основного набора

| Правило | Статус | Причина |
|---|---|---|
| A1 Create pattern control points | контрольное, после основного цикла | порождающее; `hasUpperVertex` — ObjectProperty → ожидаемый статус `unsupported` (проверка честного отказа v12) |
| A2 Create facade modules | не вводится | порождающее, не формализовано; место — Computgraph (OBJECT MARKER / ENTITY TAG) |
| C1 в исходной форме | не вводится | строковый литерал в атоме не сравнивается → ложные `failed` на всех панелях; заменено правилом R5 |
| `R_FAC_TRIANGLEANGLE_MIN_15_V` (min угол треугольной панели ≥ 15°) | резерв | включить при необходимости дополнительной нагрузки на группу A |

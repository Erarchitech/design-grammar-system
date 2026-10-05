# Шаг 5 — подключение DG на холсте

Составлено 2026-10-05 по коду компонентов (`DG.Grasshopper/Components`) и итоговой таблице [3c-ingest.md](3c-ingest.md).

## Цепочка чтения правил

```text
CONNECTOR (Token, Go=True) ─Database→ GRAPH DECONSTRUCT ─Metagraph→ METAGRAPH (Refresh=True)
    METAGRAPH.Rules / RuleName   → выбор правила по ID в графе (List Item по индексу RuleName)
    METAGRAPH.Objects / ObjectName → выбор OntologyClass по имени класса
    RULE DECONSTRUCT (Rule) → DataProperties  (только переменная тела, напр. ?a ↔ hasAspectRatio;
                                                придуманное свойство головы сюда не попадает — у него литерал true)
```

## Три условия, без которых результат будет неверным

1. **OBJECT STATE должен получать плоский список за один вызов.** `ObjectRef` берётся из GUID referenced-геометрии, а для вычисленной — `obj_{i}` по индексу внутри вызова. Если подать дерево «одна ветка — один объект», компонент вызовется на каждую ветку, и все объекты получат `obj_0` → одинаковый `StateId`. Поэтому геометрию **сплющить** (Flatten), а `Object` — **один** элемент OntologyClass (ветка `{0}`), он раздаётся всем объектам.
2. **Один объект = один элемент геометрии.** Модули (HU, GU) лежат по нескольку линий на ветку → сначала `Join Curves` по веткам (получится один замкнутый контур на модуль), затем Flatten. Панели (PB, PA) — по одной поверхности на ветку, просто Flatten. Фасад (F) — один объект: `Bounding Box` в режиме **Union Box** (ПКМ по компоненту; по умолчанию «Per Object» даёт бокс на каждую поверхность — 350) → один бокс.
3. **PROPERTY STATE парует значения с объектами по позиции.** `PropValue` — сплющенный выход скрипта замеров (тот же порядок веток, что у геометрии), `ObjState` — выход соответствующего OBJECT STATE, `Rule` и `DataProperty` — по одному элементу (раздаются на все значения). Пустые ветки нигде не должны давать элементов: скрипт их пропускает, Flatten геометрии тоже.

## OBJECT STATE — 5

| OBJECT STATE | Object (OntologyClass из METAGRAPH.Objects) | Geometry (сплющенная) | Объектов в V1 |
|---|---|---|---|
| OS-GP | `GlassPanel` | PB | 125 |
| OS-HU | `HexagonalUnit` | HU → Join Curves по веткам | 100 |
| OS-GU | `GroundFloorUnit` | GU → Join Curves по веткам | 25 |
| OS-BTP | `BottomTriangularPanel` | PA | 125 |
| OS-F | `Facade` | F → Bounding Box (union) | 1 |

## PROPERTY STATE — 11

| # | Rule (ID в графе) | DataProperty (из RULE DECONSTRUCT) | PropValue (выход скрипта, Flatten) | ObjState |
|---|---|---|---|---|
| R1 | `R_GLASS_ASPECTRATIO_MIN_1.3_V` | `hasAspectRatio` | AR | OS-GP |
| R2 | `R_GLASS_ASPECTRATIO_MAX_6_V` | `hasAspectRatio` | AR | OS-GP |
| R3 | `R_GEO_HEXUNIT_LEVELOFFSET_MAX_0_01_V` | `hasLevelOffsetM` | LO | OS-HU |
| R5 | `R_BTP_HASVERTEXCOUNT_REQ_3_V` | `hasVertexCount` | VC | OS-BTP |
| R6 | `R_GLASS_PLANARITYDEVIATION_MAX_0p005_V` | `hasPlanarityDeviationM` | PD | OS-GP |
| R7 | `R_GP_WIDTH_MIN_4.5_V` | `hasWidthM` | W | OS-GP |
| R8 | `R_FACADE_TOTALHEIGHT_MAX_120_V` | `hasTotalHeightM` | H | OS-F |
| R9 | `R_HEX_HASGAPCOUNT_MAX_0_V` | `hasGapCount` | HG | OS-HU |
| R10 | `R_GFU_HASGAPCOUNT_MAX_0_V` | `hasGapCount` | GG | OS-GU |
| R11 | `R_GF_HASVERTEXCOUNT_REQ_5_V` | `hasVertexCount` | GV | OS-GU |
| R12 | `R_HEX_HASVERTEXCOUNT_REQ_6_V` | `hasVertexCount` | HV | OS-HU |

## PARAMETER STATE, DESIGN STATE, VALIDATOR

- **PARAMETER STATE** — входы (ZUI «+»), NickName входа = ParameterId: `Module Width F1`, `Наклон чет сот`, `Наклон нечет сот` (по одному слайдеру на вход; Panel не поддерживается — находка F7).
- **DESIGN STATE** — `ObjState`: все 5 OBJECT STATE (Merge → Flatten); `ParamState`: PARAMETER STATE; `PropState`: все 11 PROPERTY STATE (Merge → Flatten); `DesignStateLabel`: `V1` … `V4`.
- **VALIDATOR** — `Rule`: METAGRAPH.Rules (11 → компонент вызовется 11 раз, один запуск = одно правило), `DesignState`: DESIGN STATE, `Token`: тот же `dgc_…` (вставить во вход, не через Panel), `SendValid` = False до проверки `Report`.

## Что собрано на холсте (2026-10-05, через RhinoCode)

Группа «DG v12 test wiring (Claude, 2026-10-05)», 50 объектов, начиная с (11700, 3500): GRAPH DECONSTRUCT, METAGRAPH, 16 × List Item (5 классов + 11 правил — индексы по алфавитному порядку `ObjectName` / `RuleName`), 2 × Join Curves (HU, GU), Bounding Box (Union Box), 5 × OBJECT STATE, 11 × RULE DECONSTRUCT, 11 × PROPERTY STATE, PARAMETER STATE (`Module Width F1`, `Наклон чет сот`, `Наклон нечет сот`), DESIGN STATE (метка `V1`), VALIDATOR (`SendValid` = False, токен не задан).

Проверено до исправления DG: METAGRAPH — 11 правил / 5 классов; OBJECT STATE 125 / 100 / 25 / 125 / 1; PROPERTY STATE 125 ×4, 100 ×3, 25 ×2, 125, 1 — всего 976; PARAMETER STATE — 3 параметра. DESIGN STATE отверг состав (F15) → исправлено в DG, требуется новый DG.gha.

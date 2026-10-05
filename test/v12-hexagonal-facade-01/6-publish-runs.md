# Шаг 6 — публикация V1–V4

Выполнено 2026-10-05 через RhinoCode: на вариант — слайдеры + метка Design State, один пересчёт с `SendValid` = True (11 запусков VALIDATOR), затем `SendValid` = False. После прогона: слайдеры V1, метка `V1`, `SendValid` = False. Публикация ≈ 195 с на вариант (≈ 18 с на запуск).

**Итог: 44/44 запуска совпали с матрицей** (провалились ровно ожидаемые правила с ожидаемым числом объектов; остальное PASS; предупреждений 0). В ValidGraph: 44 `ValidationRun` (`completed`, `SendStatus` = true, привязаны к Speckle), 3865 `ValidationEntity`.

| Вариант | Слайдеры | Design State | Состав | Провалы |
|---|---|---|---|---|
| V1 | F1 = 6000, чёт -1, нечёт +1 | `DS_09408DFEE843446F` | 376O/1P/976Pr | — |
| V2 | F1 = 4400, чёт -1, нечёт +1 | `DS_6FA0FBE79CCE3A22` | 421O/1P/1093Pr | R2 (12), R7 (57) |
| V3 | F1 = 10000, чёт -1, нечёт +1 | `DS_7BF84DAD65F82758` | 316O/1P/820Pr | R1 (4) |
| V4 | F1 = 6000, чёт -1, нечёт +0 | `DS_2891684FBED8B15F` | 376O/1P/976Pr | R6 (14) |

## ValidationRunId

| Правило | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| R1 `R_GLASS_ASPECTRATIO_MIN_1.3_V` | `ceb770f4` | `668a50ce` | ✗ `73e4d121` | `d55723c4` |
| R2 `R_GLASS_ASPECTRATIO_MAX_6_V` | `e06808eb` | ✗ `01feed8e` | `fd53ee2c` | `2a889070` |
| R3 `R_GEO_HEXUNIT_LEVELOFFSET_MAX_0_01_V` | `c022d023` | `c7ffd850` | `6078da56` | `1836fd18` |
| R5 `R_BTP_HASVERTEXCOUNT_REQ_3_V` | `38896991` | `94e5ba00` | `32e721bb` | `2052904c` |
| R6 `R_GLASS_PLANARITYDEVIATION_MAX_0p005_V` | `8c22f0db` | `5d75bc77` | `cbde3eb2` | ✗ `3db9eea3` |
| R7 `R_GP_WIDTH_MIN_4.5_V` | `bce301bf` | ✗ `5763d627` | `322d81e4` | `eb77329c` |
| R8 `R_FACADE_TOTALHEIGHT_MAX_120_V` | `df36c423` | `8cc8a5ad` | `cf539070` | `1effbf8e` |
| R9 `R_HEX_HASGAPCOUNT_MAX_0_V` | `53dd9615` | `a5021e61` | `914cbdd8` | `66c740cc` |
| R10 `R_GFU_HASGAPCOUNT_MAX_0_V` | `741dd79c` | `86d087e6` | `08f8e380` | `7b973bd4` |
| R11 `R_GF_HASVERTEXCOUNT_REQ_5_V` | `e6f41d23` | `5cee8c0c` | `a6e4c555` | `1e7f9ccf` |
| R12 `R_HEX_HASVERTEXCOUNT_REQ_6_V` | `bb9c0ca8` | `dd261202` | `67def1c0` | `4e808048` |

✗ — правило не прошло (ожидаемо по матрице). Полные id — в ValidGraph (`ValidationRun.runId`).

## Проверка `Run.ValidStatus` (исправление F16)

| Запуск | ObjState | true | Позиции true | Ожидание |
|---|---|---|---|---|
| R3 / V1 | 376 | 100 | 125…224 | модули `HexagonalUnit` (до F16 легли бы на слоты GlassPanel 0…99) |
| R7 / V2 | 421 | 83 | 35…139 | 140 панелей − 57 нарушителей, только слоты `GlassPanel` |
| R6 / V4 | 376 | 111 | 0…124 | 125 − 14 нарушителей, только слоты `GlassPanel` |

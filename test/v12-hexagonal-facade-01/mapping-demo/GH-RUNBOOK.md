# DG MAPPING в Grasshopper — runbook (Phase 1303, MVP-срез)

Компонент-прототип `DG MAPPING` (C# Script Rhino 8) отправляет в DG дескрипторы элементов фасада, показывает состояние меппинга цветом в Rhino и отдаёт геометрию по классам для OBJECT STATE. Пересборка DG.gha и перезапуск Rhino не нужны. Код: [`../gh-mapping-intake.cs`](../gh-mapping-intake.cs); контракт: `.planning/phases/1303-pravilo-gh-obekt/1303-API-CONTRACT.md`.

## 0. Подготовка (один раз)

1. Скопировать определение и модель, оригиналы не трогать:
   - `C:\Users\Admin\source\repos\design-grammar-system\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01.gh` → `C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01-mapping.gh`
   - то же для `.3dm` → `v12-hexagonal-facade-01-mapping.3dm`.
   Файлы `*.gh`/`*.3dm` в `.gitignore`, в коммит не попадут.
2. Открыть копию `.3dm` в Rhino 8, затем копию `.gh` в Grasshopper. Скрипты RhinoCode работают только с файлом, имя которого кончается на `-mapping.gh`.
3. **CONNECTOR.** В этом `.gh` стоит CONNECTOR до 1308 со старым токеном `dgc_` (выведен из обращения) — после 1308 он показывается как placeholder. Поставить текущий CONNECTOR, ввести Username / Password (не сохраняются в файле), Project = `v12-hexagonal-facade-01`, Connect. Выход `Session` даёт `dgk_…`. **Не выводить его в Panel.**
4. **Компонент.** Добавить C# Script (Rhino 8), никнейм `DG MAPPING`, создать параметры:

| Вход | Доступ | Тип | | Выход |
|---|---|---|---|---|
| `HU`, `GU`, `PB`, `PA`, `F`, `LZ` | Tree | без подсказки | | `SessionIdOut`, `Summary`, `Questions` |
| `OntoClasses` | List | без подсказки | | `Geometry`, `Colour`, `State`, `Roles`, `NativeId` |
| `Classes` | List | string | | `ByClass`, `ClassNames`, `ClassObjects` |
| `GuAsHu`, `Run`, `Refresh`, `Apply`, `DryRun` | Item | bool | | `Log` |
| `DefinitionKey`, `Project`, `Url`, `Token`, `Label`, `SessionId` | Item | string | | |

   Вставить тело из `gh-mapping-intake.cs` (сигнатура `RunScript` должна совпасть с параметрами).
5. **Проводка.** Запустить `"C:\Program Files\Rhino 8\System\RhinoCode.exe" script C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\mapping-demo\rhinocode\dgmap_wire.py` — скрипт подключит к `DG MAPPING` те же источники, что у скрипта замеров (`PB, HU, GU, PA, F, LZ`), `CONNECTOR.Session → Token`, `METAGRAPH.Objects → OntoClasses`, и задаст Project / Url / DefinitionKey / порядок `Classes`. Лог: `%TEMP%\dgmap-rhinocode.log`.
6. Добавить стандартный **Custom Preview**: Geometry ← `DG MAPPING.Geometry`, Material ← `DG MAPPING.Colour`.

Цвета: подтверждено `#2E7D32`, авто по профилю `#1565C0`, предложено `#F9A825`, неоднозначно `#E65100`, без меппинга `#9E9E9E` (как в Web UI).

## 1. Проверка без сети

`DryRun = True` → `Log` показывает JSON дескрипторов первых 50 элементов, `Summary` — счёт по потокам (V1: HU 100, GU 25, PB 125, PA 125, F 1). Классы в дескрипторы не попадают — только геометрия и имя потока (`source`).

## 2. Акты

| Акт | Команда | Ожидание |
|---|---|---|
| 1 холодный старт | `dgmap_run_act.py v1` | 2 вопроса: пакетное подтверждение 4 групп и «ошибка меппинга или проекта?» для 25 пятиугольников (GU отправлены как HU, F5) |
| — ответы | Web UI → Проекты → проект → Меппинг | ответить на вопросы |
| — обновление | `dgmap_run_act.py refresh` | цвета зелёные, `Questions = 0` |
| 2 обучение | `dgmap_run_act.py v2`, затем `v3` (и `v4`) | 0 вопросов, всё «авто по профилю»; нарушения R2/R7 (V2), R1 (V3), R6 (V4) — сигналы проекта, не вопросы |
| 4 валидация | `dgmap_run_act.py apply` | `ByClass` + `ClassObjects` подаются в 5 OBJECT STATE вместо индексных List Item; VALIDATOR даёт V1 11/11 PASS |

После каждого акта слайдеры возвращаются (флаг `--keep` оставляет вариант). Строки `EVIDENCE` в логе — материал протокола.

## 3. Подключение к OBJECT STATE (акт 4)

`ByClass` — ветка `{k}` = геометрия элементов класса `ClassNames[k]`, **в исходном порядке веток потока**, поэтому пары с PROPERTY STATE (по позиции) сохраняются. `ClassObjects[k]` — объект OntologyClass из METAGRAPH, найденный по имени/IRI (а не по индексу — индексные выборщики ломались после добавления классов A1). Каждому OBJECT STATE: Object ← `List Item(ClassObjects, k)`, Geometry ← `Tree Branch(ByClass, {k})`, порядок `k` задан входом `Classes`.

## Неполадки

| Симптом | Причина / действие |
|---|---|
| `Log`: `401 …` | CONNECTOR не вошёл или сессия истекла (8 ч) — Connect заново |
| `Log`: `403 PRINCIPAL_NOT_PERMITTED` | старый data-service без маршрутов `/mapping` — пересобрать (план 1303-06) |
| `Log`: `403 PROJECT_FORBIDDEN` / `PROJECT_MISMATCH` | CONNECTOR привязан к другому проекту |
| пустой `Summary`, ошибки веток | ветка с неподдерживаемой геометрией — см. `Log` |
| компоненты-placeholder | старые GUID (CONNECTOR до 1308) — заменить компонент |
| Rhino «подвисает» при Run | запрос синхронный, до 30 с; не держать Run включённым |

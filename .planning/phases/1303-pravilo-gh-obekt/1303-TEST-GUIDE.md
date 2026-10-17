# Инструкция по тестированию автоматизированного меппинга (Phase 1303, MVP-срез)

**Для кого:** владелец проекта, генеральная репетиция 18.10 перед демо 19.10.
**Что проверяем:** меппинг элементов фасада `v12-hexagonal-facade-01` из Grasshopper и Revit на классы DG — с групповыми вопросами, обучаемыми профилями и проверкой правилами.
**Время:** около 1,5–2 часов на полный прогон.

**Где всё лежит:** рабочая папка `C:\Users\Admin\source\repos\dg-mapping` (ветка `feature/mapping-mvp`). Основная папка `design-grammar-system` и работа 1309 не затрагиваются — в ней ничего не открывать и не менять, кроме чтения исходных файлов фасада в шаге 2.1.

Что уже сделано и проверено без вас: движок, маршруты `/mapping/*`, панель «Меппинг», чтение Revit, компонент для Grasshopper; локальный стек пересобран и запущен; генеральная проверка движка на реальных правилах проекта дала ожидаемые 2 вопроса. Не проверено вживую: Rhino, Revit, браузер и запись в граф — это и есть этот прогон.

---

## Шаг 0. Стек запущен (5 минут)

1. Docker Desktop запущен (иконка кита в трее не красная).
2. Откройте http://localhost:8080 — загружается главная страница SVOD.
3. Если позже панель «Меппинг» покажет «Меппинг недоступен» или ошибку 502 — в PowerShell:
   ```powershell
   docker start data-service
   ```
   подождите 20 секунд и обновите страницу с очисткой кэша (Ctrl+Shift+R). Причина: data-service стартует раньше Neo4j и останавливается; повторный старт решает.

## Шаг 1. Панель «Меппинг» в Web UI (3 минуты)

1. Войдите своей учётной записью.
2. «Проекты» → выберите `v12-hexagonal-facade-01` → прокрутите вниз → раскройте **«Меппинг»**.
3. **Ожидаемо:** «Сессий меппинга пока нет · импортируйте файл дескрипторов, чтобы начать».
4. Переключите язык (RU/EN, вверху справа) — подписи панели меняются.

## Шаг 2. Подготовка Grasshopper (15–20 минут)

### 2.1 Копия определения (оригинал не трогаем)

```powershell
Copy-Item "C:\Users\Admin\source\repos\design-grammar-system\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01.3dm" "C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01-mapping.3dm"
Copy-Item "C:\Users\Admin\source\repos\design-grammar-system\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01.gh" "C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\v12-hexagonal-facade-01-mapping.gh"
```

Откройте копию `.3dm` в Rhino 8, затем копию `.gh` в Grasshopper. Имя файла должно кончаться на `-mapping.gh` — скрипты автоматизации работают только с ним.

### 2.2 CONNECTOR

В этом определении стоит старый CONNECTOR (до 1308) со старым токеном — он больше не работает и может отображаться как «пустой» компонент.

1. Поставьте текущий **CONNECTOR** из вкладки DG. Если его нет в палитре — установлен старый DG.gha; скажите мне, я подготовлю установку.
2. Введите Username, Password, Project = `v12-hexagonal-facade-01`, нажмите Connect. Выход `Session` должен стать непустым. **Не подключайте к нему Panel** (токен не должен попасть в файл).
3. Переподключите выходы нового CONNECTOR вместо старого: `Database` → GRAPH DECONSTRUCT, `Session` → вход `Token` у VALIDATOR (старую панель с токеном удалите).
4. METAGRAPH → Refresh: в списке классов есть GlassPanel, HexagonalUnit, GroundFloorUnit, BottomTriangularPanel, Facade.

### 2.3 Компонент DG MAPPING

1. Добавьте компонент **C# Script** (Rhino 8), переименуйте в `DG MAPPING`.
2. Создайте параметры (правый клик по параметру → доступ и тип):

| Входы | Доступ | Тип |
|---|---|---|
| `HU`, `GU`, `PB`, `PA`, `F`, `LZ` | Tree | без подсказки |
| `OntoClasses` | List | без подсказки |
| `Classes` | List | string |
| `GuAsHu`, `Run`, `Refresh`, `Apply`, `DryRun` | Item | bool |
| `DefinitionKey`, `Project`, `Url`, `Token`, `Label`, `SessionId` | Item | string |

   Выходы: `SessionIdOut`, `Summary`, `Questions`, `Geometry`, `Colour`, `State`, `Roles`, `NativeId`, `ByClass`, `ClassNames`, `ClassObjects`, `Log`.
3. Откройте редактор, замените весь код содержимым файла `C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\gh-mapping-intake.cs`, закройте редактор. Если Rhino предложит обновить параметры по сигнатуре кода — согласитесь.

### 2.4 Подключение — одной командой

Откройте PowerShell и не закрывайте его до конца прогона. Первые две строки задают сокращения `$rc` (RhinoCode) и `$dg` (папка скриптов) — ими пользуются все команды ниже. В новом окне PowerShell выполните эти две строки снова.

```powershell
$rc = "C:\Program Files\Rhino 8\System\RhinoCode.exe"
$dg = "C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\mapping-demo\rhinocode"
& $rc script "$dg\dgmap_wire.py"
Get-Content "$env:TEMP\dgmap-rhinocode.log" -Tail 15
```

RhinoCode не передаёт скрипту параметры, поэтому у каждого действия свой файл: `dgmap_act_v1.py` … `dgmap_act_v4.py`, `dgmap_refresh.py`, `dgmap_apply.py`, `dgmap_act_validate_v1.py`, `dgmap_reset_v1.py`.

**Ожидаемо:** в конце лога `wire: done` и `OK`. Скрипт подключает к DG MAPPING те же источники, что у скрипта замеров (`HU, GU, PB, PA, F, LZ`), `CONNECTOR.Session → Token`, `METAGRAPH.Objects → OntoClasses`, и задаёт проект, адрес и порядок классов. Если в логе `FAILED` — пришлите мне последние строки. (Первый запуск RhinoCode после паузы иногда ничего не делает — просто повторите.)

### 2.5 Цвет в Rhino

Добавьте стандартный **Custom Preview**: Geometry ← `DG MAPPING.Geometry`, Material ← `DG MAPPING.Colour`.
Цвета: зелёный — подтверждено, синий — авто по профилю, жёлтый — предложено, оранжевый — неоднозначно, серый — без меппинга.

### 2.6 Проверка без сети

Включите `DryRun` (Boolean Toggle) → в `Summary` видно `elements: 376`, в `Log` — JSON первых элементов (только геометрия и имя потока, классов там нет). Выключите `DryRun`.

## Шаг 3. Акт 1 — холодный старт (10 минут)

Скрипт акта сам выставляет слайдеры варианта (`Module Width F1`, `Наклон нечет сот`) и оставляет вариант на холсте, чтобы были видны цвета. Если акт упал, слайдеры возвращаются к прежним значениям. Вернуть V1 без запроса в DG: `& $rc script "$dg\dgmap_reset_v1.py"`.

1. Запуск:
   ```powershell
   & $rc script "$dg\dgmap_act_v1.py"
   Get-Content "$env:TEMP\dgmap-rhinocode.log" -Tail 5
   ```
   (все 125 контуров модулей уходят одним потоком HU — так было до исправления F5). В логе — строка `EVIDENCE` с `sessionId` и `OK`.
2. **Ожидаемо в Grasshopper:** `Questions = 2`; 25 пятиугольников оранжевые, остальное жёлтое. Rhino может «задуматься» на несколько секунд — это запрос к DG.
3. **Web UI → «Меппинг» → «Обновить»**, выберите сессию `act1-cold-start-v1`. Две карточки:
   - «4 группы (351 элемент) имеют один очевидный класс…» → нажмите **«Принять все предложенные классы»**;
   - «25 элементов из HU (5 вершин). Как HexagonalUnit: R_HEX_HASVERTEXCOUNT_REQ_6_V нарушено ×25 … Как GroundFloorUnit: … выполняется ×25. Это ошибка меппинга или ошибка проекта?» → нажмите **«GroundFloorUnit»**.
4. **Ожидаемо:** «Подтверждено 376», «Открытых вопросов: 0», в таблице «Профили» — 5 строк «Выучен» с вашим именем и датой.
5. Обновите состояние в Grasshopper:
   ```powershell
   & $rc script "$dg\dgmap_refresh.py"
   ```
   → всё зелёное, `Questions = 0`.
6. **Запишите id сессии** (выход `SessionIdOut`, вида `ms-…`, или строка `EVIDENCE` в логе) — он нужен в шаге 5.

## Шаг 4. Акт 2 — обучение (5–10 минут)

По одному скрипту на вариант. После каждого посмотрите на Rhino и нажмите «Обновить» в Web UI:

```powershell
& $rc script "$dg\dgmap_act_v2.py"
& $rc script "$dg\dgmap_act_v3.py"
& $rc script "$dg\dgmap_act_v4.py"
```

(V4 — по желанию.)

**Ожидаемо:** `Questions = 0`, всё синее (авто по профилю), в Web UI новые сессии `act2-learned-v2` / `-v3` / `-v4` без вопросов. На холсте остаётся последний запущенный вариант: у V2 узкие соты и 140 модулей, у V3 широкие и 105. Профили узнают новую геометрию. Нарушения правил (V2: R2 ×12, R7 ×57; V3: R1 ×4; V4: R6 ×14) **не** превращаются в вопросы, потому что это ошибки проекта, а не меппинга.

## Шаг 5. Акт 3 — Revit, только чтение (15 минут)

1. Откройте модель фасада в Revit 2024 (pyRevit с расширением DeGram). Проверка в браузере: http://127.0.0.1:48884/revit_mcp/status/ отвечает JSON.
2. Выделите элементы фасада (модули и панели; до 1000 элементов). Окно модели фасада должно быть активным.
3. В PowerShell:
   ```powershell
   cd C:\Users\Admin\source\repos\dg-mapping
   python tools\mapping\revit_read.py --out test\v12-hexagonal-facade-01\mapping-demo\evidence\act3-revit-read1.json --label act3-revit-read1 --populations-from ms-XXXXXXXXXXXX
   ```
   (`ms-XXXXXXXXXXXX` — id сессии из шага 3.6). Скрипт печатает число элементов по семействам. В Revit ничего не записывается.
4. **Если имена семейств осмысленные** (например, `Hex…`, `Pent…`, `Glass…`, `Tri…`): скопируйте `test\v12-hexagonal-facade-01\mapping-demo\vocabulary.example.json` в `vocabulary.json` рядом, впишите слова из реальных имён семейств и повторите команду с `--vocabulary test\v12-hexagonal-facade-01\mapping-demo\vocabulary.json`. Можно прислать мне вывод скрипта — я подготовлю словарь.
5. Web UI → «Меппинг» → **«Импорт дескрипторов (JSON)»** → выберите файл → «Создать сессию».
6. **Ожидаемо:** вопросы по группам семейств (не больше одного на группу). Категория у всех Generic Models, IFC не различает классы — это и показываем. Отвечайте правильным классом; для шестиугольных модулей, если предложено, — **«Обе роли»** (HexagonalUnit + FacadeModule).
7. Повторите шаги 3–5 с `--label act3-revit-read2` и файлом `act3-revit-read2.json`. **Ожидаемо:** 0 вопросов, всё «авто по профилю».

## Шаг 6. Акт 4 — проверка правилами (15 минут)

1. Возврат холста в V1 и новый прогон с меткой `act4-validate-v1` (теперь V1 размечается профилями без вопросов), затем «Применить»:
   ```powershell
   & $rc script "$dg\dgmap_act_validate_v1.py"
   & $rc script "$dg\dgmap_apply.py"
   Get-Content "$env:TEMP\dgmap-rhinocode.log" -Tail 5
   ```
2. **Ожидаемо:** `ClassNames` = GlassPanel, HexagonalUnit, GroundFloorUnit, BottomTriangularPanel, Facade; в `ByClass` 5 веток (125 / 100 / 25 / 125 / 1).
3. Для каждого из 5 OBJECT STATE: `Object` ← List Item(`ClassObjects`, k), `Geometry` ← Tree Branch(`ByClass`, {k}), где k = 0…4 по порядку `ClassNames`. Классы подбираются по имени, а не по индексу — сломавшиеся раньше индексные выборщики больше не нужны.
4. VALIDATOR (`SendValid` = False) → `Report`. **Ожидаемо:** V1 — 11 из 11 правил пройдены.

## Шаг 7. Что сохранить и прислать мне

- Скриншоты: две карточки вопросов (шаг 3), прогресс и профили после ответов, Rhino до/после (оранжевый → зелёный), Revit-сессия, VALIDATOR Report.
- Лог `%TEMP%\dgmap-rhinocode.log` (строки `EVIDENCE`).
- Файлы `act3-revit-read*.json` уже лежат в `mapping-demo\evidence`.
- Где что не совпало с «Ожидаемо» — номер шага и текст ошибки.

По этим материалам я заполню протокол (`mapping-demo\PROTOCOL.md`) и чек-лист `1303-UAT.md`.

## Если что-то пошло не так

| Симптом | Что сделать |
|---|---|
| 502 или «Меппинг недоступен» | `docker start data-service`, через 20 с Ctrl+Shift+R |
| В `Log` компонента `401` | CONNECTOR → Connect заново (сессия живёт 8 часов) |
| В `Log` `403 PRINCIPAL_NOT_PERMITTED` или `ROUTE_UNCLASSIFIED` | работает старый образ data-service — сообщите мне |
| `Questions = -1` | сессии ещё нет: не нажат Run или ошибка запроса — смотрите `Log` |
| В логе RhinoCode `refusing to run` | в Grasshopper открыт не тот файл — нужна копия `…-mapping.gh` |
| В логе RhinoCode `FAILED` (`no number slider`, `expected exactly one object`, `wrapper FAILED`) | пришлите мне последние 20 строк лога; холст при этом возвращён к прежним слайдерам |
| После RhinoCode в логе ничего нового | первый запуск после паузы иногда пропадает — повторите команду |
| Импорт файла: ошибка 413 / слишком большой | повторите `revit_read.py` с `--max-parameters 15` |
| `revit_read.py`: `BRIDGE_OFF` | Revit закрыт или pyRevit Routes / расширение не загружены |
| `revit_read.py`: `IDENTITY_MISMATCH` | сделайте окно модели фасада активным |
| `revit_read.py`: «selection is empty» | выделите элементы фасада и повторите |
| Компоненты-«пустышки» на холсте | старые GUID — замените компонент текущим |

## Откат (только если нужно вернуть версию 1308)

```powershell
docker tag design-grammar-system-data-service:pre-1303 design-grammar-system-data-service
docker tag design-grammar-system-design-grammars:pre-1303 design-grammar-system-design-grammars
docker compose -p design-grammar-system -f C:\Users\Admin\source\repos\design-grammar-system\docker-compose.yml --project-directory C:\Users\Admin\source\repos\design-grammar-system up -d --no-build --no-deps data-service design-grammars
```

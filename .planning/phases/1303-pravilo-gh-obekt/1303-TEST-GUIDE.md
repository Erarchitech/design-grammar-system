# Инструкция по тестированию автоматического меппинга (Phase 1303, MVP-срез)

**Для кого:** владелец проекта, репетиция 18.10 перед демо 19.10.
**Что проверяем:** DG сам предлагает меппинг элементов фасада `v12-hexagonal-facade-01` из Grasshopper и Revit на классы DG, а слайдеров — на свойства DG. Подтверждение — групповыми вопросами в Web UI, дальше работают обучаемые профили и проверка правилами.
**Время:** около 1–1,5 часа.

**Что изменилось (18.10, план 1303-08):** компонент C# Script, проводка и Custom Preview больше не нужны. Меппинг встроен в **CONNECTOR**: после входа он сам читает холст. Элементы — это геометрия, подключённая к OBJECT STATE. Учитываются названия групп, тексты scribble, имена компонентов и класс, уже выбранный в OBJECT STATE. Именованные слайдеры тоже идут в меппинг. CONNECTOR отправляет сессию в DG, раскрашивает элементы в Rhino, следит за ответами и сам применяет меппинг, когда вопросов не осталось.

**Где всё лежит:** рабочая папка `C:\Users\Admin\source\repos\dg-mapping` (ветка `feature/mapping-mvp`). Основная папка и работа 1309 не затрагиваются.

**Уже сделано без вас:**
- стек пересобран из коммитов `6014cbc`…`efc3e3a`;
- новый DG.gha установлен в `%APPDATA%\Grasshopper\Libraries\DG`, старая версия сохранена в `%LOCALAPPDATA%\DG\plugin-backups\pre-1303-08-20261018-085637`;
- Rhino открыт с копиями `v12-hexagonal-facade-01-mapping.3dm` и `.gh`;
- пробное чтение этого холста без отправки дало 376 элементов в 5 потоках и 14 именованных слайдеров;
- расчёт на реальном графе проекта дал 6 вопросов (ниже).

**Вживую не проверено:** вход CONNECTOR, создание сессии из Rhino, цвета, ответы в браузере, применение. Это и есть этот прогон.

---

## Шаг 0. Стек (2 минуты)

1. Docker Desktop запущен. Откройте http://localhost:8080 — загружается SVOD.
2. Если панель «Меппинг» покажет ошибку 502 или «Меппинг недоступен», выполните в PowerShell `docker start data-service` и через 20 с обновите страницу (Ctrl+Shift+R).

## Шаг 1. Панель «Меппинг» (1 минута)

Войдите в Web UI → «Проекты» → `v12-hexagonal-facade-01` → раскройте **«Меппинг»**. **Оставьте панель открытой:** она сама подхватывает новые сессии, приходящие из Grasshopper (раз в 5 секунд).

## Шаг 2. Вход в CONNECTOR — меппинг стартует сам (3 минуты)

1. В Rhino открыта копия `v12-hexagonal-facade-01-mapping.gh`. Если Rhino закрыт, откройте `test\v12-hexagonal-facade-01\v12-hexagonal-facade-01-mapping.3dm`, затем `.gh` из папки `dg-mapping`.
2. На **CONNECTOR** введите Username и Password, Project = `v12-hexagonal-facade-01`, затем Connect = True. Вход `AutoMap` по умолчанию включён. **К выходу `Session` не подключайте Panel.**
3. **Ожидаемо через 3–5 секунд:**
   - сообщение на CONNECTOR: «Connected · Signed in · Map: 6?»;
   - в Rhino элементы раскрашены: оранжевый — неоднозначно, жёлтый — предложено;
   - в Web UI появилась сессия `v12-hexagonal-facade-01-mapping · ЧЧ:ММ:СС` с **6 вопросами** и таблицей «Слайдеры».
4. Выход `Mapping` у CONNECTOR (можно подключить Panel) показывает сводку: элементы, слайдеры, открытые вопросы, потоки.

## Шаг 3. Акт 1 — ответы (10 минут)

Вопросы показывают реальные ошибки подключения. Индексные List Item сдвинулись, и в OBJECT STATE стоят не те классы. Отвечайте так:

| Вопрос (кратко) | Что увидите | Ответ |
|---|---|---|
| 125 элементов из **Panels B** (4 вершины) | GlassPanel 0.99 / FacadeModule 0.88 — «OS GlassPanel» подключён к FacadeModule | **GlassPanel** (или «Обе роли») |
| 100 элементов из **join HU** (6 вершин) — «ошибка меппинга или проекта?» | как GroundFloorUnit нарушено R11 ×100, как HexagonalUnit всё выполняется | **HexagonalUnit** |
| 25 элементов из **join GU** (5 вершин) | GroundFloorUnit / GlassPanel — «OS GroundFloorUnit» подключён к GlassPanel | **GroundFloorUnit** |
| 1 элемент из **bbox F** | Facade / FacadeModule / Corridor — «OS Facade» подключён к Corridor | **Facade** |
| 125 из **Panels A** → BottomTriangularPanel | пакетное подтверждение | **«Принять все предложенные классы»** |
| 5 слайдеров «Module Width F1 … F5» | похожи на свойство DG hasWidthM (GlassPanel) | **hasWidthM** |

**Ожидаемо:**
- цвета в Rhino становятся зелёными: CONNECTOR проверяет сессию каждые 3 с;
- после последнего ответа CONNECTOR сам применяет меппинг: сообщение «· Map ✓», выход `ClassNames` = BottomTriangularPanel, Facade, GlassPanel, GroundFloorUnit, HexagonalUnit, `ByClass` — 5 веток (125 / 1 / 125 / 25 / 100);
- в Web UI в таблице «Профили» появились выученные профили (классы и слайдер), в таблице «Слайдеры» Module Width F1…F5 → hasWidthM «Подтверждено».

**Запишите id сессии** (`ms-…`, в Web UI или в выходе `Mapping`) — он нужен в шаге 5.

## Шаг 4. Акт 2 — обучение на вариантах (5 минут)

В PowerShell (одно окно до конца):

```powershell
$rc = "C:\Program Files\Rhino 8\System\RhinoCode.exe"
$dg = "C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\mapping-demo\rhinocode"
& $rc script "$dg\dgmap_act_v2.py"
```

Скрипт только выставляет слайдеры варианта. **Через несколько секунд CONNECTOR сам отправляет новое состояние, и в Web UI появляется новая сессия.** Ожидаемо: 0 вопросов, всё синее (авто по профилю), Module Width → hasWidthM «Авто по профилю». Нарушения правил (V2: R2 ×12, R7 ×57) — сигналы проекта, а не вопросы. Затем так же `dgmap_act_v3.py` (R1 ×4) и по желанию `dgmap_act_v4.py` (R6 ×14).

`& $rc script "$dg\dgmap_refresh.py"` записывает в `%TEMP%\dgmap-rhinocode.log` то, что показывает CONNECTOR (строка `EVIDENCE`). Вернуть V1: `& $rc script "$dg\dgmap_reset_v1.py"`. RhinoCode не передаёт скрипту параметры, поэтому у каждого действия свой файл. Первый запуск после паузы иногда проходит вхолостую — тогда повторите.

## Шаг 5. Акт 3 — Revit, только чтение (15 минут)

1. Откройте модель фасада в Revit 2024 (pyRevit с расширением DeGram). Проверка: http://127.0.0.1:48884/revit_mcp/status/ отвечает JSON.
2. Выделите элементы фасада (до 1000), окно модели фасада активно.
3. В PowerShell (`ms-XXXXXXXXXXXX` — id сессии из шага 3):
   ```powershell
   cd C:\Users\Admin\source\repos\dg-mapping
   python tools\mapping\revit_read.py --out test\v12-hexagonal-facade-01\mapping-demo\evidence\act3-revit-read1.json --label act3-revit-read1 --populations-from ms-XXXXXXXXXXXX
   ```
   Скрипт печатает число элементов по семействам. В Revit ничего не записывается.
4. Если имена семейств осмысленные (`Hex…`, `Glass…`), скопируйте `mapping-demo\vocabulary.example.json` в `vocabulary.json`, впишите слова из реальных имён и повторите команду с `--vocabulary test\v12-hexagonal-facade-01\mapping-demo\vocabulary.json`.
5. Web UI → «Меппинг» → **«Импорт дескрипторов (JSON)»** → файл → «Создать сессию». Ожидаемо: вопросы по группам семейств. Повторное чтение (`act3-revit-read2`) — 0 вопросов.

## Шаг 6. Акт 4 — проверка правилами (10 минут, по желанию)

Индексные выборщики классов перед OBJECT STATE сейчас дают не те классы. Замените их выходами CONNECTOR:
- для каждого из 5 OBJECT STATE: `Object` ← List Item(`CONNECTOR.ClassObjects`, k), `Geometry` ← Tree Branch(`CONNECTOR.ByClass`, {k});
- k по порядку `ClassNames`: 0 BottomTriangularPanel, 1 Facade, 2 GlassPanel, 3 GroundFloorUnit, 4 HexagonalUnit.

CONNECTOR увидит новое подключение и создаст ещё одну сессию, на этот раз без вопросов. VALIDATOR (`SendValid` = False) → `Report`: на V1 ожидается 11 из 11 правил пройдены.

## Шаг 7. Что сохранить и прислать мне

- Скриншоты: CONNECTOR с сообщением «Map: 6?», цвета в Rhino до и после ответов, вопросы и таблицы «Слайдеры» и «Профили» в Web UI, сессия варианта V2 без вопросов, Revit-сессия, VALIDATOR Report.
- Текст выхода `Mapping` CONNECTOR и лог `%TEMP%\dgmap-rhinocode.log`.
- Где результат не совпал с «Ожидаемо»: номер шага и текст.

## Если что-то пошло не так

| Симптом | Что сделать |
|---|---|
| 502 или «Меппинг недоступен» | `docker start data-service`, через 20 с Ctrl+Shift+R |
| CONNECTOR «Map !», в выходе `Mapping` «DG refused the session (401 …)» | вход истёк — Connect = False, затем True |
| `Mapping` «403 PROJECT_FORBIDDEN» | CONNECTOR привязан к другому проекту — проверьте Project |
| Сессия не появилась в Web UI | нажмите «Обновить» в панели; проверьте выход `Mapping` у CONNECTOR |
| Слишком много сессий при перетаскивании слайдера | так задумано: сессия создаётся после 1,5 с покоя холста; можно временно выключить `AutoMap` |
| В логе RhinoCode `refusing to run` | открыт не тот файл — нужна копия `…-mapping.gh` |
| Компоненты-«пустышки» на холсте | старые GUID — замените компонент текущим |

## Откат

- **Плагин:** закройте Rhino и скопируйте файлы из `%LOCALAPPDATA%\DG\plugin-backups\pre-1303-08-20261018-085637` обратно в `%APPDATA%\Grasshopper\Libraries\DG`.
- **Стек (версия 1308):**
  ```powershell
  docker tag design-grammar-system-data-service:pre-1303 design-grammar-system-data-service
  docker tag design-grammar-system-design-grammars:pre-1303 design-grammar-system-design-grammars
  docker compose -p design-grammar-system -f C:\Users\Admin\source\repos\design-grammar-system\docker-compose.yml --project-directory C:\Users\Admin\source\repos\design-grammar-system up -d --no-build --no-deps data-service design-grammars
  ```
- **Запасной путь:** прототип `gh-mapping-intake.cs` (C# Script) лежит в `test\v12-hexagonal-facade-01`.

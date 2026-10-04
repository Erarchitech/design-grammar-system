# Full-cycle test: v12-hexagonal-facade-01

Ручной сквозной тест Design Grammars v12 на параметрическом гексагональном фасаде: правила → Metagraph → Grasshopper Design States → VALIDATOR → Model Viewer → переключение Design States через PARAMETER REINSTATE.

| | |
|---|---|
| DG-проект | `v12-hexagonal-facade-01` |
| Версия системы | v12.0 (Phase 1205 security gate + Phase 1205.1 evidence v2), развёрнута |
| Модель | [v12-hexagonal-facade-01.gh](v12-hexagonal-facade-01.gh) (мм) |
| Правила | [RULES.md](RULES.md) · [rules-approved.json](rules-approved.json) |
| Инвентарь модели | [model-inventory.md](model-inventory.md) |

## Артефакты в этой папке

Все артефакты теста сохраняются здесь: правила, снимки состояния Neo4j после ввода, выходы VALIDATOR (`Report`, `FailingBindings`, `SendStatus`, `ValidationRunId`), скриншоты Model Viewer, журнал находок. Токены (`dgc_…`) и пароли сюда **не** записываются.

## Шаги

| # | Шаг | Где | Статус |
|---|---|---|---|
| 0 | Актуальный DG.gha (Release, SHA256 совпадает со сборкой) | Rhino | ✅ 2026-10-01 |
| 1 | Вход в UI, создание проекта | UI → Projects | ✅ 2026-10-01 |
| 2 | Токен Grasshopper для проекта | UI → Connectors | ⏳ |
| 3a | Посчитать величины правил в GH на базовом варианте, снять min/max | Grasshopper | ⏳ |
| 3b | Финализировать пороги по V1 (V1 проходит все правила с запасом) | RULES.md | ⏳ |
| 3c | Ввести 8 правил по одному, после каждого — сверка SWRL в Neo4j | UI → Graph (Ingest) | ⏳ |
| 4 | Назвать вариативные слайдеры (уникальные NickName) | Grasshopper | ⏳ |
| 5 | Подключить DG: CONNECTOR → GRAPH DECONSTRUCT → METAGRAPH → RULE DECONSTRUCT; 4 × OBJECT STATE; PARAMETER STATE; 8 × PROPERTY STATE; DESIGN STATE; VALIDATOR | Grasshopper | ⏳ |
| 6 | Варианты V1–V4: захват Design State, валидация, публикация | Grasshopper | ⏳ |
| 7 | Design States и результаты в Model Viewer | UI → Model | ⏳ |
| 8 | Переключение Design States: VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → PARAMETER REINSTATE | Grasshopper | ⏳ |
| 9 | Контрольное правило A1 → ожидается `unsupported` | UI + GH | ⏳ |

Порядок 3a → 3b → 3c изменён относительно исходного плана сознательно: в модели нет слайдеров этажности и числа модулей, поэтому пороги надо калибровать по реально посчитанным величинам до ввода правил, иначе V1 может не пройти собственные правила.

## Матрица ожидаемых результатов (черновик — уточняется после 3a)

| Правило | V1 Baseline | V2 Узкие соты | V3 Широкие соты | V4 Искажённые соты |
|---|---|---|---|---|
| R1 `ASPECT_MIN_2` | passed | passed | **failed** | ? |
| R2 `ASPECT_MAX_4` | passed | **failed** | passed | ? |
| R3 `LEVELOFFSET_MAX_001` | passed | passed | passed | **failed** |
| R4 `SYMMETRY_MAX_001` | passed | passed | passed | **failed** |
| R5 `VERTEXCOUNT_EQ_3` | passed | passed | passed | passed |
| R6 `PLANARITY_MAX_0005` | passed | ? | ? | **failed** |
| R7 `WIDTH_MIN_09` | passed | **failed** | passed | passed |
| R8 `HEIGHT_MAX_50` | passed | passed | passed | passed |

Драйверы вариантов (предварительно): V2/V3 — ширина соты; V4 — `Наклон чет сот` / `Наклон нечет сот` (асимметрично) и `Выступ панелей`. Тест считается пройденным, если DG показывает **именно** ожидаемые провалы, без лишних `failed`, `unknown` или `no_population`.

## Журнал

- **2026-10-01** — стек v12 поднят (15 контейнеров). Найден устаревший DG.gha (26 июля, до v12: CONNECTOR без входа `Platform Token`); пользователь пересобрал и развернул Release — SHA256 совпадает. Проект создан, правил 0. LLM-шлюз: провайдер `openai`. Speckle: токены записи/чтения сохранены, проект/базовая модель по умолчанию заданы в окружении (автопривязка при первой публикации).
- **2026-10-03** — набор правил утверждён: 6 исходных правил разобраны против вычислителя v12; D1 разделено на два правила (нижний порог 2, верхний 4 — тело SWRL не допускает «ИЛИ»); B1/B2 переведены в числовые отклонения; C1 заменено проверкой числа вершин (строки PROPERTY STATE не передаёт); A1/A2 исключены как порождающие (A1 — контрольное). Добавлены планарность, мин. ширина панели, высота фасада. Инвентарь слайдеров снят из `.gh`.

## Находки (кандидаты в knowledge/debugging)

| # | Находка | Влияние на тест |
|---|---|---|
| F1 | `docs/UPDATED_SYSTEM_SETUP_AND_TEST.md` устарел (CLASSIFICATOR, Neo4j user/password в CONNECTOR, `ValidationGraph`, legacy Model Viewer) | гайд не используется; шаги ведутся по этому README |
| F2 | В V2 UI нет формы привязки DG-проекта к Speckle-проекту/модели (была в legacy UI); остаётся только `PUT /integration/speckle/project/{project}` (owner) или автопривязка из env | при первой публикации проект привяжется к базовой модели по умолчанию из env |
| F3 | Для вычисленной (не referenced) геометрии OBJECT STATE с классом-broadcast даёт `ObjectRef = obj_0…obj_n` по индексу; у разных классов идентификаторы пересекаются | наблюдать в Model Viewer: каждый запуск VALIDATOR = одно правило = один класс, поэтому коллизия внутри запуска не ожидается |

---
session_date: 2026-09-19
phase: v9.0 AI Workflow Intelligence
focus: semantic rule deletion via LLM selection
---

## Сессия: T1 — семантическое удаление правил по условиям

### Задача
Расширить удаление правил с простого поиска по Rule_Id на условные формулировки вроде «удали все правила по высоте выше 50 м». Раньше это требовало либо regex (неподходит для сравнений), либо давало LLM писать деструктивный Cypher (T-29-01).

### Решение
Разделил задачу на две части:
1. **LLM только выбирает** (возвращает JSON с подходящими Rule_Ids, Cypher не пишет)
2. **Сервер удаляет** (фиксированный параметризованный запрос, тот же что для одного правила)

Выдуманный LLM Rule_Id безвреден: не совпадёт с реальным и попадёт в `hallucinated`, показывается пользователю, но не выполняется.

### Что реализовано

**Бэкенд** (`data-service`):
- `dg_context.py`: `select_rules_for_deletion()` отправляет LLM каталог правил, получает JSON с `ruleIds + reason`
- Parser `_parse_selection_response()` терпит code-fence, встроенный JSON, изолирует выдуманные id
- `app.py`: 
  - `POST /rules/resolve-deletion` — выбор (read-only)
  - `POST /rules/bulk-delete` — удаление подтверждённых id (parameterized, no interpolation)
- 18 новых тестов в `test_rule_deletion.py` (parsing, safety, race conditions)
- 764 тестов backend проходят

**Фронтенд** (`ui-v2`):
- `GraphScreen.jsx`: Edit-мод распознаёт `delete|remove|drop|удали…` в начале промпта
  - Если одно явное `R_…` — без LLM
  - Иначе → resolver
  - Диалог показывает каждое правило с SWRL, preview удаления, hallucinated-id отдельно
- `graphApi.js`: `resolveRuleDeletion()` и `bulkDeleteRules()`

### Проверено на живых данных

Проект: `URBAN_BLOCK_V8` с 4 правилами (высота 45, 60, 90 и площадь 28).

| Промпт | Выбрано |
|---|---|
| `удали все правила по высоте выше 50 метров` | **60, 90** (45 исключено) |
| `delete all height rules` | 45, 60, 90 |
| `remove the rule about apartment area` | 28 |

Ключевой результат: первый запрос требует семантического сравнения `50` с числом в каждом Rule_Id и SWRL. Regex это недостижимо, LLM решает.

Полный прогон через nginx:
1. resolve-deletion → 2 совпадения + по preview каждого
2. Диалог подтверждает
3. bulk-delete → удалены 60 и 90
4. 45 и площадь целы, все atoms и shared literals на месте

### Оговорки

**Намерение delete/remove** по-прежнему regex: `^delete|remove|drop|удали…`. Фраза вроде «а можно ли убрать правила по высоте?» не подойдёт. Мог бы дать это LLM, но это лишний вызов на каждый Edit-промпт.

**Пользователь видит список перед удалением**: диалог с SWRL, orphan/shared списки. Защита от ошибки выбора модели — но список нужно читать внимательно.

**Образы не обновлены**: `data-service` — в контейнер скопирован, UI пересобран. Для пересборки нужен `docker compose build data-service`.

### Коммит

```
feat: semantic rule deletion — LLM-selected conditional deletion with safe orphan handling
```

Файлы в коммите:
- `data-service/app.py` — resolve-deletion, bulk-delete endpoints
- `data-service/dg_context.py` — select_rules_for_deletion, parser
- `data-service/tests/test_rule_deletion.py` — 18 новых тестов
- `ui-v2/src/screens/GraphScreen.jsx` — Edit-мод, диалог, resolver
- `ui-v2/src/lib/graphApi.js` — API layer

### Дальше

В проекте осталось 2 тестовых правила (площадь и высота 45), созданные мной. Пользователь может удалить либо через UI, либо оставить.

T-29-01 (запрет на деструктивный Cypher от LLM) остаётся в силе: LLM выбирает id только, сервер удаляет.

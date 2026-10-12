// screens area dictionary: the LLM model, Reasoner, DG API Docs and DeGram grants screens and the lib-level messages
// (plan 1308-16). `ru` maps English text to Russian, `en` holds only tp() plural tables (English is otherwise the key).
// Wording follows the 1301-D38 glossary; proper nouns (HermiT, Pellet, provider names) stay Latin (D-13).
// "Back", "Cancel" and "Retry" live in the core and projects dictionaries; "Loading settings…" in projects.
export const ru = {
  // ── LLM model screen (D-21: «AI Engine» is now «LLM model»)
  "Region · LLM model": "Раздел · Модель LLM",
  "LLM model.": "Модель LLM.",
  "Settings unavailable · {reason}": "Настройки недоступны · {reason}",
  "Failed to load settings": "Не удалось загрузить настройки",
  "Failed to save settings": "Не удалось сохранить настройки",
  "Connection test failed": "Проверка подключения не удалась",
  Configuration: "Конфигурация",
  Provider: "Провайдер",
  Model: "Модель",
  "{model} (saved)": "{model} (сохранено)",
  "Select a provider first": "Сначала выберите провайдера",
  "Loading models…": "Загрузка моделей…",
  "No models discovered — they will populate after a successful connection test":
    "Модели не найдены — они появятся после успешной проверки подключения",
  "API Key": "Ключ API",
  "Leave blank to keep current key": "Оставьте пустым, чтобы сохранить текущий ключ",
  "Enter API key": "Введите ключ API",
  "Saving…": "Сохранение…",
  Save: "Сохранить",
  Saved: "Сохранено",
  "Key configured": "Ключ задан",
  "No key": "Нет ключа",
  "Base URL": "Базовый URL",
  "Optional — for OpenAI-compatible providers using a custom endpoint":
    "Необязательно — для OpenAI-совместимых провайдеров с собственным адресом",
  "Custom API base URL": "Свой базовый URL API",
  "Active Configuration": "Текущая конфигурация",
  Configured: "Настроен",
  "Not configured": "Не настроен",
  "Connection Test": "Проверка подключения",
  "Testing…": "Проверка…",
  "Test Connection": "Проверить подключение",
  "Save an API key first": "Сначала сохраните ключ API",
  Connected: "Подключено",
  Failed: "Сбой",
  "Latency: {ms} ms": "Задержка: {ms} мс",
  "{n} model available": {
    one: "{n} модель доступна",
    few: "{n} модели доступны",
    many: "{n} моделей доступно",
    other: "{n} модели доступны"
  },

  // ── Reasoner screen (reasoner names and descriptions come from the server and stay as received)
  "Region · Reasoner": "Раздел · Ризонер",
  "Reasoner.": "Ризонер.",
  "Loading reasoner settings…": "Загрузка настроек ризонера…",
  "Select the ontology reasoner used to evaluate design rules against the Validation Graph. Selection persists across sessions. HermiT runs a live schema-consistency check against the active project; reasoners marked":
    "Выберите ризонер онтологии, который проверяет правила проекта по графу валидации. Выбор сохраняется между сеансами. HermiT выполняет проверку согласованности схемы активного проекта; ризонеры с пометкой",
  "integration pending": "интеграция ожидается",
  "do not yet change validation behavior.": "пока не влияют на валидацию.",
  Active: "Активно",
  "Integration pending": "Интеграция ожидается",
  "Schema-consistency check — verifies the ontology's logical structure, not design compliance.":
    "Проверка согласованности схемы — проверяет логическую структуру онтологии, а не соответствие проекта правилам.",
  "No check run yet. Run a schema-consistency check against the active project.":
    "Проверка ещё не запускалась. Запустите проверку согласованности схемы для активного проекта.",
  "Run check": "Запустить проверку",
  "Running… {sec}s": "Выполняется… {sec} с",
  "✓ Schema consistent — no unsatisfiable classes found.": "✓ Схема согласована — неудовлетворимых классов не найдено.",
  Consistent: "Согласована",
  Inconsistent: "Противоречива",
  Inconclusive: "Неопределённо",
  "Schema inconsistent — {n} unsatisfiable class": {
    one: "Схема противоречива — {n} неудовлетворимый класс.",
    few: "Схема противоречива — {n} неудовлетворимых класса.",
    many: "Схема противоречива — {n} неудовлетворимых классов.",
    other: "Схема противоречива — {n} неудовлетворимых класса."
  },
  "Last checked {when}": "Проверено {when}",
  "just now": "только что",
  "{n}m ago": "{n} мин назад",
  "{n}h ago": "{n} ч назад",
  "{n}d ago": "{n} дн. назад",
  "– Inconclusive — the reasoner timed out before finishing. Try again.":
    "– Неопределённо — ризонер не успел завершить работу. Повторите попытку.",
  "× Run cancelled — no result.": "× Запуск отменён — результата нет.",
  "Reasoner unavailable": "Ризонер недоступен",
  "Reasoner unavailable · {reason}": "Ризонер недоступен · {reason}",
  "Failed to save selection": "Не удалось сохранить выбор",
  "Selected — will be used when integration is complete.":
    "Выбрано — будет использоваться после завершения интеграции.",

  // ── DG API Docs chrome (D-10: the documentation content itself stays English)
  "Region · DG API Docs": "Раздел · Документация API",
  "Select a page from the tree.": "Выберите страницу в дереве.",
  Parameters: "Параметры",
  "parameter\u0004Name": "Имя",
  Type: "Тип",
  Location: "Расположение",
  Required: "Обязательный",
  Description: "Описание",
  Yes: "Да",
  No: "Нет",
  "Request example": "Пример запроса",
  "Response example": "Пример ответа"
};

export const en = {
  "{n} model available": { one: "{n} model available", other: "{n} models available" },
  "Schema inconsistent — {n} unsatisfiable class": {
    one: "Schema inconsistent — {n} unsatisfiable class.",
    other: "Schema inconsistent — {n} unsatisfiable classes."
  }
};

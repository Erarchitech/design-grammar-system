// graph area dictionary (Graph Viewer: GraphScreen, buildRings, graphApi). `ru` maps English text (the key) to
// Russian; `en` holds only tp() plural tables (English is otherwise the key). Wording follows the 1301-D38 glossary.
// Graph data is never translated (D-13): rule text, SWRL, Cypher, class/property labels, Rule_Id, IRIs, layer names
// (OntoGraph, Metagraph, ValidGraph, Computgraph) and the answers of the LLM stay as the server sends them.
// "Cancel", "Graph Viewer" (core) and "Retry" (projects) are reused, not redefined here.
export const ru = {
  // Header, empty and error states
  "All projects": "Все проекты",
  "all projects": "все проекты",
  "Graph unavailable · {reason}": "Граф недоступен · {reason}",
  "Could not reach Neo4j.": "Нет связи с Neo4j.",
  "Property update failed": "Не удалось обновить свойство",
  "No graph data · ingest a rule to begin": "Нет данных графа · загрузите правило, чтобы начать",

  // Restore-point banner
  "Restore point · graph as before {mode} turn": "Точка восстановления · граф до шага «{mode}»",
  "restore\u0004ingest": "загрузка",
  "restore\u0004query": "запрос",
  "restore\u0004edit": "правка",
  Confirm: "Подтвердить",
  "Return to live": "Вернуться к текущему графу",

  // Left column: layers and orbits
  "Graph Layers": "Слои графа",
  "Grouped · {n}×3": "Сгруппировано · {n}×3",
  "Drag to rotate · click to align · double-click to inspect · right-click to search":
    "Перетащите, чтобы повернуть · щелчок: выровнять · двойной щелчок: подробности · правый щелчок: поиск",
  Orbits: "Орбиты",
  Core: "Ядро",
  Mid: "Середина",
  Outer: "Внешняя",
  "{n} layer node": {
    one: "{n} узел",
    few: "{n} узла",
    many: "{n} узлов",
    other: "{n} узла"
  },
  "{n} edge": {
    one: "{n} ребро",
    few: "{n} ребра",
    many: "{n} рёбер",
    other: "{n} ребра"
  },

  // Node panels and search
  "Rule actions": "Действия с правилом",
  "Delete rule…": "Удалить правило…",
  Properties: "Свойства",
  "Edges · {n}": "Рёбра · {n}",
  "Search {layer}…": "Поиск: {layer}…",
  "{n} match": {
    one: "{n} совпадение",
    few: "{n} совпадения",
    many: "{n} совпадений",
    other: "{n} совпадения"
  },
  "Type to search": "Введите запрос",
  "Search by": "Искать по",
  "Any field": "Любое поле",
  Label: "Метка",
  "any field": "любое поле",
  any: "любое поле",
  label: "метка",
  "filter by {field}…": "фильтр: {field}…",
  "{field} ~ \"{query}\" · {n} layer node": {
    one: "{field} ~ «{query}» · {n} узел",
    few: "{field} ~ «{query}» · {n} узла",
    many: "{field} ~ «{query}» · {n} узлов",
    other: "{field} ~ «{query}» · {n} узла"
  },
  "No matching values": "Нет подходящих значений",
  "No values in this layer": "В этом слое нет значений",
  Overview: "Обзор",

  // Session console and history
  All: "Все",
  Ingest: "Загрузка",
  Query: "Запрос",
  Edit: "Правка",
  "action\u0004Ingest": "Загрузить",
  "action\u0004Query": "Запросить",
  "Delete Rule": "Удалить правило",
  "Apply Edit": "Применить правку",
  "No design rule sessions yet": "Сессий по правилам проектирования пока нет",
  Session: "Сессия",
  Clear: "Очистить",
  "Collapse session": "Свернуть сессию",
  "Show session": "Показать сессию",
  Response: "Ответ",
  "Created nodes · {n}": "Созданные узлы · {n}",
  "Select {kind} node in graph": "Выбрать узел «{kind}» в графе",
  "{layer} · text": "{layer} · текст",
  "No data": "Нет данных",
  Rule: "Правило",
  "Select a rule to edit…": "Выберите правило для правки…",
  "No rules in this project": "В проекте нет правил",
  "Encode a design rule…": "Опишите правило проектирования…",
  "Ask the graph a question…": "Задайте вопрос графу…",
  "Describe the changes to apply to {ruleId}…": "Опишите изменения для {ruleId}…",
  "Select a rule above first…": "Сначала выберите правило выше…",

  // Turn progress, results and meta lines
  "Parsing intent": "Разбор замысла",
  "Reasoning over ontology": "Рассуждение над онтологией",
  "Encoding SWRL / Cypher": "Кодирование SWRL / Cypher",
  "Committing to metagraph": "Запись в метаграф",
  "Parsing query": "Разбор запроса",
  "Traversing graph": "Обход графа",
  "Ranking matches": "Ранжирование совпадений",
  "Locating rule": "Поиск правила",
  "Re-encoding SWRL / Cypher": "Повторное кодирование SWRL / Cypher",
  "Rewriting metagraph": "Перезапись метаграфа",
  "{secs}s": "{secs} с",
  "Rule ingested into the metagraph.": "Правило записано в метаграф.",
  "Rule {ruleId} rewritten in the metagraph.": "Правило {ruleId} перезаписано в метаграфе.",
  "(empty answer)": "(пустой ответ)",
  "ERROR — {message}": "ОШИБКА — {message}",
  "workflow failed": "сбой рабочего процесса",
  "Committed → Metagraph · {secs}s": "Записано → Metagraph · {secs} с",
  "Rewritten → Metagraph · {secs}s": "Перезаписано → Metagraph · {secs} с",
  "Query · {project} · {secs}s": "Запрос · {project} · {secs} с",
  Failed: "Сбой",
  "History · {date}": "История · {date}",

  // Conflict check after ingest
  "The new rule was written and may conflict with an existing one":
    "Новое правило записано и может противоречить существующему",
  "New rule: {ruleId}": "Новое правило: {ruleId}",
  "Shared classes: {classes}": "Общие классы: {classes}",
  // ── ingest duplicate question (Phase 1303-15)
  "The new rule introduced something similar to what the project already has":
    "Новое правило ввело сущность, похожую на уже существующую в проекте",
  "New {kind} «{a}» resembles existing «{b}» ({reason}).": "Новый {kind} «{a}» похож на существующий «{b}» ({reason}).",
  "Use «{b}»": "Использовать «{b}»",
  "Keep «{a}» as a new concept": "Оставить «{a}» как новое понятие",
  "Decide later": "Решить позже",
  "class": "класс",
  "property": "свойство",
  "Could not apply the decision.": "Не удалось применить решение.",
  "An existing rule already constrains this same class, property, and comparator:":
    "Существующее правило уже ограничивает тот же класс, свойство и оператор сравнения:",
  "{n} existing rules already constrain this same class, property, and comparator:": {
    one: "{n} существующее правило уже ограничивает тот же класс, свойство и оператор сравнения:",
    few: "{n} существующих правила уже ограничивают тот же класс, свойство и оператор сравнения:",
    many: "{n} существующих правил уже ограничивают тот же класс, свойство и оператор сравнения:",
    other: "{n} существующих правила уже ограничивают тот же класс, свойство и оператор сравнения:"
  },
  "Current threshold: {value}": "Текущее пороговое значение: {value}",
  "Keep both": "Оставить оба",
  "Update existing": "Обновить существующее",
  Replace: "Заменить",
  "The new rule is already written. Replace/Update keep the existing rule in the graph (marked superseded, with provenance) and stop it from taking part in validation — nothing is deleted. Keep both leaves both rules and records that you saw this overlap. Cancel opens the delete dialog for the new rule; nothing is deleted until you confirm.":
    "Новое правило уже записано. «Заменить» и «Обновить существующее» оставляют прежнее правило в графе (с пометкой «заменено» и сведениями о происхождении) и исключают его из валидации; ничего не удаляется. «Оставить оба» сохраняет оба правила и фиксирует, что вы видели это пересечение. «Отмена» открывает диалог удаления нового правила; ничего не удаляется, пока вы не подтвердите.",
  "Could not identify the newly created rule, so the conflict decision was not recorded.":
    "Не удалось определить созданное правило, поэтому решение по конфликту не записано.",
  "{ruleId} is still the rule in force.": "Правило {ruleId} по-прежнему действует.",
  "No overlap provenance was recorded.": "Сведения о пересечении не записаны.",
  "Update did not apply — {ruleId} is still the rule in force.":
    "Обновление не применено — правило {ruleId} по-прежнему действует.",
  "Recording the conflict decision failed: {message}.": "Не удалось записать решение по конфликту: {message}.",
  "{ruleId} may still be the rule in force.": "Правило {ruleId}, возможно, по-прежнему действует.",
  "unknown error": "неизвестная ошибка",
  "The conflict check for {ruleId} failed ({message}); the rule was written without it.":
    "Проверка конфликтов для {ruleId} не удалась ({message}); правило записано без неё.",
  "{ruleId} conflicts with an existing rule and stays written; delete it from the rule menu if you cancelled it.":
    "{ruleId} конфликтует с существующим правилом и остаётся записанным; если вы отменили его, удалите его через меню правила.",

  // Rule deletion dialog
  "Delete rule?": "Удалить правило?",
  "Delete {n} rules?": {
    one: "Удалить {n} правило?",
    few: "Удалить {n} правила?",
    many: "Удалить {n} правил?",
    other: "Удалить {n} правила?"
  },
  Delete: "Удалить",
  "Delete {n}": "Удалить: {n}",
  "Deleting…": "Удаление…",
  "Finding matching rules…": "Поиск подходящих правил…",
  "Loading preview…": "Загрузка предпросмотра…",
  "No rules matched that request. Nothing will be deleted.": "Ни одно правило не подошло под запрос. Ничего не будет удалено.",
  "{n} atom": {
    one: "{n} атом",
    few: "{n} атома",
    many: "{n} атомов",
    other: "{n} атома"
  },
  "also deletes {items}": "также удаляет: {items}",
  "keeps {items} (used elsewhere)": "сохраняет: {items} (используется в других правилах)",
  "Ignored — no such rule in this project: {ids}": "Пропущено — такого правила в проекте нет: {ids}",
  "This cannot be undone.": "Это действие нельзя отменить.",
  "Could not load deletion preview": "Не удалось загрузить предпросмотр удаления",
  "Could not resolve the deletion request": "Не удалось обработать запрос на удаление",
  "Delete failed": "Не удалось удалить",

  // graphApi.js (workflow relay errors, thrown with the text of the language at that moment)
  "Workflow timed out.": "Время ожидания рабочего процесса истекло.",
  "Execution not found or not permitted.": "Запуск не найден или недоступен.",
  "Workflow failed.": "Рабочий процесс завершился сбоем.",
  "Workflow cancelled.": "Рабочий процесс отменён.",
  "Workflow relay did not return an execution id.": "Ретранслятор рабочего процесса не вернул идентификатор запуска."
};

export const en = {
  "{n} layer node": { one: "{n} node", other: "{n} nodes" },
  "{n} edge": { one: "{n} edge", other: "{n} edges" },
  "{n} match": { one: "{n} match", other: "{n} matches" },
  "{field} ~ \"{query}\" · {n} layer node": {
    one: "{field} ~ \"{query}\" · {n} node",
    other: "{field} ~ \"{query}\" · {n} nodes"
  },
  "{n} existing rules already constrain this same class, property, and comparator:": {
    one: "{n} existing rule already constrains this same class, property, and comparator:",
    other: "{n} existing rules already constrain this same class, property, and comparator:"
  },
  "Delete {n} rules?": { one: "Delete {n} rule?", other: "Delete {n} rules?" },
  "{n} atom": { one: "{n} atom", other: "{n} atoms" }
};

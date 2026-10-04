# Phase 1301: Рабочий клиент и безопасное чтение — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-04
**Phase:** 1301-rabochiy-klient-i-bezopasnoe-chtenie
**Areas discussed:** Изоляция runtime и упаковка; Вход DG, сессия и встроенный web; Локальный CAD bridge и выбор документа; LLM-маршрут, состав контекста и отмена

Preflight: `python tools/degram/workspace.py verify` — gitlink = child HEAD `8b66a51`, componentContextInstalled = true, pending: desktop-runtime-isolation, product-integration-and-acceptance.
Existing plans: 1 (1301-01, executed). Owner choice: «Продолжить, перепланировать после».

---

## Изоляция runtime и упаковка

| Вопрос | Варианты | Выбрано |
|---|---|---|
| Identity | Новый variant `degram` / Upstream channel request / Реши сам | Новый variant `degram` |
| Runtime home | Фиксированный, игнорировать унаследованный HERMES_HOME / Свой путь + `DEGRAM_HOME` | Фиксированный, игнорировать унаследованный |
| Updater | Полностью отключено / Свой feed через GitHub Releases fork | Полностью отключено |
| Packaging | Bundled-инсталлятор с Python / Сначала dev-сборка / Light-клиент | Bundled-инсталлятор с Python |

**Notes:** Owner declined further questions (tool surface, upstream network, branding, first-launch gate) — moved to Claude's discretion with 1300 boundaries.

---

## Вход DG, сессия и встроенный web

| Вопрос | Варианты | Выбрано |
|---|---|---|
| Login | Страница входа DG в изолированном partition / Нативная форма Desktop | Страница входа DG в partition |
| Agent auth | Короткоживущий делегированный токен / Брокер в Electron main / Реши сам | Делегированный токен |
| Web surface | Встроенный view с полным V2 / Только #degram, полный V2 во внешнем браузере | Встроенный view с полным V2 |
| Revocation | Каждый запрос + heartbeat + focus / Только на следующем запросе / Push с сервера | Каждый запрос + heartbeat + focus |

**Notes:** Owner declined follow-ups on mutation screens in embedded V2 and Speckle token scoping — recorded as discretion/research.

---

## Локальный CAD bridge и выбор документа

| Вопрос | Варианты | Выбрано |
|---|---|---|
| Revit | Свой минимальный read-only add-in DG / Сторонний Revit MCP / Сначала только GH | **Other:** «Используй готовый revit mcp и создай форк от него: https://github.com/Demolinator/revit-mcp-server.git» |
| Doc select | Явный picker + pin на identity / Активный документ + подтверждение | Явный picker + pin |
| Snapshot | Selection + параметры через существующий сериализатор / Только identity | Selection + параметры |
| Routing | Нет, snapshot только локально / Да, registry ADR сейчас | Нет, только локально |
| Fork home | Erarchitech fork + pinned submodule / Fork без submodule / Внутри DeGram | Erarchitech fork + pinned submodule |
| Read-only | Allowlist на обоих слоях / Фильтр только в MCP | Allowlist на обоих слоях |
| Revit wire | MCP stdio, запускает DeGram / Свой typed tool к pyRevit Routes | MCP stdio |
| pyRevit | Шаг clean-install протокола / Инсталлятор автоматизирует | Шаг протокола |

**Notes:** Upstream revit-mcp-server inspected via `gh`: MIT, FastMCP + pyRevit Routes `:48884`, 48 tools including `execute_revit_code`, `save_document`, create/modify/delete; active-document model. Owner declined follow-ups on GH adapter symmetry and multi-document Revit — discretion.

---

## LLM-маршрут, состав контекста и отмена

| Вопрос | Варианты | Выбрано |
|---|---|---|
| LLM route | User-scoped relay на DG backend / Прямой вызов provider с ПК | User-scoped relay |
| Context UX | Карточка контекста у поля ввода / Диалог перед каждой отправкой | Карточка контекста |
| Cancel | Сквозная отмена, частичный ответ помечен / Отбрасывать частичный ответ | Сквозная отмена |
| History | Сессии привязаны к scope / Стирать при logout / Без локальной истории | Привязка к scope |

---

## Claude's Discretion

- Вызов GH bridge (agent tool/MCP vs Electron main), адресация закреплённого Revit-документа, TTL токена, heartbeat, timeouts, лимиты размера.
- Минимальный набор встроенных инструментов Hermes в variant `degram` (без произвольного кода/shell над данными DG; allowlist утверждает владелец в плане).
- Порядок инкрементов: изоляция runtime тестами до первого запуска; запуск/сборка/fork/push/installs/live calls — отдельная авторизация.
- Mutation-экраны во встроенном полном V2 — по серверным правам пользователя; конфликт поднимается владельцу.

## Deferred Ideas

- Собственный подписанный update feed DeGram.
- Серверный per-PC registry / outbound CAD connection (ADR).
- Server push уведомлений об отзыве.

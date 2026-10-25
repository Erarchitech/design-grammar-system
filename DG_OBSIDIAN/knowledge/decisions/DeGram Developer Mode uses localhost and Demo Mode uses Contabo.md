---
tags: [decision, degram, client, hosting, gsd]
date: 2026-10-25
status: captured
---

# DeGram Developer Mode uses localhost and Demo Mode uses Contabo

## Решение владельца

2026-10-25 владелец запросил два явных режима DeGram и включение их в ближайшие планы GSD:

- **Developer Mode** — продолжение разработки и внутреннее тестирование с DG на localhost.
- **Demo Mode** — тестирование реального стенда DG на сервере Contabo.

Localhost не заменяется стендом. Demo Mode не означает mock-данные или выдуманные результаты, Developer Mode не даёт обхода авторизации.

## Включение в GSD

Client delivery owner — **Phase 1301**; hosted integration — **Phase 1309 / HOST-05**. Добавлены **DGMODE-01..04** вне исходных 51 MVP ID, без переназначения существующего ownership.

Ближайший bounded client follow-up не должен ждать всей цепочки 1302–1307 либо полного recovery HOST-04. Применимые security, runtime isolation и live/publication gates сохраняются. Это способ планирования запроса, не новое подтверждение безопасности/приёмки существующего клиента.

Канонические артефакты:

- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DUAL-MODE.md` — planning brief, пакеты A/B/C, acceptance matrix.
- `.planning/todos/pending/2026-10-25-add-degram-developer-mode-and-demo-mode.md`.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`.

## Планируемые инварианты

Явный выбор и видимый target; раздельные credentials/cookies, project/company, agent sessions/history/context, caches и document bindings по environment/origin. Проверка **Developer → Demo → Developer**, в том числе одинаковые user/project IDs. Без скрытого fallback на localhost, переноса данных/секретов, позднего ответа старого target или повторной отправки уже подтверждённой операции другому серверу. Native bridges остаются локальными и отдельно авторизованными.

Точная UI-компоновка, формат хранения и executable PLAN-файлы пока не утверждены/не созданы. Реализация не начата; existing product/phase gates не закрыты.

## Продолжение

Scoped planning Phase 1301 по brief: A — config/isolation; B — selector/safe switch/real-path tests; C — published gitlink/framework integration и отдельно разрешённая сборка/приёмка localhost + Contabo.

Связано: [[sessions/2026-10-25 DeGram Developer and Demo modes captured in GSD]], [[knowledge/decisions/DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls]], [[knowledge/decisions/Hosted stand first and recovery proof in parallel]].

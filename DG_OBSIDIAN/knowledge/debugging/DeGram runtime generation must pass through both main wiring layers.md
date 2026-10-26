---
tags: [debugging, degram, isolation, electron, generation]
date: 2026-10-26
status: fixed-offline
---

# Runtime generation must pass through both main wiring layers

## Дефект

При реализации 1301-45 `createDegramEnvironmentWiring` уже передавал `descriptor.generation` в `createDegramMainWiring`, но второй слой не передавал его в `createDegramRuntime`. Поэтому actual production composition публиковала state/events без stamp, хотя direct runtime test с заданным generation проходил. Renderer нового coordinator отвергает unstamped state, поэтому прямой unit test не доказывал интеграцию.

## Исправление

В `apps/degram/apps/desktop/electron/degram/main-wiring.ts` вызов `createDegramRuntime` получает `generation: deps.generation`. Runtime добавляет immutable environmentId/generation в getState, state publications и события.

В `main-wiring.test.ts` добавлен тест actual environment composition A→B→A: для каждой authoritative generation проверяются getState, последний stateChanged и событие native did-fail-load. Вместе с IPC focused suite — 64/64, полный Electron DeGram — 304/304, typecheck PASS (2026-10-26).

## Урок

Проверять producer stamp на всей цепочке coordinator → main wiring → runtime → renderer, а не только на прямой runtime fixture. Буферизация renderer допускает startup state раньше environment publication, но не должна подменять отсутствующий producer contract permissive fallback.

Исправление пока в uncommitted component source, child/gitlink `b619e02e`; нет build/live acceptance. Полный summary: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-45-SUMMARY.md`.

Связано: [[sessions/2026-10-26 DeGram plan 1301-45 renderer isolation complete]], [[knowledge/debugging/DeGram quiescence must reserve RPC work before enqueue]].

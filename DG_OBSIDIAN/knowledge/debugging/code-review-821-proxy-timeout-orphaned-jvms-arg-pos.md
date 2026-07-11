---
tags: [debugging, reasoner]
date: 2026-07-12
---

# Code review Phase 821: proxy timeout mismatch, orphaned JVMs, silent ARG.pos data loss

## Симптомы (до фикса)

Три critical finding из code review Phase 821:

1. **CR-01 — Proxy timeout mismatch**: `data-service/app.py` → `/reasoner/consistency` proxy использовал `httpx.Timeout(read=5.0)`, но `dg-reasoner/reasoning.py` имел `DG_REASONER_TIMEOUT_SECONDS=90`. Любой реальный HermiT run превышал 5s — endpoint возвращал ложный `504` до того, как sidecar успевал закончить.

2. **CR-02 — Orphaned JVMs**: `reasoning.py._reason_with_timeout()` вызывал `process.terminate()`, который шлёт SIGTERM только Python-процессу, но не Java-grandchild, которого Owlready2 запускает через `subprocess.Popen`. Каждый timeout создавал orphaned JVM.

3. **CR-03 — Silent ARG.pos data loss**: `ontology_export.py` молча дефолтил `null` позиции в `0`. Для BuiltinAtom порядок аргументов семантически значим (`greaterThan(?h, 9)` ≠ `greaterThan(9, ?h)`), и положение могло стать зависимым от порядка записей в Neo4j без `ORDER BY`.

## Корневая причина

- **CR-01**: Две независимые timeout-конфигурации (proxy и sidecar) не синхронизированы. proxy писался с мотивацией "fast fail на hangs", но не учитывал, что sidecar документально ждёт до 90s.
- **CR-02**: `multiprocessing.Process.terminate()` SIGTERM не распространяется на grandchild процессы. Документация модуля утверждала "kills java grandchild too", но это не было реализовано в коде.
- **CR-03**: Позиция ARG.pos дефолтилась до кода emission, до того как completeness check мог её проверить — недостаток архитектуры проверок.

## Фикс

- **CR-01**: `httpx.Timeout(read=95.0)` — превышает 90s hard timeout с запасом. (Commit `207ffc2`)
- **CR-02**: `os.setsid()` в worker → `os.killpg(process.pid, signal.SIGKILL)` в timeout handler. Использован `spawn` context вместо `fork`. (Commit `207ffc2`)
- **CR-03**: Введён `raw_positions_by_atom` — pre-default значения `record["pos"]`, проверяемые `_atom_completeness_reason()` до дефолта. BuiltinAtom с null/дубликатом pos → SkippedAtom. (Commit `207ffc2`)
- Дополнительно: WR-02 (HAS_BODY/HAS_HEAD.order) тем же паттерном. WR-04 (SHACL timeout) — тот же spawn+killpg паттерн.

## Статус
- Fix: commit `207ffc2` — 4 файла, 147 insertions, 38 deletions
- Проверено: 13/13 тестов green после фикса
- Verification: 22/22 must-haves passed

**Why:** Code review findings — критический разрыв между ожиданием (timeout убивает grandchild) и реальностью (не убивает), и между документацией endpoint (consistency check) и реализацией (timeout гарантированно срабатывал раньше, чем endpoint мог ответить).

**How to apply:** При добавлении нового timeout-обёртки для subprocess всегда:
1. Синхронизируй все timeout-конфигурации в цепочке
2. Используй `os.setsid()` + `os.killpg()` для grandchild coverage
3. Для FastAPI используй `spawn` context, не `fork`
4. Валидируй данные до дефолта, не после

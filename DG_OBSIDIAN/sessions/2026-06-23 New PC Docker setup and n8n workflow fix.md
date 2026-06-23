---
tags: [session, devops, docker, n8n, debugging]
date: 2026-06-23
---

# 2026-06-23 — New PC Docker Setup and n8n Workflow Fix

## Сессия

Запуск Docker-стека на новой машине. Диагностика и исправление двух критических проблем: CRLF в shell-скриптах и сломанная Basic Auth в n8n-воркфлоу.

- Модель: claude-sonnet-4-6
- Дата: 2026-06-23
- Изменено файлов: 3

## Изменённые файлы

- `.gitattributes` (новый)
- `docker-compose.yml`
- `n8n/workflows/rules-to-metagraph.json`

## Результаты

### Проблема 1: CRLF в shell-скриптах — `env: can't execute 'sh\r'`

**Причина:** `git config core.autocrlf=true` на Windows конвертировал все `.sh` в CRLF при checkout. Linux-контейнер читал shebang как `#!/bin/sh\r` и падал.

**Исправление:**
- Добавлен `.gitattributes` с `*.sh text eol=lf` — навсегда фиксирует LF для shell-скриптов независимо от `autocrlf`
- `graph-viewer/entrypoint.sh`, `scripts/refresh_graphify.sh`, `test/test_phase04_update_flow.sh` — конвертированы в LF
- `docker compose build --no-cache design-grammars` — пересборка образа с LF-версией entrypoint

Коммит: `cd4e607`

### Проблема 2: Ollama DNS failures в контейнере

**Причина:** Docker Desktop/WSL2 embedded DNS (`127.0.0.11:53`) периодически не форвардит запросы к внешним хостам (registry.ollama.ai, Cloudflare R2), вызывая ошибку `server misbehaving` при `ollama pull`.

**Исправление:** добавлены `dns: [8.8.8.8, 1.1.1.1]` в ollama service в `docker-compose.yml`. Модель `llama3.1` (4.9 GB) успешно загружена.

Коммит: `cd4e607` (в том же)

### Проблема 3: n8n import workflow требует поле `id`

**Симптом:** `n8n import:workflow` падал с `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id`.

**Причина:** n8n 2.26.9 требует `id` в JSON воркфлоу при импорте; репозиторные файлы содержат пустой id.

**Исправление:** inject `id` в scratch-копию перед импортом. Также: `docker cp` с path `/tmp/...` требует обёртки `docker exec ... sh -c` на git-bash/Windows (иначе MSYS path conversion ломает аргумент).

### Проблема 4 (основная): `rules-to-metagraph` воркфлоу зависал на шаге 1/20% навсегда

**Симптом:** UI "Ingest Rules" зависал на "Send Rules" после step 1 и никогда не обновлялся.

**Диагностика:**
1. Прямой тест Ollama → работает (71s cold start, 0.6s warm) — не причина
2. Граф воркфлоу: `Mark Running → Fetch Existing Entities → Build LLM Prompt → Mark Step 2 → Ollama Generate → ...`
3. `Mark Running` (шаг 1/20%) выполнялся — но после него всё умирало
4. Следующий узел — `Fetch Existing Entities` (httpRequest к Neo4j)
5. Этот узел имел `authentication: "basicAuth"` с параметрами `basicAuthUser` / `basicAuthPassword` — но `credentials` был `NONE`
6. n8n 2.x httpRequest v1 node с `authentication: "basicAuth"` требует **хранимого credential** (выбранного в UI), а не inline-параметров; inline-параметры просто игнорировались
7. Узел отправлял запрос без авторизации → 401 от Neo4j → воркфлоу падал молча (нет ветки обработки ошибок → data-service никогда не получал `failed` статус → UI висел навсегда)

То же самое у `Execute LLM Cypher` и `Annotate Graph Props`.

**Исправление:**
- Добавлен Function node `Compute Neo4j Auth` между `Mark Running` и `Fetch Existing Entities`
  - Вычисляет `neo4j_auth_header = 'Basic ' + Buffer.from(user+':'+pass).toString('base64')`
  - Использует `$node["Set Input Defaults"].json` для cross-reference (Function nodes имеют полный Node.js — Buffer доступен)
- `Prepare Graph Payload` — добавлена аналогичная строка для `Execute LLM Cypher` и `Annotate Graph Props`
- Все три httpRequest узла к Neo4j: убраны `authentication`/`basicAuthUser`/`basicAuthPassword`, добавлен `headerParametersJson` с `{"Authorization": $items("...")[0].json.neo4j_auth_header}`
- Перехватывающие попытки исправления: `Buffer.from` в `{{ }}` expression не работает (нет Buffer в n8n expression sandbox), `btoa()` тоже под вопросом → только Function node надёжен

**Результат:** Полный e2e тест прошёл — статус `completed` через 45s, 27 MERGE-statements записано в Neo4j.

Коммит: `398cb76`

## Итоговое состояние стека

| Компонент | Статус |
|---|---|
| 14 Docker-контейнеров | ✅ running |
| CRLF fix committed | ✅ |
| Ollama DNS fix committed | ✅ |
| llama3.1 (4.9 GB) | ✅ загружен |
| n8n workflows (2) | ✅ активны |
| rules-ingest end-to-end | ✅ работает |

## Известные моменты для следующего запуска

1. **n8n workflow import на новой машине** — при `docker compose up -d` (новые volumes) необходимо: inject `id` → `docker cp` → `docker exec sh -c "n8n import:workflow ..."` → `n8n update:workflow --active=true` → `docker restart n8n`
2. **Ollama pull** — модель не персистируется в образе, хранится в named volume `ollama`. При потере volume нужен повторный `docker exec ollama ollama pull llama3.1`
3. **ollama cold start** — первый запрос после idle (5 min OLLAMA_KEEP_ALIVE default, но воркфлоу посылает 30m) занимает 40-70s из-за GPU discovery watchdog в Ollama (известная проблема с новыми NVIDIA драйверами / CUDA 13.1). Не является ошибкой.

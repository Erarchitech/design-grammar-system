# Hosted HTTPS origins и граница ingress — Phase 1309-02

**Статус: только офлайн-конфигурация, не разрешение на установку.** Три файла `docker-compose.yml`, `docker-compose.multi-user.yml`, `docker-compose.hosted.yml` применяются строго в этом порядке. Последний файл — единственная авторитетная сборка edge; `deploy/hosted/edge/Caddyfile` монтируется напрямую. Профиль требует Docker Compose >= 2.24.4 (`!override`); Windows 2.40.3 проверен парсером, Linux и Caddy ещё не проверены. Текущий единственный host-publish — **127.0.0.1:443/tcp**: это не публичный HTTPS. Порт 80 не открыт; для ACME/внешнего маршрута нужны отдельное решение и проверка. Никакой `docker compose up/build` на этой стадии.

## Значения, которые назначает оператор

Ниже — **не реальные DNS, не действующие сертификаты и не разрешение на ingress**. Все значения обязательны; пример предназначен лишь для синтетического `docker compose config` в изолированном окружении без чтения `.env`:

```text
HOSTED_DG_HOST=dg.example.invalid
HOSTED_SPECKLE_HOST=speckle.example.invalid
HOSTED_OBJECT_HOST=objects.example.invalid
HOSTED_EDGE_CIDR=172.30.90.0/28
HOSTED_EDGE_IP=172.30.90.2
HOSTED_EDGE_CERT_DIR=<одобренный абсолютный каталог тестовых сертификатов>
```

Оператор до развёртывания выбирает три **различных, одобренных DNS-имени** (без схемы/порта/пути, не `localhost`, loopback или IP), непересекающуюся частную IPv4 Docker-сеть, фактический адрес Caddy внутри неё и отдельный каталог сертификатов для `dg.crt/key`, `speckle.crt/key`, `object.crt/key`. `HOSTED_EDGE_CERT_DIR` монтируется read-only; ключи не попадают в репозиторий или логи. TLS — только утверждённые смонтированные сертификаты; ACME не включён. Отсутствующая переменная приводит к отказу интерполяции Compose (`:?`); это **проверка наличия, не валидация значения**. До выбора topology, проверки DNS/сертификатов, корректности hostname/CIDR и безопасного опубликования за gate запуск запрещён. `config --no-interpolate` проверяет только структуру, не доказывает этот gate. Нельзя использовать файлы/пароли из рабочей `.env` для тестового вывода.

| Публичный origin после отдельного разрешения | Внутренний upstream | Назначение |
|---|---|---|
| `https://${HOSTED_DG_HOST}` | Caddy → `design-grammars:80` | `/`, `index.html`, `config.js`, `/assets/*`, два статических GIF, `/data-service/*`, `/llm/*`, `/reasoner/*`; запросы проходят авторизацию DG, edge её не заменяет |
| `https://${HOSTED_SPECKLE_HOST}` | Caddy → `speckle-ingress:8080` | Явный пилотный allowlist `/`, `/auth/*`, `/api/*`, `/graphql`, `/projects/*`, `/models/*`, `/streams/*`, `/static/*`, `/_nuxt/*`, favicon/robots; состав ещё проверяется на закреплённом Speckle |
| `https://${HOSTED_OBJECT_HOST}` | Caddy → `speckle-minio:9000` | Только GET/HEAD/PUT/OPTIONS на path-style `/speckle-server` и `/speckle-server/*`; Host, путь и query S3-подписи не переписываются; **передача объектов ещё не подтверждена** |

`DG_BASE_URL`, `SPECKLE_BASE_URL` в data-service/UI, `CANONICAL_URL`, `FRONTEND_ORIGIN`, `NUXT_PUBLIC_API_ORIGIN`, `NUXT_PUBLIC_BASE_URL` и `S3_PUBLIC_ENDPOINT` получают указанные внешние HTTPS origins. `S3_ENDPOINT=http://speckle-minio:9000`, `SPECKLE_INTERNAL_URL=http://speckle-ingress:8080`, `NEO4J_URI=bolt://neo4j:7687` и `N8N_INTERNAL_URL=http://n8n:5678` остаются **только внутренними**. `DG_COOKIE_SECURE=true`; `DG_DEPLOYMENT=multi-user` и `DG_ALLOW_SELF_REGISTRATION=false` наследуются из второго файла. `DG_TRUSTED_PROXIES` для UI и data-service задан **только** адресом `HOSTED_EDGE_IP/32`; передача клиентского `X-Forwarded-For` через edge не должна позволить произвольный spoof, проверка — после разрешения. Не подставлять `0.0.0.0/0` или общую Docker-подсеть.

## Запреты и остаточные границы

Edge возвращает 404 неизвестному Host/пути и явно запрещает DG `/neo4j`, `/n8n`, документацию API, административные и service-only пути, а также Speckle admin paths. Это **не** замена серверной `spec/SECURITY-BOUNDARY.md`: `/neo4j/` и `/n8n/` в nginx UI — tombstones, а не внешняя защита. Сеть/host firewall должны запретить извне Neo4j HTTP 7474 и Bolt 7687, n8n 5678, PostgreSQL, Redis, MinIO 9000 и console 9001, data-service 8000, reasoner 8001, Speckle internal 8080 и локальный CAD bridge 8720. У этих служб нет host-publish в merged hosted Compose; проверить отдельно IPv4 **и IPv6**, Docker NAT, host firewall и off-host доступ. `GH_BRIDGE_HOST=host.docker.internal` относится к серверу, не к ПК рецензента; direct Bolt/GH write не обещается. Сервисам, оставшимся на default Compose network, внутренний доступ сохраняется; edge-сеть сама по себе не доказывает полную lateral isolation.

**Object upload в invited pilot исключён по умолчанию** до доказательства на закреплённых Speckle/MinIO образах: удалённый signed URL должен сохранять host/path/query/signature; с отдельного клиента проверить browser CORS, PUT/GET, ETag, завершение импорта и download. Пока нет результатов, нельзя утверждать поддержку upload/download через публичный объектный origin. Публичное открытие самого Speckle может потребовать отдельного решения о tenancy: DG Model Viewer использует проектно-авторизованный `/data-service/speckle-proxy/`, прямой Speckle route нельзя считать эквивалентным этой проверке.

## Офлайн-проверка и контрольная точка

`python deploy/hosted/tests/run_required.py test_compose_profile.py` запускает **только один** указанный модуль, использует искусственные значения и `config --no-interpolate --format json`; не стартует контейнеры. Позитивная интерполяция, отказ `localhost`/HTTP и негативные тесты принадлежат Task 2 и **ещё не выполнены**. До Black-box проверки отдельное согласие владельца должно назвать изолированную машину, синтетические upstreams, loopback bind, границы сети/времени и очистку. **Approval reference: отсутствует; black-box test BLOCKED.** Это согласие не разрешает public ingress, DNS/TLS cutover, оплаченный вызов модели или реальные данные. Отсутствие локального Caddy CLI не разрешает контейнерный обход gate. Не считать HOST-03 или весь план 1309-02 выполненными.

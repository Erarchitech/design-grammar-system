# Phase 1301: Рабочий клиент и безопасное чтение — Context

**Gathered:** 2026-10-04
**Status:** Ready for planning
**Scope:** DGCL-01..07. Решения ниже относятся к оставшейся части фазы. Выполненный bounded increment `1301-01` (`ui-v2/#degram`, offline-проверен, ни один DGCL не закрыт) сохраняется как есть; новые планы начинаются с `1301-02`.
**Authority:** решения Phase 1300 (`1300-CONTEXT.md` D-01..27 с поправками `1300-SCOPE-REVISION.md`) действуют и здесь не пересматриваются. Нумерация D-NN ниже — локальная для 1301; ссылки на решения 1300 записаны как «1300 D-NN».

<domain>
## Phase Boundary

Участник на поддержанном ПК устанавливает минимальный DeGram Desktop (fork Hermes, `apps/degram`), входит существующим способом DG, явно выбирает доступный проект и конкретный локальный Revit/GH документ. Он получает read-only snapshot через typed adapter, открывает существующий DG web и Model Viewer внутри DeGram и работает с системной LLM-парой, видя состав отправляемого контекста. Отмена, сбои и reconnect дают конкретную диагностику.

Не входит: записи в CAD/граф/Drive, серверная маршрутизация к CAD по ПК, правила/словарь/lessons learned (1302), binding/trace (1303), contextual Viewer parity и review workflow (1304), editing (1305), handover (1306).

### Переносится из Phase 1300 (не переобсуждалось)
- 1300 D-05/D-09: одна системная пара `genpro` / `mimo-v2.5-pro`, скрыта от обычного пользователя, без selector и без automatic fallback; endpoint/served attestation не выдумывать.
- 1300 D-06: ограниченный контекст по политике; доступ к данным DG и разрешение передачи provider — разные проверки; whole-definition требует отдельного подтверждения; подтверждение пользователя не снимает policy deny.
- 1300 D-07: существующие DG-аккаунты/приглашения; Desktop, web, chat и tools работают от имени пользователя, без сервисных/connector полномочий; SSO не обязателен.
- 1300 D-10: timeout/недоступность/лимит → остановка с понятной причиной и ручной повтор; без автоповтора mutation.
- 1300 D-12/D-16: local single-user, текущий ПК, затем ПК reviewer; Revit 2024 / Rhino 8; CAD/graph только read-only, локальные файлы, без Drive.
- `1300-ORCHESTRATION-ADR.md`: один локальный DeGram-оркестратор на ПК; `/llm/generate`, `/context/*`, `/mcp` — service-only, не пользовательский chat/tool путь; произвольный CAD/Python/C# execution исключён.

</domain>

<decisions>
## Implementation Decisions

### Изоляция runtime и упаковка Desktop
- **D-01:** Identity DeGram задаётся новым variant `degram` в `apps/degram/apps/desktop/product-identity.cjs`.
  - Display «DeGram», собственный appId (например `com.erarchitech.degram`), cliName, userData и single-instance lock, отдельные от любого варианта Hermes. Это минимальный seam, переносимый при merge upstream. Upstream channel-request механизм не используется.
- **D-02:** Runtime home фиксирован в каталоге DeGram (например `%LOCALAPPDATA%\DeGram\...`); унаследованный `HERMES_HOME` игнорируется.
  - `electron/backend-env.ts` сейчас наследует `HERMES_HOME` из окружения; для variant `degram` это запрещено. При совпадении/вложенности пути с профилем Hermes пользователя старт отказывает fail-closed с диагностикой. Тест доказывает, что заданный в окружении `HERMES_HOME` не используется.
- **D-03:** Автообновление в 1301 полностью отключено.
  - Нет feed и нет проверки; тест доказывает, что DeGram никогда не обращается к upstream release feed Nous. Собственный канал обновлений — отдельная будущая задача.
- **D-04:** Поставка для clean-PC протокола DGCL-01 — неподписанный NSIS-инсталлятор на основе upstream `bundled` (с Python-агентом), собранный локально.
  - На чистом ПК не требуется отдельный Python/Hermes. Upstream `light` (remote-only) не используется: он противоречит ADR «один локальный оркестратор» и доступу к локальному CAD.

### Вход DG, сессия и встроенный web
- **D-05:** Вход — существующая страница входа/приглашения DG, открытая top-level в изолированном Electron session partition DeGram (например `persist:degram-dg`).
  - Cookie остаётся httpOnly `SameSite=Strict`; security headers DG (`X-Frame-Options: DENY`, `frame-ancestors 'none'`) не ослабляются и не обходятся; iframe не используется. Второй реализации входа нет.
- **D-06:** Инструменты Python-агента читают DG по короткоживущему делегированному user-scoped токену, привязанному к сессии пользователя и выбранному проекту.
  - Токен живёт только в памяти агента, не пишется на диск/в логи/в LLM payload и прекращает действовать при logout/revoke/истечении сессии. Принципал остаётся user, это не connector token и не service header. Новый route выдачи/проверки вносится в route-policy таблицу и fenced blocks `spec/SECURITY-BOUNDARY.md`.
- **D-07:** DG web показывается во встроенном WebContentsView/окне DeGram в том же изолированном partition (общий вход), с allowlist навигации только на DG origin и без Node/preload.
  - Доступны и срез `#degram`, и полный V2 с Model Viewer. Внешние ссылки не открываются внутри view.
- **D-08:** Отзыв доступа обнаруживается тремя путями: сервер проверяет каждый защищённый запрос, клиент периодически вызывает `/auth/me` (heartbeat), а при фокусе окна проверяет доступ.
  - При 401/403 стираются проектный контекст агента, делегированный токен и состояние web views; уже показанные данные чужого/отозванного scope не остаются на экране. Период heartbeat выбирает planner. Server push не вводится.

### Локальный CAD bridge и выбор документа
- **D-09:** Revit 2024 читается через fork `https://github.com/Demolinator/revit-mcp-server` (MIT, FastMCP + pyRevit Routes на `localhost:48884`).
  - Fork владельца: `Erarchitech/revit-mcp-server`, подключается как pinned submodule (например `apps/revit-mcp`) по той же схеме, что `apps/degram`: origin = fork, upstream = Demolinator, gitlink, запись в workspace-манифесте и проверка в `tools/degram/workspace.py verify` (или его аналоге). Создание fork на GitHub, push и регистрация submodule — исходящие действия, при исполнении требуют отдельной явной авторизации владельца.
- **D-10:** Read-only гарантируется allowlist на обоих слоях fork.
  - Внутри Revit (`startup.py` / `revit_mcp/`) регистрируются только разрешённые read routes, в MCP (`tools/`) — только read tools. `execute_revit_code`, `save_document`, create/modify/delete/transform/tag/color/link/load/export-to-disk не регистрируются вовсе (а не только скрываются), потому что pyRevit Routes вызываются напрямую по HTTP любым локальным процессом. Тест проверяет точный набор зарегистрированных routes и tools. Записи 1306 позже возвращаются отдельным typed allowlist, не восстановлением upstream-набора.
- **D-11:** Агент DeGram подключается к Revit-адаптеру как MCP-клиент по stdio. Процесс запускает DeGram через bundled Python.
  - HTTP/SSE-порт MCP не открывается. Процесс адаптера завершается вместе с DeGram, освобождение listener/процесса проверяется (DGCL-06).
- **D-12:** pyRevit и подключение extension — явный шаг clean-install протокола с закреплённой версией pyRevit.
  - Инсталлятор DeGram не меняет конфигурацию pyRevit/Revit автоматически. DeGram проверяет статус (Routes включены, extension загружен, документ открыт) и даёт конкретную диагностику отсутствующего звена.
- **D-13:** Документ выбирается явно: picker показывает открытые документы каждого доступного bridge, выбор закрепляется на identity.
  - Picker показывает приложение, имя, путь, process/document identity. Последующие чтения адресуются закреплённому документу. Закрытие, смена активного документа или несовпадение identity дают диагностируемый operational outcome; молчаливого переключения на другой документ нет. Upstream revit-mcp работает с активным документом — fork добавляет перечисление документов и проверку identity перед чтением.
- **D-14:** Read snapshot 1301 = selection + параметры.
  - GH — через существующий сериализатор DG (`get_canvas_context` / `get_selection` в `CanvasListenerComponent`, loopback `127.0.0.1:8720`). Revit — identity выбранных элементов (UniqueId/ElementId, категория, тип) и их параметры с единицами. Размер ограничен; сокращение и отсутствующие данные раскрываются (связано с D-16).
- **D-15:** Серверной маршрутизации к CAD по ПК в 1301 нет; snapshot используется только локально внутри DeGram (агент и показ).
  - DG backend и web не обращаются к CAD; `host.docker.internal`/server-localhost путь `data-service/gh_bridge.py` не используется для DeGram. «Два ПК» в DGCL-04 проверяются как две независимые установки. Outbound registry из ADR откладывается до фазы, где серверу нужен доступ к CAD.

### LLM-маршрут, состав контекста и отмена
- **D-16:** Агент обращается к системной паре через новый user-scoped OpenAI-compatible chat/tools endpoint на DG backend со streaming; Hermes настроен на него как на единственный provider.
  - **Поправка владельца 2026-10-06:** источник endpoint/модели/ключа relay — настройки LLM в DG Web UI, см. D-24.
  - Вызов идёт за делегированным токеном D-06. Системный ключ остаётся на сервере и никогда не попадает на ПК. Сервер проверяет company/project scope и policy передачи данных provider (1300 D-06), пишет requested/served model provenance, не делает fallback. Пользователь не видит provider/model и не вводит ключи. Новый route вносится в `spec/SECURITY-BOUNDARY.md`; LLM call site — в `spec/REPRODUCIBILITY.md`. Существующий `/llm/generate` не переиспользуется как пользовательский путь.
- **D-17:** Состав контекста показывается постоянной карточкой у поля ввода.
  - В карточке: проект, документ, число объектов/параметров/правил/фрагментов, объём, пометки о сокращении и отсутствующих данных. Она раскрывается до точного payload (без секретов). Обычная отправка не требует подтверждения (1300 D-06); whole-definition проходит через отдельный confirm. Policy deny сервера показывается как причина и не снимается подтверждением.
- **D-18:** Отмена сквозная: client → relay → provider, а также текущее CAD-чтение.
  - Частичный ответ сохраняется с пометкой «прервано». Сбои называют конкретную причину (provider недоступен, timeout, лимит, DG сервер недоступен, bridge выключен/занят) и дают кнопку «Повторить»; автоповтора нет. Native UI остаётся отзывчивым.
- **D-19:** Локальная история чата привязана к scope user + company + project.
  - Смена проекта открывает новую сессию; контекст другого проекта не переиспользуется. После logout история скрыта до повторного входа с подтверждённым membership. При обнаруженном revoke история этого scope удаляется локально.

### Решения владельца при планировании (2026-10-04, после research)
- **D-20:** Минимальный атрибут company: admin-задаваемое соответствие project→company в auth store data-service.
  - Сейчас в auth нет понятия company, только membership на проект. Соответствие отдаётся в `/auth/me` memberships; делегированный токен (D-06) и LLM relay (D-16) проверяют company + project. Governance словаря компании остаётся в 1302.
- **D-21:** Model Viewer получает геометрию через серверный Speckle proxy, авторизованный по проекту; read token Speckle не покидает сервер.
  - Сейчас `/validation/view` отдаёт браузеру один read token на весь Speckle server. Новый route отдаёт только объекты `speckleProjectId`, привязанного к проекту DG; viewer грузит их через DG origin. Запись в route-policy и fenced blocks `spec/SECURITY-BOUNDARY.md`.
- **D-22:** Allowlist инструментов variant `degram` = clarify, todo, toolset `degram` (чтение графа проекта DG, GH snapshot/selection) и read tools revit-mcp.
  - Не регистрируются вовсе (фильтр на уровне registry, не только config): terminal, process, execute_code, file, web, browser, vision/image/tts, skills, memory, session_search, delegation, cronjob, kanban, computer_use, connections, terminal-инструменты desktop_ui. MCP sampling выключен; auxiliary LLM-вызовы закреплены за relay D-16 или отключены, discovery chain провайдеров закрыт.
- **D-23:** Revit bridge работает только при loopback-привязке pyRevit Routes, иначе fail-closed.
  - Fork `startup.py` регистрирует только read routes; шаг установки задаёт `[routes] host = 127.0.0.1`; DeGram проверяет, что listener `:48884` слушает только loopback, иначе статус `setup-incomplete` и чтения не выполняются.

- **D-24:** Relay берёт endpoint, модель и ключ из настроек LLM в DG Web UI (`llm-settings.json`), собственной конфигурации у relay нет [владелец 2026-10-06].
  - Поправка к D-16, реализована в `c5966d4`: `degram-llm.json` и `PUT /degram/admin/llm-config` удалены; только provider `openai` (OpenAI или OpenAI-compatible base URL); иначе relay не настроен, fallback нет. Генпро и «Гена» — только образец, данные оттуда для подключения не используются.
- **D-25:** Подключение DeGram к DG выдаётся отдельным коннектором DeGram во вкладке Connectors DG Web UI как токен сопряжения [владелец 2026-10-06].
  - DeGram хранит токен сопряжения зашифрованным (Electron `safeStorage`) и обменивает его на тот же короткоживущий `dgd_` (D-06), который relay и инструменты принимают без изменений; отзыв в Connectors немедленно гасит все `dgd_`, выпущенные по этому сопряжению. Агент по-прежнему действует от имени пользователя (1300 D-07): токен сопряжения не является connector-принципалом и не принимается ни одним маршрутом, кроме обмена.
- **D-26:** Токен сопряжения DeGram привязан к пользователю, а не к проекту [владелец 2026-10-06].
  - Проект выбирается в DeGram; обмен проверяет живое членство пользователя в проекте и компанию проекта, как при выпуске `dgd_` из сессии.
- **D-27:** Вход DG (D-05) для встроенной страницы DG сохраняется, токен сопряжения бессрочен и гаснет только при отзыве [владелец 2026-10-06].
  - Встроенная страница DG живёт на своей cookie-сессии; агент, relay и инструменты берут `dgd_` из сопряжения, когда оно сохранено, иначе из cookie-сессии (D-05). `expires_at` записи сопряжения = null; отзыв в Connectors, удаление пользователя или смена пароля гасят сопряжение и все его `dgd_`. Выбран вариант keep-signin-no-expiry плана 1301-17 Task 1.
- **D-28:** Проверка DeGram на ПК ревьювера переносится в последнюю фазу v13.0; в 1301 весь функционал и UI DeGram доделываются и проверяются на одном ПК (пилотный) [владелец 2026-10-06].
  - Поправка к D-15 и к plan 16 Task 3: live-приёмка DGCL-01..07 в 1301 идёт на PC1; запуск на втором независимом ПК (D-15) выполняется в последней фазе milestone и остаётся обязательным там. Открытые находки 1301 (G-1, F-11) закрываются до приёмки на PC1.

- **D-29:** Закрепляется по одному документу на мост: одна модель Revit и одно определение Grasshopper одновременно [владелец 2026-10-09].
  - Поправка к D-13, по находке live-приёмки (1301-UAT G-13): закрепление определения GH больше не снимает закрепление модели Revit, и наоборот. Карточка контекста и payload несут оба снимка, каждый со своей identity и своими счётчиками; потеря identity одного моста (закрыт, другой активный файл) блокирует чтения только этого моста. Смена проекта снимает оба закрепления. Перепроверка DGCL-04/07 на сборке 0.1.6.
- **D-30:** Профили без манифеста (созданные 0.1.0–0.1.5) при открытии подходящего scope получают манифест (back-fill), а при первом запуске 0.1.6 после входа оставшиеся профили без манифеста удаляются один раз [владелец 2026-10-09].

### Claude's Discretion
Planner/researcher выбирают HOW в пределах решений выше и границ 1300:
- Кто вызывает GH bridge: typed tool/MCP в агенте (симметрично D-11) или Electron main через typed IPC. По умолчанию — симметрично с Revit, только loopback.
- Как fork revit-mcp перечисляет документы и адресует закреплённый документ при модели pyRevit «активный документ» (D-13).
- TTL и формат делегированного токена, период heartbeat, значения timeout, лимиты размера snapshot/payload.
- **Минимальный набор встроенных инструментов Hermes** в variant `degram` (terminal, файлы, web, cron, внешние MCP). Обязательная граница: никакого произвольного исполнения кода/shell из LLM над данными DG (1300 exclusions). Planner предлагает точный allowlist, владелец утверждает его в плане.
- **Порядок инкрементов.** Изоляция runtime (D-01..D-03) реализуется и проверяется тестами до первого запуска/сборки Desktop. Сам первый запуск, сборка инсталлятора, fork/push/submodule, установка pyRevit и любые live-вызовы DG/LLM/CAD требуют отдельной явной авторизации владельца при исполнении.
- Встроенный полный V2 (D-07) показывает ровно то, что разрешают серверные права пользователя; DeGram не добавляет и не снимает прав. Экраны mutation в V2 этим решением не ограничиваются и не расширяются; при конфликте с «безопасным чтением» planner поднимает вопрос владельцу.

</decisions>

<open_research>
## Что researcher должен проверить (не решено, не выдумывать)

- Адрес привязки pyRevit Routes (`:48884`): должен быть loopback. Если он слушает на всех интерфейсах, это security finding: заблокировать или вынести владельцу.
- Совместимость endpoint `genpro` / `mimo-v2.5-pro` со streaming и tool calling, served-model attestation (1300 D-09: unknown остаётся unknown).
- Как Hermes Desktop/agent подключает кастомный OpenAI-compatible provider и MCP stdio сервер в bundled-сборке, и как в variant `degram` отключить UI выбора provider/model.
- Как Model Viewer получает Speckle-доступ без токена на все модели (DGCL-03).
- CSRF/Origin проверки `data-service/auth.py` для запросов Python-агента с делегированным токеном.
- Требование UI-thread marshalling для Revit read routes (pyRevit) и для GH listener.

</open_research>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone и требования
- `.planning/ROADMAP.md` — Phase 1301 goal, success criteria 1–5, entry/exit gates, verification evidence.
- `.planning/REQUIREMENTS.md` — DGCL-01..07 (строки 31–39).
- `.planning/STATE.md` — текущая авторизация и статус 1300/1301.
- `.planning/v13.0-ACTIVATION.md` — активация и влияющий OPEN v12 долг.
- `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-CONTEXT.md` — D-01..27, open gates G-01..13 (особенно G-03, G-05, G-07).
- `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-SCOPE-REVISION.md` — последняя авторизация, разрешённый independent client development и запреты.
- `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-ORCHESTRATION-ADR.md` — один локальный оркестратор, service-only routes, предлагаемая per-PC архитектура (отложена D-15).
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-01-PLAN.md` и `1301-01-SUMMARY.md` — выполненный web-срез, его границы и ограничения.

### DeGram workspace и Desktop
- `spec/degram/WORKSPACE.md` — контракт submodule, обязательная изоляция runtime перед запуском Desktop, update/contribution workflow (шаблон и для fork revit-mcp).
- `integration/degram/workspace.json` — манифест workspace.
- `tools/degram/workspace.py` — preflight `verify` / `install-context`.
- `DG_OBSIDIAN/degram/index.md` — точка входа в vault по DeGram.
- `apps/degram/AGENTS.md`, `apps/degram/apps/desktop/AGENTS.md`, `apps/degram/apps/desktop/DESIGN.md` — инженерные инварианты fork (Electron/renderer/backend seams).
- `apps/degram/apps/desktop/product-identity.cjs` — seam variant identity (D-01).
- `apps/degram/apps/desktop/electron-builder.config.cjs` — appId/productName/publish (D-01, D-03, D-04).
- `apps/degram/apps/desktop/electron/backend-env.ts` — наследование `HERMES_HOME` (D-02).
- `apps/degram/apps/desktop/update-feed.cjs` — updater feed (D-03).

### Безопасность, контракты и LLM
- `spec/SECURITY-BOUNDARY.md` — принципалы, route-policy таблица, fenced blocks; обновляется для D-06 и D-16.
- `spec/REPRODUCIBILITY.md` — новый LLM call site D-16.
- `spec/API.md` — существующие endpoints и authorization boundaries.
- `spec/EVIDENCE-CONTRACT.md` — operational outcome отдельно от evaluator verdict (диагностика bridge/LLM не становится verdict).
- `data-service/auth.py`, `data-service/auth_routes.py` — cookie-сессия, connector Bearer, порядок разрешения credential.
- `data-service/llm_gateway.py` — существующие адаптеры, requested/served provenance; `/llm/generate` service-only.
- `ui-v2/nginx.conf` — security headers, которые нельзя ослаблять (D-05, D-07).
- `ui-v2/src/lib/auth.js` — login/invite/me/logout.

### CAD
- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` — loopback GH listener `127.0.0.1:8720`, read команды.
- `DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs`, `DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs` — протокол bridge.
- `data-service/gh_bridge.py` — существующий клиент; путь через `host.docker.internal` DeGram не использует (D-15).
- `spec/GRASSHOPPER.md` — сериализатор и ограничения плагина.
- `https://github.com/Demolinator/revit-mcp-server` — upstream Revit адаптера (README: архитектура, 48 tools, pyRevit Routes, SECURITY.md).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ui-v2/src/degram/` (1301-01): изолированный read-only web root `#degram` с session/project/graph/inspection, stale-result и revoke обработкой; встраивается во view D-07 без изменений.
- `ui-v2/src/lib/auth.js`: существующий login/invite/logout — переиспользуется страницей входа D-05.
- `CanvasListenerComponent` + `CanvasBridgeProtocol`: готовые loopback read команды GH (`get_canvas_context`, `get_selection`) и сериализатор DG для D-14.
- `llm_gateway.py` адаптеры (OpenAI-compatible с настраиваемым base URL) и поля provenance — основа relay D-16, но новый streaming/tool endpoint нужен отдельно.
- Upstream variants `light`/`bundled`/`store` в `product-identity.cjs` — образец для variant `degram`; bundled toolchain поставляет Python.

### Established Patterns
- Desktop: Electron владеет машиной и узким typed capability bridge, renderer — презентацией, backend агента — сессиями/tools/моделями; state хранится у своего authority, persisted keys объявляют scope (D-19).
- DG: принципалы user/connector/service разделены; новые routes обязаны попасть в SECURITY-BOUNDARY fenced blocks; operational outcome отделён от evaluator verdict.
- Submodule-компонент: fork + upstream remote + pinned gitlink + workspace verify; cross-repo изменения упорядочены (child commit → push с авторизацией → framework gitlink).

### Integration Points
- `product-identity.cjs` / `electron-builder.config.cjs` / `backend-env.ts` / updater — изоляция runtime.
- Electron main: partition, WebContentsView, heartbeat, передача делегированного токена backend-процессу агента.
- Hermes agent config: единственный custom provider = DG relay; MCP stdio сервер revit-mcp; GH adapter.
- `data-service`: новые routes — выдача делегированного токена и user-scoped chat relay.
- Fork revit-mcp: `startup.py` (routes allowlist), `tools/__init__.py` (tools allowlist), перечисление документов.

</code_context>

<specifics>
## Specific Ideas

- Владелец явно выбрал готовый `Demolinator/revit-mcp-server` с собственным fork вместо написания Revit add-in с нуля.
- DeGram не должен трогать установленный Hermes пользователя: отдельные identity, home, userData, lock, без updater.

</specifics>

<deferred>
## Deferred Ideas

- Собственный канал обновлений DeGram (подписанный feed) — будущая задача после 1301.
- Серверный per-PC registry/outbound CAD connection из ADR — фаза, где серверу нужен доступ к CAD (не 1301).
- Server push уведомлений об отзыве доступа — не вводится; при необходимости отдельная задача.
- Записи Revit через typed allowlist fork — 1306 (уже в roadmap).

Новых возможностей вне phase scope в обсуждении не предлагалось.

</deferred>

## Граница текущей авторизации

Эта запись — решения для research/planning, не implementation evidence и не закрытие DGCL. Действующая авторизация (2026-10-04) разрешает read-only client code и offline tests. Создание fork на GitHub, push, регистрация submodule, сборка/запуск Desktop, установка pyRevit/пакетов, live вызовы DG/LLM/CAD, deploy и paid inference при исполнении требуют отдельного явного разрешения владельца.

---

*Phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie*
*Context gathered: 2026-10-04*

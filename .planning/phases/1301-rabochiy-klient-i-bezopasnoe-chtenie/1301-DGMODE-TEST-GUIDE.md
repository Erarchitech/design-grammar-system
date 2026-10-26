---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 47
scope: DGMODE-01..04
status: prepared-not-run
---

# DeGram: руководство владельца по проверке Developer ↔ Demo

## Назначение и граница

Это приватная, воспроизводимая инструкция для разрешённой runtime-проверки DeGram на одной Windows-машине:

```text
Developer (http://localhost:8080) → Demo (https://dg.173-249-46-99.nip.io) → Developer
```

Она не является разрешением на commit, push, обновление gitlink, изменение stand/DG, платный inference, отзыв grant, CAD/graph write, доступ к Bolt или отключение TLS. Эти действия требуют отдельного явно записанного разрешения. Результаты заполняются только в [1301-DGMODE-LIVE-EVIDENCE.md](1301-DGMODE-LIVE-EVIDENCE.md); пока они не наблюдались, все DGMODE-требования остаются Pending.

## Известные факты конфигурации

| Параметр | Проверенное значение/правило |
| --- | --- |
| Developer target | `http://localhost:8080` |
| Demo target | `https://dg.173-249-46-99.nip.io` |
| Ограничение Developer | только `localhost`, `127.0.0.1` или `[::1]` |
| Ограничение Demo | только HTTPS; удалённый HTTP отклоняется |
| Хранение выбора | `<DeGram home>/degram.json`: `schemaVersion: 2`, `activeDgTarget`, `dgTargets` |
| Временное переопределение | `DEGRAM_DG_ORIGIN` допускается только при точном совпадении с одним из двух настроенных origin; блокирует selector до удаления переменной и перезапуска |
| Идентичность среды | `dg-env-v1-` + SHA-256 canonical origin; Electron partition `persist:degram-dg-<hash>` |
| DeGram runtime | `%LOCALAPPDATA%\DeGram\home` и `%LOCALAPPDATA%\DeGram\userData`; inherited `HERMES_HOME` игнорируется |
| Product identity | `DeGram`, `com.erarchitech.degram`, без updater feed |
| Native boundary | bridge/MCP остаётся локальным (loopback или stdio); Demo не открывает listener, Bolt или дополнительные write-права |

Источник конфигурации: `apps/degram/apps/desktop/electron/degram/dg-target-config.ts`; правила изоляции: [spec/degram/WORKSPACE.md](../../../spec/degram/WORKSPACE.md) и [spec/SECURITY-BOUNDARY.md](../../../spec/SECURITY-BOUNDARY.md).

## Обязательные стоп-условия

Немедленно прекратить запуск и записать фактическое состояние как `blocked`/`failed`, если:

1. проверяемый installer/`win-unpacked` не имеет зафиксированных версии, SHA-256 и исходного commit;
2. packaged identity не `DeGram` / `com.erarchitech.degram`, runtime home/userData не изолированы или приложение пытается attach к Hermes backend;
3. `DEGRAM_DG_ORIGIN` задаёт неизвестный origin, либо конфигурация target невалидна;
4. для Demo предлагается HTTP, отключение проверки сертификата, добавление исключения TLS, cookie/token forwarding или fallback на localhost;
5. окно/лог/evidence показывает пароль, `dgd_` token, cookie, API key, pairing secret или содержимое password Panel;
6. проверка требует inference, CAD action, server mutation или grant revocation без отдельного разрешения;
7. наблюдается ambiguous target, перенос project/document/history/credential в другую среду, либо stock Hermes получает запись, которую нельзя объяснить независимым control window.

Не удалять старые installs, build artifacts или profiles «для чистоты» без отдельного разрешения. Не запускать `hermes update` и не выполнять upstream Windows-тест, изменяющий user PATH.

## 1. Подготовка до запуска

1. В framework root выполнить и записать вывод без секретов:

   ```text
   python tools/degram/workspace.py verify
   python -m unittest discover -s tools/degram/tests -v
   ```

2. Зафиксировать в live evidence:
   - framework `HEAD`, child `HEAD`, состояние gitlink и наличие незакоммиченных изменений;
   - origin/branch child, а также факт: commit/push/gitlink **не выполнялись** этим прогоном;
   - путь build-only clone `D:\dgb\src`, его commit и cleanliness, если он используется;
   - installer или `win-unpacked` version, SHA-256, installation path, start/end timestamp;
   - локальную и stand версию/ревизию только из реально наблюдаемого UI/API/операторского источника.

3. Проверить packaged artifact до запуска: exe metadata (ProductName, CompanyName, version), наличие `com.erarchitech.degram` в packaged `electron-main.mjs`, отсутствие updater feed. Не приравнивать commit к реально собранному или развёрнутому коду.
4. Проверить, что `%LOCALAPPDATA%\DeGram\home` и `\userData` принадлежат DeGram, а запущенный Hermes не будет остановлен/изменён. Для сравнения stock Hermes снять control window **без DeGram**; допустимый churn живого Hermes нужно отличать по времени и PID.
5. Зафиксировать, что Docker/local DG запущен перед Developer-проверкой. Отказ `localhost:8080` — результат проверки, не повод переключать приложение на Demo автоматически.
6. Закрыть процессы только по их PID или корню install DeGram; никогда не завершать процесс по имени `hermes.exe`.

## 2. Existing install → Developer

1. Запустить только разрешённый artifact с очищенным `ELECTRON_RUN_AS_NODE`; не подменять home/profile вручную.
2. До sign-in проверить заголовок selector: видны «Среда DG», выбранный режим и origin. При первом старте не должен показываться выдуманный готовый target до ответа main process.
3. Если приложение мигрирует legacy `dgOrigin`, подтвердить, что loopback origin стал Developer, без потери local profile. Не менять `degram.json` вручную во время проверки.
4. Войти в Developer с тестовой учётной записью и выбрать разрешённый тестовый company/project/grant. Не вводить в evidence пароль/token.
5. Проверить local DG page, auth/session exchange и только разрешённые read-only normal UI действия. Не запускать model relay, mapping/CAD, graph mutation или inference.
6. Записать фактический project/grant status, effective origin и environment ID в evidence; не записывать credential.

Ожидание: активный адрес `http://localhost:8080`; Developer session не использует/не меняет Demo state, и stock Hermes не получает атрибутируемых DeGram writes.

## 3. Developer → Demo

1. Убедиться, что нет активной операции. Если selector/main сообщает busy refusal, **не** рассчитывать на автоматическую отмену: завершить или нажать explicit Stop, дождаться settled completion, затем выбрать Demo повторно.
2. В selector выбрать Demo Mode. Во время переключения controls disabled; selected mode/origin видны, effective runtime может быть пустым. Не закрывать/не перезапускать приложение, чтобы «починить» переход.
3. Дождаться authoritative ready state. Проверить, что effective origin ровно `https://dg.173-249-46-99.nip.io`, а session partition/environment ID отличаются от Developer.
4. На Demo выполнить независимый sign-in и выбрать его тестовый project/grant. Нельзя переносить local cookie, delegated token, историю, selected project или document binding. Совпадение user/company/project ID намеренно допустимо, но state обязан оставаться независимым.
5. Проверить, что встроенная DG navigation, auth, relay/tools/API target используют Demo origin. Не вызывать paid relay/inference и не выполнять CAD/mapping writes.

Ожидание: нет fallback на localhost, нет credential reuse, нет старого local context в Demo. Demo не открывает native bridge/Bolt и не повышает права.

## 4. Demo → Developer и restart

1. Выбрать Developer Mode после отсутствия активной операции. Проверить новый selected/effective origin, environment ID и partition.
2. Подтвердить возврат собственного Developer project/session/history/context только после новой валидной auth/membership проверки. Demo data, document binding, preview, armed consent и cache не должны появляться в Developer.
3. Закрыть DeGram штатно и убедиться в cleanup только DeGram-owned PIDs/listeners.
4. Повторить запуск сначала с selected Developer, затем (отдельным перезапуском) с selected Demo. Для каждого режима проверить сохранённый target, корректный isolated home/userData и отсутствие cross-origin cookies/context.

Ожидание: A→B→A восстанавливает отдельный A state, а restart восстанавливает выбранный target без автоматического переноса B данных в A или наоборот.

## 5. Negative/recovery checks

| Сценарий | Действие | Ожидаемый результат |
| --- | --- | --- |
| Busy switching | Попытаться выбрать другой target во время operation | Явный отказ; operation не перенаправляется; после explicit Stop/retry target можно выбрать заново |
| Demo unavailable | При контролируемой недоступности stand открыть/выбрать Demo | Явная diagnostic surface; selected Demo сохраняется; localhost не активируется сам |
| TLS error | Наблюдать реальную TLS ошибку без изменения trust store и без bypass | Явная ошибка; никакого отключения certificate validation, fallback или retry на другом origin |
| Login/grant denied | Использовать обычный отказ/отсутствие access на тестовом account | Явный auth/grant error; отсутствие weaker-credential fallback |
| Expired/revoked delegated access | Только после отдельного разрешения на expiry/revocation | 401/403 согласно security contract; без повторной отправки и без переключения среды |
| Delayed old response | Использовать встроенную безопасную test/retry observation, не отправляя mutation | Поздний ответ старой generation не публикуется в новом target |

Для unavailable/TLS/grant failures не выполнять server change, certificate override, token revoke или искусственное изменение production state без отдельного разрешения. Если такой сценарий не разрешён, оставить строку `blocked-not-authorized`.

## 6. Boundary checks после каждого запуска

1. Убедиться, что DeGram listener/bridge не опубликован наружу: только loopback или stdio child; не проверять Bolt путём подключения к нему.
2. Сравнить DeGram-owned runtime с исходным snapshot. Проверить, что `HERMES_HOME` не стал источником DeGram runtime.
3. Сравнить stock Hermes control/launch windows. Изменения, которые происходят в control window, не приписывать DeGram; любые дополнительные DeGram-attributable files/logs/DB writes — failure и stop.
4. Подтвердить, что user PATH, install/update config и stock Hermes profile не были изменены. Не удалять следы до фиксации redacted evidence.
5. Проверить отсутствие `DEGRAM_LOCKED` flood и отсутствие provider-key UI. Locked endpoints должны оставаться locked, не пробоваться через обход.

## 7. Rollback

1. При ошибке или ambiguous target прекратить текущую проверку и сохранить redacted timestamp/diagnostic в evidence.
2. Закрыть только DeGram-owned window/processes; не удалять Hermes processes или runtime.
3. Не переключать конфигурацию обратно вручную до того, как зафиксированы selected/effective state, origin и error.
4. Для recovery выбрать target только через selector после settled state либо исправить валидную configured target/override и перезапустить DeGram. Удаление `DEGRAM_DG_ORIGIN` требует явного restart.
5. Installer uninstall, удаление `%LOCALAPPDATA%\DeGram` или изменение stand выполняются только по отдельному решению; они не являются стандартным rollback этой проверки.

## Связанные офлайн-доказательства

[1301-DGMODE-OFFLINE-EVIDENCE.md](1301-DGMODE-OFFLINE-EVIDENCE.md) содержит наблюдённые green offline suites: real-profile CLI A→B→A, same-ID isolation, race/busy barrier, no-fallback TLS-shaped failure, renderer fencing, Electron/UI/typecheck и Python suites. Они не доказывают runtime build/install/network/TLS/login или visual native-view behavior.

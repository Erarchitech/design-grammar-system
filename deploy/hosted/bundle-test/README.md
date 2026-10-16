# Проверка capability собранного hosted-кандидата

Это **не установщик и не frozen release**. Архив содержит чистый allowlisted
кандидат указанной Git-ревизии и отдельный тестовый контур из Neo4j,
data-service и n8n. UI, HTTPS, Speckle, reasoner, внешний LLM и restore здесь
не проверяются. Даже PASS не закрывает полный hosted runtime/freeze gate.

## Требования и границы

- Запуск runtime разрешён только на `DESKTOP-OS4Q8CP`, физически владельцем.
- Windows PowerShell 5.1+, Docker Desktop с Linux containers, Compose 2.24.4+.
- Не менее 12 ГБ свободного диска; лимиты контейнеров суммарно около 4 ГБ RAM,
  3 CPU; время операций до 35 минут плюс ограниченный cleanup.
- Docker downloads/build требуют интернета; запущенные сервисы находятся
  только во внутренней сети, без опубликованных портов и внешнего inference.
- Проект `dg-hosted-1309-sandbox` должен быть пуст. Существующие ресурсы не
  удаляются: запуск остановится. Не запускайте два экземпляра одновременно.
- Только синтетические записи и одноразовые случайные секреты в памяти
  процесса/metadata контейнеров. Личные профили и `.env` не используются.
- Скрипт удаляет созданные контейнеры, сети и volumes; скачанные/собранные
  образы и build cache остаются в Docker. При принудительном выключении ПК
  автоматическая очистка не гарантирована; верните отчёт о незавершённом запуске.

## Ручная передача (после выпуска проверенного ZIP)

1. Перенесите ZIP и отдельно сообщённый SHA-256 на целевой ПК. Не используйте
   архив из предыдущей проверки V11. Распакуйте в новый пустой каталог;
   сам ZIP должен находиться снаружи распакованного каталога.
2. Откройте PowerShell, перейдите в распакованный каталог. В команде ниже
   замените пути и `SHA256_ИЗ_СООБЩЕНИЯ` реальными значениями. Не запускайте
   до получения от разработчика имени финального ZIP и его контрольной суммы.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\support\Run-BundleTest.ps1 -PackageZip C:\DG-test\candidate-test.zip -ExpectedZipSha256 SHA256_ИЗ_СООБЩЕНИЯ -ReportPath C:\DG-test\bundle-report.json
$LASTEXITCODE
```

3. Верните только `bundle-report.json` и показанный exit code. Отчёт должен
   быть новым файлом вне распакованного каталога; существующий не перезаписывается.
   Не присылайте Docker inspect, логи, env, пароли или raw stdout/stderr.

`-PreflightOnly` проверяет ZIP, состав и SHA-256 файлов, manifest кандидата
без вызовов Docker на любом ПК. Результат `PREFLIGHT_ONLY` — не runtime PASS.

## Для разработчика

Из корня framework после разрешённого scoped commit:

```text
python deploy/hosted/build_bundle_test.py --repo . --revision <full-commit> --output <external-new-path.zip>
python deploy/hosted/build_bundle_test.py --output <external-new-path.zip> --verify-only
```

Builder откажет, если подготовительные файлы или policy отличаются от указанной
ревизии. Candidate bytes сверяются с Git blobs. Никакие новые коммиты, публикация,
VPS/deployment или Docker на development ПК этой инструкцией не разрешаются.

---
tags: [debugging, recovery, ntfs, subprocess]
date: 2026-10-16
---

# Offline recovery inventory and process cleanup regressions

## Воспроизведённые причины

1. Обычный directory walk и default-stream SHA не видят NTFS ADS. Синтетический `api/state.bin:unlisted` принимался вне file inventory/byte bounds; ADS на marker/директории/root также нуждаются в отказе.
2. Windows metadata может оставаться cached при открытом handle: same-length archive mutation внутри attestation callback не всегда меняет видимый mtime. Проверка только size/mtime недостаточна.
3. Reader-thread создавался/запускался после Popen, но до cleanup try/finally. При start failure ребёнок оставался живым, хотя частичный файл удалялся.
4. Обычный argparse повторяет неизвестные аргументы в stderr до domain handler — случайно переданные секреты утекали в диагностический текст.
5. Debian PostgreSQL binary path не соответствует official Alpine prefix; KeyboardInterrupt обходил обычный Exception cleanup экспорта.

## Исправления и регрессии

`deploy/hosted/recovery_filesystem.py` использует fail-closed Windows stream enumeration; checkpoint/PG проверяют ADS, links/junctions и explicit stream path. PG повторно хеширует held archive после attestation и до child launch. Все операции после успешного Popen охвачены cleanup; allocation до spawn; join только для стартовавшего reader, pipe закрывается. Checkpoint parser.error не выводит исходное сообщение и возвращает только generic rejection. Export interruption удаляет только owned partial и сохраняет interruption.

Review `deleg_119a1570` воспроизвёл пункты3–4; parent tests RED→GREEN подтвердили исправления. Финально checkpoint14 + PG20 + прежние two-store56 =90/90 без skips. Это не native PostgreSQL тест: binaries заменены disposable Python child processes. Нет hostile same-user mutation guarantee, ACL/non-Windows xattr certification или full recovery acceptance.

См. [[sessions/2026-10-16 Phase 1309 two-store recovery PASS and offline multi-store preparation|session]], `deploy/hosted/MULTI-STORE-RECOVERY.md` и offline evidence JSON.

---
tags: [debugging, degram, packaging, versioning]
date: 2026-10-27
---

# Перед новой сборкой DeGram нужно обновлять variant version

## Симптом

DGMODE build из опубликованного `846d67a…` завершился успешно 2026-10-27, но снова создал `DeGram-Setup-0.1.11.exe`. Разные source commits и SHA-256 не обеспечивают уникальную версию установщика. Исторические сборки 1308 уже также использовали 0.1.11; это не новое разрешение на повтор номера.

## Причина

DeGram-specific version задаётся `apps/degram/apps/desktop/electron-builder.config.cjs` через `extraMetadata.version`. Shared package.json и upstream stamp baseVersion/displayVersion остаются 0.0.0. Build driver намеренно не переопределяет DeGram version; обновление commit само по себе не повышает patch.

## Исправление и проверка

Одна строка в canonical submodule: 0.1.11 → 0.1.12, опубликованный child commit `aee247efc6bf92349aeff4161079e62133755cfb`. Build-only clone fetched этот commit без локального патча. Реальный exe нового build имеет ProductVersion 0.1.12.0, installer 490659129 bytes, SHA-256 `A08F838B172B09E4FB1C2405E020E115804054FA4983CD26C7DA4013799535A4`. Packaging/isolation 40/40; workspace 27/27.

## Правило

Перед очередным installer build проверять доступный следующий номер и поднимать patch в canonical source до commit/push. Затем обновлять gitlink/build clone и проверять exe metadata, stamp commit, installer/app.asar hashes. Не патчить build clone, не переименовывать старый installer как замену версии и не считать hash заменой unique-version policy (`spec/degram/WORKSPACE.md`). Повтор неуспешного незавершённого build отличать от уже выпущенного installer artifact.

Runtime installation/launch/acceptance из этой проверки не следуют. [[sessions/2026-10-27 DeGram 0.1.12 build verified awaiting isolated installation|Сессия и точка продолжения]].

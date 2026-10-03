---
tags: [decision, degram, v13, phase-1300, governance, graph-storage]
date: 2026-10-03
status: accepted-for-planning
---

# DeGram Phase 1300: V8 и серверные графы как основание MVP

## Основание и уровень принятия

Владелец интерактивно выбрал D-01..D-27, уточнил централизованные Web Design Grammars/LLM и graph storage, затем разрешил завершить CONTEXT. Приняты product/planning решения; technical acceptance, baseline и exit Phase 1300 ещё OPEN. Полные канонические решения: `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-CONTEXT.md`. Эта заметка — навигационное summary, не второй нормативный ledger.

## Контракты и authority

- **D-01..04:** V8 — обязательное основание всего выбранного MVP; приёмка всех потребляемых contracts с версиями/хешами, независимым technical verifier и утверждением владельца. Подготовка/current-DG baseline возможны до V8 acceptance, а dependent implementation остаётся gated. v11/v12 normative owners сохраняются; завершение всей публикации/рукописи v11 не требуется.
- Transfer/adapted/superseded не означает completion. Прежний accepted OPEN долг v12/Phase40/824/825 не закрывается выбором нового продукта.

## Web, доступ и LLM

- **D-05 (revision 2), D-09, D-12:** Web Design Grammars/Docker на отдельном test server управляет данными, правами и системными providers/models. Модель назначает task-конфигурация оператора; пользователю видны фактические provider/model. Личные providers/credentials и manual model selector не выбраны. Ранее выбранный личный режим явно отменён.
- **D-06:** ограниченный рабочий context по policy, видимый состав; whole-definition — отдельный confirm + policy permission. DG read permission и LLM export permission различаются.
- **D-07..08:** существующие DG accounts/invites, без обязательного SSO; явные role assignments с допустимым совмещением operator/steward/project approver. Нужны server-side enforcement и logout/revocation evidence; независимость V8 verifier сохраняется.
- **D-10..11:** остановка запроса при сбое назначенной LLM, повтор пользователем без replay выполненной mutation; automatic fallback отсутствует. Учёт расхода/warnings advisory, operator manual restriction, без budget auto-stop. Квоты provider и safety bounds сохраняются.

## Revit/CAD

- **D-13..15:** bounded typed confirmed writes выбранных instance/type parameters, с показом всех affected объектов типа, native read-back, negative cases и undo/recovery. Два обязательных сценария: размеры → геометрия/измерения; отметки/смещения → положение/размеры зависимых объектов. Exact parameters/ranges/units/invariants ещё определяются; arbitrary code, universal model sync, создание/удаление и Family Editor не разрешены этими решениями.
- **D-16/19:** одна fixed CAD/adapter combination на двух ПК; специально подготовленный учебный corpus с independent gold. Legacy .gh/GUID compatibility проверяется отдельно; поддержка произвольных версий и рабочих проектов не заявлена.

## Где данные, а где файлы

- **D-21:** все полноценные DG domain records — terms/rules/bindings/states/measurements/evidence/decisions/history — authoritative в серверных графах. Ontograph/Metagraph/ComputGraph/ValidGraph/SpecGraph сохраняют свои роли, шестой граф не создаётся. Нужны реальные revision/provenance/read-back/restore evidence; готовность нынешней persistence не предполагается.
- Native `.gh`/`.rvt` binaries и исходные документы хранятся отдельно в Drive/CAD-среде; графы содержат точные identity/versions/hashes и необходимые данные. Полные binary files внутри graph DB не требуются.
- **D-17/18/20:** Google Drive компании, отдельная папка пилота и отдельный комплект каждой принятой редакции. Комплект — publication representation серверной записи, не второй source of truth DG; прежние комплекты сохраняются. Confirm/receipt/read-back и доступ получателя обязательны. Никакой новой CDE внутри DeGram.

## Pilot и приёмка

- **D-22..25:** сквозные paired/counterbalanced учебные задания, одинаковое согласованное основание сравнения DG/DeGram; два участника и смена ролей на двух ПК, без population claims. Setup/training и failures раскрыты отдельно, handover без author chat. Независимый предметный эксперт проверяет gold, затем владелец утверждает.
- Главный benefit — общая трудоёмкость цепочки, а не только скорость автора. Correctness/traceability/security не обмениваются на скорость.
- **D-26:** full Model Viewer inventory/matrix + automated regression и live browser/Desktop/web-only UAT; baseline defects не объявляются исправленными из-за reuse.
- **D-27:** numeric gates/repetitions/analysis готовятся после исходного baseline, проходят предметную проверку и owner approval до comparative series. Post-hoc выбор удобного порога исключён.

## Что остаётся OPEN

G-01..G-13 в CONTEXT содержат реальные владельцы-roles и блокируемые capabilities. Конкретные server/CAD/LLM/Drive/participants targets, contracts, baseline evidence, matrix и numeric gates ещё принимаются. Обсуждение завершено, **Ready to plan**; реализация/deploy/live/paid tests, DB/Drive/CAD mutations и phase acceptance не выполнены.

## Связанные материалы

- [[sessions/2026-10-03 v13 activation and Phase 1300 context|Сессия и граница scoped commit]]
- [[knowledge/decisions/DeGram approved process and company-project rule scope|Ранее принятый общий процесс]]
- `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-CONTEXT.md`
- `.planning/phases/1300-kontrakty-baseline-i-ownership/1300-DISCUSSION-LOG.md` — только human audit alternatives/corrections.
- `.planning/v13.0-ACTIVATION.md` — actual activation и retained dependency gates.

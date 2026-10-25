---
tags: [decision, degram, planning]
date: 2026-10-25
status: planned
---

# DeGram dual mode is an additive plan slice with explicit runtime gates

DGMODE-01..04 реализуются отдельной цепочкой 1301-42→43→44→45→46→47 (waves 29–34), без перепланирования 01–41 и без зависимости от старого release-плана 41. Developer = localhost, Demo = настоящий Contabo DG; это не новый продукт/моковый evaluator и не расширение прав.

Implementation choices описаны в `1301-DGMODE-RESEARCH.md`: canonical origin в environment/profile identity и scoped cleanup, доказанная ownership legacy cookies/history, main/backend switch barrier, монотонная generation для stale replies, отсутствие replay/fallback, same-home real-path A→B→A. Это проект плана, не реализованная или принятая архитектура.

UI supplement создаётся до UI-кода. Код/тесты ребёнка, framework evidence и будущие commits разделены по репозиториям. Публикация child, build/install/launch/live требуют отдельных явных разрешений; gitlink только на опубликованный проверенный объект. DGMODE не закрывает DGCL, HOST-05, full recovery или всю Phase1301.

Независимый checker не запускался; владелец разрешил inline-подготовку и структурную самопроверку без дальнейших субагентов. Постоянное правило владельца: субагенты работают только в текущем checkout, без isolated worktrees/веток.

Исполнять через поддерживаемый `--wave N --no-transition`, начиная с 29, затем отдельно 30–34; не через bare execute-phase всей фазы. Контекст и команды: [[sessions/2026-10-25 DeGram dual mode plans 42-47 prepared]]. Исходное требование: [[DeGram Developer Mode uses localhost and Demo Mode uses Contabo]].

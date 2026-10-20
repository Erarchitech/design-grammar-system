# str-openings-01 — правила КР для отверстий (ввод по одному)

Проект DG: `str-openings-01`. Вводить в DG Web UI → Graph → консоль, режим **Ingest**, **по одному правилу**, после каждого — сверка в Neo4j (Claude). Класс и свойства названы в тексте явно: так конвейер не переиспользует чужой класс (находка F12 v12) и генератор скриптов находит калькулятор по имени свойства.

| # | Текст для ввода | Ожидаемое тело |
|---|---|---|
| R1 | Отверстие OpeningBox не допускается в балках: нарушение, если свойство hasBeamIntersectionCount бокса OpeningBox больше 0. | `OpeningBox(?b) ^ hasBeamIntersectionCount(?b, ?n) ^ swrlb:greaterThan(?n, 0)` |
| R2 | Отверстие OpeningBox не допускается в колоннах: нарушение, если свойство hasColumnIntersectionCount бокса OpeningBox больше 0. | `OpeningBox(?b) ^ hasColumnIntersectionCount(?b, ?n) ^ swrlb:greaterThan(?n, 0)` |
| R3 | Отверстие OpeningBox не допускается над дверными и оконными проёмами: нарушение, если свойство hasOpeningsBelowCount бокса OpeningBox больше 0. | `OpeningBox(?b) ^ hasOpeningsBelowCount(?b, ?n) ^ swrlb:greaterThan(?n, 0)` |
| R4 | Отверстие OpeningBox должно быть не ближе 300 мм к границе дверного или оконного проёма: нарушение, если свойство hasMinOpeningClearanceMm бокса OpeningBox меньше 300. | `OpeningBox(?b) ^ hasMinOpeningClearanceMm(?b, ?d) ^ swrlb:lessThan(?d, 300)` |

Rule_Id выбирает конвейер (находка F9 v12); генератор берёт фактические id из графа.

## Геометрические определения (приняты владельцем 2026-10-20)

- **hasBeamIntersectionCount / hasColumnIntersectionCount** — число элементов «Каркас несущий» (`OST_StructuralFraming`) / «Несущие колонны» + «Колонны» (`OST_StructuralColumns`, `OST_Columns`), чьё тело пересекает тело бокса (`ElementIntersectsSolidFilter`); если у бокса нет тела — пересечение габаритов.
- **hasOpeningsBelowCount** — число дверей, окон и проёмов в стене (`OST_Doors`, `OST_Windows`, `OST_SWallRectOpening`) в стенах, которые пересекает бокс, у которых проекция на ось стены перекрывается с боксом и верх не выше низа бокса.
- **hasMinOpeningClearanceMm** — минимальный чистый зазор в плоскости стены между габаритом бокса и габаритом проёма той же стены, мм; если в стене проёмов нет — 100000 (правило выполняется).

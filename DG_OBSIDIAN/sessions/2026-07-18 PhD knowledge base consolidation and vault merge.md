---
type: session
date: 2026-07-18
tags: [session, vault-consolidation, dissemination, research]
summary: "Консолидация PhD баз знаний из 3 источников в единый repo-vault. Создана структура dissemination/ (публикации T1–T4 + venue-статусы + consistency-map), research/ (SoA-таксономия, конспекты, ключевые слова). Архивированы старые ревизии (52 файла), удалены temp/lock-файлы (25), переведены секреты в .secrets/."
---

# Session: PhD knowledge base consolidation (2026-07-18)

## Что было сделано

### 1. Консолидация структуры вольта
**Целевая структура:** repo `DG_OBSIDIAN/` + исходные Yandex-папки (читаемы, копии не удалены).

- **`research/`** (новое) — 78 мигрированных заметок с frontmatter:
  - `soa/` — 43 заметки SoA-таксономии (10000–60000)
  - `conspects/` — 19 конспектов статей/вебинаров (включая восстановленную заметку из Couros_PC)
  - `keywords/` — 9 индексов (авторы, технологии, инструменты и т.д.)
  - `_attachments/` — 30 изображений, на которые ссылаются заметки
  - Loose: 000_SoA_Methodology, THINKBOOK, QUESTIONS, Vocabular, MAIN CONCEPT DRAFT

- **`dissemination/`** (новое, переделано из `knowledge/publications/`) — публикации и диссеминация:
  - `index.md` — MOC статуса по площадкам (ptBIM24, ptBIM26, IJAC26, ITcon T1–T4, доклады, BIMA+/ZeroSkin)
  - `venues/` — 4 venue-заметки (2024 ptBIM, 2026 ptBIM, 2026 IJAC, Conference talks) с `dev_anchor:` frontmatter, связывающим публикации со spec-версиями и фазами
  - `consistency-map.md` — обратный индекс (dev-артефакт → публикации, которые на него опираются)
  - T1–T4 (перемещены из knowledge/publications/, ссылки обновлены)

### 2. Архивирование и очистка

| Группа | Сработано | Результат |
|---|---|---|
| **G1** | Temp/lock-файлы | 25 файлов удалено (`~$*.docx`, `~WRL*.tmp`, `*.bkp`, `*.dtmp`, `*.3dmbak`) |
| **G3** | Старые ревизии статей (ptBIM26, IJAC26) | 34 файла → `99_ARCHIVE/01_Publications_Revisions/`; оставлены: latest R12 + camera-ready + абстракты |
| **G4** | SoA-презентации ревизии | Rev00/Rev01/Rev02 → `99_ARCHIVE/02_Presentations_Revisions/`; оставлена current |
| **G5** | Course/exercise bulk | `04_EXERCISES`, `04_COURCES` → архив; venv/stubs удаляются фоном (~1.2k осталось из 4.4k) |
| **G6** | Couros_PC (старый ПК) | Перемещён в архив, уникальная заметка восстановлена |
| **G9** | Секреты | DeepSeek_API_key.txt, Speckle_tokens.txt → `.secrets/` (удалены из индекса git, но остаются в истории) |

**Не трогали (утверждено):** G2 (exploded docx `unpacked_orig/_r5`), G8 (exact duplicates типа template_ptBIM).

### 3. Token-economy оптимизация

- **Knowledge routing** в CLAUDE.md: индекс-первый поиск (04-home/index.md → atlas/knowledge/research/dissemination)
- **Исключения из агент-поиска:** `.graphifyignore`, Obsidian Excluded Files (`archive/`, `graphify/communities/`)
- **Frontmatter нормализация:** все 72 мигрированные заметки получили `type/status/source/migrated`

### 4. Документация

- **MIGRATION-LOG.md** — полный аудит-трейл (что перемещено/удалено/создано, почему)
- **research/index.md**, **dissemination/index.md** — MOC с описанием структуры
- **consistency-map.md** — сопоставление публикаций с версиями spec/онтологии

## Проверки

✓ G2/G8 файлы не тронуты  
✓ Последние ревизии сохранены (IJAC_R08, ptBIM26_R12, T1_R7, 01_ptBIM26_R6)  
✓ 52 архивированных файла в 99_ARCHIVE  
✓ 78 исследовательских заметок мигрировано с frontmatter  
✓ 30 изображений скопировано в _attachments/  
✓ Link integrity: 55 wiki-links, 1 битая (была уже в исходном vault)  
✓ Ключи удалены из git-индекса (но в истории остаются)

## Оставшиеся действия

1. **Ротация ключей** — DeepSeek и Speckle токены в истории git (нужна ротация).
2. **Фоновая очистка G5** — удаление stubs продолжается (~1.2k файлов осталось).
3. **Git commit** — закоммитить:
   - Удаление ключей из индекса (staged)
   - Vault-реструктуризация: research/ + dissemination/ + MIGRATION-LOG.md + CLAUDE.md + .graphifyignore

## Знания для следующих сессий

- **Консолидированный vault** теперь в repo (git-версионирован), исходные Yandex-папки остаются источником для чтения/восстановления
- **Диссеминация связана с dev** через `dev_anchor:` frontmatter и consistency-map — при изменении spec/онтологии grep найдёт затронутые статьи
- **Research-слой** готов для дальнейшего расширения (новые конспекты, SoA-анализы, теоретические заметки)
- Старый `01_OBSIDIAN_REPOSITORY` может быть архивирован целиком отдельным решением

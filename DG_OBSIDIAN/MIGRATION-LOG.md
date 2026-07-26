---
type: log
tags: [migration, vault-maintenance]
date: 2026-07-18
summary: "Лог консолидации PhD-баз знаний: что перемещено/удалено/создано 2026-07-18. Все перемещения обратимы — источник и назначение указаны."
---

# Vault consolidation — migration log (2026-07-18)

Approved groups: G1, G3, G4, G5, G6, G9. **Not approved (untouched): G2** (`Publications/unpacked_orig|_r5`), **G8** (cross-source exact duplicates).

## Deleted (G1) — 25 temp/lock/backup files
`~$*`, `~WRL*.tmp`, `*.bkp`, `*.dtmp`, `*.3dmbak` across repo `Publications/`+root, Yandex `06_PUBLICATIONS`, `04_DEVELOPMENT`, `03_PRESENTATIONS`, `PC ADMINISTRATOR/PhD` root.

## Archived → `Yandex.Disk\Studying\03_PHD\99_ARCHIVE\`

| From | To | What |
|---|---|---|
| `06_PUBLICATIONS/2026_IJAC` | `01_Publications_Revisions/2026_IJAC` | 13 файлов: Abstract R00–R02, Article R00–R07, R09_NoFigures, DraftR03_BF. Оставлено: Abstract_R03, Article_R08 docx+pdf, 00_Source |
| `06_PUBLICATIONS/2026_ptBIM` | `01_Publications_Revisions/2026_ptBIM` | 21 файл: R01–R11 docx/pdf, R2.pdf, Revised*.pdf, UMinho unversioned. Оставлено: R12.docx, UMinho_R2 docx+pdf, абстракты, template, 00_Sources |
| repo `Publications/` | `01_Publications_Revisions/repo_Publications` | 18 файлов: T1_ITcon Draft+R2–R6 (docx/pdf), 01_ptBIM26 R2–R5, PPT instructions R2–R3. Оставлено: T1 R7 + Revision Plan, 01_ptBIM26_R6 pdf+pptx, instructions R5 |
| `03_PRESENTATIONS/00_ARCHIVE` | `02_Presentations_Revisions/00_ARCHIVE_Rev01` | SoA presentation Rev01 + sources |
| `03_PRESENTATIONS/02_SoA_Presentation_Rev00, _Rev02` | `02_Presentations_Revisions/` | SoA presentation revisions (дубли изображений Rev01↔Rev02 внутри) |
| `02_PhD_2024/04_EXERCISES` | `03_Exercises/04_EXERCISES` | Учебные проекты (Swiftlet, LunchBoxML, FastAPI, RAG, LLM-GH) |
| `01_OBSIDIAN_REPOSITORY/04_COURCES` | `03_Exercises/04_COURCES` | Курсы (Stepik Python, STEMPS C#) |
| `02_PhD_2024/Couros_PC` | `04_Couros_PC/Couros_PC` | Копии вольтов со старого ПК; уникальная заметка: `Obsidian vaults/Knowledge_DB/Literature Review/01_Source/004_From Concept to Construction...md` — скопировать в `research/conspects/` после гидрации |

## Deleted (G5, regenerable)
`04_COURCES/Stepik_Python/stubs.min` (~4.4k Python stubs), `04_EXERCISES` venv/.venv/__pycache__/.vs/vector_store (фоновая очистка).

## Secrets (G9)
`DeepSeek_API_key.txt`, `Speckle_tokens.txt` → repo `.secrets/` (добавлен в `.gitignore`), удалены из git-индекса. **Ключи остаются в истории git — требуется ротация.** `.env` возвращён в корень (нужен docker-compose, уже был в .gitignore).

## Created in vault
`research/` (index, soa/, conspects/, keywords/, _attachments/ — контент после гидрации Yandex), `dissemination/` (index, consistency-map, venues/×4; T1–T4 + Series coherence map перемещены из `knowledge/publications/`), обновлены `00-home/index.md`, `CLAUDE.md` (Knowledge routing), `.graphifyignore`, `.obsidian/app.json` (excluded: archive/, graphify/communities/).

## Migration completed 2026-07-18 (after Yandex hydration)
- `research/`: 78 md (43 soa + 19 conspects incl. Couros_PC note + 9 keywords + 6 loose + index) + 30 изображений в `_attachments/`.
- Frontmatter (`type/status/source/migrated`) добавлен 72 заметкам без YAML.
- Link check: 55 wiki-links, 1 реально битая (`001_IFC-graph for facilitating building information access and query` — отсутствовала уже в исходном vault).
- Исходные заметки в `02_PhD_2024/01_OBSIDIAN_REPOSITORY` НЕ удалены (копия, не перенос) — старый vault можно архивировать целиком отдельным решением.

## Pending
1. Фоновая очистка G5 (venv/stubs) продолжается — проверить `99_ARCHIVE/03_Exercises/04_COURCES/Stepik_Python` позже.
2. Ротация ключей DeepSeek/Speckle (остаются в истории git).
3. Закоммитить изменения репозитория (staged: удаление ключей из индекса; unstaged: vault-реструктуризация).

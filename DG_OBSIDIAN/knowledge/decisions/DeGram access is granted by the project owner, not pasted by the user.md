---
tags: [decision, degram, phase-1301, security, ux]
date: 2026-10-11
---

# DeGram access is granted by the project owner, not pasted by the user (D-39..D-44)

## Context

The 0.1.9 live UAT worked, but the owner found the access flow and the shell too technical: users created their own `dgp_` pairing token in the DG Web UI and pasted it into DeGram; after a project was chosen DeGram jumped straight into a Hermes chat with the full inherited sidebar.

## Decision (owner, 2026-10-11)

- **D-39:** a DG admin or the project owner issues a server-side grant on CONNECTORS for a chosen project member (name + purpose). The key stays on the server and is never shown. DeGram exchanges the user's DG cookie session for a delegated token only while an active grant exists (`POST /auth/degram/session-exchange`). User-created pairing is retired.
- **D-40:** inside DeGram, Коннекторы is a trimmed DG page: the user's own grants and «Запросить новый токен».
- **D-41:** after the project choice DeGram stays on the DG ring; the «Начать новую сессию» pill appears under Sign out; chats open only from the pill or history.
- **D-42:** sidebar = Новая сессия, Граф проекта, Валидатор, Коннекторы, Модели, Меню, pinned + history per project and user; nothing else from Hermes; no «DEGRAM» heading.
- **D-43:** «Модели» screen hosts document choice (Revit, Grasshopper, further bridges); the strip keeps statuses.
- **D-44:** «Подключение к DG» with the Graph Viewer sphere at the ring centre while the project opens.

## Consequences

- Plans 1301-30..36 (0.1.10). `spec/SECURITY-BOUNDARY.md` route-policy block and §3.5 change; the cookie mint `/auth/delegated-token` stays for the ui-v2 `#degram` slice.
- A fixed-vocabulary fragment channel between DeGram and the DG page: page→host `#degram-select=`, `#degram-new-session`; host→page `#degram-state=`, `#degram-go=`, `?lang=`.
- Supersedes D-33's token field and D-35's pairing notice.

---
tags: [decision, degram, phase-1301, connectors, security, ux]
date: 2026-10-11
---

# DeGram connectors table and per-connector access requests (D-45..D-48)

## Context

The 0.1.10 UAT showed that DeGram «Коннекторы» offered only the user's own DeGram access (D-40). A member could not see Grasshopper, Revit or other connectors, nor ask for access to them. Two other owner comments: the connecting state was shown twice, and a project member without a DeGram grant could not open the project.

## Decision (owner, 2026-10-11)

- **D-45:** DeGram «Коннекторы» is a table of all connectors like the DG Web UI: names in the first column, invisible row and column separators, each row «Доступен» or «Запросить доступ», status Вкл/Выкл on the right with a green (active) or red (not active) dot. Amends D-40: DeGram access is one row of the table. The Web UI keeps its monochrome status dot.
- **D-46:** «Запросить доступ» on a connector sends a request to the project owner/admin, who sees it under that connector's «Pending requests» in the Web UI and approves it; the member then creates the connector token in DeGram and only they see it. Clarification: owner and editor stay «Доступен» without a request (current rule); only a viewer requests.
- **D-47:** while a project opens there is one sphere, without a caption, exactly in the ring centre; DeGram's own «Подключение к DG» loader is removed for that state; the pre-paint loader stays. Amends D-44.
- **D-48:** membership (even editor) without a DeGram grant does not open the project in DeGram; the grant stays separate. Confirms D-39. A refused pick must keep the open project or return to the start screen with the notice.

## Alternatives rejected

- Access through the project role only (no per-connector right).
- Owner creates the token and passes it on outside the system.
- Automatic DeGram access for every editor/owner (would change D-39).

## Consequences

- Plan 1301-40: new store `connector-access.json`, five routes (`/connector-access-requests`, `/connector-access/mine`, `/projects/{project}/connector-access` GET/POST/DELETE), `GET /connectors?project=` with an `access` field. The credential POST policy role drops from editor to viewer, and the handler enforces role ≥ editor or an approved access (403 `CONNECTOR_ACCESS_REQUIRED`). `spec/SECURITY-BOUNDARY.md` route-policy block grows to 109 rows. New CSS token `--status-on`.
- Plans 1301-37 (D-48 refusal path), 1301-39 (D-47), build 0.1.11 in 1301-41.

## Related

- [[knowledge/decisions/DeGram access is granted by the project owner, not pasted by the user]]
- [[knowledge/debugging/DeGram refused project pick released the open project first (F-07)]]
- [[sessions/2026-10-11 DeGram 0.1.10 UAT and 0.1.11 fix round planned]]

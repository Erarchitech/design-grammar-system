---
tags: [decision, degram, connectors, grants, phase-1308]
date: 2026-10-12
---

# Connector access is a per-connector grant without tokens, owner and admin exempt (D-49)

## Context

0.1.11 UAT step 6: a project member (editor) could create a Grasshopper token without a grant from the project owner. The code allowed it by design: `POST /connectors/{id}/credentials` admits owner, editor and admin directly and asks `connector_access` only of a viewer (D-46). The owner asked whether one common grant covers all connectors. It does not: connector access is already stored per `(username, project, connector_id)`, and the DeGram grant is a separate store.

## Decision (owner, 2026-10-12)

- A grant is issued per connector, separately for each.
- Connector tokens are not created at all; only the grant exists. The Grasshopper add-in signs in with the user's own account, as DeGram does.
- The project owner and the DG admin are exempt from the grant. Editor and viewer need one (the editor part is inferred from the step-6 remark).
- Planned in Phase 1308, not in a Phase 1301 gap round.

## Consequences

- Amends D-46: the token reveal flow is retired, and an editor loses the direct path.
- The add-in authentication changes from the connector token plus `POST /connectors/heartbeat` (`ConnectorHeartbeatClient.cs`, `ConnectorComponent.cs`) to an account sign-in; `spec/SECURITY-BOUNDARY.md`, the route policy and the connector spec change with it.
- Open: the meaning of the status «Вкл» without a token heartbeat. Today it means a token use or a DeGram grant exchange within 7 days (`connectors.derive_status`), not «Grasshopper is open now».

## Related

- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` (D-46, D-49), `1301-UAT.md` § 0.1.11, `.planning/phases/1308-dg-web-ui/1308-SEED.md`
- [[knowledge/decisions/DeGram connectors table and per-connector access requests (D-45..D-48)]]
- [[sessions/2026-10-12 Phase 1301 gap plans 37-41 executed, DeGram 0.1.11 built and UAT result]]

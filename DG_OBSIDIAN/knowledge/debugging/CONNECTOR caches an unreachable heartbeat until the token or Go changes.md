---
tags: [debugging, grasshopper, connector, auth, open]
date: 2026-10-05
status: open
---

# CONNECTOR caches an unreachable heartbeat until the token or Go changes (F14)

## Symptom

After the containers were restarted (data-service briefly down), CONNECTOR stayed at **"Connect failed · Auth unreachable"** with `Project = default-project`, even though `POST /connectors/heartbeat` already answered (401 for a bad token, 200 for the real one). Re-solving the component did not help. Downstream components received a not-connected handle to `default-project` with no error of their own.

## Cause

`ConnectorComponent` keeps `_connectTask` keyed by the token hash and starts a new heartbeat only when there is no task or the token changes. A completed `Unreachable` result is reused on every solution.

## Workaround

Toggle `Go` False → True (CancelPendingConnection resets the task). After that, the CONNECTOR showed "Connected · Auth OK" (2026-10-05).

## Proposed fix

Retry the heartbeat on re-solve when the previous outcome was `Unreachable`, and do not reuse it.

## Related

- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]

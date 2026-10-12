# Release Notes — v13.0 "DeGram Agent"

## Phase 1308 — connector sign-in

The Grasshopper add-in now signs in with your DG account instead of a pasted
connector token.

### What changed

- **Connector tokens are retired.** The Connectors screen no longer creates
  them, and the server answers `410 CONNECTOR_TOKENS_RETIRED` on
  `POST /connectors/{id}/credentials`. Old `dgc_` tokens are no longer accepted
  anywhere.
- **CONNECTOR** has a new component GUID and new ports:
  inputs `Username`, `Password`, `Project` (optional) and `Connect`; outputs
  `Database`, `Project` and `Session`.
- **VALIDATOR** and **COMPUTGRAPH PUBLISH** keep their GUIDs and port order.
  Their `Token` input now takes `CONNECTOR.Session`.
- `Connect = false`, or deleting the CONNECTOR, ends the session; the connector
  then reads off in the web UI immediately. A session also expires after 8 hours.
- Owners and admins can use the connector without a grant. **Editors and
  viewers need a grant per connector**: ask a project owner to grant access on
  the Connectors screen.
- The account password and the session are never saved in a `.gh` file.
  `Username`, `Password` and `Token` are cleared when the canvas is saved, so
  enter them again when you reopen it.
- Sign-in over plain `http://` to a non-local host is refused and sends no
  password.
- A masked password dialog is not part of this release (D-38). The password is
  typed into the `Password` input, which shows it as plain text on the canvas;
  do not share screenshots of that panel.

### Re-wiring a saved canvas

Because the CONNECTOR component changed, a canvas saved with the old CONNECTOR
shows a missing-component placeholder in its place. Re-wire it once:

1. Delete the CONNECTOR placeholder.
2. Place the new **CONNECTOR** component (DG tab, Graph group).
3. Enter `Username` and `Password` for your DG account. If your account has more
   than one eligible project, also enter `Project`.
4. Set `Connect` to true. The component shows "Connected" when sign-in and the
   graph connection succeed.
5. Wire the `Database` and `Project` outputs where the old CONNECTOR outputs
   were wired.
6. Wire the `Session` output into `VALIDATOR.Token` and
   `COMPUTGRAPH PUBLISH.Token`.

If sign-in fails, the CONNECTOR message says why: wrong username or password,
no connector grant for the account, a project that must be named, or
data-service not reachable.

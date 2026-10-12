# API Coverage — DG data-service API used by Phase 1308 clients

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> Detector note: `api-coverage.cjs` fired on the 1308 plan scope (signals "wire … API", "connect … SDK"). The phase integrates no third-party API; the surface below is the project's own data-service API as consumed by the two clients this phase changes: the Grasshopper add-in (`DG.Core` `ConnectorSessionClient`, plans 1308-04/07) and the Web UI (`ui-v2`, plans 1308-10/11/15). Every connector-facing and 1308-touched route is listed.

| capability | decision | reason |
|---|---|---|
| addin.auth-login (POST /auth/login) | INTEGRATE | |
| addin.auth-logout (POST /auth/logout) | INTEGRATE | |
| addin.connector-session-mint (POST /auth/connector-session) | INTEGRATE | |
| addin.connector-session-revoke (DELETE /auth/connector-session) | INTEGRATE | |
| addin.validation-publish (POST /validation/publish) | INTEGRATE | |
| addin.computgraph-publish (POST /computgraph/publish) | INTEGRATE | |
| addin.validation-view (GET /validation/view/{project}, /{run_id}) | INTEGRATE | |
| addin.designstate-capture (POST /designstate/capture) | INTEGRATE | |
| addin.connector-heartbeat (POST /connectors/heartbeat) | OPT-OUT | not needed — D-27 drops the add-in's periodic heartbeat; status derives from live sign-in sessions; the route stays server-side for other connectors |
| addin.auth-me (GET /auth/me) | OPT-OUT | not needed — the server picks the only eligible project when Project is blank (D-36); the add-in keeps no project list |
| addin.connector-access-request (POST /connector-access-requests) | OPT-OUT | explicitly out of scope — access requests are made from the Web UI and the DeGram table (D-39, D-40) |
| addin.connectors-list (GET /connectors) | OPT-OUT | not needed — connector status is shown in the Web UI, not in Grasshopper |
| addin.credentials-create (POST /connectors/{id}/credentials) | OPT-OUT | explicitly out of scope — retired with 410 CONNECTOR_TOKENS_RETIRED (D-31) |
| addin.credentials-revoke (DELETE /connectors/{id}/credentials/{credential_id}) | OPT-OUT | not needed — cleanup route kept one release for owners only (D-31); retirement runs through d49_store_cleanup.py (D-47) |
| webui.member-role-change (PUT /projects/{project}/members/{username}) | INTEGRATE | |
| webui.members-list (GET /projects/{project}/members) | INTEGRATE | |
| webui.degram-policy-read (GET /projects/{project}/degram-policy) | INTEGRATE | |
| webui.degram-policy-write (PUT /projects/{project}/degram-policy) | INTEGRATE | |
| webui.project-summary (GET /projects/{project}/summary) | INTEGRATE | |
| webui.validation-runs (GET /validation/runs/{project}) | INTEGRATE | |
| webui.llm-settings-read (GET /llm/settings) | INTEGRATE | |
| webui.reasoner-settings-read (GET /reasoner/settings) | INTEGRATE | |
| webui.connectors-list (GET /connectors?project=) | INTEGRATE | |
| webui.connector-access-grant (POST /projects/{project}/connector-access) | INTEGRATE | |
| webui.connector-access-revoke (DELETE /projects/{p}/connector-access/{id}) | INTEGRATE | |
| webui.connector-access-list (GET /projects/{project}/connector-access) | INTEGRATE | |
| webui.connector-access-request (POST /connector-access-requests) | INTEGRATE | |
| webui.connector-access-mine (GET /connector-access/mine) | INTEGRATE | |
| webui.credentials-create (POST /connectors/{id}/credentials) | OPT-OUT | explicitly out of scope — token flow removed from the Web UI (D-39) and retired server-side (D-31) |
| webui.credentials-revoke (DELETE /connectors/{id}/credentials/{credential_id}) | OPT-OUT | explicitly out of scope — token UI removed (D-39); the deferred removal of this route is a later phase |

// Authentication — account login, connector session and access policy

export default {
  id: "authentication",
  title: "Authentication",
  pages: [
    {
      id: "principal-types",
      title: "Principal Types",
      summary: "Browser sessions and connector sessions have different scopes; project data is never anonymous.",
      blocks: [
        { type: "text", content: "The data-service denies routes by default. An add-in first signs in with a DG account, then obtains its own short-lived connector session for one project and connector." },
        { type: "table", headers: ["Principal", "Credential", "Used by"], rows: [
          ["Browser session", "HttpOnly dg_session cookie from POST /auth/login, plus X-DG-CSRF: 1 on unsafe requests", "Web UI and add-in sign-in"],
          ["Connector session", "Bearer dgk_... for one user, project and connector; expires after 8 hours", "Connector heartbeat and authorized connector routes"],
          ["Internal service token", "Shared secret held by the stack, never issued to users", "n8n workflows calling the data-service"],
        ] },
        { type: "text", content: "In the multi-user profile, project owners invite accounts; the invitee accepts a one-time code and sets a password. The local profile can also offer self-registration. Project owner or DG admin access is included with the role. An editor or viewer needs an active per-connector grant from an owner or admin." },
        { type: "endpoint", method: "GET", path: "/data-service/auth/options", description: "Public. Reports whether self-registration is available.", params: [], response: 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"selfRegistration": true}' },
        { type: "endpoint", method: "POST", path: "/data-service/auth/register", description: "Available only when self-registration is enabled. Requires X-DG-CSRF: 1.", params: [
          { name: "username", type: "string", location: "body", required: true, description: "Account name" },
          { name: "password", type: "string", location: "body", required: true, description: "Account password" },
        ] },
      ],
    },
    {
      id: "token-format",
      title: "Connector Session",
      summary: "A connector session is issued after account login and scoped to one connector and project.",
      blocks: [
        { type: "endpoint", method: "POST", path: "/data-service/auth/login", description: "Sign in with your DG account; keep the returned HttpOnly session cookie for the next call.", params: [
          { name: "username", type: "string", location: "body", required: true, description: "DG account username" },
          { name: "password", type: "string", location: "body", required: true, description: "DG account password" },
        ], request: 'POST /data-service/auth/login\nContent-Type: application/json\nX-DG-CSRF: 1\n\n{"username":"alice@example.org","password":"your-password"}', response: "HTTP/1.1 200 OK\nSet-Cookie: dg_session=...; HttpOnly; SameSite=Strict" },
        { type: "endpoint", method: "POST", path: "/data-service/auth/connector-session", description: "Exchange the account cookie for an 8-hour dgk_ session; requires X-DG-CSRF: 1. A blank project chooses the only eligible project or returns 422 PROJECT_REQUIRED if there are several.", params: [
          { name: "project", type: "string | null", location: "body", required: false, description: "Selected project, or omit when exactly one project is eligible" },
          { name: "connector_id", type: "string", location: "body", required: true, description: "Registry connector identifier" },
        ], request: 'POST /data-service/auth/connector-session\nCookie: dg_session=...\nX-DG-CSRF: 1\nContent-Type: application/json\n\n{"project":"example-project","connector_id":"grasshopper"}', response: 'HTTP/1.1 201 Created\nCache-Control: no-store\n\n{"token":"dgk_...","project":"example-project","connectorId":"grasshopper","username":"alice@example.org","expiresInSeconds":28800}' },
        { type: "note", variant: "warning", content: "The response contains the session credential. Keep it inside the add-in, never log it or show it in the Web UI. A Neo4j connection bundle is included only in the local deployment profile, not the multi-user profile." },
      ],
    },
    {
      id: "creating-credentials",
      title: "Signing In From an Add-in",
      summary: "Authenticate as a user, select a project, and request connector access if required.",
      blocks: [
        { type: "text", content: "Use POST /auth/login with your DG account, then POST /auth/connector-session with the connector_id and project. Present the resulting dgk_ Bearer on permitted connector endpoints. Owners and admins are exempt from per-connector grants; editors and viewers request access from the Connectors screen and wait for an owner or admin to grant it." },
        { type: "note", variant: "info", content: "A missing grant answers 403 CONNECTOR_ACCESS_REQUIRED. A non-member answers 403 PROJECT_FORBIDDEN. The session ends on sign-out, expiry or relevant access changes; sign in again when needed." },
      ],
    },
    {
      id: "token-lifecycle",
      title: "Signing Out",
      summary: "Revoke the current connector session from the add-in.",
      blocks: [
        { type: "endpoint", method: "DELETE", path: "/data-service/auth/connector-session", description: "Sign out the presented connector session. Subsequent calls with it answer 401 CONNECTOR_SESSION_ENDED.", params: [
          { name: "Authorization", type: "string", location: "header", required: true, description: "Bearer dgk_... from connector sign-in" },
        ], request: "DELETE /data-service/auth/connector-session\nAuthorization: Bearer dgk_...", response: "HTTP/1.1 204 No Content" },
        { type: "text", content: "An expired session answers 401 CONNECTOR_SESSION_EXPIRED. Unknown or malformed Bearers answer 401 CONNECTOR_AUTH_FAILED. Sign in again instead of trying to extend an expired session." },
      ],
    },
  ],
};

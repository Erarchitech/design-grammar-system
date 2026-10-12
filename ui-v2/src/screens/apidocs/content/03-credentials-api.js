// Connector sign-in session reference (keeps the section id for existing links)

export default {
  id: "credentials-api",
  title: "Connector Sign-in Sessions",
  pages: [
    {
      id: "create-credential",
      title: "Start a Connector Session",
      summary: "After account login, issue a short-lived session for the selected project and connector.",
      blocks: [
        { type: "text", content: "The add-in signs in with the user's DG account via POST /auth/login, retains the cookie, then requests POST /auth/connector-session. This creates a user-, project- and connector-bound dgk_ Bearer for eight hours. The response must not be cached or logged." },
        { type: "endpoint", method: "POST", path: "/data-service/auth/connector-session", description: "Create a connector session using the signed-in user's cookie and X-DG-CSRF: 1. Owners and admins are exempt; editors and viewers require an active grant for that connector.", params: [
          { name: "project", type: "string | null", location: "body", required: false, description: "Project, omitted only when exactly one eligible project exists" },
          { name: "connector_id", type: "string", location: "body", required: true, description: "Registry connector identifier" },
        ], request: 'POST /data-service/auth/connector-session\nCookie: dg_session=...\nX-DG-CSRF: 1\nContent-Type: application/json\n\n{"project":"example-project","connector_id":"grasshopper"}', response: 'HTTP/1.1 201 Created\nCache-Control: no-store\n\n{"token":"dgk_...","project":"example-project","connectorId":"grasshopper","expiresInSeconds":28800}' },
        { type: "note", variant: "warning", content: "The old POST /data-service/connectors/{connector_id}/credentials creation route is retired. A signed-in caller receives 410 CONNECTOR_TOKENS_RETIRED; it creates nothing. Do not use it to sign in." },
      ],
    },
    {
      id: "revoke-credential",
      title: "End a Connector Session",
      summary: "Sign out from the add-in to end the presented session immediately.",
      blocks: [
        { type: "endpoint", method: "DELETE", path: "/data-service/auth/connector-session", description: "Revoke the presented connector session. A later request using it answers 401 CONNECTOR_SESSION_ENDED.", params: [
          { name: "Authorization", type: "string", location: "header", required: true, description: "Bearer dgk_... issued to this add-in" },
        ], request: "DELETE /data-service/auth/connector-session\nAuthorization: Bearer dgk_...", response: "HTTP/1.1 204 No Content" },
        { type: "text", content: "The old credential deletion route exists for cleanup of stored legacy records for one release; it does not revoke a dgk_ session. Use DELETE /auth/connector-session for sign-out." },
      ],
    },
  ],
};

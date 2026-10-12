// Heartbeat API — connector session status reporting

export default {
  id: "heartbeat-api",
  title: "Heartbeat API",
  pages: [
    {
      id: "send-heartbeat",
      title: "Send Heartbeat",
      summary: "An add-in presents its signed-in connector session to report a heartbeat.",
      blocks: [
        { type: "text", content: "After POST /auth/login and POST /auth/connector-session, the add-in sends its dgk_ Bearer to the heartbeat endpoint. The server refreshes last_seen for that session and reports status for its bound connector and project." },
        { type: "endpoint", method: "POST", path: "/data-service/connectors/heartbeat", description: "Touch the current connector session and return the derived status and bound project.", params: [
          { name: "Authorization", type: "string", location: "header", required: true, description: "Bearer dgk_... from connector sign-in" },
        ], request: "POST /data-service/connectors/heartbeat\nAuthorization: Bearer dgk_...", response: 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"connector_id":"grasshopper","status":"active","project":"example-project","neo4j":null}' },
        { type: "note", variant: "info", content: "The neo4j bundle is returned only in the local deployment profile. It is omitted in the multi-user profile; do not depend on direct Bolt access there." },
        { type: "code", label: "Session failures", content: "401 CONNECTOR_SESSION_EXPIRED — sign in again\n401 CONNECTOR_SESSION_ENDED — sign in again after sign-out or revocation\n401 CONNECTOR_AUTH_FAILED — invalid or unsupported Bearer" },
      ],
    },
    {
      id: "status-semantics",
      title: "Status Semantics",
      summary: "The registry reflects connector sign-in sessions, not a seven-day heartbeat window.",
      blocks: [
        { type: "text", content: "GET /connectors derives status from connector sessions in projects visible to the caller. A heartbeat touches an existing live session; last_connection in the registry is the latest sign-in time. The DeGram card has a separate grant-based, seven-day status rule." },
        { type: "table", headers: ["Status", "Meaning"], rows: [
          ["never_connected", "No sign-in session exists in the caller's visible projects"],
          ["active", "At least one session remains live"],
          ["stale", "A session existed, but none is live"],
        ] },
        { type: "text", content: "active_sessions counts unexpired, non-revoked sessions visible to the caller. When a session expires or is revoked, the count and status change without a new heartbeat." },
      ],
    },
  ],
};

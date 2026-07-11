// Heartbeat API — token-authenticated status reporting

export default {
  id: "heartbeat-api",
  title: "Heartbeat API",
  pages: [
    {
      id: "send-heartbeat",
      title: "Send Heartbeat",
      summary: "Connectors send heartbeats to report their status. The heartbeat endpoint is token-authenticated.",
      blocks: [
        {
          type: "text",
          content:
            "The heartbeat endpoint is called by connector components periodically (e.g., on Grasshopper solve, Revit document open) to report their connection status. The endpoint authenticates the request via the Authorization header and returns the connector's derived status.",
        },
        {
          type: "endpoint",
          method: "POST",
          path: "/data-service/connectors/heartbeat",
          description:
            "Authenticate a connector token and record a heartbeat timestamp. Returns the connector's status derived from the time since last connection.",
          params: [
            { name: "Authorization", type: "string", location: "header", required: true, description: "Bearer token with dgc_ prefix (format: Bearer dgc_<token>)" },
          ],
          request:
            'POST /data-service/connectors/heartbeat\nAuthorization: Bearer dgc_X5o8JxG2kL9pQ3rY7vB4nM1wC6fT0uA8iZ3sH5dK2eR\nContent-Type: application/json',
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "connector_id": "grasshopper",\n  "status": "active"\n}',
        },
        {
          type: "code",
          label: "Error response — invalid or revoked token",
          content:
            'HTTP/1.1 401 Unauthorized\nContent-Type: application/json\n\n{\n  "error": "Invalid or revoked connector token.",\n  "hint": "Create a new credential via POST /connectors/{connector_id}/credentials.",\n  "code": "CONNECTOR_AUTH_FAILED"\n}',
        },
        {
          type: "note",
          variant: "info",
          content:
            "The heartbeat endpoint expects the token exactly as received at creation — with the dgc_ prefix. If the connector component strips the prefix, authentication will fail with 401.",
        },
      ],
    },
    {
      id: "status-semantics",
      title: "Status Semantics",
      summary: "Connector status is derived from the most recent heartbeat timestamp and a 7-day stale threshold.",
      blocks: [
        {
          type: "text",
          content:
            "Each connector's status is computed from the most recent successful heartbeat across all of its credentials (including revoked ones — a past successful connection still happened). The status is returned by the heartbeat endpoint and the GET /connectors overview.",
        },
        {
          type: "table",
          headers: ["Status", "Meaning", "Criteria"],
          rows: [
            ["never_connected", "No heartbeat ever recorded", "last_connection is null"],
            ["active", "Heartbeat received recently", "Last connection <= 7 days ago"],
            ["stale", "Heartbeat older than threshold", "Last connection > 7 days ago, or timestamp is unparseable"],
          ],
        },
        {
          type: "text",
          content:
            "The stale threshold (STALE_THRESHOLD_DAYS = 7) is a server-side constant. Connectors that stop sending heartbeats for more than 7 days automatically transition to stale status. Sending a new heartbeat immediately restores active status.",
        },
        {
          type: "code",
          label: "Status derivation logic (simplified)",
          content:
            "def derive_status(last_connection):\n    if last_connection is None:\n        return \"never_connected\"\n    \n    age = now - parse_iso8601(last_connection)\n    if age <= timedelta(days=7):\n        return \"active\"\n    else:\n        return \"stale\"",
        },
        {
          type: "note",
          variant: "tip",
          content:
            "After creating a new credential, send a heartbeat immediately to confirm the token works and to set the initial status to active.",
        },
      ],
    },
  ],
};

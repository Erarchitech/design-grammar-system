// Getting Started — base URL, proxy paths, API conventions

export default {
  id: "getting-started",
  title: "Getting Started",
  pages: [
    {
      id: "overview",
      title: "Overview",
      summary: "DG connectors sign in with a user's account to access a project and report connection status.",
      blocks: [
        { type: "text", content: "Sign in from your add-in with your DG account. The add-in exchanges its login cookie for a short-lived, project- and connector-bound session and presents that session as a Bearer credential on connector routes. Project owners and DG admins have connector access automatically; editors and viewers need a grant from an owner or admin." },
        { type: "note", variant: "info", content: "The Web UI displays connector access and live sign-ins; it does not issue connector credentials. Sign out from the add-in to revoke its session." },
      ],
    },
    {
      id: "base-url",
      title: "Base URL and Proxying",
      summary: "All API paths are proxied through the Nginx reverse proxy at port 8080.",
      blocks: [
        { type: "text", content: "The V2 UI's Nginx reverse proxy (port 8080) forwards /data-service/ and /llm/ paths to the data-service container (port 8000). When you deploy the DG stack, use the V2 UI URL as your base." },
        { type: "table", headers: ["Public Path", "Upstream", "Description"], rows: [
          ["/data-service/*", "http://data-service:8000", "Connector and validation endpoints"],
          ["/llm/*", "http://data-service:8000", "LLM gateway settings and generation"],
          ["/reasoner/*", "http://data-service:8000", "Reasoner endpoints (session-authenticated)"],
        ] },
        { type: "text", content: "The proxy strips the /data-service prefix before forwarding. For example, GET /data-service/connectors reaches the data-service as GET /connectors. Graph reads and writes go through named data-service endpoints; rule ingest and graph queries use the data-service workflow relay." },
        { type: "code", label: "Base URL example (docker-compose deployment)", content: "# From outside (browser / add-in):\n#   http://<host>:8080/data-service/connectors\n#   http://<host>:8080/data-service/auth/login" },
      ],
    },
    {
      id: "conventions",
      title: "API Conventions",
      summary: "Standard patterns used across DG API endpoints.",
      blocks: [
        { type: "text", content: "The authentication method depends on the route and principal. Browser-session mutations require X-DG-CSRF: 1; connector routes use the add-in's scoped session Bearer." },
        { type: "table", headers: ["Convention", "Detail"], rows: [
          ["Method", "GET for reads, POST for creates, PUT for updates, DELETE for removals"],
          ["Request body", "JSON, with Content-Type: application/json"],
          ["Response format", "JSON object or array; errors use structured JSON with error/hint/code fields"],
          ["Authentication", "dg_session cookie plus X-DG-CSRF on unsafe session requests; Authorization: Bearer dgk_... for connector routes"],
          ["Status codes", "200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 410 Gone, 422 Unprocessable Entity"],
          ["Error format", '{"error": "...", "hint": "...", "code": "..."}'],
        ] },
      ],
    },
  ],
};

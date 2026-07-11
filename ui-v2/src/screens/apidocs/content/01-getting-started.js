// Getting Started — base URL, proxy paths, API conventions

export default {
  id: "getting-started",
  title: "Getting Started",
  pages: [
    {
      id: "overview",
      title: "Overview",
      summary: "The DG Connector API lets third-party tools (Grasshopper, Revit, Dynamo, etc.) authenticate, report status, and publish validation results to the Design Grammar system.",
      blocks: [
        {
          type: "text",
          content:
            "The API follows a resource-oriented design. Every endpoint is served through the V2 UI's reverse proxy at port 8080. All request and response bodies use JSON. All endpoints that write require a valid connector token in the Authorization header.",
        },
        {
          type: "note",
          variant: "info",
          content:
            "Connector tokens use the dgc_ prefix. They are generated server-side, returned exactly once on creation, and never stored in plaintext — only the SHA-256 hash is persisted.",
        },
      ],
    },
    {
      id: "base-url",
      title: "Base URL and Proxying",
      summary: "All API paths are proxied through the Nginx reverse proxy at port 8080.",
      blocks: [
        {
          type: "text",
          content:
            "The V2 UI's Nginx reverse proxy (port 8080) forwards /data-service/ and /llm/ paths to the data-service container (port 8000). When you deploy the DG stack, use the V2 UI URL as your base.",
        },
        {
          type: "table",
          headers: ["Public Path", "Upstream", "Description"],
          rows: [
            ["/data-service/*", "http://data-service:8000", "Connector and validation endpoints"],
            ["/llm/*", "http://data-service:8000", "LLM gateway settings and generation"],
            ["/neo4j/*", "http://neo4j:7474", "Direct Neo4j HTTP API (not for connectors)"],
            ["/n8n/*", "http://n8n:5678", "n8n workflow webhooks (not for connectors)"],
          ],
        },
        {
          type: "text",
          content:
            "The proxy strips the /data-service prefix before forwarding. For example, GET /data-service/connectors reaches the data-service as GET /connectors.",
        },
        {
          type: "code",
          label: "Base URL example (docker-compose deployment)",
          content:
            "# Inside the docker network, the data-service container is reachable at:\n#   http://data-service:8000\n#\n# From outside (browser / connector component):\n#   http://<host>:8080/data-service/connectors\n#   http://<host>:8080/llm/settings",
        },
      ],
    },
    {
      id: "conventions",
      title: "API Conventions",
      summary: "Standard patterns used across all DG API endpoints.",
      blocks: [
        {
          type: "text",
          content: "All endpoints follow these conventions:",
        },
        {
          type: "table",
          headers: ["Convention", "Detail"],
          rows: [
            ["Method", "GET for reads, POST for creates, PUT for updates, DELETE for removals"],
            ["Request body", "JSON, with Content-Type: application/json"],
            ["Response format", "JSON object or array; errors use structured JSON with error/hint/code fields"],
            ["Authentication", "Bearer token in the Authorization header (format: Authorization: Bearer dgc_<token>)"],
            ["Status codes", "200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 404 Not Found, 500 Internal Server Error"],
            ["Error format", '{"error": "...", "hint": "...", "code": "..."}'],
          ],
        },
      ],
    },
  ],
};

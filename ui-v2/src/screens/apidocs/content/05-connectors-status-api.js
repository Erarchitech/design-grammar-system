// Connectors Status API — query connector registry and status overview

export default {
  id: "connectors-status-api",
  title: "Connectors Status API",
  pages: [
    {
      id: "list-connectors",
      title: "List All Connectors",
      summary: "Retrieve the full connector registry with per-connector status and credential summaries.",
      blocks: [
        {
          type: "endpoint",
          method: "GET",
          path: "/data-service/connectors",
          description:
            "Returns the connector registry joined with per-connector status, last-connection date, and credential summaries. Never exposes tokens or token hashes (CONNB-01, CONNB-04).",
          params: [],
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "categories": [\n    "VPL Platforms",\n    "BIM Authoring",\n    "BIM Coordination",\n    "BCF Trackers",\n    "Visualization"\n  ],\n  "connectors": [\n    {\n      "id": "grasshopper",\n      "name": "Grasshopper",\n      "category": "VPL Platforms",\n      "status": "active",\n      "last_connection": "2026-07-10T14:30:00.000000",\n      "credentials": [\n        {\n          "credential_id": "a1b2c3d4e5f6g7h8i9j0k1l2",\n          "label": "Office workstation",\n          "created_at": "2026-07-01T10:00:00.000000",\n          "revoked": false\n        }\n      ]\n    },\n    {\n      "id": "dynamo",\n      "name": "Dynamo",\n      "category": "VPL Platforms",\n      "status": "never_connected",\n      "last_connection": null,\n      "credentials": []\n    }\n  ]\n}',
        },
        {
          type: "text",
          content:
            "The GET /connectors endpoint is unauthenticated. It provides a read-only view of the connector ecosystem. The response structure mirrors the connector registry with live status enrichment:",
        },
        {
          type: "table",
          headers: ["Field", "Type", "Description"],
          rows: [
            ["id", "string", "Connector identifier used in path parameters"],
            ["name", "string", "Human-readable display name"],
            ["category", "string", "One of the five connector categories"],
            ["status", "string", "Derived status: never_connected | active | stale"],
            ["last_connection", "string | null", "ISO 8601 timestamp of the most recent heartbeat"],
            ["credentials", "array", "Summary list of credential records (never includes tokens or hashes)"],
          ],
        },
        {
          type: "code",
          label: "Full connector ID list",
          content:
            "Connector IDs (use in path parameters):\n  grasshopper, dynamo, revit, blender, tekla,\n  archicad, civil3d, infraworks, navisworks,\n  solibri, bimcollab, bimtrack, lumion, twinmotion\n\n5 categories — 14 connectors total",
        },
      ],
    },
  ],
};

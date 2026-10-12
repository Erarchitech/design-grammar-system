// Connectors Status API — registry and project-scoped sign-in overview

export default {
  id: "connectors-status-api",
  title: "Connectors Status API",
  pages: [
    {
      id: "list-connectors",
      title: "List All Connectors",
      summary: "Read the registry with session-derived status, visible sign-in counts, and optional project access.",
      blocks: [
        { type: "endpoint", method: "GET", path: "/data-service/connectors?project={project}", description: "Requires a DG browser session. Returns all registry connector names, but derives status from sessions in the caller's visible projects. With a project membership, each registry connector also includes the caller's access state.", params: [
          { name: "project", type: "string", location: "query", required: false, description: "Project for per-connector access state" },
        ], response: 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"categories":["VPL Platforms"],"connectors":[{"id":"grasshopper","name":"Grasshopper","category":"VPL Platforms","status":"active","last_connection":"2026-10-12T14:30:00Z","active_sessions":1,"access":"available"}]}' },
        { type: "text", content: "A member sees only sessions from projects they belong to; a DG admin sees sessions from all projects. No historical credential list is exposed. The DeGram card is separate and keeps its grant-based status behavior." },
        { type: "table", headers: ["Field", "Type", "Description"], rows: [
          ["id", "string", "Connector identifier"],
          ["name", "string", "Display name"],
          ["category", "string", "Registry category"],
          ["status", "string", "active (live sign-in), stale (past session, none live), never_connected (none ever)"],
          ["last_connection", "string | null", "Latest sign-in time in UTC, not last heartbeat"],
          ["active_sessions", "number", "Live, unexpired sign-ins in the caller's visible projects"],
          ["access", "string | omitted", "With an accessible project: available, pending, or requestable"],
        ] },
        { type: "code", label: "Connector identifiers", content: "grasshopper, dynamo, revit, blender, tekla,\narchicad, civil3d, infraworks, navisworks,\nsolibri, bimcollab, bimtrack, lumion, twinmotion" },
      ],
    },
  ],
};

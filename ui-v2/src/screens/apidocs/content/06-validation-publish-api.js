// Validation Publish API — publish, list, view, and delete validation runs

export default {
  id: "validation-publish-api",
  title: "Validation Publish API",
  pages: [
    {
      id: "publish-validation",
      title: "Publish Validation",
      summary: "Publish validation results to Speckle. Requires Speckle integration configuration.",
      blocks: [
        {
          type: "text",
          content:
            "The validation publish endpoint accepts a complete validation run payload: rules evaluated, entities with statuses, and an optional design state snapshot. It publishes the results to the configured Speckle project as a new version on the validation model.",
        },
        {
          type: "endpoint",
          method: "POST",
          path: "/data-service/validation/publish",
          description:
            "Publish validation results. Creates a Speckle version, stores the run metadata in Neo4j (ValidationRun + per-entity ValidationEntity records), and returns run details.",
          params: [
            { name: "project", type: "string", location: "body", required: true, description: "DG project name" },
            { name: "statePayloadJson", type: "string | null", location: "body", required: false, description: "Captured DesignState snapshot as JSON (DS_/OS_-prefixed stateId values)" },
            { name: "validStatus", type: "array[bool] | null", location: "body", required: false, description: "Per-ObjState Boolean list, index-matched to DesignState.ObjStates order" },
            { name: "rules", type: "array", location: "body", required: false, description: "List of rules evaluated (ruleId, ruleName, ruleDescription)" },
            { name: "ruleResults", type: "array", location: "body", required: false, description: "Per-rule pass/fail results (ruleId, passed, failedEntityIds, passedEntityIds)" },
            { name: "entities", type: "array", location: "body", required: false, description: "List of entities with geometry, rule statuses, and overallStatus" },
          ],
          request:
            'POST /data-service/validation/publish\nContent-Type: application/json\n\n{\n  "project": "my-project",\n  "statePayloadJson": "{...}",\n  "validStatus": [true, false, true],\n  "rules": [\n    {\n      "ruleId": "R_URB_HEIGHT_MAX_75_V",\n      "ruleName": "Maximum building height",\n      "ruleDescription": "Building height must not exceed 75 meters"\n    }\n  ],\n  "ruleResults": [\n    {\n      "ruleId": "R_URB_HEIGHT_MAX_75_V",\n      "passed": false,\n      "failedEntityIds": ["entity_002"],\n      "passedEntityIds": ["entity_001", "entity_003"]\n    }\n  ],\n  "entities": [\n    {\n      "dgEntityId": "entity_001",\n      "displayName": "Building A",\n      "ruleIds": ["R_URB_HEIGHT_MAX_75_V"],\n      "overallStatus": "passed"\n    },\n    {\n      "dgEntityId": "entity_002",\n      "displayName": "Building B",\n      "ruleIds": ["R_URB_HEIGHT_MAX_75_V"],\n      "geometry": {\n        "units": "m",\n        "items": []\n      },\n      "overallStatus": "failed"\n    }\n  ]\n}',
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "status": "published",\n  "runId": "a1b2c3d4e5f6g7h8i9j0k1l2",\n  "validationModelId": "validation-model-uuid",\n  "validationVersionId": "version-uuid",\n  "baseVersionId": "base-version-uuid",\n  "modelViewerUrl": "http://localhost:8090/projects/.../models/...@"\n}',
        },
        {
          type: "text",
          content:
            "The publish endpoint performs the following steps:",
        },
        {
          type: "table",
          headers: ["Step", "Description"],
          rows: [
            ["1. Check config", "Loads Speckle IntegrationConfig for the project; auto-configures from env vars if absent"],
            ["2. Validate settings", "Checks that Speckle write token is configured"],
            ["3. Build Speckle client", "Connects to Speckle server with configured credentials"],
            ["4. Get/create validation model", "Resolves or creates the validation model in the Speckle project"],
            ["5. Get base version", "Fetches the latest version of the base model for diff context"],
            ["6. Publish version", "Sends validation geometry and overlay data to Speckle as a new version"],
            ["7. Store run metadata", "Saves run record and ValidationEntity records to Neo4j ValidGraph"],
          ],
        },
        {
          type: "note",
          variant: "info",
          content:
            "The request body includes an overallStatus per entity ('passed', 'failed', 'unknown') plus per-rule breakdowns in ruleResults. The geometry field on each entity carries colored mesh data that Speckle renders as overlays on the 3D model.",
        },
      ],
    },
    {
      id: "list-validation-runs",
      title: "List Validation Runs",
      summary: "Retrieve all validation runs for a project.",
      blocks: [
        {
          type: "endpoint",
          method: "GET",
          path: "/data-service/validation/runs/{project}",
          description:
            "Returns all validation runs for the specified project, ordered by creation date (newest first). Each run includes rule summaries, entity counts, and a state projection.",
          params: [
            { name: "project", type: "string", location: "path", required: true, description: "DG project name" },
          ],
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "project": "my-project",\n  "runs": [\n    {\n      "runId": "a1b2c3d4e5f6g7h8i9j0k1l2",\n      "speckleProjectId": null,\n      "baseModelId": null,\n      "createdAt": "2026-07-10T14:30:00.000000",\n      "ruleIds": ["R_URB_HEIGHT_MAX_75_V"],\n      "ruleCount": 1,\n      "failedRuleCount": 1,\n      "entityCount": 3,\n      "state": {\n        "stateId": "DS_a1b2c3d4",\n        "label": null,\n        "capturedAtUtc": "2026-07-10T14:29:00.000000",\n        "parameterCount": 5,\n        "props": [\n          {"iri": "dgv:objectRefName", "label": "Object Name", "value": "Building A"}\n        ]\n      }\n    }\n  ]\n}',
        },
      ],
    },
    {
      id: "get-validation-view",
      title: "Get Validation View",
      summary: "Retrieve the validation view payload for rendering in the Model Viewer.",
      blocks: [
        {
          type: "text",
          content:
            "Three view endpoints provide progressively scoped validation data for the Speckle-based 3D Model Viewer:",
        },
        {
          type: "endpoint",
          method: "GET",
          path: "/data-service/validation/view/{project}",
          description:
            "Get the latest validation run's view payload for the project.",
          params: [
            { name: "project", type: "string", location: "path", required: true, description: "DG project name" },
          ],
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "project": "my-project",\n  "runId": "...",\n  "selectedRuleId": null,\n  "speckleBaseUrl": "http://localhost:8090",\n  "readToken": "...",\n  "baseProjectId": "...",\n  "baseModelId": "...",\n  "baseVersionId": "...",\n  "validationModelId": "...",\n  "validationVersionId": "...",\n  "rules": [],\n  "objectSets": {\n    "failed": [...],\n    "passed": [...]\n  }\n}',
        },
        {
          type: "endpoint",
          method: "GET",
          path: "/data-service/validation/view/{project}/{run_id}",
          description:
            "Get the view payload for a specific validation run.",
          params: [
            { name: "project", type: "string", location: "path", required: true, description: "DG project name" },
            { name: "run_id", type: "string", location: "path", required: true, description: "Validation run ID" },
          ],
        },
        {
          type: "endpoint",
          method: "GET",
          path: "/data-service/validation/view/{project}/{run_id}/{rule_id}",
          description:
            "Get the view payload scoped to a specific rule within a run.",
          params: [
            { name: "project", type: "string", location: "path", required: true, description: "DG project name" },
            { name: "run_id", type: "string", location: "path", required: true, description: "Validation run ID" },
            { name: "rule_id", type: "string", location: "path", required: true, description: "Rule ID to filter entities by" },
          ],
        },
        {
          type: "note",
          variant: "info",
          content:
            "The view endpoints are primarily consumed by the Model Viewer screen. They return Speckle URLs and tokens that the 3D viewer uses to render the validation overlay directly on the model.",
        },
      ],
    },
    {
      id: "delete-validation-run",
      title: "Delete Validation Run",
      summary: "Delete a validation run from Speckle and Neo4j.",
      blocks: [
        {
          type: "endpoint",
          method: "DELETE",
          path: "/data-service/validation/run/{project}/{run_id}",
          description:
            "Delete a validation run. Removes the Speckle version, the ValidationRun node, and all associated ValidationEntity nodes from Neo4j.",
          params: [
            { name: "project", type: "string", location: "path", required: true, description: "DG project name" },
            { name: "run_id", type: "string", location: "path", required: true, description: "Validation run ID to delete" },
          ],
          response:
            'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "status": "deleted",\n  "project": "my-project",\n  "runId": "a1b2c3d4e5f6g7h8i9j0k1l2",\n  "validationModelId": "validation-model-uuid",\n  "validationVersionId": "version-uuid"\n}',
        },
        {
          type: "code",
          label: "Error response — run not found",
          content:
            'HTTP/1.1 404 Not Found\nContent-Type: application/json\n\n{\n  "error": "Validation run not found.",\n  "hint": "Verify the run ID exists for this project.",\n  "code": "RUN_NOT_FOUND"\n}',
        },
      ],
    },
    {
      id: "error-response-format",
      title: "Error Response Format",
      summary: "All DG API endpoints return structured JSON error responses.",
      blocks: [
        {
          type: "text",
          content:
            "When an API call fails, the response body follows a standard three-field format. The error field describes what went wrong, hint suggests how to fix it, and code is a machine-readable error identifier.",
        },
        {
          type: "code",
          label: "Structured JSON error envelope",
          content:
            'HTTP/1.1 <status_code>\nContent-Type: application/json\n\n{\n  "error": "Human-readable error description",\n  "hint": "Actionable suggestion for resolving the error",\n  "code": "MACHINE_READABLE_CODE"\n}',
        },
        {
          type: "table",
          headers: ["Error Code", "HTTP Status", "Scenario"],
          rows: [
            ["CONNECTOR_NOT_FOUND", "404", "Unknown connector ID used in path"],
            ["CREDENTIAL_NOT_FOUND", "404", "Credential ID not found for the connector"],
            ["CONNECTOR_AUTH_FAILED", "401", "Invalid, revoked, or missing Bearer token"],
            ["SPECKLE_CONFIG_MISSING", "404", "No Speckle project configuration for the DG project"],
            ["SPECKLE_TOKEN_MISSING", "500", "Speckle write token not configured on the server"],
            ["PUBLISH_VALIDATION_ERROR", "400", "Speckle publish failed (connection, project ID)"],
            ["PUBLISH_INTERNAL_ERROR", "500", "Unexpected error during publish"],
            ["DELETE_VALIDATION_ERROR", "400", "Speckle delete failed (connection, project ID)"],
            ["DELETE_INTERNAL_ERROR", "500", "Unexpected error during delete"],
            ["RUN_NOT_FOUND", "404", "Validation run ID not found for the project"],
            ["REASONER_NOT_FOUND", "422", "Unknown reasoner ID in reasoner settings"],
          ],
        },
        {
          type: "note",
          variant: "tip",
          content:
            "Always check the hint field in error responses. It is crafted to give the end user (or a support engineer) a concrete next step, such as which environment variable to set or which UI panel to open.",
        },
      ],
    },
  ],
};

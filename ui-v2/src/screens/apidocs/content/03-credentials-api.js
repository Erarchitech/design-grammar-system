// Credentials API — create and revoke connector credentials

export default {
  id: "credentials-api",
  title: "Credentials API",
  pages: [
    {
      id: "create-credential",
      title: "Create Credential",
      summary: "Mint a new credential for a connector. The token is returned once and never stored in plaintext.",
      blocks: [
        {
          type: "endpoint",
          method: "POST",
          path: "/data-service/connectors/{connector_id}/credentials",
          description:
            "Creates a new credential record and generates a connector token. The token is returned in the response body — this is the only opportunity to capture it.",
          params: [
            { name: "connector_id", type: "string", location: "path", required: true, description: "Connector ID from the registry (grasshopper, revit, dynamo, blender, tekla, archicad, civil3d, infraworks, navisworks, solibri, bimcollab, bimtrack, lumion, twinmotion)" },
            { name: "label", type: "string | null", location: "body (optional)", required: false, description: "Human-readable label to identify this credential (e.g., 'Office workstation - Alice')" },
          ],
          request:
            'POST /data-service/connectors/grasshopper/credentials\nContent-Type: application/json\n\n{\n  "label": "BIM workstation" \n}',
          response:
            'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{\n  "credential_id": "a1b2c3d4e5f6g7h8i9j0k1l2",\n  "token": "dgc_X5o8JxG2kL9pQ3rY7vB4nM1wC6fT0uA8iZ3sH5dK2eR"\n}',
        },
        {
          type: "text",
          content:
            "Internally, the server generates a token using secrets.token_urlsafe(32), computes its SHA-256 hash, and stores the hash alongside the credential_id, connector_id, label, and creation timestamp. The plaintext token is never written to disk.",
        },
        {
          type: "code",
          label: "Error response — unknown connector",
          content:
            'HTTP/1.1 404 Not Found\nContent-Type: application/json\n\n{\n  "error": "Unknown connector: unknown_tool",\n  "hint": "Use a connector id from GET /connectors.",\n  "code": "CONNECTOR_NOT_FOUND"\n}',
        },
      ],
    },
    {
      id: "revoke-credential",
      title: "Revoke Credential",
      summary: "Revoke a credential by its credential_id. Revoked tokens stop authenticating heartbeats immediately.",
      blocks: [
        {
          type: "endpoint",
          method: "DELETE",
          path: "/data-service/connectors/{connector_id}/credentials/{credential_id}",
          description:
            "Marks a credential as revoked. The token hash remains in the store but the revoked flag prevents future authentication. This is a soft delete — the record persists for audit purposes.",
          params: [
            { name: "connector_id", type: "string", location: "path", required: true, description: "Connector identifier" },
            { name: "credential_id", type: "string", location: "path", required: true, description: "Credential ID returned at creation or from GET /connectors overview" },
          ],
          response:
            'HTTP/1.1 204 No Content',
        },
        {
          type: "code",
          label: "Error response — credential not found",
          content:
            'HTTP/1.1 404 Not Found\nContent-Type: application/json\n\n{\n  "error": "Credential not found: unknown_credential_id",\n  "hint": "Use a credential_id from GET /connectors.",\n  "code": "CREDENTIAL_NOT_FOUND"\n}',
        },
        {
          type: "note",
          variant: "warning",
          content:
            "Revocation is irreversible. If a token was compromised, also consider whether the connector component itself needs re-deployment with a fresh token.",
        },
      ],
    },
  ],
};

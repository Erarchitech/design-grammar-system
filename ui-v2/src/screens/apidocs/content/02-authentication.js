// Authentication — token format, credential lifecycle, security model

export default {
  id: "authentication",
  title: "Authentication",
  pages: [
    {
      id: "token-format",
      title: "Token Format",
      summary: "Connector tokens use the dgc_ prefix followed by 43 characters of url-safe base64 randomness.",
      blocks: [
        {
          type: "text",
          content:
            "Connector tokens are generated server-side by the data-service. Each token consists of the dgc_ prefix (identifying it as a DG connector token) followed by 32 bytes of cryptographically random data encoded as url-safe base64 (43 characters).",
        },
        {
          type: "code",
          label: "Token structure",
          content:
            "dgc_<43-characters-of-urlsafe-base64>\n\nExample:\ndgc_X5o8JxG2kL9pQ3rY7vB4nM1wC6fT0uA8iZ3sH5dK2eR",
        },
        {
          type: "note",
          variant: "warning",
          content:
            "The token is returned to you exactly once, at credential creation time. The server stores only the SHA-256 hash of the token. If you lose the token, you must create a new credential.",
        },
        {
          type: "text",
          content:
            "Tokens are stored on the server as SHA-256 hashes. This means that even with access to the data-service filesystem, an attacker cannot recover plaintext tokens. The hashing approach is preferred over encryption because the server never needs the plaintext token — authentication is done by hashing the presented token and comparing against stored hashes.",
        },
      ],
    },
    {
      id: "creating-credentials",
      title: "Creating Credentials",
      summary: "Credentials are created via the credentials API and return the token once.",
      blocks: [
        {
          type: "text",
          content:
            "To create a credential, send a POST request to the connector's credentials endpoint. The server generates a new token, stores its SHA-256 hash, and returns the plaintext token in the response. This is the only time the token is visible.",
        },
        {
          type: "endpoint",
          method: "POST",
          path: "/data-service/connectors/{connector_id}/credentials",
          description: "Create a new credential for a connector. Returns the token once.",
          params: [
            { name: "connector_id", type: "string", location: "path", required: true, description: "The connector identifier (e.g. grasshopper, revit, dynamo)" },
            { name: "label", type: "string | null", location: "body", required: false, description: "An optional human-readable label for the credential" },
          ],
          request:
            'POST /data-service/connectors/grasshopper/credentials\nContent-Type: application/json\n\n{\n  "label": "Office workstation - Alice" \n}',
          response:
            'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{\n  "credential_id": "a1b2c3d4e5f6g7h8i9j0k1l2",\n  "token": "dgc_X5o8JxG2kL9pQ3rY7vB4nM1wC6fT0uA8iZ3sH5dK2eR"\n}',
        },
        {
          type: "note",
          variant: "tip",
          content:
            "Copy the token immediately from the response. If you navigate away or lose the token before pasting it into your connector component, you will need to revoke the credential and create a new one.",
        },
      ],
    },
    {
      id: "token-lifecycle",
      title: "Token Lifecycle",
      summary: "Tokens can be active or revoked. Revoked tokens stop authenticating heartbeats immediately.",
      blocks: [
        {
          type: "text",
          content:
            "A credential goes through three stages:",
        },
        {
          type: "table",
          headers: ["Stage", "Description"],
          rows: [
            ["Created", "Token is generated and returned once. The credential record is persisted with the token hash."],
            ["Active", "The token can authenticate heartbeats and API calls. Lasts indefinitely until revoked."],
            ["Revoked", "The credential is marked as revoked. Its token stops authenticating. No cleanup of stored data."],
          ],
        },
        {
          type: "text",
          content:
            "Revocation is permanent and immediate. The server marks the credential record as revoked in the credentials store. Once revoked, any heartbeat or API call with that token receives a 401 Unauthorized response.",
        },
        {
          type: "endpoint",
          method: "DELETE",
          path: "/data-service/connectors/{connector_id}/credentials/{credential_id}",
          description: "Revoke a credential. The token stops working immediately.",
          params: [
            { name: "connector_id", type: "string", location: "path", required: true, description: "The connector identifier" },
            { name: "credential_id", type: "string", location: "path", required: true, description: "The credential ID returned at creation" },
          ],
          response:
            'HTTP/1.1 204 No Content',
        },
        {
          type: "note",
          variant: "warning",
          content:
            "There is no way to un-revoke a credential. If a token is compromised, revoke the credential immediately and create a new one.",
        },
      ],
    },
  ],
};

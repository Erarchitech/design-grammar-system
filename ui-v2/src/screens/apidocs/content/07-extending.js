// Extending — content module format documentation

export default {
  id: "extending",
  title: "Extending This Documentation",
  pages: [
    {
      id: "content-module-format",
      title: "Content Module Format",
      summary:
        "This documentation is driven by content modules in ui-v2/src/screens/apidocs/content/. Adding a new page requires no viewer code changes.",
      blocks: [
        {
          type: "text",
          content:
            "Each content module is a plain JavaScript file named ##-<slug>.js in the content/ directory. The ## prefix determines the section ordering. Each file exports a default object with the following shape:",
        },
        {
          type: "code",
          label: "Content module structure",
          content:
            'export default {\n  id: "my-section",          // unique section identifier\n  title: "My Section",        // section heading in the tree\n  pages: [\n    {\n      id: "my-page",         // unique page identifier (within section)\n      title: "My Page",       // page heading\n      summary: "Short description shown in the tree tooltip and page header.",\n      blocks: [\n        // Block objects (see below for types)\n      ],\n    },\n  ],\n};',
        },
        {
          type: "text",
          content:
            "The index.js uses Vite's import.meta.glob to discover all ##-*.js files eagerly and sort them by their numeric prefix. Adding a new file to the content directory automatically registers the section.",
        },
        {
          type: "text",
          content:
            "Supported block types:",
        },
        {
          type: "table",
          headers: ["Type", "Properties", "Rendering"],
          rows: [
            ['text', '{ type: "text", content: string }', 'Paragraph of prose text'],
            ['code', '{ type: "code", content: string, label?: string }', 'Monospace code block with optional header label. Uses the CodeBlock component and --font-mono (Geist Mono).'],
            ['endpoint', '{ type: "endpoint", method, path, description, params, request?, response? }', 'API endpoint reference: signature line, parameter table, request/response example blocks. Revit-API-style layout.'],
            ['table', '{ type: "table", headers: string[], rows: string[][] }', 'Grid table for structured reference data (field types, enumerations, route tables).'],
            ['note', '{ type: "note", variant: "info" | "warning" | "tip", content: string }', 'Colored callout box for emphasis, warnings, and contextual tips.'],
          ],
        },
        {
          type: "code",
          label: "Example: endpoint block",
          content:
            '{\n  type: "endpoint",\n  method: "POST",\n  path: "/data-service/connectors/{id}/credentials",\n  description: "Creates a new credential and returns the token once.",\n  params: [\n    { name: "id", type: "string", location: "path", required: true, description: "Connector ID" },\n  ],\n  request: \'POST /path\\nContent-Type: application/json\\n\\n{"key": "value"}\',\n  response: \'HTTP/1.1 201 Created\\n\\n{"token": "dgc_..."}\',\n}',
        },
        {
          type: "note",
          variant: "tip",
          content:
            "To add a new section: create ##-<slug>.js in the content/ directory with the exported section object. The index.js aggregator picks it up automatically. Use a ## prefix number that places it in the desired order among existing sections.",
        },
      ],
    },
  ],
};

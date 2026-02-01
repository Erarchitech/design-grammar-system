window.GRAPH_CONFIG = {
  neo4jUri: "bolt://localhost:7687",
  neo4jHttp: "/neo4j",
  neo4jUser: "neo4j",
  neo4jPassword: "12345678",
  n8nWebhook: "/n8n/webhook/dg/rules-ingest",
  n8nQueryWebhook: "/n8n/webhook/dg/graph-query",
  dataServiceUrl: "/data-service",
  n8nRestBase: "/n8n/rest",
  n8nUser: "erarchitech@gmail.com",
  n8nPassword: "Ermolenko#^4538!",
  driverConfig: {
    encrypted: "ENCRYPTION_OFF"
  },
  labels: {
    Rule: { label: "id" },
    Atom: { label: "id" },
    Class: { label: "name" },
    DataProperty: { label: "name" },
    ObjectProperty: { label: "name" },
    Builtin: { label: "name" }
  },
  relationships: {
    HAS_ATOM: { caption: true, thickness: 2 },
    REFERS_TO: { caption: true, thickness: 2 },
    HAS_DATA_PROPERTY: { caption: true, thickness: 2 },
    HAS_OBJECT_PROPERTY: { caption: true, thickness: 2 }
  },
  visGroups: {
    Class: { color: { background: "#78c38a", border: "#5aa46c" } },
    DataProperty: { color: { background: "#ffb36b", border: "#e5923a" } },
    ObjectProperty: { color: { background: "#ff8f3a", border: "#d86d1f" } },
    Builtin: { color: { background: "#9aa4b2", border: "#6f7884" } },
    Rule: { color: { background: "#6da7ff", border: "#3f7ed9" } },
    Atom: { color: { background: "#b7c0cc", border: "#8c96a3" } }
  }
};

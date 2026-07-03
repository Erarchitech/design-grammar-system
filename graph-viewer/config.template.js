window.GRAPH_CONFIG = {
  neo4jUri: "bolt://localhost:7687",
  neo4jHttp: "/neo4j",
  neo4jUser: "neo4j",
  neo4jPassword: "12345678",
  n8nWebhook: "/n8n/webhook/dg/rules-ingest",
  n8nQueryWebhook: "/n8n/webhook/dg/graph-query",
  dataServiceUrl: "/data-service",
  speckleBaseUrl: "http://localhost:8090",
  speckleReadToken: "",
  n8nRestBase: "/n8n/rest",
  n8nUser: "erarchitech@gmail.com",
  n8nPassword: "Ermolenko#^4538!",
  driverConfig: {
    encrypted: "ENCRYPTION_OFF"
  },
  labels: {
    Rule: { label: "Rule_Id" },
    Atom: { label: "Atom_Id", secondaryLabel: "SWRL_label" },
    Class: { label: "label" },
    DatatypeProperty: { label: "SWRL_label" },
    ObjectProperty: { label: "label" },
    Builtin: { label: "label" },
    Var: { label: "name" },
    Literal: { label: "lex" },
    DesignState: { label: "StateId", group: "kind" },
    KnowledgeNote: { label: "title" },
    KnowledgeTag: { label: "name" },
    KnowledgeSession: { label: "mode" },
    KnowledgeClass: { label: "label" }
  },
  relationships: {
    HAS_BODY: { caption: true, thickness: 2 },
    HAS_HEAD: { caption: true, thickness: 2 },
    REFERS_TO: { caption: true, thickness: 2 },
    ARG: { caption: true, thickness: 2 },
    TAGGED_WITH: { caption: true, thickness: 2 },
    HAS_SESSION: { caption: true, thickness: 2 },
    INSTANCE_OF: { caption: true, thickness: 2 }
  },
  visGroups: {
    Class: { color: { background: "#78c38a", border: "#5aa46c" } },
    DatatypeProperty: { color: { background: "#ffb36b", border: "#e5923a" } },
    ObjectProperty: { color: { background: "#ff8f3a", border: "#d86d1f" } },
    Builtin: { color: { background: "#9aa4b2", border: "#6f7884" } },
    Rule: { color: { background: "#6da7ff", border: "#3f7ed9" } },
    Atom: { color: { background: "#b7c0cc", border: "#8c96a3" } },
    Var: { color: { background: "#c6b5ff", border: "#9278d9" } },
    Literal: { color: { background: "#ffd6a5", border: "#d9a36a" } },
    // DesignState uses group: "kind" (see labels above) so visGroups is keyed by kind VALUES (ParamState/ObjState/PropState), not by the DesignState label — unlike every other entry in this file, which keys visGroups by label name directly.
    ParamState: { color: { background: "#a8d8ea", border: "#6fb3cf" } },
    ObjState: { color: { background: "#f4a261", border: "#d4823a" } },
    PropState: { color: { background: "#7bcfc0", border: "#4fa696" } },
    KnowledgeNote: { color: { background: "#4ecdc4", border: "#2fa89f" } },
    KnowledgeTag: { color: { background: "#ffe66d", border: "#d4bf3a" } },
    KnowledgeSession: { color: { background: "#a78bfa", border: "#7c5fcf" } },
    KnowledgeClass: { color: { background: "#f472b6", border: "#db2777" } }
  }
};

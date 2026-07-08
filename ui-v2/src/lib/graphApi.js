// Backend access for the Graph Viewer — Neo4j HTTP tx endpoint via the nginx
// proxy, plus the two n8n webhooks (rules-ingest / graph-query) with the
// data-service async polling contract used by the legacy SPA.

const DEFAULTS = {
  neo4jHttp: "/neo4j",
  neo4jUser: "neo4j",
  neo4jPassword: "12345678",
  n8nWebhook: "/n8n/webhook/dg/rules-ingest",
  n8nQueryWebhook: "/n8n/webhook/dg/graph-query",
  dataServiceUrl: "/data-service"
};

export function getConfig() {
  return { ...DEFAULTS, ...(window.GRAPH_CONFIG || {}) };
}

export async function executeCypher(statement, parameters = {}) {
  const cfg = getConfig();
  const res = await fetch(cfg.neo4jHttp + "/db/neo4j/tx/commit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Basic " + btoa(`${cfg.neo4jUser}:${cfg.neo4jPassword}`)
    },
    body: JSON.stringify({ statements: [{ statement, parameters }] })
  });
  const json = await res.json().catch(() => null);
  if (!res.ok) throw new Error(json?.errors?.[0]?.message || res.statusText || "Neo4j error");
  if (Array.isArray(json?.errors) && json.errors.length) {
    throw new Error(json.errors[0]?.message || "Neo4j error");
  }
  return json;
}

const rowsOf = (json) => json?.results?.[0]?.data?.map((d) => d.row) || [];

// Fetch the project-scoped graph: all tagged nodes plus the relationships
// among them. Untagged (project IS NULL) nodes are included when no project
// scope is set, matching the legacy viewer's behaviour.
export async function fetchGraph(project) {
  const scope = project
    ? "n.project = $project"
    : "TRUE";
  const nodesJson = await executeCypher(
    `MATCH (n) WHERE ${scope} RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props LIMIT 2000`,
    project ? { project } : {}
  );
  const relsJson = await executeCypher(
    `MATCH (a)-[r]->(b) WHERE ${scope.replace(/n\./g, "a.")} AND ${scope.replace(/n\./g, "b.")}
     RETURN id(a) AS source, type(r) AS type, id(b) AS target LIMIT 8000`,
    project ? { project } : {}
  );
  return {
    nodes: rowsOf(nodesJson).map(([id, labels, props]) => ({ id, labels, props })),
    rels: rowsOf(relsJson).map(([source, type, target]) => ({ source, type, target }))
  };
}

// Legacy-parity post-ingest fixup ("Neo4j node tagging" gotcha): the n8n
// workflow writes nodes under default-project; the client claims them for
// the active project afterwards, exactly like the legacy SPA's tagProjectNodes.
export async function tagProjectNodes(project) {
  if (!project) return;
  await executeCypher(
    "MATCH (n) WHERE n.project IS NULL OR n.project = 'default-project' SET n.project = $project",
    { project }
  );
}

export async function fetchProjects() {
  const json = await executeCypher(
    "MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT n.project AS project, count(n) AS nodes ORDER BY project"
  );
  return rowsOf(json).map(([project, nodes]) => ({ project, nodes }));
}

// ---- design-rule session history (data-service, legacy SPA parity) ----

export async function fetchDrSessions(project) {
  const cfg = getConfig();
  const base = (cfg.dataServiceUrl || "/data-service").replace(/\/$/, "");
  const res = await fetch(`${base}/design-rule-sessions/${encodeURIComponent(project || "default-project")}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json().catch(() => null);
  return Array.isArray(data?.sessions) ? data.sessions : [];
}

export async function saveDrSession(project, mode, prompt, result) {
  const cfg = getConfig();
  const base = (cfg.dataServiceUrl || "/data-service").replace(/\/$/, "");
  try {
    await fetch(`${base}/design-rule-sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project: project || "default-project",
        mode,
        prompt,
        result: (result || "").slice(0, 2000)
      })
    });
  } catch {
    // history is best-effort — never block the workflow on it
  }
}

// ---- n8n webhooks with the async "accepted → poll data-service" contract ----

function webhookHeaders(cfg) {
  const headers = { "Content-Type": "application/json" };
  if (cfg.n8nUser && cfg.n8nPassword) {
    headers["Authorization"] = "Basic " + btoa(`${cfg.n8nUser}:${cfg.n8nPassword}`);
  }
  return headers;
}

async function pollExecution(url, { onProgress, intervalMs = 1500, timeoutMs = 180000 } = {}) {
  const t0 = Date.now();
  for (;;) {
    if (Date.now() - t0 > timeoutMs) throw new Error("Workflow timed out.");
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json().catch(() => null);
      const status = data?.status || "running";
      if (status === "completed") return data?.payload || {};
      if (status === "failed") throw new Error("Workflow failed.");
      if (status === "cancelled") throw new Error("Workflow cancelled.");
      if (onProgress) onProgress(data);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

async function callWorkflow(url, body, workflowKey, { onProgress } = {}) {
  const cfg = getConfig();
  const res = await fetch(url, { method: "POST", headers: webhookHeaders(cfg), body: JSON.stringify(body) });
  const rawText = await res.text();
  let data = null;
  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      /* non-JSON response — handled below */
    }
  }
  if (!res.ok) throw new Error(data?.message || rawText || `HTTP ${res.status}`);
  const base = cfg.dataServiceUrl.replace(/\/$/, "");
  if (data?.status === "accepted" && data?.executionId) {
    return pollExecution(`${base}/execution-result/${data.executionId}`, { onProgress });
  }
  // "accepted" without id, "started" messages, or intermediate echo payloads
  // all mean the workflow is running — poll the latest result for this key.
  const intermediate =
    data &&
    !data.answer &&
    !data.response &&
    !data.cypher &&
    (data.rules_text || data.prompt_text || data.ollama_model || data.neo4j_url || data.mcp_url);
  if (
    data?.status === "accepted" ||
    (typeof data?.message === "string" && data.message.toLowerCase().includes("started")) ||
    intermediate
  ) {
    return pollExecution(`${base}/execution-result/latest/${workflowKey}`, { onProgress });
  }
  return data || { answer: rawText };
}

// Both `project` (legacy SPA contract) and `project_name` (v7 workflow
// contract) are sent — the live workflows read project_name.
export function ingestRules(rulesText, project, opts) {
  const cfg = getConfig();
  const p = project || "default-project";
  return callWorkflow(
    cfg.n8nWebhook,
    { rules_text: rulesText, cypher_prompt: false, project: p, project_name: p },
    "rules-ingest",
    opts
  );
}

export function queryGraph(prompt, project, opts) {
  const cfg = getConfig();
  const p = project || "default-project";
  return callWorkflow(
    cfg.n8nQueryWebhook,
    { prompt, cypher_prompt: false, project: p, project_name: p },
    "graph-query",
    opts
  );
}

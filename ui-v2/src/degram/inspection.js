// Surface-level display policy only, not a server-side permission boundary.
// Sanitize before ring mapping, so canvas labels and property tables share it.
const restricted = /provider|model|apikey|credential|password|secret|token|llm/i;
export function inspectionValue(value) {
  if (Array.isArray(value)) return value.map(inspectionValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value)
      .filter(([key]) => !restricted.test(key.replace(/[^a-z0-9]/gi, "")))
      .map(([key, item]) => [key, inspectionValue(item)]));
  }
  if (typeof value === "string" && /^[\s]*[\[{]/.test(value)) {
    try { return JSON.stringify(inspectionValue(JSON.parse(value))); }
    catch { return "[Structured value unavailable]"; }
  }
  return value;
}
export function inspectionGraph(graph) {
  return { nodes: graph.nodes.map(node => ({ ...node, props: inspectionValue(node.props) })), rels: graph.rels };
}

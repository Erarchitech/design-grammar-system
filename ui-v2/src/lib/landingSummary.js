import { t } from "../i18n/index.js";
import { groupRunsByState } from "./runGroups.js";

const DASH = "—";

function value(data, key) {
  return data?.[key] === null || data?.[key] === undefined || data?.[key] === "" ? DASH : data[key];
}

function graphParts(graph) {
  return [
    { label: t("Classes"), value: value(graph, "classes") },
    { label: t("Properties"), value: value(graph, "properties") },
    { label: t("Rules"), value: value(graph, "rules") }
  ];
}

export function formatActiveNames(names) {
  if (!names.length) return DASH;
  const displayed = names.slice(0, 2).join(", ");
  return names.length > 2 ? `${displayed} +${names.length - 2}` : displayed;
}

export function buildLandingSummaries({ project, hostMode = false, summary, runs, llm, reasoner, connectors } = {}) {
  const projectSummary = summary?.status === "ok" && summary.data?.project === project ? summary.data : null;
  const graph = !project ? DASH : !summary || summary.status === "loading"
    ? null : graphParts(projectSummary?.graph);

  const model = !project ? DASH : !runs || runs.status === "loading" ? null : (() => {
    const matched = runs.status === "ok" && runs.data?.project === project && Array.isArray(runs.data.runs)
      ? runs.data.runs : null;
    return [
      { label: t("Design States"), value: matched ? groupRunsByState(matched).length : DASH },
      { label: t("Validation runs"), value: matched ? matched.length : DASH }
    ];
  })();

  const aiengine = hostMode ? null : !llm || llm.status === "loading" ? null : (() => {
    const settings = llm.status === "ok" ? llm.data : null;
    const modelName = value(settings, "model");
    return [
      { label: t("Provider"), value: value(settings, "provider") },
      { label: t("Model"), value: modelName, title: modelName === DASH ? undefined : String(modelName) }
    ];
  })();

  const reasonerParts = hostMode ? null : !reasoner || reasoner.status === "loading" ? null : (() => {
    const settings = reasoner.status === "ok" ? reasoner.data : null;
    const name = settings?.reasoners?.find(item => item.id === settings.selected)?.name;
    return [{ label: t("Active"), value: name || DASH }];
  })();

  const connectorParts = hostMode ? null : !project ? DASH : !connectors || connectors.status === "loading" || !summary || summary.status === "loading" ? null : (() => {
    const registry = connectors.status === "ok" && Array.isArray(connectors.data?.connectors)
      ? connectors.data.connectors : [];
    const active = registry.filter(item => item.id !== "degram" && item.status === "active").map(item => item.name);
    const degram = registry.find(item => item.id === "degram" && item.status === "active");
    if (degram) active.push(degram.name || "DeGram");
    return [
      { label: t("Active"), value: formatActiveNames(active.filter(Boolean)) },
      { label: t("Grants issued"), value: value(projectSummary?.connectors, "grantsIssued") }
    ];
  })();

  return { graph, model, aiengine, connectors: connectorParts, reasoner: reasonerParts };
}

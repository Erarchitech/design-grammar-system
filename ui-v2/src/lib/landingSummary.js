import { t } from "../i18n/index.js";

const DASH = "—";

function graphParts(graph) {
  return [
    { label: t("Classes"), value: graph?.classes ?? DASH },
    { label: t("Properties"), value: graph?.properties ?? DASH },
    { label: t("Rules"), value: graph?.rules ?? DASH }
  ];
}

export function buildLandingSummaries({ project, summary } = {}) {
  const graph = !project ? DASH : summary?.status === "loading" || !summary
    ? null
    : graphParts(summary.status === "ok" && summary.data?.project === project ? summary.data.graph : null);
  return { graph, model: null, aiengine: null, connectors: null, reasoner: null };
}

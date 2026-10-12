// Merges the per-area dictionaries. Each area module exports `ru` and `en`; later plans fill their own module.
import * as core from "./core.js";
import * as errors from "./errors.js";
import * as projects from "./projects.js";
import * as landing from "./landing.js";
import * as graph from "./graph.js";
import * as model from "./model.js";
import * as connectors from "./connectors.js";
import * as screens from "./screens.js";

export const AREAS = { core, errors, projects, landing, graph, model, connectors, screens };

function merge(lang) {
  // A null-prototype table: lookups also go through Object.hasOwn, so prototype keys never resolve.
  return Object.freeze(Object.assign(Object.create(null), ...Object.values(AREAS).map((area) => area[lang])));
}

export const RU = merge("ru");
export const EN = merge("en");

// Merges the per-area dictionaries. Each area module exports `ru` and `en`; later plans fill their own module.
import * as core from "./core.js";

export const AREAS = { core };

function merge(lang) {
  // A null-prototype table: lookups also go through Object.hasOwn, so prototype keys never resolve.
  return Object.freeze(Object.assign(Object.create(null), ...Object.values(AREAS).map((area) => area[lang])));
}

export const RU = merge("ru");
export const EN = merge("en");

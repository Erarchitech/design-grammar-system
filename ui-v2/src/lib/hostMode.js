// The host query is only a display filter for the untrusted remote page.
// It grants no API, token, or storage capability.
const DEGRAM_HOST = new URLSearchParams(globalThis.location?.search || "").get("host") === "degram";

export const HOST_REGIONS = ["graph", "model", "projects", "connectors"];

export function isDegramHost() {
  return DEGRAM_HOST;
}

export function isRegionAllowed(region) {
  return region === "landing" || !DEGRAM_HOST || HOST_REGIONS.includes(region);
}

export function hostLang() {
  return DEGRAM_HOST && new URLSearchParams(globalThis.location?.search || "").get("lang") === "ru" ? "ru" : "en";
}

export function clearHostSignal() {
  if (!DEGRAM_HOST) return;
  globalThis.history.replaceState(null, "", globalThis.location.pathname + globalThis.location.search);
}

export function parseHostSignal(hash) {
  if (!DEGRAM_HOST || typeof hash !== "string") return null;
  if (/^#degram-state=(connecting|ready|idle)$/.test(hash)) return { state: hash.slice(14) };
  if (/^#degram-go=(landing|graph|model|connectors)$/.test(hash)) return { go: hash.slice(11) };
  return null;
}

export function announceProject(name) {
  if (!DEGRAM_HOST || typeof name !== "string" || name.length === 0 || name.length > 64) return;
  globalThis.location.hash = `#degram-select=${encodeURIComponent(name)}`;
  clearHostSignal();
}

export function announceNewSession() {
  if (!DEGRAM_HOST) return;
  globalThis.location.hash = "#degram-new-session";
  clearHostSignal();
}

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

export function announceProject(name) {
  if (!DEGRAM_HOST || typeof name !== "string" || name.length === 0 || name.length > 64) return;
  globalThis.location.hash = `#degram-select=${encodeURIComponent(name)}`;
  globalThis.history.replaceState(null, "", "");
}

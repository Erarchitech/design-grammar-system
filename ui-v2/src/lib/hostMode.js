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
  // Keep this vocabulary paired with the fork's HOST_GO_FRAGMENT in apps/degram/apps/desktop/electron/degram/dg-view.ts.
  if (/^#degram-go=(landing|graph|model|connectors|projects)$/.test(hash)) return { go: hash.slice(11) };
  // The language DeGram Settings -> Appearance -> Language selected (sender: DeGram dg-view.ts `signal`, plan
  // 1308-21). Closed vocabulary; it only changes the display language and grants no API, storage or navigation
  // capability (D-52).
  if (/^#degram-lang=(ru|en)$/.test(hash)) return { lang: hash.slice(13) };
  // The project DeGram actually opened (empty: none). Display-only: it moves the page's selection back after a
  // refused pick and grants no capability. Bounded like announceProject.
  const project = /^#degram-project=([^&#]{0,200})$/.exec(hash);
  if (project) {
    let name;
    try {
      name = decodeURIComponent(project[1]);
    } catch {
      return null;
    }
    if (name.length === 0) return { project: null };
    // eslint-disable-next-line no-control-regex
    if (name.length > 64 || /[\u0000-\u001f/\\]/.test(name)) return null;
    return { project: name };
  }
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

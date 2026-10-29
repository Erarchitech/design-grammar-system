// The host query is only a display filter for the untrusted remote page.
// It grants no API, token, or storage capability.
const DEGRAM_HOST = new URLSearchParams(globalThis.location?.search || "").get("host") === "degram";

export const HOST_REGIONS = ["graph", "model", "projects", "connectors"];

// Quick 261027-sgc: the connectors DeGram can install from its own bundle, and the install states it reports.
// Paired with the fork's PAGE_INSTALL_FRAGMENT / HOST_INSTALLED_FRAGMENT in apps/degram/apps/desktop/electron/degram/dg-view.ts.
export const INSTALLABLE_CONNECTORS = ["revit", "grasshopper"];
export const CONNECTOR_INSTALL_STATES = ["ready", "install", "installing", "unavailable", "needs-host", "locked", "failed"];
const CONNECTOR_STATE = `(${INSTALLABLE_CONNECTORS.join("|")}):(${CONNECTOR_INSTALL_STATES.join("|")})`;
const INSTALLED_SIGNAL = new RegExp(`^#degram-installed=${CONNECTOR_STATE}(?:,${CONNECTOR_STATE})?$`);

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
  if (hash === "#degram-target-refused") return { targetRefused: true };
  if (/^#degram-state=(connecting|ready|idle)$/.test(hash)) return { state: hash.slice(14) };
  // Keep this vocabulary paired with the fork's HOST_GO_FRAGMENT in apps/degram/apps/desktop/electron/degram/dg-view.ts.
  if (/^#degram-go=(landing|graph|model|connectors|projects)$/.test(hash)) return { go: hash.slice(11) };
  // The language DeGram Settings -> Appearance -> Language selected (sender: DeGram dg-view.ts `signal`, plan
  // 1308-21). Closed vocabulary; it only changes the display language and grants no API, storage or navigation
  // capability (D-52).
  if (/^#degram-lang=(ru|en)$/.test(hash)) return { lang: hash.slice(13) };
  // What DeGram reports about its bundled connectors (quick 261027-sgc). Display-only: the page can ask for an
  // install, DeGram confirms it natively; this signal never authorizes anything.
  if (INSTALLED_SIGNAL.test(hash)) {
    const installed = {};
    for (const pair of hash.slice(18).split(",")) {
      const [id, state] = pair.split(":");
      installed[id] = state;
    }
    return { installed };
  }
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

/** Ask DeGram for the install state of its bundled connectors (answered with #degram-installed=). */
export function requestConnectorStatus() {
  if (!DEGRAM_HOST) return;
  globalThis.location.hash = "#degram-connectors-check";
  clearHostSignal();
}

/** Ask DeGram to install a bundled connector; DeGram shows its own confirmation before writing anything. */
export function requestConnectorInstall(id) {
  if (!DEGRAM_HOST || !INSTALLABLE_CONNECTORS.includes(id)) return;
  globalThis.location.hash = `#degram-install=${id}`;
  clearHostSignal();
}

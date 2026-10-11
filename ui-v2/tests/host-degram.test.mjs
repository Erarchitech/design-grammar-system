import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const originalLocation = globalThis.location;
const originalHistory = globalThis.history;

async function hostMode(search) {
  globalThis.location = { search, hash: "", pathname: "/" };
  globalThis.history = { replaceState() {} };
  return import(`../src/lib/hostMode.js?case=${encodeURIComponent(search)}-${Math.random()}`);
}

test.after(() => {
  globalThis.location = originalLocation;
  globalThis.history = originalHistory;
});

test("host flag permits DeGram regions and trimmed connectors", async () => {
  const normal = await hostMode("");
  assert.equal(normal.isDegramHost(), false);
  assert.equal(normal.isRegionAllowed("connectors"), true);

  const hosted = await hostMode("?host=degram");
  assert.equal(hosted.isDegramHost(), true);
  assert.deepEqual(hosted.HOST_REGIONS, ["graph", "model", "projects", "connectors"]);
  for (const region of ["landing", ...hosted.HOST_REGIONS]) assert.equal(hosted.isRegionAllowed(region), true);
  for (const region of ["aiengine", "reasoner", "apidocs", "unknown"]) assert.equal(hosted.isRegionAllowed(region), false);
});

test("host project announcement is bounded, encoded and transient", async () => {
  const hosted = await hostMode("?host=degram");
  const calls = [];
  globalThis.history = { replaceState(...args) { calls.push(args); } };
  hosted.announceProject("A b&c");
  assert.equal(globalThis.location.hash, "#degram-select=A%20b%26c");
  assert.equal(calls.length, 1);
  assert.equal(calls[0][2], "/?host=degram");
  hosted.announceProject("");
  hosted.announceProject("x".repeat(65));
  assert.equal(calls.length, 1);

  const normal = await hostMode("");
  globalThis.location.hash = "#unchanged";
  normal.announceProject("Project");
  assert.equal(globalThis.location.hash, "#unchanged");
});

test("host signals accept only exact state and navigation vocabulary", async () => {
  const hosted = await hostMode("?host=degram&lang=ru");
  assert.equal(hosted.hostLang(), "ru");
  for (const state of ["connecting", "ready", "idle"]) assert.deepEqual(hosted.parseHostSignal(`#degram-state=${state}`), { state });
  for (const go of ["landing", "graph", "model", "connectors"]) assert.deepEqual(hosted.parseHostSignal(`#degram-go=${go}`), { go });
  for (const hash of ["#degram", "#degram-state=READY", "#degram-state=ready&x=1", "#degram-go=reasoner", "#degram-go=projects", "#degram-go=graph/other", "#degram-select=A", "#degram-new-session"]) {
    assert.equal(hosted.parseHostSignal(hash), null, hash);
  }
  const normal = await hostMode("?lang=ru");
  assert.equal(normal.hostLang(), "en");
  assert.equal(normal.parseHostSignal("#degram-state=ready"), null);
  const english = await hostMode("?host=degram");
  assert.equal(english.hostLang(), "en");
});

test("host new-session announcement is transient and absent outside host mode", async () => {
  const hosted = await hostMode("?host=degram");
  const calls = [];
  globalThis.history = { replaceState(...args) { calls.push(args); } };
  hosted.announceNewSession();
  assert.equal(globalThis.location.hash, "#degram-new-session");
  assert.deepEqual(calls, [[null, "", "/?host=degram"]]);
  const normal = await hostMode("");
  globalThis.location.hash = "#unchanged";
  normal.announceNewSession();
  assert.equal(globalThis.location.hash, "#unchanged");
});

test("host-only ring centre is wired without altering the normal root selector", async () => {
  const main = await readFile(new URL("../src/main.jsx", import.meta.url), "utf8");
  const app = await readFile(new URL("../src/App.jsx", import.meta.url), "utf8");
  const landing = await readFile(new URL("../src/landing/LandingLayer.jsx", import.meta.url), "utf8");
  const centre = await readFile(new URL("../src/landing/HostCentre.jsx", import.meta.url), "utf8");
  assert.match(main, /location\.hash === "#degram"/);
  assert.match(main, /#degram-select/);
  assert.match(app, /parseHostSignal/);
  assert.match(app, /setHostState\(name \? "connecting" : "idle"\)/);
  assert.match(app, /clearHostSignal/);
  assert.match(landing, /degramHost\s*&&\s*<HostCentre/);
  assert.match(centre, /announceNewSession/);
  assert.match(centre, /dg-think-dark\.gif/);
  assert.match(centre, /dg-think-light\.gif/);
});

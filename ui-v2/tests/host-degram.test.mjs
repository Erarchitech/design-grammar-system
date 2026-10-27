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
  for (const go of ["landing", "graph", "model", "connectors", "projects"]) assert.deepEqual(hosted.parseHostSignal(`#degram-go=${go}`), { go });
  for (const hash of ["#degram", "#degram-state=READY", "#degram-state=ready&x=1", "#degram-go=reasoner", "#degram-go=aiengine", "#degram-go=", "#degram-go=graph/other", "#degram-select=A", "#degram-new-session"]) {
    assert.equal(hosted.parseHostSignal(hash), null, hash);
  }
  const normal = await hostMode("?lang=ru");
  assert.equal(normal.hostLang(), "en");
  assert.equal(normal.parseHostSignal("#degram-state=ready"), null);
  const english = await hostMode("?host=degram");
  assert.equal(english.hostLang(), "en");
});

test("host language signal accepts only ru and en, in host mode only (D-52)", async () => {
  const hosted = await hostMode("?host=degram");
  assert.deepEqual(hosted.parseHostSignal("#degram-lang=ru"), { lang: "ru" });
  assert.deepEqual(hosted.parseHostSignal("#degram-lang=en"), { lang: "en" });
  for (const hash of ["#degram-lang=de", "#degram-lang=RU", "#degram-lang=ru ", "#degram-lang=", "#degram-lang", "#degram-lang=ru&x=1", "#degram-lang=ruru", "#degram-lang=ru#a"]) {
    assert.equal(hosted.parseHostSignal(hash), null, hash);
  }
  const normal = await hostMode("");
  assert.equal(normal.parseHostSignal("#degram-lang=ru"), null);
});

test("host project signal names the project DeGram actually opened, or none (F-07)", async () => {
  const hosted = await hostMode("?host=degram");
  assert.deepEqual(hosted.parseHostSignal("#degram-project=degram-uat-c"), { project: "degram-uat-c" });
  assert.deepEqual(hosted.parseHostSignal("#degram-project=My%20Project_1.2"), { project: "My Project_1.2" });
  assert.deepEqual(hosted.parseHostSignal("#degram-project="), { project: null });
  assert.deepEqual(hosted.parseHostSignal(`#degram-project=${"x".repeat(64)}`), { project: "x".repeat(64) });
  for (const hash of [
    `#degram-project=${"x".repeat(65)}`,
    "#degram-project=a&x=1",
    "#degram-project=a#b",
    "#degram-project=%E0%A4%A",
    "#degram-project=a%0Ab",
    "#degram-project",
    "#degram-project=A/B/../C"
  ]) {
    assert.equal(hosted.parseHostSignal(hash), null, hash);
  }
  const normal = await hostMode("");
  assert.equal(normal.parseHostSignal("#degram-project=alpha"), null);
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

test("connector install signals: closed vocabulary both ways, absent outside host mode (quick 261027-sgc)", async () => {
  const hosted = await hostMode("?host=degram");
  assert.deepEqual(hosted.INSTALLABLE_CONNECTORS, ["revit", "grasshopper"]);
  assert.deepEqual(hosted.parseHostSignal("#degram-installed=revit:ready,grasshopper:install"), { installed: { revit: "ready", grasshopper: "install" } });
  assert.deepEqual(hosted.parseHostSignal("#degram-installed=grasshopper:needs-host"), { installed: { grasshopper: "needs-host" } });
  for (const hash of [
    "#degram-installed=",
    "#degram-installed=revit:done",
    "#degram-installed=dynamo:ready",
    "#degram-installed=revit:ready,grasshopper:install,revit:ready",
    "#degram-installed=revit:ready&x=1",
    "#degram-install=revit",
    "#degram-connectors-check"
  ]) {
    assert.equal(hosted.parseHostSignal(hash), null, hash);
  }

  const calls = [];
  globalThis.history = { replaceState(...args) { calls.push(args); } };
  hosted.requestConnectorStatus();
  assert.equal(globalThis.location.hash, "#degram-connectors-check");
  hosted.requestConnectorInstall("grasshopper");
  assert.equal(globalThis.location.hash, "#degram-install=grasshopper");
  globalThis.location.hash = "#unchanged";
  for (const id of ["dynamo", "Revit", "../revit", "", undefined]) hosted.requestConnectorInstall(id);
  assert.equal(globalThis.location.hash, "#unchanged");
  assert.equal(calls.length, 2);

  const normal = await hostMode("");
  globalThis.location.hash = "#unchanged";
  assert.equal(normal.parseHostSignal("#degram-installed=revit:ready"), null);
  normal.requestConnectorStatus();
  normal.requestConnectorInstall("revit");
  assert.equal(globalThis.location.hash, "#unchanged");

  // App hands the reported state to the Connectors table.
  const app = await readFile(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.match(app, /signal\.installed\) window\.dispatchEvent\(new CustomEvent\("dg-connector-install", \{ detail: signal\.installed \}\)\)/);
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
  // F-07: a project signal puts the page back on the open project without echoing it to the host.
  assert.match(app, /signal\.project !== undefined/);
  const projectBranch = app.slice(app.indexOf("signal.project !== undefined"), app.indexOf("clearHostSignal();", app.indexOf("signal.project !== undefined")));
  assert.match(projectBranch, /setProject\(signal\.project\)/);
  assert.match(projectBranch, /dgv2_project/);
  assert.doesNotMatch(projectBranch, /announceProject/);
  assert.match(landing, /degramHost\s*&&\s*<HostCentre/);
  assert.match(centre, /announceNewSession/);
  assert.match(centre, /dg-think-dark\.gif/);
  assert.match(centre, /dg-think-light\.gif/);
});

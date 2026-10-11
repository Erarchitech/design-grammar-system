import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const originalLocation = globalThis.location;
const originalHistory = globalThis.history;

async function hostMode(search) {
  globalThis.location = { search, hash: "" };
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
  assert.equal(calls[0][2], "");
  hosted.announceProject("");
  hosted.announceProject("x".repeat(65));
  assert.equal(calls.length, 1);

  const normal = await hostMode("");
  globalThis.location.hash = "#unchanged";
  normal.announceProject("Project");
  assert.equal(globalThis.location.hash, "#unchanged");
});

test("main only reloads when the #degram root slice toggles", async () => {
  const code = await readFile(new URL("../src/main.jsx", import.meta.url), "utf8");
  assert.match(code, /location\.hash === "#degram"/);
  assert.match(code, /#degram-select/);
});

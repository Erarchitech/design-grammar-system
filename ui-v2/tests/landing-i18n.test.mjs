import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

// Plan 1308-23: the landing layer is bilingual (D-03, D-21) and relayouts on a live switch (D-52); the browser control lives above every layer in App.
const read = (path) => readFile(new URL(`../src/landing/${path}`, import.meta.url), "utf8");

test("landing engine adds and removes a dg-lang listener next to the dg-theme one (D-52, T-1308-23-02)", async () => {
  const engine = await read("landingEngine.js");
  assert.match(engine, /addEventListener\(\s*"dg-lang"/);
  assert.match(engine, /removeEventListener\(\s*"dg-lang"/);
  assert.match(engine, /addEventListener\(\s*"dg-theme"/);
  const stop = engine.slice(engine.indexOf("  stop() {"), engine.indexOf("  setVisible("));
  assert.match(stop, /removeEventListener\(\s*"dg-lang"/, "the listener is removed in stop()");
  assert.match(stop, /cancelAnimationFrame\(this\._langRaf\)/, "a pending relayout is cancelled on teardown");
});

test("landing hero, region labels and hint go through t(); AI Engine is renamed LLM model (D-03, D-21)", async () => {
  const landing = await read("LandingLayer.jsx");
  for (const key of [
    "Encode Design Grammars",
    "System initiated",
    "Graph Viewer",
    "Model Viewer",
    "Projects",
    "LLM model",
    "Connectors",
    "Reasoner",
    "DG API Docs",
    "Select a region"
  ]) {
    assert.ok(landing.includes(`t("${key}")`), `t("${key}") missing`);
  }
  assert.doesNotMatch(landing, /AI Engine/);
  assert.ok(landing.includes("text={PRODUCT_NAME}"), "the hero title is the product name, a proper noun");
});

test("the landing itself has no separate language control (browser uses AppShell)", async () => {
  const landing = await read("LandingLayer.jsx");
  assert.doesNotMatch(landing, /setLang|LanguageBadge|dgv2_lang|EN\s*\|\s*RU/);
});

test("HostCentre no longer branches on hostLang; its texts are keyed", async () => {
  const centre = await read("HostCentre.jsx");
  assert.doesNotMatch(centre, /hostLang/);
  assert.ok(centre.includes('t("Start new session")'));
  assert.ok(centre.includes('t("Connecting to DG")'));
});

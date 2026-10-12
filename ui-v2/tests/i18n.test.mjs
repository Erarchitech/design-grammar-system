import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// The i18n core reads the host flag when hostMode.js is first evaluated, so the location stub is installed before
// the first import. This process therefore behaves as a DeGram host window opened with ?lang=ru.
const originalLocation = globalThis.location;
const originalHistory = globalThis.history;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
globalThis.location = { search: "?host=degram&lang=ru", hash: "", pathname: "/" };
globalThis.history = { replaceState() {} };

const i18nUrl = new URL("../src/i18n/index.js", import.meta.url);

// A fresh module instance per test keeps the module-level language state isolated.
async function fresh() {
  return import(`${i18nUrl.href}?case=${Math.random()}`);
}

function stubBrowser() {
  const events = [];
  const doc = { documentElement: { lang: "" } };
  globalThis.document = doc;
  globalThis.window = { dispatchEvent: (event) => events.push(event) };
  return { events, doc };
}

test.after(() => {
  globalThis.location = originalLocation;
  globalThis.history = originalHistory;
  if (originalWindow === undefined) delete globalThis.window;
  else globalThis.window = originalWindow;
  if (originalDocument === undefined) delete globalThis.document;
  else globalThis.document = originalDocument;
});

test("owner-fixed strings translate verbatim and EN returns the key (D-03)", async () => {
  const i18n = await fresh();
  assert.equal(i18n.translate("ru", "Design Grammars."), "Грамматика.");
  assert.equal(i18n.translate("ru", "Encode your design intent."), "Граф правил проекта.");
  assert.equal(i18n.translate("ru", "System initiated"), "Система инициализирована");
  assert.equal(i18n.translate("en", "Design Grammars."), "Design Grammars.");
  assert.equal(i18n.translate("en", "anything at all"), "anything at all");
  assert.deepEqual({ ...i18n.OWNER_FIXED }, {
    "Design Grammars.": "Грамматика.",
    "Encode your design intent.": "Граф правил проекта.",
    "System initiated": "Система инициализирована"
  });
});

test("dictionary lookups ignore prototype keys (T-1308-05-03)", async () => {
  const i18n = await fresh();
  for (const key of ["toString", "__proto__", "constructor", "hasOwnProperty"]) {
    assert.equal(i18n.translate("ru", key), key);
    assert.equal(i18n.translate("en", key), key);
  }
});

test("placeholders interpolate as plain text and unknown ones stay", async () => {
  const i18n = await fresh();
  assert.equal(i18n.translate("en", "Hello {name}", { name: "A" }), "Hello A");
  assert.equal(i18n.translate("en", "Hello {x}", { name: "A" }), "Hello {x}");
  assert.equal(i18n.translate("en", "Hello {name}", { name: "<b>A</b>" }), "Hello <b>A</b>");
  assert.equal(i18n.translate("en", "Hello {name}"), "Hello {name}");
});

test("Russian plural categories follow Intl.PluralRules", () => {
  const rules = new Intl.PluralRules("ru");
  assert.equal(rules.select(1), "one");
  assert.equal(rules.select(2), "few");
  assert.equal(rules.select(5), "many");
  assert.equal(rules.select(21), "one");
});

test("plural() picks the form for the language and fills {n}", async () => {
  const i18n = await fresh();
  // Not in the dictionary: falls back to the English key with {n} filled.
  assert.equal(i18n.plural("en", "{n} node", 3), "3 node");
  assert.equal(i18n.plural("ru", "{n} node", 3), "3 node");
});

test("resolveLang: host uses the allowlisted host language and ignores the browser (D-07)", async () => {
  const { resolveLang } = await fresh();
  assert.equal(resolveLang({ isHost: true, hostLang: "ru", browserLanguages: ["en-US"] }), "ru");
  assert.equal(resolveLang({ isHost: true, hostLang: "en", browserLanguages: ["ru-RU"] }), "en");
  assert.equal(resolveLang({ isHost: true, hostLang: undefined, browserLanguages: ["ru"] }), "en");
  assert.equal(resolveLang({ isHost: true, hostLang: "fr", browserLanguages: ["ru"] }), "en");
  assert.equal(resolveLang({ isHost: true, hostLang: "RU ", browserLanguages: [] }), "en");
});

test("resolveLang: outside the host only the primary browser language counts (D-53)", async () => {
  const { resolveLang } = await fresh();
  assert.equal(resolveLang({ isHost: false, browserLanguages: ["ru"] }), "ru");
  assert.equal(resolveLang({ isHost: false, browserLanguages: ["ru-RU", "en"] }), "ru");
  assert.equal(resolveLang({ isHost: false, browserLanguages: ["RU-ru"] }), "ru");
  assert.equal(resolveLang({ isHost: false, browserLanguages: ["en-US", "ru"] }), "en");
  assert.equal(resolveLang({ isHost: false, browserLanguages: ["de"] }), "en");
  assert.equal(resolveLang({ isHost: false, browserLanguages: [] }), "en");
  assert.equal(resolveLang({ isHost: false }), "en");
  assert.equal(resolveLang({ isHost: false, hostLang: "ru", browserLanguages: ["en"] }), "en");
  assert.equal(resolveLang(), "en");
});

test("setLang notifies subscribers, sets html lang, dispatches dg-lang and rejects other values", async () => {
  const { events, doc } = stubBrowser();
  const i18n = await fresh();
  const seen = [];
  const off = i18n.subscribe((lang) => seen.push(lang));
  assert.equal(i18n.getLang(), "en");
  i18n.setLang("ru");
  assert.equal(i18n.getLang(), "ru");
  assert.equal(doc.documentElement.lang, "ru");
  assert.deepEqual(seen, ["ru"]);
  assert.equal(events.length, 1);
  assert.equal(events[0].type, "dg-lang");
  assert.equal(events[0].detail, "ru");

  i18n.setLang("de");
  i18n.setLang("RU ");
  i18n.setLang(undefined);
  assert.equal(i18n.getLang(), "ru");
  assert.equal(events.length, 1);

  i18n.setLang("ru");
  assert.equal(events.length, 1, "no notification when nothing changed");

  off();
  i18n.setLang("en");
  assert.deepEqual(seen, ["ru"]);
  assert.equal(doc.documentElement.lang, "en");
  assert.equal(i18n.t("Design Grammars."), "Design Grammars.");
  i18n.setLang("ru");
  assert.equal(i18n.t("Design Grammars."), "Грамматика.");
});

test("initLang in host mode reads ?lang= and ignores the browser; the live signal then wins", async () => {
  stubBrowser();
  Object.defineProperty(globalThis, "navigator", { value: { languages: ["en-US"], language: "en-US" }, configurable: true });
  const i18n = await fresh();
  assert.equal(i18n.initLang(), "ru", "host ?lang=ru with an English browser stays ru");
  assert.equal(i18n.getLang(), "ru");
  i18n.setLang("en");
  assert.equal(i18n.getLang(), "en", "a live signal after load wins over ?lang=");
  i18n.setLang("ru");
  assert.equal(i18n.getLang(), "ru");
  delete globalThis.navigator;
});

test("initLang with an injected plain-browser environment follows the browser language", async () => {
  stubBrowser();
  const i18n = await fresh();
  assert.equal(i18n.initLang({ isHost: false, hostLang: "en", browserLanguages: ["ru-RU"] }), "ru");
  assert.equal(i18n.getLang(), "ru");
  assert.equal(i18n.initLang({ isHost: false, hostLang: "ru", browserLanguages: [] }), "en");
  assert.equal(i18n.getLang(), "en");
});

test("t, tc and tp are bound to the current language", async () => {
  stubBrowser();
  const i18n = await fresh();
  i18n.setLang("ru");
  assert.equal(i18n.t("System initiated"), "Система инициализирована");
  assert.equal(i18n.tc("verb", "Open"), "Open", "tc strips the context when there is no entry");
  assert.equal(i18n.tp("{n} item", 2), "2 item");
});

test("App applies the host language signal through setLang inside the provider and clears the hash", async () => {
  const app = await readFile(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.match(app, /<LanguageProvider>/);
  assert.match(app, /if \(signal\.lang\) setLang\(signal\.lang\);/);
  const handler = app.slice(app.indexOf("const onHash"), app.indexOf('window.addEventListener("hashchange"'));
  assert.ok(handler.indexOf("setLang(signal.lang)") < handler.indexOf("clearHostSignal()"));
});

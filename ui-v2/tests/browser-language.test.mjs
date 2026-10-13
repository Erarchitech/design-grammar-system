import test from "node:test";
import assert from "node:assert/strict";

const original = {
  location: globalThis.location,
  navigator: globalThis.navigator,
  document: globalThis.document,
  window: globalThis.window,
  localStorage: globalThis.localStorage
};
const values = new Map();
const events = [];
globalThis.location = { search: "", hash: "", pathname: "/" };
globalThis.navigator = { languages: ["en-US"], language: "en-US" };
globalThis.document = { documentElement: { lang: "" } };
globalThis.window = { dispatchEvent: (event) => events.push(event) };
globalThis.localStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value)
};

const i18nUrl = new URL("../src/i18n/index.js", import.meta.url);
const fresh = () => import(`${i18nUrl.href}?browserCase=${Math.random()}`);

test.after(() => {
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete globalThis[key];
    else globalThis[key] = value;
  }
});

test("a browser choice changes the live page and survives a fresh module load", async () => {
  values.clear();
  const first = await fresh();
  assert.equal(first.initLang(), "en");
  first.chooseBrowserLang("ru");
  assert.equal(first.getLang(), "ru");
  assert.equal(globalThis.document.documentElement.lang, "ru");
  assert.equal(values.get(first.BROWSER_LANG_KEY), "ru");
  const next = await fresh();
  assert.equal(next.initLang(), "ru");
  next.chooseBrowserLang("en");
  assert.equal(values.get(first.BROWSER_LANG_KEY), "en");
  assert.equal(next.getLang(), "en");
});

test("invalid stored or selected values fall back without overwriting the preference", async () => {
  values.set("dgv2_lang", "fr");
  const i18n = await fresh();
  assert.equal(i18n.initLang(), "en");
  i18n.chooseBrowserLang("RU ");
  assert.equal(i18n.getLang(), "en");
  assert.equal(values.get("dgv2_lang"), "fr");
});

test("blocked browser storage does not prevent a live choice", async () => {
  const storage = globalThis.localStorage;
  try {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      get() { throw new Error("storage blocked"); }
    });
    const i18n = await fresh();
    assert.equal(i18n.initLang(), "en");
    i18n.chooseBrowserLang("ru");
    assert.equal(i18n.getLang(), "ru");
    assert.equal(globalThis.document.documentElement.lang, "ru");
  } finally {
    Object.defineProperty(globalThis, "localStorage", { configurable: true, value: storage, writable: true });
  }
});

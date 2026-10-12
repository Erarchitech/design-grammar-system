import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

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

// ---------------------------------------------------------------------------------------------------------------
// Task 2: error mapping, enums, dates, key coverage (D-12 rules a-f, h) and the raw-text guard.
// ---------------------------------------------------------------------------------------------------------------
const SRC_DIR = fileURLToPath(new URL("../src/", import.meta.url));
const SWEPT_DIR = fileURLToPath(new URL("./i18n-swept/", import.meta.url));
const SEP = "\u0004";
const D09_CODES = [
  "AUTH_FAILED", "INVITE_INVALID", "PASSWORD_POLICY", "REGISTRATION_INVALID", "PROJECT_NAME_UNAVAILABLE",
  "PROJECT_FORBIDDEN", "LAST_OWNER", "MEMBER_NOT_FOUND", "ROLE_INVALID", "ADMIN_REQUIRED",
  "CONNECTOR_ACCESS_REQUIRED", "ACCESS_EXISTS", "NOT_A_MEMBER", "DEGRAM_POLICY_INVALID", "CONNECTOR_TOKENS_RETIRED"
];
// Not scanned for t() calls: the dictionaries themselves, the throwaway specimen page and the API-docs body (D-10).
const COVERAGE_EXCLUDED = [/[\\/]specimen[\\/]/, /[\\/]screens[\\/]apidocs[\\/]content[\\/]/, /[\\/]i18n[\\/]dict[\\/]/];

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = `${dir}${entry.name}`;
    if (entry.isDirectory()) out.push(...(await walk(`${full}/`)));
    else out.push(full);
  }
  return out;
}

async function sourceFiles() {
  return (await walk(SRC_DIR)).filter((file) => /\.(js|jsx)$/.test(file));
}

function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, (block) => block.replace(/[^\n]/g, " "))
    .replace(/(^|[\s;,{(])\/\/.*$/gm, "$1");
}

function parseLiteral(text) {
  const quote = text[0];
  const inner = text.slice(1, -1);
  try {
    return JSON.parse(quote === '"' ? text : `"${inner.replace(/\\'/g, "'").replace(/"/g, '\\"')}"`);
  } catch {
    return inner;
  }
}

const LITERAL = /^("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')/;

// Finds every t/tc/tp call. A call whose key argument is not a plain quoted literal is reported as non-literal.
function findCalls(source) {
  const text = stripComments(source).replace(/\bfunction\s+(?:t|tc|tp)\s*\(/g, "function _decl(");
  const calls = [];
  const bad = [];
  for (const match of text.matchAll(/(?<![\w$.])(t|tc|tp)\(\s*/g)) {
    const fn = match[1];
    let rest = text.slice(match.index + match[0].length);
    const first = LITERAL.exec(rest);
    if (!first) {
      bad.push(`${fn}(${rest.slice(0, 24).replace(/\s+/g, " ")}`);
      continue;
    }
    if (fn === "tc") {
      rest = rest.slice(first[0].length);
      const comma = /^\s*,\s*/.exec(rest);
      const second = comma && LITERAL.exec(rest.slice(comma[0].length));
      if (!second) {
        bad.push(`tc(${first[0]}, ${rest.slice(0, 24).replace(/\s+/g, " ")}`);
        continue;
      }
      calls.push({ fn, key: parseLiteral(first[0]) + SEP + parseLiteral(second[0]) });
    } else {
      calls.push({ fn, key: parseLiteral(first[0]) });
    }
  }
  return { calls, bad };
}

function placeholders(text) {
  return [...new Set([...String(text).matchAll(/\{(\w+)\}/g)].map((m) => m[1]))].sort();
}

async function dictionary() {
  const { AREAS, RU, EN } = await import("../src/i18n/dict/index.js");
  return { AREAS, RU, EN };
}

test("describeError maps coded errors, then server text, then the fallback (D-09)", async () => {
  stubBrowser();
  const i18n = await fresh();
  const { RU, EN } = await dictionary();
  i18n.setLang("ru");
  assert.equal(i18n.describeError({ code: "LAST_OWNER" }, "fb"), RU["error.LAST_OWNER"]);
  assert.match(i18n.describeError({ code: "LAST_OWNER" }, "fb"), /владелец/);
  assert.equal(i18n.describeError({ code: "UNKNOWN", message: "srv" }, "fb"), "srv");
  assert.equal(i18n.describeError({}, "fb"), "fb");
  assert.equal(i18n.describeError(null, "fb"), "fb");
  assert.equal(i18n.describeError(undefined), "");
  assert.equal(i18n.describeError({ code: "toString", message: "" }, "fb"), "fb");
  assert.equal(i18n.describeError({ code: "LAST_OWNER", message: "server text" }, "fb"), RU["error.LAST_OWNER"]);
  i18n.setLang("en");
  assert.equal(i18n.describeError({ code: "LAST_OWNER" }, "fb"), EN["error.LAST_OWNER"]);
});

test("error keys exist in EN and RU for the 15 D-09 codes with equal placeholders", async () => {
  const { RU, EN } = await dictionary();
  for (const code of D09_CODES) {
    const key = `error.${code}`;
    assert.equal(typeof EN[key], "string", `EN ${key}`);
    assert.equal(typeof RU[key], "string", `RU ${key}`);
    assert.ok(EN[key].length > 0 && RU[key].length > 0, key);
    assert.deepEqual(placeholders(RU[key]), placeholders(EN[key]), key);
  }
  const enErrors = Object.keys(EN).filter((key) => key.startsWith("error."));
  const ruErrors = Object.keys(RU).filter((key) => key.startsWith("error."));
  assert.deepEqual([...enErrors].sort(), [...ruErrors].sort());
  assert.ok(enErrors.length >= D09_CODES.length);
});

test("enums map server roles and connector statuses through keys (D-13)", async () => {
  stubBrowser();
  const { roleLabel, connectorStatusLabel, ROLE_VALUES } = await import("../src/i18n/enums.js");
  // enums.js binds to the default module instance of index.js, so the language is set on that instance.
  const base = await import("../src/i18n/index.js");
  assert.deepEqual([...ROLE_VALUES], ["viewer", "editor", "owner"]);
  base.setLang("en");
  assert.equal(roleLabel("viewer"), "Viewer");
  assert.equal(connectorStatusLabel("active"), "On");
  assert.equal(connectorStatusLabel("stale"), "Off");
  base.setLang("ru");
  assert.equal(roleLabel("viewer"), "Наблюдатель");
  assert.equal(roleLabel("editor"), "Редактор");
  assert.equal(roleLabel("owner"), "Владелец");
  assert.equal(connectorStatusLabel("active"), "Вкл");
  assert.equal(connectorStatusLabel("stale"), "Выкл");
  assert.equal(roleLabel("auditor"), "auditor");
  assert.equal(roleLabel(undefined), "");
  base.setLang("en");
});

test("formatDate and formatTime use the current language and show a dash for empty or invalid input", async () => {
  stubBrowser();
  const i18n = await fresh();
  const iso = "2026-10-12T09:30:00Z";
  const opts = { dateStyle: "long", timeZone: "UTC" };
  i18n.setLang("en");
  const en = i18n.formatDate(iso, opts);
  i18n.setLang("ru");
  const ru = i18n.formatDate(iso, opts);
  assert.equal(en, new Intl.DateTimeFormat("en-US", opts).format(new Date(iso)));
  assert.equal(ru, new Intl.DateTimeFormat("ru-RU", opts).format(new Date(iso)));
  assert.notEqual(en, ru);
  for (const bad of ["", null, undefined, "not a date", {}]) {
    assert.equal(i18n.formatDate(bad), "—");
    assert.equal(i18n.formatTime(bad), "—");
  }
  const timeOpts = { timeStyle: "short", timeZone: "UTC" };
  assert.equal(i18n.formatTime(new Date(iso), timeOpts), new Intl.DateTimeFormat("ru-RU", timeOpts).format(new Date(iso)));
});

test("rule (f): resolution precedence is host live signal, then ?lang=, then browser (outside host only), then en", async () => {
  stubBrowser();
  const i18n = await fresh();
  // host live signal over ?lang= at load
  assert.equal(i18n.initLang({ isHost: true, hostLang: "en", browserLanguages: ["ru"] }), "en");
  i18n.setLang("ru");
  assert.equal(i18n.getLang(), "ru");
  assert.equal(i18n.initLang({ isHost: true, hostLang: "ru", browserLanguages: ["en"] }), "ru");
  i18n.setLang("en");
  assert.equal(i18n.getLang(), "en");
  // ?lang= over the browser language in host mode, both directions
  assert.equal(i18n.resolveLang({ isHost: true, hostLang: "en", browserLanguages: ["ru-RU"] }), "en");
  assert.equal(i18n.resolveLang({ isHost: true, hostLang: "ru", browserLanguages: ["en-US"] }), "ru");
  // browser language over the default outside the host
  assert.equal(i18n.resolveLang({ isHost: false, browserLanguages: ["ru"] }), "ru");
  assert.equal(i18n.resolveLang({ isHost: false, browserLanguages: ["fr"] }), "en");
  // default
  assert.equal(i18n.resolveLang({ isHost: true }), "en");
  assert.equal(i18n.resolveLang({ isHost: false, browserLanguages: [] }), "en");
  // out-of-vocabulary values are ignored
  for (const bad of ["fr", "de", "RU ", "ru ", "", null, 7]) {
    assert.equal(i18n.resolveLang({ isHost: true, hostLang: bad, browserLanguages: ["ru"] }), "en", String(bad));
  }
});

test("rule (e): owner strings are verbatim in the dictionary and in OWNER_FIXED", async () => {
  const { RU } = await dictionary();
  const { OWNER_FIXED } = await fresh();
  const expected = [
    ["Design Grammars.", "Грамматика."],
    ["Encode your design intent.", "Граф правил проекта."],
    ["System initiated", "Система инициализирована"]
  ];
  for (const [en, ru] of expected) {
    assert.equal(RU[en], ru);
    assert.equal(OWNER_FIXED[en], ru);
  }
  assert.ok(Object.isFrozen(OWNER_FIXED));
});

test("rules (a),(b),(c),(d): every literal key has an RU entry, no RU key is unused, placeholders match, keys are literals", async () => {
  const { RU, EN } = await dictionary();
  const { OWNER_FIXED } = await fresh();
  const used = new Map();
  const nonLiteral = [];
  for (const file of await sourceFiles()) {
    if (COVERAGE_EXCLUDED.some((pattern) => pattern.test(file))) continue;
    const { calls, bad } = findCalls(await readFile(file, "utf8"));
    for (const call of calls) used.set(call.key, call.fn);
    for (const snippet of bad) nonLiteral.push(`${file.slice(SRC_DIR.length)}: ${snippet}`);
  }
  assert.deepEqual(nonLiteral, [], "first argument of t/tc/tp must be a quoted literal");

  const missing = [];
  for (const [key, fn] of used) {
    const entry = RU[key];
    if (fn === "tp") {
      if (!entry || typeof entry !== "object") missing.push(`RU plural ${key}`);
      if (!EN[key] || typeof EN[key] !== "object") missing.push(`EN plural ${key}`);
    } else if (typeof entry !== "string") {
      missing.push(`RU ${key.replace(SEP, " | ")}`);
    }
  }
  assert.deepEqual(missing, [], "keys used in source without an RU entry");

  // The owner-fixed strings are exempt until the landing renders them (plan 1308-23); error.* keys are looked up
  // dynamically by describeError.
  const unused = Object.keys(RU).filter(
    (key) => !key.startsWith("error.") && !Object.hasOwn(OWNER_FIXED, key) && !used.has(key)
  );
  assert.deepEqual(unused, [], "RU keys never used by a literal t/tc/tp call");

  const mismatched = [];
  for (const key of Object.keys(RU)) {
    const value = RU[key];
    if (key.startsWith("error.")) {
      if (typeof EN[key] !== "string") mismatched.push(`${key}: no EN text`);
      else if (placeholders(value).join() !== placeholders(EN[key]).join()) mismatched.push(key);
      continue;
    }
    if (value && typeof value === "object") {
      const en = EN[key];
      if (!en || typeof en !== "object" || typeof en.other !== "string") {
        mismatched.push(`${key}: plural without an EN table`);
        continue;
      }
      for (const [form, text] of Object.entries(value)) {
        if (placeholders(text).join() !== placeholders(en.other).join()) mismatched.push(`${key} [${form}]`);
      }
      continue;
    }
    const english = key.includes(SEP) ? key.split(SEP)[1] : key;
    if (placeholders(value).join() !== placeholders(english).join()) mismatched.push(key);
  }
  assert.deepEqual(mismatched, [], "placeholder parity between EN and RU");
  for (const key of Object.keys(EN)) {
    assert.ok(key.startsWith("error.") || typeof EN[key] === "object", `EN entry ${key} must be an error text or a plural table`);
  }
});

test("rule (d) detector: non-literal and template-literal first arguments are reported", () => {
  assert.equal(findCalls("const a = t(label);").bad.length, 1);
  assert.equal(findCalls("const a = t(`x ${y}`);").bad.length, 1);
  assert.equal(findCalls("const a = tp(name, 2);").bad.length, 1);
  assert.equal(findCalls('const a = tc(ctx, "Open");').bad.length, 1);
  assert.equal(findCalls('const a = tc("verb", name);').bad.length, 1);
  assert.equal(findCalls('const a = "x".split("y"); const b = set(1); Math.min(a);').bad.length, 0);
  assert.equal(findCalls("export function t(key, params) { return 1; }").bad.length, 0);
  assert.deepEqual(findCalls("const a = t('It\\'s fine');").calls, [{ fn: "t", key: "It's fine" }]);
  assert.deepEqual(findCalls('const a = tc("verb", "Open");').calls, [{ fn: "tc", key: `verb${SEP}Open` }]);
});

test("rule (h): no key has conflicting RU values in two area modules (identical duplicates are allowed)", async () => {
  const { AREAS } = await dictionary();
  const seen = new Map();
  const conflicts = [];
  for (const [area, module] of Object.entries(AREAS)) {
    assert.equal(typeof module.ru, "object", `${area}.ru`);
    assert.equal(typeof module.en, "object", `${area}.en`);
    for (const [key, value] of Object.entries(module.ru)) {
      const text = JSON.stringify(value);
      if (seen.has(key) && seen.get(key).text !== text) conflicts.push(`${key} (${seen.get(key).area} vs ${area})`);
      else seen.set(key, { area, text });
    }
  }
  assert.deepEqual(conflicts, []);
});

test("dict/index exports RU, EN and AREAS with the eight area modules", async () => {
  const { AREAS } = await dictionary();
  assert.deepEqual(Object.keys(AREAS), ["core", "errors", "projects", "landing", "graph", "model", "connectors", "screens"]);
});

test("D-50/D-11: no language control, no language storage and no LanguageBadge in ui-v2", async () => {
  const files = await walk(SRC_DIR);
  assert.deepEqual(files.filter((file) => /LanguageBadge/i.test(file)), []);
  for (const file of files.filter((f) => /\.(js|jsx|css)$/.test(f))) {
    const text = await readFile(file, "utf8");
    assert.doesNotMatch(text, /dgv2_lang/, file);
    assert.doesNotMatch(text, /\bEN\s*\|\s*RU\b/, file);
    if (/[\\/]i18n[\\/]/.test(file)) {
      assert.doesNotMatch(text, /localStorage|sessionStorage|document\.cookie/, file);
    }
  }
});

test("package.json adds no dependency for i18n and keeps the test script", async () => {
  const pkg = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  assert.deepEqual(Object.keys(pkg.dependencies).sort(), ["@speckle/objectloader2", "@speckle/viewer", "react", "react-dom"]);
  assert.match(pkg.scripts.test, /node --test/);
});

// --- raw-text guard -------------------------------------------------------------------------------------------

function scanRawText(source, { allow = [], properNouns = [] } = {}) {
  const permitted = (text) => {
    const trimmed = text.trim();
    if (allow.includes(trimmed) || properNouns.includes(trimmed)) return true;
    return trimmed
      .split(/[\s,./·|—:;()+-]+/)
      .filter(Boolean)
      .every((word) => properNouns.includes(word) || !/[A-Za-z]{2,}/.test(word));
  };
  const cleaned = stripComments(source)
    .split("\n")
    .map((line) => (/^\s*import\s/.test(line) || /\bconsole\.\w+\(/.test(line) ? "" : line))
    .join("\n");
  const findings = new Map();
  const flag = (kind, text) => {
    if (!findings.has(text)) findings.set(text, kind);
  };
  for (const match of cleaned.matchAll(/(?<![=\-])>([^<>{}]*)</g)) {
    const text = match[1];
    if (/[=;]|&&|\|\|/.test(text)) continue;
    if (/[A-Za-z]{2,}/.test(text) && !permitted(text)) flag("jsx-text", text.trim());
  }
  for (const match of cleaned.matchAll(/\b(?:title|placeholder|aria-label|label|alt)=("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g)) {
    const text = parseLiteral(match[1]);
    if (/[A-Za-z]{2,}/.test(text) && !permitted(text)) flag("attribute", text);
  }
  for (const match of cleaned.matchAll(/"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'/g)) {
    const before = cleaned.slice(Math.max(0, match.index - 80), match.index);
    if (/(?<![\w$.])(?:t|tp)\(\s*$/.test(before) || /(?<![\w$.])tc\(\s*(?:"[^"]*"|'[^']*')\s*,\s*$/.test(before)) continue;
    const text = parseLiteral(match[0]);
    if (/^[A-Z][A-Za-z'’-]*\s+\S/.test(text) && !permitted(text)) flag("sentence", text);
  }
  return [...findings].map(([text, kind]) => ({ kind, text }));
}

test("raw-text guard flags JSX text, UI attributes and sentence-like literals outside t()", async () => {
  const { PROPER_NOUNS } = await fresh();
  const scan = (src, allow = []) => scanRawText(src, { allow, properNouns: [...PROPER_NOUNS] }).map((f) => f.text);
  assert.deepEqual(scan("<div>Hello world</div>"), ["Hello world"]);
  assert.deepEqual(scan('<button title="Close it" />'), ["Close it"]);
  assert.deepEqual(scan('<input placeholder="Search" aria-label="Search box" />'), ["Search", "Search box"]);
  assert.deepEqual(scan('const msg = "Could not save the setting";'), ["Could not save the setting"]);
  assert.deepEqual(scan("<span>\n  Sign out\n</span>"), ["Sign out"]);
});

test("raw-text guard accepts t() calls, proper nouns, allow-listed text, console lines and imports", async () => {
  const { PROPER_NOUNS } = await fresh();
  const scan = (src, allow = []) => scanRawText(src, { allow, properNouns: [...PROPER_NOUNS] }).map((f) => f.text);
  assert.deepEqual(scan('<div>{t("Hello world")}</div>'), []);
  assert.deepEqual(scan('<button title={t("Close it")} aria-label={tc("verb", "Close it")} />'), []);
  assert.deepEqual(scan('const m = tp("Select the project", 2);'), []);
  assert.deepEqual(scan("<span>Neo4j</span><i>Speckle · Rhino</i>"), []);
  assert.deepEqual(scan('console.warn("Something went wrong here");'), []);
  assert.deepEqual(scan('import { x } from "Some thing";'), []);
  assert.deepEqual(scan("const f = (a) => a > 1 && b < 2;"), []);
  assert.deepEqual(scan("<div>Inter Medium</div>", ["Inter Medium"]), []);
  assert.deepEqual(scan('// Comment with "Quoted Words here"\nconst a = 1;'), []);
  assert.deepEqual(scan('const k = "lower case words";'), []);
  assert.deepEqual(scan("<div>  </div><b>42</b>"), []);
});

test("raw-text guard passes every swept file listed in tests/i18n-swept/*.json (zero manifests is a pass)", async () => {
  const { PROPER_NOUNS } = await fresh();
  let manifests = [];
  try {
    manifests = (await readdir(SWEPT_DIR)).filter((name) => name.endsWith(".json"));
  } catch {
    manifests = [];
  }
  for (const name of manifests) {
    const manifest = JSON.parse(await readFile(`${SWEPT_DIR}${name}`, "utf8"));
    assert.equal(typeof manifest.area, "string", `${name}: area`);
    assert.ok(Array.isArray(manifest.files), `${name}: files`);
    assert.ok(Array.isArray(manifest.allow ?? []), `${name}: allow`);
    for (const file of manifest.files) {
      const source = await readFile(fileURLToPath(new URL(`../${file}`, import.meta.url)), "utf8");
      const findings = scanRawText(source, { allow: manifest.allow ?? [], properNouns: [...PROPER_NOUNS] });
      assert.deepEqual(findings, [], `${name}: ${file} has untranslated text`);
    }
  }
});

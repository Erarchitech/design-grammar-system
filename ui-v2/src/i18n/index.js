// In-house EN/RU i18n for ui-v2 (phase 1308, D-06..D-13).
//
// English text is the key: EN returns the key itself (after {name} interpolation), RU looks the key up in the
// merged dictionary and falls back to the English key. In DeGram the language comes from the host (live
// #degram-lang signal, else ?lang= at load). A plain browser starts from a remembered choice, then its primary
// browser language. Both paths share the same store; only the browser persists a choice.
import { hostLang, isDegramHost } from "../lib/hostMode.js";
import { EN, RU } from "./dict/index.js";

export const LANGS = Object.freeze(["en", "ru"]);

// D-13: proper nouns and identifiers stay Latin in every language and never go through t().
export const PROPER_NOUNS = Object.freeze([
  "Neo4j",
  "Speckle",
  "Grasshopper",
  "Rhino",
  "Revit",
  "DeGram",
  "Pellet",
  "HermiT",
  "Rule_Id",
  "IRI",
  "SWRL",
  "OntoGraph",
  "Metagraph",
  "ValidGraph",
  "Computgraph"
]);

// D-03: strings fixed by the owner. The landing renders them in plan 1308-23; the test pins them verbatim.
export const OWNER_FIXED = Object.freeze({
  "Design Grammars.": "Грамматика.",
  "Encode your design intent.": "Граф правил проекта.",
  "System initiated": "Система инициализирована"
});

export const LANG_EVENT = "dg-lang";
export const BROWSER_LANG_KEY = "dgv2_lang";
const CONTEXT_SEP = "\u0004";

function isLang(value) {
  return value === "en" || value === "ru";
}

function interpolate(text, params) {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name) => (Object.hasOwn(params, name) ? String(params[name]) : whole));
}

function table(lang) {
  return lang === "ru" ? RU : EN;
}

// Pure lookup. Object.hasOwn keeps prototype keys ("toString", "__proto__") from resolving to functions.
export function translate(lang, key, params) {
  const t = table(lang);
  const raw = Object.hasOwn(t, key) && typeof t[key] === "string" ? t[key] : key;
  return interpolate(raw, params);
}

// Plural lookup: the dictionary entry is an object of plural forms ({one, few, many, other}); {n} is always set.
export function plural(lang, key, n, params) {
  const entry = table(lang)[key];
  const merged = { ...(params || {}), n };
  if (entry && typeof entry === "object") {
    const form = new Intl.PluralRules(lang === "ru" ? "ru" : "en").select(n);
    const text = Object.hasOwn(entry, form) ? entry[form] : entry.other;
    if (typeof text === "string") return interpolate(text, merged);
  }
  return interpolate(key, merged);
}

// D-07: host live signal is applied through setLang; this resolves the language at load.
export function resolveLang({ isHost = false, hostLang: fromHost, browserChoice, browserLanguages } = {}) {
  if (isHost) return isLang(fromHost) ? fromHost : "en";
  if (isLang(browserChoice)) return browserChoice;
  const first = Array.isArray(browserLanguages) ? browserLanguages[0] : undefined;
  return typeof first === "string" && first.toLowerCase().startsWith("ru") ? "ru" : "en";
}

let current = "en";
const listeners = new Set();

function apply(lang) {
  const changed = current !== lang;
  current = lang;
  // D-08: only the validated value reaches <html lang>.
  if (typeof document !== "undefined" && document.documentElement) document.documentElement.lang = lang;
  return changed;
}

function announce() {
  for (const listener of [...listeners]) listener(current);
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function" && typeof CustomEvent === "function") {
    window.dispatchEvent(new CustomEvent(LANG_EVENT, { detail: current }));
  }
}

export function getLang() {
  return current;
}

export function setLang(lang) {
  if (!isLang(lang)) return;
  const changed = apply(lang);
  if (changed) announce();
}

// Browser choice is presentation-only, never an authority over DeGram's host language.
export function chooseBrowserLang(lang) {
  if (!isLang(lang) || isDegramHost()) return;
  try {
    globalThis.localStorage?.setItem(BROWSER_LANG_KEY, lang);
  } catch {
    // Unavailable storage leaves the choice active for this page only.
  }
  setLang(lang);
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function browserLanguages() {
  const nav = globalThis.navigator;
  if (!nav) return [];
  if (Array.isArray(nav.languages) && nav.languages.length > 0) return nav.languages;
  return nav.language ? [nav.language] : [];
}

function savedBrowserLang() {
  try {
    return globalThis.localStorage?.getItem(BROWSER_LANG_KEY);
  } catch {
    return null;
  }
}

// The optional argument lets a test inject the environment; production calls it with none.
export function initLang(env) {
  const lang = resolveLang(
    env || { isHost: isDegramHost(), hostLang: hostLang(), browserChoice: savedBrowserLang(), browserLanguages: browserLanguages() }
  );
  const changed = apply(lang);
  if (changed) announce();
  return lang;
}

export function t(key, params) {
  return translate(current, key, params);
}

// Context-disambiguated key: same English word, different Russian (verb vs noun).
export function tc(context, key, params) {
  return translate(current, context + CONTEXT_SEP + key, params).replace(/^[^\u0004]*\u0004/, "");
}

export function tp(key, n, params) {
  return plural(current, key, n, params);
}

// D-09: server errors are translated by code; unmapped codes show the server text, then the caller's fallback.
export function describeError(err, fallback) {
  const code = err && typeof err.code === "string" ? err.code : "";
  if (code) {
    const key = `error.${code}`;
    const mapped = table(current);
    if (Object.hasOwn(mapped, key) && typeof mapped[key] === "string") return mapped[key];
  }
  if (err && typeof err.message === "string" && err.message) return err.message;
  return fallback === undefined ? "" : fallback;
}

function locale() {
  return current === "ru" ? "ru-RU" : "en-US";
}

function toDate(value) {
  if (value === null || value === undefined || value === "") return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(iso, opts = { dateStyle: "medium", timeStyle: "short" }) {
  const date = toDate(iso);
  return date ? new Intl.DateTimeFormat(locale(), opts).format(date) : "—";
}

export function formatTime(date, opts = { timeStyle: "short" }) {
  const value = toDate(date);
  return value ? new Intl.DateTimeFormat(locale(), opts).format(value) : "—";
}

export { CONTEXT_SEP };

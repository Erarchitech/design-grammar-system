import React from "react";
import { getLang, initLang, subscribe, translate, plural, CONTEXT_SEP } from "./index.js";

// The store is module-level, so useT() works without the provider (browser harnesses keep rendering). The provider
// only resolves the language once, before the first child renders. It renders no control: the language is switched
// in DeGram Settings and reaches the page as a host signal (D-50, D-52).
export function useT() {
  const lang = React.useSyncExternalStore(subscribe, getLang, getLang);
  return React.useMemo(
    () => ({
      lang,
      t: (key, params) => translate(lang, key, params),
      tc: (context, key, params) => translate(lang, context + CONTEXT_SEP + key, params).replace(/^[^\u0004]*\u0004/, ""),
      tp: (key, n, params) => plural(lang, key, n, params)
    }),
    [lang]
  );
}

export function LanguageProvider({ children }) {
  React.useState(() => {
    initLang();
    return true;
  });
  useT();
  return children;
}

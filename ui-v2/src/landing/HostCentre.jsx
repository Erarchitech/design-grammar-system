import React from "react";
import { announceNewSession } from "../lib/hostMode.js";
import { useT } from "../i18n/LanguageProvider.jsx";

export default function HostCentre({ hostState, mode }) {
  const { t } = useT();
  const [theme, setTheme] = React.useState(() => document.documentElement.dataset.theme);
  const [imageFailed, setImageFailed] = React.useState(false);

  React.useEffect(() => {
    const onTheme = () => setTheme(document.documentElement.dataset.theme);
    window.addEventListener("dg-theme", onTheme);
    return () => window.removeEventListener("dg-theme", onTheme);
  }, []);
  React.useEffect(() => setImageFailed(false), [theme]);

  if (mode === "pill") return hostState === "ready" ? (
    <button type="button" className="dgl-host-pill" onClick={announceNewSession}>
      {t("Start new session")}
    </button>
  ) : null;

  return (
    <div
      className={`dgl-host-centre${hostState === "connecting" ? " dgl-host-centre--visible" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={t("Connecting to DG")}
      aria-hidden={hostState !== "connecting"}
    >
      {imageFailed ? <span className="dgl-host-centre-fallback" aria-hidden="true" /> :
        <img className="dgl-host-centre-sphere" src={theme === "dark" ? "/dg-think-dark.gif" : "/dg-think-light.gif"} onError={() => setImageFailed(true)} alt="" />}
    </div>
  );
}

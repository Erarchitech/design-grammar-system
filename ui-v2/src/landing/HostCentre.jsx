import React from "react";
import { announceNewSession, hostLang } from "../lib/hostMode.js";

export default function HostCentre({ hostState, mode }) {
  const ru = hostLang() === "ru";
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
      {ru ? "Начать новую сессию" : "Start new session"}
    </button>
  ) : null;

  return (
    <div className={`dgl-host-centre${hostState === "connecting" ? " dgl-host-centre--visible" : ""}`} aria-live="polite" aria-hidden={hostState !== "connecting"}>
      {imageFailed ? <span className="dgl-host-centre-fallback" aria-hidden="true" /> :
        <img className="dgl-host-centre-sphere" src={theme === "dark" ? "/dg-think-dark.gif" : "/dg-think-light.gif"} onError={() => setImageFailed(true)} alt="" />}
      <span>{ru ? "Подключение к DG" : "Connecting to DG"}</span>
    </div>
  );
}

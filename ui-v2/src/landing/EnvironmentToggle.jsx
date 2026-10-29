import React from "react";
import { useT } from "../i18n/LanguageProvider.jsx";
import { isDegramHost } from "../lib/hostMode.js";
import "./environment-toggle.css";

const TARGETS = { developer: "http://localhost:8080", demo: "https://dg.173-249-46-99.nip.io" };

export default function EnvironmentToggle() {
  const { t } = useT();
  const hosted = isDegramHost();
  const params = new URLSearchParams(globalThis.location?.search || "");
  const mode = hosted ? params.get("dgTarget") : ["localhost", "127.0.0.1", "[::1]"].includes(globalThis.location?.hostname) ? "developer" : "demo";
  const [open, setOpen] = React.useState(false);
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState(false);
  const timer = React.useRef(null);
  const root = React.useRef(null);
  const cancel = () => clearTimeout(timer.current);
  const close = () => { cancel(); setOpen(false); };
  const schedule = () => { cancel(); timer.current = setTimeout(() => setOpen(true), 1000); };
  React.useEffect(() => () => clearTimeout(timer.current), []);
  React.useEffect(() => {
    const failed = () => { setPending(false); setError(true); setOpen(true); };
    window.addEventListener("dg-target-refused", failed);
    return () => window.removeEventListener("dg-target-refused", failed);
  }, []);
  const select = async () => {
    const next = mode === "developer" ? "demo" : "developer";
    setPending(true);
    setError(false);
    if (hosted) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      // A bounded intent only. Main validates the current generation and owns the runtime switch.
      window.location.hash = `#degram-target=${next}:${params.get("dgGeneration")}`;
      return;
    }
    try {
      // Probe without cookies; never transfer the current session, project, query or hash to another origin.
      await fetch(`${TARGETS[next]}/`, { mode: "no-cors", credentials: "omit", cache: "no-store", signal: AbortSignal.timeout(5000) });
      window.location.assign(`${TARGETS[next]}/`);
    } catch {
      setPending(false);
      setError(true);
      setOpen(true);
    }
  };
  const locked = hosted && (params.get("dgTargetLocked") === "1" || !/^\d+$/.test(params.get("dgGeneration") || ""));
  return (
    <div className="dg-environment" ref={root} onPointerLeave={close} onBlur={event => { if (!root.current?.contains(event.relatedTarget)) close(); }} onKeyDown={event => { if (event.key === "Escape") close(); }}>
      <button type="button" className="dg-environment-switch" role="switch" aria-label={t("Demo environment")} aria-checked={mode === "demo"} aria-expanded={open} aria-busy={pending} aria-disabled={pending || locked} data-mode={mode} onPointerEnter={event => { if (event.pointerType !== "touch") schedule(); }} onPointerLeave={cancel} onFocus={schedule} onClick={() => { if (!pending && !locked) void select(); }}>
        <span>{mode === "developer" ? "Dev" : "Demo"}</span>
      </button>
      {open && <div className="dg-environment-details" role="status">
        <strong>{t("Operating mode")}</strong>
        <code>{globalThis.location?.origin}</code>
        <span>{pending ? t("Switching environment…") : error ? t("Environment switch failed. Try again.") : locked ? t("Environment is locked by startup settings.") : mode === "developer" ? t("Local environment") : t("Demo environment")}</span>
      </div>}
    </div>
  );
}

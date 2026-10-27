import React from "react";
import { Button } from "../components/index.js";
import { DEGRAM_CONNECTOR_ID } from "../lib/connectorsApi.js";
import { INSTALLABLE_CONNECTORS, requestConnectorInstall, requestConnectorStatus } from "../lib/hostMode.js";
import { useT } from "../i18n/LanguageProvider.jsx";

// DeGram-hosted table: one registry connector per row, with its own access
// request flow. The hosted status dots intentionally keep their green/red colors.
// The Installed column (quick 261027-sgc) installs DeGram's bundled add-ins: the
// page only asks; DeGram confirms natively, copies, and reports the state back.

const muted = { color: "var(--text-muted)", font: "400 12px/1.4 var(--font-sans)" };
const errorStyle = { color: "var(--status-fail)", font: "400 12px/1.4 var(--font-sans)" };
const cell = { padding: "10px 14px", border: "none", verticalAlign: "middle", font: "400 13px/1.3 var(--font-sans)" };
const noteField = {
  height: 28,
  minWidth: 150,
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-inputs)",
  padding: "0 10px",
  background: "var(--surface-input)",
  color: "var(--color-ink)",
  font: "400 12px/1 var(--font-sans)"
};

// What a locked install needs the user to close first.
const HOST_APP = { revit: "Revit", grasshopper: "Rhino" };

function InstalledCell({ connector, state, waiting, onInstall, t }) {
  if (!INSTALLABLE_CONNECTORS.includes(connector.id)) return <span style={muted}>—</span>;
  if (waiting) return <span data-installed="waiting" style={muted}>{t("Confirm in DeGram...")}</span>;
  if (state === "installing") return <span data-installed="installing" style={muted}>{t("Installing...")}</span>;
  if (state === "ready") {
    return (
      <span data-installed="ready" style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "var(--color-ink)" }}>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--status-on)", flex: "none" }} />
        {t("Ready")}
      </span>
    );
  }
  if (state === "needs-host") return <span data-installed="needs-host" style={muted}>{t("Install pyRevit first.")}</span>;
  if (state === "unavailable") return <span data-installed="unavailable" style={muted}>{t("Not included in this DeGram build.")}</span>;
  if (state !== "install" && state !== "locked" && state !== "failed") return <span style={muted}>—</span>;
  return (
    <span data-installed={state} style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <Button size="sm" onClick={() => onInstall(connector.id)} aria-label={`${t("Install")}: ${connector.name}`}>{t("Install")}</Button>
      {state === "locked" && <span style={muted}>{t("Close {app} and try again.", { app: HOST_APP[connector.id] })}</span>}
      {state === "failed" && <span style={errorStyle}>{t("Installation failed.")}</span>}
    </span>
  );
}

function StatusCell({ active, t }) {
  const color = active ? "var(--status-on)" : "var(--status-fail)";
  return (
    <span data-status={active ? "on" : "off"} style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "var(--color-ink)" }}>
      <span
        data-testid="status-dot"
        style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: color, flex: "none" }}
      />
      {active ? t("On") : t("Off")}
    </span>
  );
}

export default function HostedConnectorsTable({
  connectors,
  project,
  myGrants,
  loading,
  error,
  busy,
  errors,
  onRefresh,
  onRequestAccess,
  onRequestDegram
}) {
  const { t } = useT();
  const [notes, setNotes] = React.useState({});
  const [installs, setInstalls] = React.useState({});
  const [waiting, setWaiting] = React.useState(null);

  // DeGram answers every check and every install request with #degram-installed= (App -> dg-connector-install).
  React.useEffect(() => {
    const onInstalled = (event) => {
      setInstalls((prev) => ({ ...prev, ...event.detail }));
      setWaiting(null);
    };
    window.addEventListener("dg-connector-install", onInstalled);
    requestConnectorStatus();
    return () => window.removeEventListener("dg-connector-install", onInstalled);
  }, []);

  const refresh = () => {
    onRefresh();
    requestConnectorStatus();
  };

  const install = (id) => {
    if (waiting) return;
    setWaiting(id);
    requestConnectorInstall(id);
  };

  const accessOf = (connector) => {
    if (connector.id === DEGRAM_CONNECTOR_ID) {
      const grants = myGrants?.grants || [];
      const requests = myGrants?.requests || [];
      if (grants.some((g) => g.project === project && g.active)) return "available";
      if (requests.some((r) => r.project === project)) return "pending";
      return "requestable";
    }
    return connector.access || null;
  };

  const renderAccess = (connector) => {
    const state = accessOf(connector);
    const isDegram = connector.id === DEGRAM_CONNECTOR_ID;
    const working = !!busy[connector.id];
    if (state === "available") return <span data-access="available">{t("Available")}</span>;
    if (state === "pending") return <span data-access="pending" style={muted}>{t("Request sent")}</span>;
    if (state === "requestable") {
      const submit = (event) => {
        event.preventDefault();
        if (working) return;
        const note = (notes[connector.id] || "").trim();
        if (isDegram) onRequestDegram(note);
        else onRequestAccess(connector.id, note);
      };
      return (
        <form onSubmit={submit} data-access="requestable" style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            aria-label={`${t("Note (optional)")}: ${connector.name}`}
            placeholder={t("Note (optional)")}
            maxLength={200}
            value={notes[connector.id] || ""}
            onChange={(event) => setNotes((prev) => ({ ...prev, [connector.id]: event.target.value }))}
            style={noteField}
          />
          <Button size="sm" type="submit" disabled={working}>{t("Request access")}</Button>
        </form>
      );
    }
    return <span style={muted}>—</span>;
  };

  return (
    <section data-testid="hosted-connectors" style={{ padding: "16px 18px", display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <strong style={{ font: "500 15px/1.3 var(--font-sans)" }}>{t("Connectors")}</strong>
        <Button size="sm" variant="secondary" onClick={refresh} disabled={loading} style={{ marginLeft: "auto" }}>
          {t("Refresh")}
        </Button>
      </div>
      {error && <p role="alert" style={errorStyle}>{error}</p>}
      {!project && <p style={muted}>{t("Select a project.")}</p>}
      {project && loading && connectors.length === 0 && <p style={muted}>{t("Loading...")}</p>}
      {project && !loading && !error && connectors.length === 0 && <p style={muted}>{t("No connectors.")}</p>}
      {connectors.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", border: "none", borderSpacing: 0 }}>
          <thead>
            <tr>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "left", fontWeight: 500 }}>{t("Connector")}</th>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "left", fontWeight: 500 }}>{t("Access")}</th>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "left", fontWeight: 500 }}>{t("Installed")}</th>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "right", fontWeight: 500 }}>{t("Status")}</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map((connector) => (
              <React.Fragment key={connector.id}>
                <tr data-connector={connector.id}>
                  <th scope="row" style={{ ...cell, textAlign: "left", fontWeight: 500, color: "var(--color-ink)" }}>{connector.name}</th>
                  <td style={cell}>{renderAccess(connector)}</td>
                  <td style={cell}>
                    <InstalledCell connector={connector} state={installs[connector.id]} waiting={waiting === connector.id} onInstall={install} t={t} />
                  </td>
                  <td style={{ ...cell, textAlign: "right" }}>
                    <StatusCell active={connector.status === "active"} t={t} />
                  </td>
                </tr>
                {errors?.[connector.id] && (
                  <tr><td colSpan={4} style={cell}><p role="alert" style={errorStyle}>{errors[connector.id]}</p></td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
      <p style={{ ...muted, margin: 0 }}>{t("Sign in from the add-in with your DG account.")}</p>
    </section>
  );
}

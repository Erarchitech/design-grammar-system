import React from "react";
import { Button } from "../components/index.js";
import { DEGRAM_CONNECTOR_ID } from "../lib/connectorsApi.js";
import { hostLang, isDegramHost } from "../lib/hostMode.js";

// The DeGram-hosted Connectors page (Phase 1301-40, D-45, D-46): every connector
// of GET /connectors is one row. Name | access | status. Row and column
// separators are invisible. The access cell reads «Доступен» (with a token
// action), «Запросить доступ» (an owner/admin approves it in the DG Web UI) or
// «Запрос отправлен». The status cell reads «Вкл» with a green dot when the
// connector is active, «Выкл» with a red dot otherwise. DeGram access is one
// row of the same table and keeps its own request flow (D-40): it carries no
// token, so it has no token action.

const WORDS = {
  ru: {
    title: "Коннекторы", name: "Коннектор", access: "Доступ", status: "Статус",
    available: "Доступен", request: "Запросить доступ", pending: "Запрос отправлен",
    create: "Создать токен", creating: "Создание...", on: "Вкл", off: "Выкл", note: "Примечание (необязательно)",
    refresh: "Обновить", loading: "Загрузка...", noProject: "Выберите проект.", none: "Нет коннекторов."
  },
  en: {
    title: "Connectors", name: "Connector", access: "Access", status: "Status",
    available: "Available", request: "Request access", pending: "Request sent",
    create: "Create token", creating: "Creating...", on: "On", off: "Off", note: "Note (optional)",
    refresh: "Refresh", loading: "Loading...", noProject: "Select a project.", none: "No connectors."
  }
};

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

function StatusCell({ active, words }) {
  const color = active ? "var(--status-on)" : "var(--status-fail)";
  return (
    <span data-status={active ? "on" : "off"} style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "var(--color-ink)" }}>
      <span
        data-testid="status-dot"
        style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: color, flex: "none" }}
      />
      {active ? words.on : words.off}
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
  tokenReveal,
  renderReveal,
  onRefresh,
  onRequestAccess,
  onRequestDegram,
  onCreateToken
}) {
  const words = WORDS[isDegramHost() ? hostLang() : "en"];
  const [notes, setNotes] = React.useState({});

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
    if (state === "available") {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span data-access="available">{words.available}</span>
          {!isDegram && (
            <Button size="sm" variant="outline" disabled={working} onClick={() => onCreateToken(connector.id)}>
              {working ? words.creating : words.create}
            </Button>
          )}
        </span>
      );
    }
    if (state === "pending") return <span data-access="pending" style={muted}>{words.pending}</span>;
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
            aria-label={`${words.note}: ${connector.name}`}
            placeholder={words.note}
            maxLength={200}
            value={notes[connector.id] || ""}
            onChange={(event) => setNotes((prev) => ({ ...prev, [connector.id]: event.target.value }))}
            style={noteField}
          />
          <Button size="sm" type="submit" disabled={working}>{words.request}</Button>
        </form>
      );
    }
    return <span style={muted}>—</span>;
  };

  return (
    <section data-testid="hosted-connectors" style={{ padding: "16px 18px", display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <strong style={{ font: "500 15px/1.3 var(--font-sans)" }}>{words.title}</strong>
        <Button size="sm" variant="secondary" onClick={onRefresh} disabled={loading} style={{ marginLeft: "auto" }}>
          {words.refresh}
        </Button>
      </div>
      {error && <p role="alert" style={errorStyle}>{error}</p>}
      {!project && <p style={muted}>{words.noProject}</p>}
      {project && loading && connectors.length === 0 && <p style={muted}>{words.loading}</p>}
      {project && !loading && !error && connectors.length === 0 && <p style={muted}>{words.none}</p>}
      {connectors.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", border: "none", borderSpacing: 0 }}>
          <thead>
            <tr>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "left", fontWeight: 500 }}>{words.name}</th>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "left", fontWeight: 500 }}>{words.access}</th>
              <th scope="col" style={{ ...cell, ...muted, textAlign: "right", fontWeight: 500 }}>{words.status}</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map((connector) => (
              <React.Fragment key={connector.id}>
                <tr data-connector={connector.id}>
                  <th scope="row" style={{ ...cell, textAlign: "left", fontWeight: 500, color: "var(--color-ink)" }}>{connector.name}</th>
                  <td style={cell}>{renderAccess(connector)}</td>
                  <td style={{ ...cell, textAlign: "right" }}>
                    <StatusCell active={connector.status === "active"} words={words} />
                  </td>
                </tr>
                {(tokenReveal?.[connector.id] || errors?.[connector.id]) && (
                  <tr>
                    <td colSpan={3} style={cell}>
                      {tokenReveal?.[connector.id] && renderReveal(connector)}
                      {errors?.[connector.id] && <p role="alert" style={errorStyle}>{errors[connector.id]}</p>}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

import React from "react";
import { Button } from "../components/index.js";
import { listConnectors, createCredential, revokeCredential } from "../lib/connectorsApi.js";

// ── Helpers ──

function formatDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  } catch {
    return iso;
  }
}

function statusLabel(status) {
  switch (status) {
    case "active":
      return "Active";
    case "stale":
      return "Stale";
    default:
      return "Never connected";
  }
}

function lastConnectionText(lastConnection) {
  if (!lastConnection) return "never connected";
  return formatDate(lastConnection);
}

// ── StatusDot ──
// Monochromatic: active uses --status-pass (ink), stale/never uses --status-base
// (muted gray). never_connected gets lower opacity. Signal Red is never spent
// on status — it is selection/fail-only.

function StatusDot({ status }) {
  const color =
    status === "active" ? "var(--status-pass)" : "var(--status-base)";
  const opacity = status === "never_connected" ? 0.35 : 1;
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
        opacity,
        flex: "none"
      }}
    />
  );
}

// ── UISection ──
// Lightweight eyebrow — no extra component abstraction needed.

const SECTION_EYEBROW = {
  font: "500 11px/1 var(--font-sans)",
  letterSpacing: "1.5px",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  margin: "32px 0 12px"
};

// ── TokenRevealPanel ──
// Shown exactly once after credential creation. Copy button + "shown once"
// annotation per the design brief (CONN-02).

function TokenRevealPanel({ credentialId, token, label, connectorName, onDismiss, onCopied, copyOk }) {
  const doCopy = () => {
    navigator.clipboard.writeText(token).then(
      () => onCopied(),
      () => {
        /* clipboard unavailable — token is selectable in the UI */
      }
    );
  };

  return (
    <div
      style={{
        background: "var(--color-canvas)",
        borderRadius: "var(--radius-nested)",
        border: "1px solid var(--color-hairline)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        marginTop: 8
      }}
    >
      <div style={{ font: "500 12px/1.3 var(--font-sans)", color: "var(--text-primary)" }}>
        {label ? `"${label}" created` : "Credential created"}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "var(--color-paper)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-small)",
          padding: "6px 8px"
        }}
      >
        <code
          style={{
            flex: 1,
            font: "400 13px/1.5 var(--font-mono)",
            color: "var(--color-ink)",
            wordBreak: "break-all",
            userSelect: "all"
          }}
        >
          {token}
        </code>
        <Button size="sm" variant="outline" onClick={doCopy} style={{ flex: "none" }}>
          {copyOk ? "Copied" : "Copy"}
        </Button>
      </div>

      <div
        style={{
          font: "400 11px/1.4 var(--font-sans)",
          color: "var(--text-muted)",
          display: "flex",
          alignItems: "flex-start",
          gap: 4
        }}
      >
        <span style={{ flex: "none" }}>&#9888;&#65039;</span>
        <span>
          This token is shown once. Paste it into the{" "}
          <strong style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
            {connectorName}
          </strong>{" "}
          connector component in your target software. If you lose it, create a
          new credential.
        </span>
      </div>

      <Button size="sm" variant="secondary" onClick={onDismiss} style={{ alignSelf: "flex-end" }}>
        Dismiss
      </Button>
    </div>
  );
}

// ── CredentialRow ──
// Single credential entry: label, created date, revoked badge, revoke button.

function CredentialRow({ cred, connectorId, confirmRevoke, busyBusy, onRevoke, onToggleConfirm }) {
  const label = cred.label || `Credential ${cred.credential_id.slice(0, 8)}`;
  const revoked = cred.revoked;
  const confirming = confirmRevoke[cred.credential_id];
  const busy = busyBusy[cred.credential_id];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "7px 10px",
        borderBottom: "1px solid var(--color-hairline)"
      }}
    >
      <span
        style={{
          flex: 1,
          font: "400 13px/1.3 var(--font-mono)",
          color: revoked ? "var(--text-muted)" : "var(--color-ink)"
        }}
      >
        {label}
      </span>
      <span style={{ font: "400 11px/1 var(--font-mono)", color: "var(--text-muted)", flex: "none" }}>
        {formatDate(cred.created_at)}
      </span>
      {revoked ? (
        <span
          style={{
            font: "500 11px/1 var(--font-sans)",
            color: "var(--text-muted)",
            padding: "2px 6px",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-hairline)",
            flex: "none"
          }}
        >
          Revoked
        </span>
      ) : confirming ? (
        <div style={{ display: "flex", gap: 4, flex: "none" }}>
          <Button
            size="sm"
            variant="destructive"
            disabled={busy}
            onClick={() => onRevoke(connectorId, cred.credential_id)}
          >
            {busy ? "Revoking..." : "Confirm revoke"}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => onToggleConfirm(cred.credential_id)}>
            Cancel
          </Button>
        </div>
      ) : (
        <Button
          size="sm"
          variant="destructive"
          onClick={() => onToggleConfirm(cred.credential_id)}
        >
          Revoke
        </Button>
      )}
    </div>
  );
}

// ── CredentialSection ──
// Credential list inside a connector card: existing credentials, create form,
// token reveal panel.

function CredentialSection({
  connector,
  creating,
  labelInputs,
  projectInputs,
  tokenReveal,
  confirmRevoke,
  busyBusy,
  busyErrs,
  copyOk,
  setCopyOk,
  onStartCreate,
  onCancelCreate,
  onSetLabelInput,
  onSetProjectInput,
  onCreate,
  onRevoke,
  onToggleConfirm,
  onDismissToken,
}) {
  const creds = connector.credentials || [];
  const reveal = tokenReveal[connector.id];
  const labelValue = labelInputs[connector.id] || "";
  const projectValue = projectInputs[connector.id] || "";

  const doCreate = (e) => {
    e.preventDefault();
    onCreate(connector.id);
  };

  return (
    <div style={{ borderTop: "1px solid var(--color-hairline)" }}>
      {/* existing credentials */}
      {creds.map((cred) => (
        <CredentialRow
          key={cred.credential_id}
          cred={cred}
          connectorId={connector.id}
          confirmRevoke={confirmRevoke}
          busyBusy={busyBusy}
          onRevoke={onRevoke}
          onToggleConfirm={onToggleConfirm}
        />
      ))}

      {/* create form or token reveal */}
      <div style={{ padding: "8px 10px" }}>
        {reveal ? (
          <TokenRevealPanel
            credentialId={reveal.credential_id}
            token={reveal.token}
            label={reveal.label}
            connectorName={connector.name}
            onDismiss={() => onDismissToken(connector.id)}
            onCopied={() => {
              setCopyOk((prev) => ({ ...prev, [connector.id]: true }));
              setTimeout(
                () => setCopyOk((prev) => ({ ...prev, [connector.id]: false })),
                2000
              );
            }}
            copyOk={copyOk[connector.id]}
          />
        ) : creating[connector.id] ? (
          <form onSubmit={doCreate} style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              placeholder="Label (optional)"
              value={labelValue}
              onChange={(e) => onSetLabelInput(connector.id, e.target.value)}
              style={{
                flex: 1,
                height: 28,
                borderRadius: "var(--radius-inputs)",
                border: "1px solid var(--color-hairline)",
                padding: "0 10px",
                font: "400 13px/1 var(--font-sans)",
                color: "var(--color-ink)",
                background: "var(--surface-input)",
                outline: "none"
              }}
            />
            {/* Phase 825: the token is project-scoped — the CONNECTOR component
                reads the project from the token, so no Project input on-canvas. */}
            <input
              placeholder="Project"
              value={projectValue}
              onChange={(e) => onSetProjectInput(connector.id, e.target.value)}
              style={{
                flex: 1,
                height: 28,
                borderRadius: "var(--radius-inputs)",
                border: "1px solid var(--color-hairline)",
                padding: "0 10px",
                font: "400 13px/1 var(--font-sans)",
                color: "var(--color-ink)",
                background: "var(--surface-input)",
                outline: "none"
              }}
            />
            <Button size="sm" type="submit">
              Create
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onCancelCreate(connector.id)}>
              Cancel
            </Button>
          </form>
        ) : (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onStartCreate(connector.id)}
            style={{ font: "400 12px/1 var(--font-sans)" }}
          >
            + Create credential
          </Button>
        )}

        {busyErrs[connector.id] && (
          <div
            style={{
              font: "400 11px/1.3 var(--font-sans)",
              color: "var(--status-fail)",
              marginTop: 6
            }}
          >
            {busyErrs[connector.id]}
          </div>
        )}
      </div>
    </div>
  );
}

// ── ConnectorCard ──

function ConnectorCard({
  connector,
  expanded,
  creating,
  labelInputs,
  projectInputs,
  tokenReveal,
  confirmRevoke,
  busyBusy,
  busyErrs,
  copyOk,
  setCopyOk,
  onToggleExpanded,
  onStartCreate,
  onCancelCreate,
  onSetLabelInput,
  onSetProjectInput,
  onCreate,
  onRevoke,
  onToggleConfirm,
  onDismissToken,
}) {
  const creds = connector.credentials || [];
  const activeCreds = creds.filter((c) => !c.revoked);
  const expiredCreds = creds.filter((c) => c.revoked);
  const credCount = creds.length;

  return (
    <div
      className="dg-frost"
      style={{
        borderRadius: "var(--radius-cards)",
        boxShadow: "var(--shadow-panel)",
        marginBottom: 10,
        overflow: "hidden"
      }}
    >
      {/* Status row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 18px",
          cursor: "pointer",
          userSelect: "none"
        }}
        onClick={() => onToggleExpanded(connector.id)}
      >
        <StatusDot status={connector.status} />
        <span
          style={{
            font: "500 15px/1 var(--font-sans)",
            color: "var(--color-ink)",
            flex: 1
          }}
        >
          {connector.name}
        </span>
        <span
          style={{
            font: "400 12px/1 var(--font-sans)",
            color: "var(--text-muted)",
            flex: "none"
          }}
        >
          {statusLabel(connector.status)}
        </span>
        <span
          style={{
            font: "400 11px/1 var(--font-mono)",
            color: "var(--text-muted)",
            flex: "none"
          }}
        >
          {lastConnectionText(connector.last_connection)}
        </span>
        <svg
          viewBox="0 0 24 24"
          width="13"
          height="13"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: expanded[connector.id] ? "rotate(0deg)" : "rotate(-90deg)",
            transition: "transform var(--duration-fast) var(--ease-out)",
            color: "var(--text-muted)",
            flex: "none"
          }}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
        {credCount > 0 && (
          <span
            style={{
              font: "500 11px/1 var(--font-mono)",
              padding: "2px 7px",
              borderRadius: "var(--radius-full)",
              background: "var(--color-paper)",
              color: "var(--text-muted)",
              border: "1px solid var(--color-hairline)",
              flex: "none"
            }}
          >
            {credCount}
          </span>
        )}
      </div>

      {/* Expandable credentials area */}
      {expanded[connector.id] && (
        <CredentialSection
          connector={connector}
          creating={creating}
          labelInputs={labelInputs}
          projectInputs={projectInputs}
          tokenReveal={tokenReveal}
          confirmRevoke={confirmRevoke}
          busyBusy={busyBusy}
          busyErrs={busyErrs}
          copyOk={copyOk}
          setCopyOk={setCopyOk}
          onStartCreate={onStartCreate}
          onCancelCreate={onCancelCreate}
          onSetLabelInput={onSetLabelInput}
          onSetProjectInput={onSetProjectInput}
          onCreate={onCreate}
          onRevoke={onRevoke}
          onToggleConfirm={onToggleConfirm}
          onDismissToken={onDismissToken}
        />
      )}
    </div>
  );
}

// ── Main Screen ──

export default function ConnectorsScreen({ active, onBack, project }) {
  const [categories, setCategories] = React.useState([]);
  const [connectors, setConnectors] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [loadErr, setLoadErr] = React.useState("");

  // Per-connector UI state
  const [expanded, setExpanded] = React.useState({});
  const [creating, setCreating] = React.useState({});
  const [labelInputs, setLabelInputs] = React.useState({});
  const [projectInputs, setProjectInputs] = React.useState({});
  const [tokenReveal, setTokenReveal] = React.useState({});
  const [confirmRevoke, setConfirmRevoke] = React.useState({});
  const [busyBusy, setBusyBusy] = React.useState({});
  const [busyErrs, setBusyErrs] = React.useState({});
  const [copyOk, setCopyOk] = React.useState({});

  const load = React.useCallback(() => {
    setLoading(true);
    setLoadErr("");
    listConnectors()
      .then((data) => {
        setCategories(data.categories || []);
        setConnectors(data.connectors || []);
      })
      .catch((err) =>
        setLoadErr(err.message || "data-service unreachable")
      )
      .finally(() => setLoading(false));
  }, []);

  React.useEffect(() => {
    if (active) load();
  }, [active, load]);

  // ── UI action handlers ──

  const toggleExpanded = (id) =>
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const startCreate = (id) => {
    setCreating((prev) => ({ ...prev, [id]: true }));
    // Phase 825: default the token's project to the active project so the common
    // case (scope the token to what you're working on) needs no extra typing.
    setProjectInputs((prev) => ({ ...prev, [id]: prev[id] || project || "" }));
    setTokenReveal((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
  };
  const cancelCreate = (id) => {
    setCreating((prev) => ({ ...prev, [id]: false }));
    setLabelInputs((prev) => ({ ...prev, [id]: "" }));
    setProjectInputs((prev) => ({ ...prev, [id]: "" }));
    setBusyErrs((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
  };

  const doCreate = async (id) => {
    setBusyErrs((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
    setBusyBusy((prev) => ({ ...prev, [id]: true }));
    const label = labelInputs[id]?.trim() || undefined;
    const project = projectInputs[id]?.trim() || undefined;
    try {
      const result = await createCredential(id, label, project);
      setTokenReveal((prev) => ({ ...prev, [id]: result }));
      setCreating((prev) => ({ ...prev, [id]: false }));
      setLabelInputs((prev) => ({ ...prev, [id]: "" }));
      setProjectInputs((prev) => ({ ...prev, [id]: "" }));
      // Refresh to show new credential in list
      load();
    } catch (err) {
      setBusyErrs((prev) => ({ ...prev, [id]: err.message || "Create failed" }));
    } finally {
      setBusyBusy((prev) => ({ ...prev, [id]: false }));
    }
  };

  const toggleConfirmRevoke = (credId) =>
    setConfirmRevoke((prev) => ({ ...prev, [credId]: !prev[credId] }));

  const doRevoke = async (connectorId, credentialId) => {
    setBusyBusy((prev) => ({ ...prev, [credentialId]: true }));
    setBusyErrs((prev) => {
      const copy = { ...prev };
      delete copy[connectorId];
      return copy;
    });
    try {
      await revokeCredential(connectorId, credentialId);
      setConfirmRevoke((prev) => ({ ...prev, [credentialId]: false }));
      // Clear token reveal if it was for this credential
      setTokenReveal((prev) => {
        const copy = { ...prev };
        if (copy[connectorId]?.credential_id === credentialId) {
          delete copy[connectorId];
        }
        return copy;
      });
      load();
    } catch (err) {
      setBusyErrs((prev) => ({
        ...prev,
        [connectorId]: err.message || "Revoke failed"
      }));
    } finally {
      setBusyBusy((prev) => ({ ...prev, [credentialId]: false }));
    }
  };

  const dismissToken = (id) =>
    setTokenReveal((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });

  // ── Group connectors by category, preserving category order ──

  const grouped = React.useMemo(() => {
    const map = {};
    categories.forEach((cat) => {
      map[cat] = [];
    });
    connectors.forEach((c) => {
      if (map[c.category]) map[c.category].push(c);
    });
    return map;
  }, [categories, connectors]);

  const hasData = connectors.length > 0;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "var(--surface-canvas)",
        overflow: "auto"
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "28px 40px 60px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          gap: 28
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            &larr; Back
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div
              className="dg-annotation dg-annotation--muted"
              style={{ fontSize: 10 }}
            >
              Region &middot; Connectors
            </div>
            <div
              style={{
                font: "600 34px/1.1 var(--font-sans)",
                letterSpacing: "-1.2px"
              }}
            >
              Connectors.
            </div>
          </div>

          {/* Refresh */}
          <div style={{ marginLeft: "auto" }}>
            <Button size="sm" variant="secondary" onClick={load} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </div>

        {/* Description */}
        <div
          className="dg-frost"
          style={{
            borderRadius: "var(--radius-cards)",
            padding: 26,
            boxShadow: "var(--shadow-panel)"
          }}
        >
          <div
            style={{
              font: "400 14px/1.5 var(--font-sans)",
              color: "var(--text-muted)"
            }}
          >
            Manage credentials and connection status for the platform&apos;s
            external connectors. Create tokens to authenticate connector plugins
            in your BIM, VPL, or visualization software.
          </div>
        </div>

        {/* Error */}
        {loadErr && (
          <div
            style={{
              font: "400 13px/1.4 var(--font-sans)",
              color: "var(--color-signal)"
            }}
          >
            Connectors unavailable.{" "}
            {loadErr}
            <span
              onClick={load}
              style={{
                cursor: "pointer",
                textDecoration: "underline",
                marginLeft: 6
              }}
            >
              Retry
            </span>
          </div>
        )}

        {/* Loading */}
        {loading && !hasData && (
          <div
            className="dg-annotation dg-annotation--muted"
            style={{ fontSize: 11 }}
          >
            Loading connectors...
          </div>
        )}

        {/* Empty */}
        {!loading && !loadErr && !hasData && (
          <div
            className="dg-annotation dg-annotation--muted"
            style={{ fontSize: 11 }}
          >
            No connector data &middot; data-service may be unreachable
          </div>
        )}

        {/* Category sections */}
        {categories.map((category) => {
          const items = grouped[category] || [];
          if (items.length === 0) return null;
          return (
            <div key={category}>
              <div style={SECTION_EYEBROW}>{category}</div>
              {items.map((connector) => (
                <ConnectorCard
                  key={connector.id}
                  connector={connector}
                  expanded={expanded}
                  creating={creating}
                  labelInputs={labelInputs}
                  projectInputs={projectInputs}
                  tokenReveal={tokenReveal}
                  confirmRevoke={confirmRevoke}
                  busyBusy={busyBusy}
                  busyErrs={busyErrs}
                  copyOk={copyOk}
                  setCopyOk={setCopyOk}
                  onToggleExpanded={toggleExpanded}
                  onStartCreate={startCreate}
                  onCancelCreate={cancelCreate}
                  onSetLabelInput={(id, value) => setLabelInputs((prev) => ({ ...prev, [id]: value }))}
                  onSetProjectInput={(id, value) => setProjectInputs((prev) => ({ ...prev, [id]: value }))}
                  onCreate={doCreate}
                  onRevoke={doRevoke}
                  onToggleConfirm={toggleConfirmRevoke}
                  onDismissToken={dismissToken}
                />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

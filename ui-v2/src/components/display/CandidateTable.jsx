import React from "react";
import Badge from "./Badge.jsx";
import Callout from "./Callout.jsx";
import Button from "../forms/Button.jsx";

// Row-per-candidate, column-per-parameter table for AI-generated Grasshopper
// script inputs (Phase 38). Follows the Colibri/MIT design-space-exploration
// convention (38-RESEARCH.md §4.4): a design space reads as a table an
// architect already knows how to scan, not a chat transcript.
//
// Presentational only — no data fetching, no API import, no write of any
// kind. The only thing that ever leaves this component is `onAccept`
// (called from the Accept button click handler) and `onReject` (a local
// dismissal signal). See the per-handler comments below.

function pickValue(param) {
  if (param.numberValue !== null && param.numberValue !== undefined) return param.numberValue;
  if (param.integerValue !== null && param.integerValue !== undefined) return param.integerValue;
  if (param.booleanValue !== null && param.booleanValue !== undefined) return String(param.booleanValue);
  return null;
}

function findExcludedReason(candidate, boundParam) {
  const excluded = candidate.excludedParameters || [];
  return excluded.find(
    (ex) => ex.cgId === boundParam.cgId || ex.parameterName === boundParam.parameterName
  )?.reason;
}

const cellStyle = {
  padding: "8px 10px",
  font: "400 13px/1.4 var(--font-sans)",
  verticalAlign: "top",
  borderBottom: "1px solid var(--color-hairline)"
};
const headStyle = {
  padding: "8px 10px",
  textAlign: "left",
  font: "500 11px/1.3 var(--font-sans)",
  letterSpacing: "var(--tracking-caption)",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  borderBottom: "1px solid var(--color-hairline-strong)"
};

export default function CandidateTable({
  candidates = [],
  boundParameters = [],
  determinabilityClass,
  ruleLimit,
  acceptedStateIds = [],
  onAccept,
  onReject,
  busyCandidateId
}) {
  // acceptedStateIds is keyed by candidateId as returned within THIS
  // generate-inputs response — the panel tracks "already accepted in this
  // UI session" per candidate rather than recomputing the server's content
  // hash (cg_paramstate_store.compute_param_state_id) client-side. The real
  // graph StateId is still what acceptCandidate persists and returns; this
  // component only needs a session-scoped "was this one accepted" flag.
  const isAccepted = (candidate) => acceptedStateIds.includes(candidate.candidateId);

  return (
    <div>
      {determinabilityClass === "geometry-required" && (
        <Callout
          signal
          title="Geometry required"
          detail="This rule depends on geometry the model did not evaluate — candidates are proposals only"
          style={{ marginBottom: 12 }}
        />
      )}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={headStyle}>Strategy</th>
            {boundParameters.map((bp) => (
              <th key={bp.cgId} style={headStyle}>
                {bp.parameterName}
                <div style={{ font: "400 11px/1.3 var(--font-mono)", textTransform: "none", color: "var(--text-muted)", marginTop: 2 }}>
                  [{bp.domainMin} … {bp.domainMax}]
                </div>
              </th>
            ))}
            <th style={headStyle}>Claim</th>
            <th style={headStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => {
            const accepted = isAccepted(candidate);
            const busy = busyCandidateId === candidate.candidateId;
            const claim = candidate.ruleSatisfaction?.claim;
            const basis = candidate.ruleSatisfaction?.basis || "";
            const limitLabel = ruleLimit !== null && ruleLimit !== undefined ? `≤ ${ruleLimit}` : "limit";
            return (
              <tr key={candidate.candidateId}>
                <td style={cellStyle}>
                  <Badge variant="outline">{candidate.strategy}</Badge>
                </td>
                {boundParameters.map((bp) => {
                  const param = (candidate.parameters || []).find((p) => p.parameterId === bp.reinstateParameterId);
                  if (param) {
                    return (
                      <td key={bp.cgId} style={{ ...cellStyle, fontFamily: "var(--font-mono)" }}>
                        {pickValue(param)}
                      </td>
                    );
                  }
                  // A bound parameter absent from this candidate's parameters[]
                  // is either excluded (with reason) or a data anomaly — never
                  // rendered as a silent blank cell, which would read as zero
                  // (D-04): a parameter left out must be visible, not missing.
                  const reason = findExcludedReason(candidate, bp);
                  return (
                    <td key={bp.cgId} style={{ ...cellStyle, color: "var(--text-muted)" }} title={reason || "excluded"}>
                      &mdash;
                    </td>
                  );
                })}
                <td style={cellStyle}>
                  {claim === "satisfied" && <Badge variant="signal" style={{ background: "var(--color-info-soft)", color: "var(--color-info-ink)" }}>{limitLabel}</Badge>}
                  {claim === "violated" && <Badge variant="violation">{limitLabel}</Badge>}
                  {claim === "undeterminable" && (
                    // D-09: this rule cannot be checked from parameters alone.
                    // The badge is deliberately NEUTRAL (Badge's "soft"/default
                    // variant, not signal/success and not violation/failure)
                    // and carries no percentage or confidence number — claiming
                    // satisfaction for a geometry-level rule would be a
                    // fabrication the system never actually computed.
                    <Badge variant="soft" title={basis}>
                      not checkable from parameters
                    </Badge>
                  )}
                </td>
                <td style={cellStyle}>
                  {accepted ? (
                    <Badge variant="outline">Accepted</Badge>
                  ) : (
                    <div style={{ display: "flex", gap: 6 }}>
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => onAccept && onAccept(candidate)}
                      >
                        {busy ? "Accepting…" : "Accept"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          // Rejection is a local dismissal only — it issues no
                          // request of any kind. Rejected candidates leave no
                          // trace anywhere (D-19); the component contains no
                          // fetch and no API import.
                          onReject && onReject(candidate);
                        }}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

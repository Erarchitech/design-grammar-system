import React from "react";
import { Badge, Button, Checkbox, Chip, Panel, Select } from "../components/index.js";
import {
  SESSION_LIMIT,
  MAX_ELEMENTS,
  appliedByClass,
  applySession,
  classLabels,
  classLocalName,
  confidencePercent,
  consequenceRows,
  createSession,
  getSession,
  includedGroupIds,
  labelFromFileName,
  listProfiles,
  listSessions,
  mergeProfiles,
  optionKind,
  parseDescriptorUpload,
  postDecision,
  progressSegments,
  questionText,
  selectorEntries,
  summaryTotals,
  upsertSession
} from "../lib/mappingApi.js";
import { describeError, formatDate } from "../i18n/index.js";
import { useT } from "../i18n/LanguageProvider.jsx";

// Mapping review panel of the Projects screen — Phase 1303 MVP slice (1303-CONTEXT D-15, D-21, D-26, D-29).
// Collapsed by default: nothing is requested until the owner opens it, and only while the Projects screen is active
// (the exact-request browser tests rely on this). Shapes follow 1303-API-CONTRACT v0.1. The server owns every
// decision; this panel only shows its queue, posts one answer per click and re-renders the session it returns.

const ERR_STYLE = { font: "400 12px/1.33 var(--font-sans)", color: "var(--color-signal)" };
const MUTED = { font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)" };
const BODY = { font: "400 14px/1.43 var(--font-sans)" };
const MONO = { font: "400 12px/1.4 var(--font-mono)" };
const CAPTION = {
  margin: 0,
  font: "500 12px/1.33 var(--font-sans)",
  letterSpacing: "var(--tracking-caption)",
  textTransform: "uppercase",
  color: "var(--text-muted)"
};
const TOGGLE = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: 0,
  border: "none",
  background: "transparent",
  cursor: "pointer",
  font: "500 12px/1.33 var(--font-sans)",
  letterSpacing: "var(--tracking-caption)",
  textTransform: "uppercase",
  color: "var(--text-muted)"
};
const CARD = {
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-nested)",
  background: "var(--color-paper)",
  padding: 12,
  display: "flex",
  flexDirection: "column",
  gap: 10
};
const TABLE = { width: "100%", borderCollapse: "collapse", font: "400 12px/1.4 var(--font-sans)" };
const TH = {
  textAlign: "left",
  padding: "4px 8px",
  borderBottom: "1px solid var(--color-hairline)",
  color: "var(--text-muted)",
  fontWeight: 500,
  whiteSpace: "nowrap"
};
const TD = { padding: "4px 8px", borderBottom: "1px solid var(--color-hairline)", verticalAlign: "top" };
const CHIP = { height: 22, padding: "0 8px", font: "400 11px/1 var(--font-mono)" };

// Screen-reader-only text (live region).
const VISUALLY_HIDDEN = {
  position: "absolute",
  width: 1,
  height: 1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap"
};

// The five mapping-state colours (shared palette with the Rhino preview; D-29 discretion). The tokens have no green,
// so the states are local custom properties, with lighter variants for the dark theme.
const MAPPING_CSS = `
.dg-mapping {
  --mapping-confirmed: #2E7D32;
  --mapping-auto: #1565C0;
  --mapping-suggested: #F9A825;
  --mapping-ambiguous: #E65100;
  --mapping-unmapped: #9E9E9E;
}
:root[data-theme="dark"] .dg-mapping {
  --mapping-confirmed: #66BB6A;
  --mapping-auto: #64B5F6;
  --mapping-suggested: #FDD835;
  --mapping-ambiguous: #FF8A50;
  --mapping-unmapped: #8C8C8C;
}
`;

function stateLabel(t, state) {
  switch (state) {
    case "confirmed":
      return t("Confirmed");
    case "auto":
      return t("Auto by profile");
    case "suggested":
      return t("Suggested");
    case "ambiguous":
      return t("Ambiguous");
    case "unmapped":
      return t("Unmapped");
    default:
      return state || "";
  }
}

function questionTypeLabel(t, type) {
  switch (type) {
    case "batch-assign":
      return t("Accept proposed classes");
    case "assign":
      return t("Assign a class");
    case "disambiguate":
      return t("Choose roles");
    case "mapping-or-design":
      return t("Mapping or design error");
    default:
      return type || "";
  }
}

function evidenceKindLabel(t, kind) {
  switch (kind) {
    case "profile":
      return t("Profile");
    case "name":
      return t("Name match");
    case "rule":
      return t("Rule");
    case "ifc":
      return t("IFC");
    case "population":
      return t("Population");
    default:
      return kind || "";
  }
}

function effectLabel(t, effect) {
  switch (effect) {
    case "passes":
      return t("passes");
    case "violated":
      return t("violated");
    case "applies":
      return t("applies");
    default:
      return effect || "";
  }
}

function sourceLabel(t, source) {
  if (source === "learned") return t("Learned");
  if (source === "authored") return t("Authored");
  return source || "—";
}

function uploadErrorText(t, error) {
  switch (error) {
    case "json":
      return t("The file is not valid JSON.");
    case "elements":
      return t("The file has no list of elements.");
    case "empty":
      return t("The file has no elements.");
    case "descriptor":
      return t("Every element needs a unique nativeId.");
    case "platform":
      return t("The platform must be grasshopper or revit.");
    case "too-many":
      return t("The file has more than {max} elements.", { max: MAX_ELEMENTS });
    default:
      return t("Could not read the file.");
  }
}

// Fixed option labels are UI text; class names stay data. Unknown option kinds show the server label.
function optionLabel(t, option, labelOf) {
  const { kind, arg } = optionKind(option?.optionId);
  switch (kind) {
    case "accept-all":
      return t("Accept all proposed classes");
    case "class":
      return labelOf(arg);
    case "design-error":
      return t("{label} — rule violations are design errors", { label: labelOf(arg) });
    case "both":
      return t("Both roles");
    case "split":
      return t("Split by {feature}", { feature: arg });
    case "none":
      return t("None of these");
    default:
      return typeof option?.label === "string" && option.label ? option.label : String(option?.optionId ?? "");
  }
}

function list(value) {
  return Array.isArray(value) ? value : [];
}

function StateDot({ state }) {
  return (
    <span
      aria-hidden="true"
      style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", flex: "none", background: `var(--mapping-${state})` }}
    />
  );
}

// Five-segment bar (the Progress primitive has a single fill) with a legend that carries the accessible counts.
function MappingProgress({ summary }) {
  const { t } = useT();
  const segments = progressSegments(summary);
  const totals = summaryTotals(summary);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h5 style={CAPTION}>{t("Progress")}</h5>
      <div
        aria-hidden="true"
        style={{
          display: "flex",
          height: 12,
          boxSizing: "border-box",
          borderRadius: "var(--radius-full)",
          overflow: "hidden",
          background: "var(--color-surface-alt)",
          border: "1px solid var(--color-hairline)"
        }}
      >
        {segments
          .filter((segment) => segment.percent)
          .map(({ state, percent }) => (
            <div key={state} style={{ width: `${percent}%`, background: `var(--mapping-${state})` }} />
          ))}
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexWrap: "wrap", gap: "6px 16px" }}>
        {segments.map(({ state, count }) => (
          <li key={state} style={{ display: "inline-flex", alignItems: "center", gap: 6, ...MUTED }}>
            <StateDot state={state} />
            <span>{stateLabel(t, state)}</span>
            <span style={{ ...MONO, color: "var(--color-ink)" }}>{count}</span>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", ...MUTED }}>
        <span>{t("Total: {n}", { n: totals.total })}</span>
        <span>{t("Open questions: {n}", { n: totals.openQuestions })}</span>
      </div>
    </div>
  );
}

// One group: state, size, signature chips, representative native ids, candidates with confidence, evidence and conflicts.
function GroupDetails({ group, labelOf }) {
  const { t, tp } = useT();
  const candidates = list(group.candidates);
  const representatives = list(group.representatives).slice(0, 3);
  const signature = selectorEntries(group.signature);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", ...BODY }}>
        <StateDot state={group.status} />
        <span>{stateLabel(t, group.status)}</span>
        <span style={MUTED}>{tp("{n} element", Number(group.size) || 0)}</span>
        <span style={{ ...MONO, color: "var(--text-muted)" }}>{group.groupId}</span>
      </div>
      {signature.length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {signature.map((entry) => (
            <Chip key={entry} style={CHIP}>
              {entry}
            </Chip>
          ))}
        </div>
      )}
      {representatives.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={MUTED}>{t("Representatives")}</span>
          {representatives.map((id) => (
            <code key={id} style={{ ...MONO, overflowWrap: "anywhere" }}>
              {id}
            </code>
          ))}
        </div>
      )}
      {candidates.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={MUTED}>{t("Candidates")}</span>
          {candidates.map((candidate) => {
            const evidence = list(candidate.evidence);
            const conflicts = list(candidate.conflicts);
            return (
              <div key={candidate.classIri} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={BODY}>{candidate.label || labelOf(candidate.classIri)}</span>
                  <span title={t("Confidence")}>
                    <Badge variant={conflicts.length ? "violation" : "outline"}>{confidencePercent(candidate.confidence)}</Badge>
                  </span>
                </div>
                {evidence.length > 0 && (
                  <ul style={{ margin: 0, paddingLeft: 16, ...MUTED }}>
                    {evidence.slice(0, 6).map((item, index) => (
                      <li key={index}>
                        {evidenceKindLabel(t, item.kind)}: {item.detail}
                        {Number(item.count) > 1 ? ` ×${item.count}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {conflicts.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <span style={{ ...MUTED, color: "var(--color-signal-ink)" }}>{t("Conflicts")}</span>
                    {conflicts.map((conflict, index) => (
                      <span key={index} style={{ ...MONO, color: "var(--color-signal-ink)", overflowWrap: "anywhere" }}>
                        {conflict.detail || conflict.ruleId}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Batch-assign row: the Checkbox primitive has no input element, so the wrapper carries role, focus and keys.
function GroupCheck({ checked, disabled, label, onToggle, children }) {
  const labelId = React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div
        role="checkbox"
        tabIndex={0}
        aria-checked={checked}
        aria-disabled={disabled}
        aria-labelledby={labelId}
        onKeyDown={(event) => {
          if (event.key !== " " && event.key !== "Enter") return;
          event.preventDefault();
          if (!disabled) onToggle();
        }}
        style={{ alignSelf: "flex-start", opacity: disabled ? 0.45 : 1, pointerEvents: disabled ? "none" : undefined }}
      >
        <Checkbox
          checked={checked}
          onChange={() => {
            if (!disabled) onToggle();
          }}
          label={
            <span id={labelId} style={BODY}>
              {label}
            </span>
          }
        />
      </div>
      <div style={{ paddingLeft: 24 }}>{children}</div>
    </div>
  );
}

function Consequences({ question, optionText }) {
  const { t } = useT();
  const rows = consequenceRows(question);
  if (rows.length === 0) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={MUTED}>{t("Consequences")}</span>
      <div style={{ overflowX: "auto" }}>
        <table style={TABLE}>
          <thead>
            <tr>
              <th style={TH}>{t("Option")}</th>
              <th style={TH}>{t("Rule")}</th>
              <th style={TH}>{t("Effect")}</th>
              <th style={TH}>{t("Count")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td style={TD}>{optionText(row.optionId)}</td>
                <td style={{ ...TD, ...MONO, overflowWrap: "anywhere" }}>{row.ruleId}</td>
                <td style={{ ...TD, color: row.effect === "violated" ? "var(--color-signal-ink)" : undefined }}>{effectLabel(t, row.effect)}</td>
                <td style={{ ...TD, ...MONO }}>×{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// One queued question in server order: canonical text in the UI language, its groups, consequences and one button
// per option. A batch-assign answer carries the checked groups as groupIds.
function QuestionCard({ question, groupsById, labelOf, excluded, busy, posting, error, onToggleGroup, onAnswer }) {
  const { t, tp, lang } = useT();
  const isBatch = question.type === "batch-assign";
  const groups = list(question.groupIds)
    .map((id) => groupsById.get(id))
    .filter(Boolean);
  const included = includedGroupIds(question, excluded);
  const skip = new Set(list(excluded));
  const options = list(question.options);
  const optionText = (optionId) => optionLabel(t, options.find((option) => option.optionId === optionId) || { optionId }, labelOf);
  const noneSelected = isBatch && included.length === 0;
  return (
    <div style={CARD}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <Badge variant={question.type === "mapping-or-design" ? "warning" : "outline"}>{questionTypeLabel(t, question.type)}</Badge>
        <span style={{ ...MONO, color: "var(--text-muted)" }}>{question.questionId}</span>
      </div>
      <div style={{ ...BODY, overflowWrap: "anywhere" }}>{questionText(question, lang)}</div>
      {isBatch ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={MUTED}>{t("Groups to accept")}</span>
          {groups.map((group) => {
            const top = list(group.candidates)[0];
            const name = top ? top.label || labelOf(top.classIri) : group.groupId;
            return (
              <GroupCheck
                key={group.groupId}
                checked={!skip.has(group.groupId)}
                disabled={busy}
                label={`${name} · ${tp("{n} element", Number(group.size) || 0)}`}
                onToggle={() => onToggleGroup(question.questionId, group.groupId)}
              >
                <GroupDetails group={group} labelOf={labelOf} />
              </GroupCheck>
            );
          })}
        </div>
      ) : (
        groups.map((group) => <GroupDetails key={group.groupId} group={group} labelOf={labelOf} />)
      )}
      <Consequences question={question} optionText={optionText} />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {options.map((option, index) => (
          <Button
            key={option.optionId}
            size="sm"
            variant={index === 0 ? "primary" : "outline"}
            disabled={busy || noneSelected}
            onClick={() => onAnswer(question, option, included)}
          >
            {optionText(option.optionId)}
          </Button>
        ))}
      </div>
      {noneSelected && <div style={MUTED}>{t("Select at least one group.")}</div>}
      {posting && <div style={MUTED}>{t("Sending answer…")}</div>}
      {error && <div style={ERR_STYLE}>{describeError(error, t("Could not save the answer."))}</div>}
    </div>
  );
}

function profileChips(profile) {
  const chips = selectorEntries(profile.selector);
  const hasPlatform = profile.selector && typeof profile.selector === "object" && Object.hasOwn(profile.selector, "platform");
  return profile.platform && !hasPlatform ? [`platform=${profile.platform}`, ...chips] : chips;
}

function number(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function ProfilesTable({ profiles, labelOf }) {
  const { t } = useT();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h5 style={CAPTION}>{t("Profiles")}</h5>
      {profiles.length === 0 ? (
        <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
          {t("No profiles yet.")}
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={TABLE}>
            <thead>
              <tr>
                <th style={TH}>{t("Selector")}</th>
                <th style={TH}>{t("Roles")}</th>
                <th style={TH}>{t("Source")}</th>
                <th style={TH}>{t("Confirmations / rejections")}</th>
                <th style={TH}>{t("Confidence")}</th>
                <th style={TH}>{t("Support")}</th>
                <th style={TH}>{t("Created")}</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((profile) => {
                const roles = list(profile.roles).map((iri) => labelOf(iri));
                const excludedRoles = list(profile.excludedRoles).map((iri) => `¬${labelOf(iri)}`);
                return (
                  <tr key={profile.profileId}>
                    <td style={TD}>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {profileChips(profile).map((chip) => (
                          <Chip key={chip} style={CHIP}>
                            {chip}
                          </Chip>
                        ))}
                      </div>
                    </td>
                    <td style={TD}>{[roles.join(" + "), excludedRoles.join(" ")].filter(Boolean).join(" · ") || "—"}</td>
                    <td style={TD}>{sourceLabel(t, profile.source)}</td>
                    <td style={{ ...TD, ...MONO }}>{`${number(profile.confirmations)} / ${number(profile.rejections)}`}</td>
                    <td style={{ ...TD, ...MONO }}>{confidencePercent(profile.confidence)}</td>
                    <td style={{ ...TD, ...MONO }}>{profile.support ?? "—"}</td>
                    <td style={TD}>{`${profile.createdBy || "—"} · ${formatDate(profile.createdAt)}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ApplyResult({ result, labelOf }) {
  const { t, tp } = useT();
  const rows = appliedByClass(result);
  const skipped = list(result.skipped).length;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={BODY}>
        {tp("{n} element applied", number(result.applied))}
        {skipped ? ` · ${t("Skipped: {n}", { n: skipped })}` : ""}
      </div>
      {rows.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 16, ...MUTED }}>
          {rows.map((row) => (
            <li key={row.classIri}>
              <span style={{ color: "var(--color-ink)" }}>{labelOf(row.classIri)}</span> <span style={MONO}>{row.count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MappingPanel({ project, active }) {
  const { t, tp } = useT();
  const [open, setOpen] = React.useState(false);
  const [status, setStatus] = React.useState("idle"); // idle | loading | ready | failed
  const [loadErr, setLoadErr] = React.useState(null);
  const [sessions, setSessions] = React.useState([]);
  const [profiles, setProfiles] = React.useState([]);
  const [selectedId, setSelectedId] = React.useState(null);
  const [session, setSession] = React.useState(null);
  const [sessionBusy, setSessionBusy] = React.useState(false);
  const [sessionErr, setSessionErr] = React.useState(null);
  const [upload, setUpload] = React.useState(null);
  const [creating, setCreating] = React.useState(false);
  const [createErr, setCreateErr] = React.useState(null);
  const [posting, setPosting] = React.useState(null);
  const [answerErr, setAnswerErr] = React.useState(null);
  const [excluded, setExcluded] = React.useState({});
  const [applying, setApplying] = React.useState(false);
  const [applied, setApplied] = React.useState(null);
  const [applyErr, setApplyErr] = React.useState(null);
  const [notice, setNotice] = React.useState(null);
  // scopeRef drops replies after a collapse, a screen change or an unmount; readRef keeps only the latest session read.
  const scopeRef = React.useRef(0);
  const readRef = React.useRef(0);
  const selectedRef = React.useRef(null);
  const fileRef = React.useRef(null);
  const bodyId = React.useId();
  const busy = posting !== null || creating || applying || sessionBusy;

  React.useEffect(() => {
    selectedRef.current = selectedId;
  }, [selectedId]);

  // Sessions and profiles, then the selected (else newest) session.
  const load = React.useCallback(
    (preferId) => {
      const scope = scopeRef.current;
      const read = ++readRef.current;
      setStatus((prev) => (prev === "ready" ? "ready" : "loading"));
      setLoadErr(null);
      Promise.all([listSessions(project, SESSION_LIMIT), listProfiles(project)])
        .then(async ([listed, profileList]) => {
          if (scope !== scopeRef.current) return;
          const items = list(listed?.sessions);
          setSessions(items);
          setProfiles(list(profileList?.profiles));
          const id = preferId && items.some((s) => s.sessionId === preferId) ? preferId : items[0]?.sessionId || null;
          let full = null;
          let failure = null;
          if (id) {
            try {
              full = await getSession(project, id);
            } catch (err) {
              failure = err;
            }
          }
          if (scope !== scopeRef.current || read !== readRef.current) return;
          setSelectedId(id);
          setSession(full && typeof full === "object" ? full : null);
          setSessionErr(failure);
          setStatus("ready");
        })
        .catch((err) => {
          if (scope !== scopeRef.current) return;
          setLoadErr(err);
          setStatus("failed");
        });
    },
    [project]
  );

  // Opening the panel (or returning to the screen with it open) loads; collapsing or leaving drops late replies.
  React.useEffect(() => {
    setPosting(null);
    setCreating(false);
    setApplying(false);
    setSessionBusy(false);
    if (open && active) load(selectedRef.current);
    return () => {
      scopeRef.current += 1;
    };
  }, [open, active, load]);

  const selectSession = (id) => {
    if (!id || id === selectedId || busy) return;
    const scope = scopeRef.current;
    const read = ++readRef.current;
    setSelectedId(id);
    setSession(null);
    setSessionErr(null);
    setSessionBusy(true);
    setApplied(null);
    setApplyErr(null);
    setAnswerErr(null);
    setExcluded({});
    setNotice(null);
    getSession(project, id)
      .then((full) => {
        if (scope !== scopeRef.current || read !== readRef.current) return;
        setSession(full && typeof full === "object" ? full : null);
        setSessionBusy(false);
      })
      .catch((err) => {
        if (scope !== scopeRef.current || read !== readRef.current) return;
        setSessionErr(err);
        setSessionBusy(false);
      });
  };

  const onFile = async (event) => {
    const input = event.target;
    const file = input.files && input.files[0];
    input.value = ""; // the same file can be chosen again
    if (!file) return;
    setCreateErr(null);
    setNotice(null);
    let text;
    try {
      text = await file.text();
    } catch {
      setUpload({ fileName: file.name, error: "read" });
      return;
    }
    const parsed = parseDescriptorUpload(text);
    if (parsed.error) {
      setUpload({ fileName: file.name, error: parsed.error });
      return;
    }
    const label = parsed.body.label || labelFromFileName(file.name);
    setUpload({ fileName: file.name, count: parsed.count, fileProject: parsed.fileProject, body: label ? { ...parsed.body, label } : parsed.body });
  };

  const create = async () => {
    if (!upload?.body || busy) return;
    const scope = scopeRef.current;
    setCreating(true);
    setCreateErr(null);
    setNotice(null);
    try {
      const created = await createSession(project, upload.body);
      if (scope !== scopeRef.current) return;
      setCreating(false);
      setUpload(null);
      if (created && typeof created === "object" && created.sessionId) {
        readRef.current += 1; // an older session read must not replace the new session
        setSelectedId(created.sessionId);
        setSession(created);
        setSessionErr(null);
        setSessions((items) => upsertSession(items, created));
        setApplied(null);
        setApplyErr(null);
        setAnswerErr(null);
        setExcluded({});
        setNotice({ kind: "created" });
      }
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setCreating(false);
      setCreateErr(err);
    }
  };

  const toggleGroup = (questionId, groupId) => {
    setExcluded((prev) => {
      const current = prev[questionId] || [];
      return { ...prev, [questionId]: current.includes(groupId) ? current.filter((id) => id !== groupId) : [...current, groupId] };
    });
  };

  const answer = async (question, option, included) => {
    if (!session || busy) return;
    const isBatch = question.type === "batch-assign";
    if (isBatch && included.length === 0) return;
    const scope = scopeRef.current;
    const sessionId = session.sessionId;
    setPosting(question.questionId);
    setAnswerErr(null);
    setNotice(null);
    setApplied(null);
    setApplyErr(null);
    try {
      const res = await postDecision(project, sessionId, {
        questionId: question.questionId,
        optionId: option.optionId,
        ...(isBatch ? { groupIds: included } : {})
      });
      if (scope !== scopeRef.current) return;
      setPosting(null);
      const next = res?.session;
      if (next && typeof next === "object" && (!next.sessionId || next.sessionId === sessionId)) {
        const merged = { ...next, sessionId };
        setSession(merged);
        setSessions((items) => upsertSession(items, merged));
      }
      if (Array.isArray(res?.profiles)) setProfiles((items) => mergeProfiles(items, res.profiles));
      setExcluded((prev) => {
        const rest = { ...prev };
        delete rest[question.questionId];
        return rest;
      });
      setNotice({ kind: "decided", n: list(res?.decisions).length });
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setPosting(null);
      setAnswerErr({ questionId: question.questionId, err });
    }
  };

  const apply = async () => {
    if (!session || busy) return;
    const scope = scopeRef.current;
    setApplying(true);
    setApplyErr(null);
    setApplied(null);
    setNotice(null);
    try {
      const res = await applySession(project, session.sessionId);
      if (scope !== scopeRef.current) return;
      setApplying(false);
      setApplied(res && typeof res === "object" ? res : { applied: 0 });
      setNotice({ kind: "applied", n: number(res?.applied) });
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setApplying(false);
      setApplyErr(err);
    }
  };

  let noticeText = "";
  if (notice?.kind === "decided") noticeText = tp("{n} decision recorded", notice.n);
  else if (notice?.kind === "applied") noticeText = tp("{n} element applied", notice.n);
  else if (notice?.kind === "created") noticeText = t("Mapping session created");

  const labels = classLabels(session);
  const labelOf = (iri) => labels.get(iri) || classLocalName(iri);
  const groupsById = new Map(list(session?.groups).map((group) => [group.groupId, group]));
  const questions = list(session?.questions);
  const totals = summaryTotals(session?.summary);
  const sessionOptions = sessions.map((item) => {
    const done = summaryTotals(item.summary);
    return {
      value: item.sessionId,
      label: `${item.label || item.sessionId} · ${item.platform || "—"} · ${formatDate(item.createdAt)} · ${t("{done}/{total} mapped", { done: done.mapped, total: done.total })}`
    };
  });
  if (!selectedId) sessionOptions.unshift({ value: "", label: t("Select a session") });

  let content;
  if (status === "failed") {
    content = (
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={ERR_STYLE}>{t("Mapping unavailable · {reason}", { reason: describeError(loadErr, t("Service unavailable. Try again.")) })}</span>
        <Button variant="outline" size="sm" onClick={() => load(selectedRef.current)}>
          {t("Retry")}
        </Button>
      </div>
    );
  } else if (status !== "ready") {
    content = <div style={{ ...BODY, color: "var(--text-muted)" }}>{t("Loading mapping…")}</div>;
  } else {
    content = (
      <>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {sessions.length > 0 && (
              <div style={{ flex: "1 1 320px", minWidth: 0 }}>
                <Select
                  aria-label={t("Mapping session")}
                  options={sessionOptions}
                  value={selectedId || ""}
                  disabled={busy}
                  onChange={(event) => selectSession(event.target.value)}
                />
              </div>
            )}
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => fileRef.current?.click()}>
              {t("Import descriptors (JSON)")}
            </Button>
            <input ref={fileRef} type="file" accept="application/json,.json" tabIndex={-1} aria-hidden="true" onChange={onFile} style={{ display: "none" }} />
          </div>
          {upload?.error && <div style={ERR_STYLE}>{uploadErrorText(t, upload.error)}</div>}
          {upload?.body && (
            <div style={CARD}>
              <div style={BODY}>{tp("{n} element ready to import", upload.count)}</div>
              <div style={{ ...MONO, color: "var(--text-muted)", overflowWrap: "anywhere" }}>
                {`${upload.fileName} · ${upload.body.platform}${upload.body.label ? ` · ${upload.body.label}` : ""}`}
              </div>
              {upload.fileProject && upload.fileProject !== project && (
                <div style={{ ...MUTED, color: "var(--color-warning-ink)" }}>
                  {t("This file was prepared for project {fileProject}; the session is created in {project}.", { fileProject: upload.fileProject, project })}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button size="sm" disabled={busy} onClick={create}>
                  {creating ? t("Creating session…") : t("Create session")}
                </Button>
                <Button variant="outline" size="sm" disabled={creating} onClick={() => setUpload(null)}>
                  {t("Cancel")}
                </Button>
              </div>
            </div>
          )}
          {createErr && <div style={ERR_STYLE}>{describeError(createErr, t("Could not create the session."))}</div>}
          {sessions.length === 0 && !upload?.body && (
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
              {t("No mapping sessions yet · import a descriptor file to start")}
            </div>
          )}
          {sessionBusy && <div style={MUTED}>{t("Loading session…")}</div>}
          {sessionErr && <div style={ERR_STYLE}>{describeError(sessionErr, t("Could not load the session."))}</div>}
          {session && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", ...MUTED }}>
              <span>{t("Created {date} by {user}", { date: formatDate(session.createdAt), user: session.createdBy || "—" })}</span>
              {session.appliedAt && <span>{t("Applied {date}", { date: formatDate(session.appliedAt) })}</span>}
              {session.engineVersion && <span style={MONO}>{session.engineVersion}</span>}
            </div>
          )}
        </div>

        {session && <MappingProgress summary={session.summary} />}

        {session && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <h5 style={CAPTION}>{t("Questions")}</h5>
            {notice?.kind === "decided" && <div style={MUTED}>{noticeText}</div>}
            {questions.length === 0 ? (
              <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                {t("No open questions.")}
              </div>
            ) : (
              questions.map((question) => (
                <QuestionCard
                  key={question.questionId}
                  question={question}
                  groupsById={groupsById}
                  labelOf={labelOf}
                  excluded={excluded[question.questionId]}
                  busy={busy}
                  posting={posting === question.questionId}
                  error={answerErr?.questionId === question.questionId ? answerErr.err : null}
                  onToggleGroup={toggleGroup}
                  onAnswer={answer}
                />
              ))
            )}
          </div>
        )}

        <ProfilesTable profiles={profiles} labelOf={labelOf} />

        {session && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <Button size="sm" disabled={busy} onClick={apply}>
                {applying ? t("Applying…") : t("Apply mapping")}
              </Button>
              {totals.openQuestions > 0 && <span style={MUTED}>{t("Groups without an answer are skipped.")}</span>}
            </div>
            {applyErr && <div style={ERR_STYLE}>{describeError(applyErr, t("Could not apply the mapping."))}</div>}
            {applied && <ApplyResult result={applied} labelOf={labelOf} />}
          </div>
        )}
      </>
    );
  }

  return (
    <Panel style={{ userSelect: "text" }}>
      <div className="dg-mapping" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <style>{MAPPING_CSS}</style>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h4 style={{ margin: 0, flex: 1, minWidth: 0 }}>
            <button type="button" aria-expanded={open} aria-controls={open ? bodyId : undefined} onClick={() => setOpen((value) => !value)} style={TOGGLE}>
              <svg
                viewBox="0 0 24 24"
                width="13"
                height="13"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                style={{ transform: open ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform var(--duration-fast) var(--ease-out)", flex: "none" }}
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
              <span>{t("Mapping")}</span>
            </button>
          </h4>
          {open && status === "ready" && (
            <Button variant="outline" size="sm" disabled={busy} onClick={() => load(selectedId)}>
              {t("Refresh")}
            </Button>
          )}
        </div>
        {!open && <div style={MUTED}>{t("Review how elements from Grasshopper and Revit map to project classes.")}</div>}
        {open && (
          <div id={bodyId} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {content}
          </div>
        )}
        <span aria-live="polite" style={VISUALLY_HIDDEN}>
          {noticeText}
        </span>
      </div>
    </Panel>
  );
}

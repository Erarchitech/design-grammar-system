import React from "react";
import { Badge, Button, Checkbox, Chip, Panel, Select } from "../components/index.js";
import {
  SESSION_LIMIT,
  MAX_ELEMENTS,
  answerUndoable,
  appliedByClass,
  applySession,
  awaitingApply,
  cardOpen,
  classLabels,
  classLocalName,
  confidencePercent,
  consequenceRows,
  createSession,
  getSession,
  includedGroupIds,
  itemView,
  labelFromFileName,
  listProfiles,
  listSessions,
  pendingAnswerIds,
  placePropertyCheck,
  optionKind,
  parseDescriptorUpload,
  postDecision,
  progressSegments,
  proposalItems,
  proposalTitle,
  questionText,
  selectorEntries,
  sessionAnswers,
  summaryTotals,
  toggleCard,
  undoAnswer,
  upsertSession
} from "../lib/mappingApi.js";
import { describeError, formatDate } from "../i18n/index.js";
import { useT } from "../i18n/LanguageProvider.jsx";

// Mapping review panel of the Projects screen — Phase 1303 MVP slice (1303-CONTEXT D-15, D-21, D-26, D-29).
// Collapsed by default: nothing is requested until the owner opens it, and only while the Projects screen is active
// (the exact-request browser tests rely on this). Shapes follow 1303-API-CONTRACT v0.1. The server owns every
// decision; this panel only shows its queue, posts one answer per click and re-renders the session it returns.

const FOLLOW_MS = 5000;
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
// Proposal and answer cards (contract §7, owner 2026-10-18): a one-line header that toggles the card on its own.
const CARD_HEAD = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  width: "100%",
  minWidth: 0,
  padding: 0,
  border: "none",
  background: "transparent",
  cursor: "pointer",
  textAlign: "left",
  font: "500 14px/1.43 var(--font-sans)",
  color: "var(--color-ink)"
};
const ONE_LINE = { minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const ITEM_LIST = { listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6 };
const DETAILS = {
  display: "flex",
  flexDirection: "column",
  gap: 10,
  paddingTop: 10,
  borderTop: "1px solid var(--color-hairline)"
};

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
    case "batch-parameters":
      return t("Sliders as DG parameters");
    case "batch-measures":
      return t("Accept proposed properties");
    case "map-measure":
      return t("Map an output to a property");
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
    case "llm":
      return "LLM";
    case "measure":
      return t("Calculation output");
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

// Type-specific wording of the fixed option ids, shared by the open proposals and the given answers.
function optionTextFor(t, type, options, optionId, labelOf) {
  if (type === "map-measure" && optionId === "none") return t("Not a DG property");
  if (type === "batch-parameters" && optionId === "accept-all") return t("Accept all as DG parameters");
  if (type === "batch-measures" && optionId === "accept-all") return t("Accept all proposed properties");
  return optionLabel(t, list(options).find((option) => option.optionId === optionId) || { optionId }, labelOf);
}

function itemKindLabel(t, kind) {
  switch (kind) {
    case "stream":
      return t("Element stream");
    case "measure":
      return t("Calculation output");
    case "parameter":
      return t("Slider");
    default:
      return "";
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

function Chevron({ open }) {
  return (
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
      style={{ transform: open ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform var(--duration-fast) var(--ease-out)", flex: "none", color: "var(--text-muted)" }}
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

// Coloured, non-interactive state chip (DeGram has the clickable variant that focuses the canvas component).
function StateChip({ state }) {
  const { t } = useT();
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        height: 20,
        padding: "0 8px",
        boxSizing: "border-box",
        borderRadius: "var(--radius-full)",
        border: `1px solid var(--mapping-${state})`,
        background: `color-mix(in srgb, var(--mapping-${state}) 14%, transparent)`,
        font: "500 11px/1 var(--font-sans)",
        color: "var(--color-ink)",
        whiteSpace: "nowrap",
        flex: "none"
      }}
    >
      <StateDot state={state} />
      {stateLabel(t, state)}
    </span>
  );
}

// One proposed canvas component on its own row: state, name, kind, proposal, count and alternatives (contract §7.1).
export function ItemRow({ item, index = 0 }) {
  const { t, tp } = useT();
  const view = itemView(item, index);
  const kind = itemKindLabel(t, view.kind);
  let amount = "";
  if (view.count !== null) amount = view.kind === "measure" ? tp("{n} val.", view.count) : tp("{n} el.", view.count);
  return (
    <div data-mapping-item={view.key} style={{ display: "flex", alignItems: "center", gap: "4px 10px", flexWrap: "wrap", minWidth: 0, ...BODY }}>
      <StateChip state={view.state} />
      <span style={{ fontWeight: 500, overflowWrap: "anywhere" }}>{view.name}</span>
      {kind && <span style={MUTED}>{kind}</span>}
      <span style={{ overflowWrap: "anywhere" }}>
        {"→ "}
        {view.proposal ? <span style={{ fontWeight: 500 }}>{view.proposal}</span> : <span style={MUTED}>{t("no proposal")}</span>}
      </span>
      {amount && <span style={{ ...MONO, color: "var(--text-muted)" }}>{amount}</span>}
      {view.alternatives.length > 0 && <span style={MUTED}>{t("or {labels}", { labels: view.alternatives.join(", ") })}</span>}
    </div>
  );
}

// Batch-assign item row with a checkbox; the Checkbox primitive has no input element, so the row carries role and keys.
function ItemCheck({ checked, disabled, onToggle, children }) {
  const labelId = React.useId();
  const toggle = () => {
    if (!disabled) onToggle();
  };
  return (
    <div
      role="checkbox"
      tabIndex={0}
      aria-checked={checked}
      aria-disabled={disabled}
      aria-labelledby={labelId}
      onClick={toggle}
      onKeyDown={(event) => {
        if (event.key !== " " && event.key !== "Enter") return;
        event.preventDefault();
        toggle();
      }}
      style={{ display: "flex", alignItems: "center", gap: 8, cursor: disabled ? "default" : "pointer" }}
    >
      <span style={{ display: "inline-flex", flex: "none", opacity: disabled ? 0.45 : 1 }}>
        <Checkbox checked={checked} />
      </span>
      <div id={labelId} style={{ flex: 1, minWidth: 0 }}>
        {children}
      </div>
    </div>
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

// One open proposal in server order, collapsible on its own (owner 2026-10-18). Header: type, title, component count.
// Body: one row per proposed component, the option buttons, then «Details» with the full text, the evidence and the
// consequences. A session without items (older engine) keeps the text rendering. A batch-assign answer carries the
// checked groups as groupIds.
export function ProposalCard({ question, expanded, onToggleExpanded, groupsById, labelOf, excluded, busy, posting, error, onToggleGroup, onAnswer }) {
  const { t, tp, lang } = useT();
  const [details, setDetails] = React.useState(false);
  const bodyId = React.useId();
  const detailsId = React.useId();
  const isBatch = question.type === "batch-assign";
  const items = proposalItems(question);
  const groups = list(question.groupIds)
    .map((id) => groupsById.get(id))
    .filter(Boolean);
  const included = includedGroupIds(question, excluded);
  const skip = new Set(list(excluded));
  const checkable = new Set(isBatch ? list(question.groupIds) : []);
  const options = list(question.options);
  const optionText = (optionId) => optionTextFor(t, question.type, options, optionId, labelOf);
  const noneSelected = isBatch && included.length === 0;
  const title = proposalTitle(question, lang);
  const components = tp("{n} component", items.length || list(question.groupIds).length);

  const optionButtons = (
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
  );
  const status = (
    <>
      {noneSelected && <div style={MUTED}>{t("Select at least one group.")}</div>}
      {posting && <div style={MUTED}>{t("Sending answer…")}</div>}
      {error && <div style={ERR_STYLE}>{describeError(error, t("Could not save the answer."))}</div>}
    </>
  );

  let body;
  if (items.length > 0) {
    body = (
      <>
        <ul style={ITEM_LIST}>
          {items.map((item, index) => {
            const view = itemView(item, index);
            const row = <ItemRow item={item} index={index} />;
            return (
              <li key={view.key}>
                {checkable.has(view.itemId) ? (
                  <ItemCheck checked={!skip.has(view.itemId)} disabled={busy} onToggle={() => onToggleGroup(question.questionId, view.itemId)}>
                    {row}
                  </ItemCheck>
                ) : (
                  row
                )}
              </li>
            );
          })}
        </ul>
        {optionButtons}
        {status}
        <button type="button" aria-expanded={details} aria-controls={details ? detailsId : undefined} onClick={() => setDetails((value) => !value)} style={{ ...TOGGLE, alignSelf: "flex-start" }}>
          <Chevron open={details} />
          <span>{t("Details")}</span>
        </button>
        {details && (
          <div id={detailsId} style={DETAILS}>
            <div style={{ ...BODY, overflowWrap: "anywhere" }}>{questionText(question, lang)}</div>
            {groups.map((group) => (
              <GroupDetails key={group.groupId} group={group} labelOf={labelOf} />
            ))}
            <Consequences question={question} optionText={optionText} />
            <span style={{ ...MONO, color: "var(--text-muted)" }}>{question.questionId}</span>
          </div>
        )}
      </>
    );
  } else {
    body = (
      <>
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
        {optionButtons}
        {status}
      </>
    );
  }

  return (
    <div style={CARD} data-question-id={question.questionId}>
      <button type="button" aria-expanded={expanded} aria-controls={expanded ? bodyId : undefined} onClick={onToggleExpanded} style={CARD_HEAD}>
        <Chevron open={expanded} />
        <Badge variant={question.type === "mapping-or-design" ? "warning" : "outline"} style={{ flex: "none", whiteSpace: "nowrap" }}>
          {questionTypeLabel(t, question.type)}
        </Badge>
        <span style={{ ...ONE_LINE, flex: "1 1 auto" }}>{title || components}</span>
        {title && <span style={{ ...MUTED, flex: "none", whiteSpace: "nowrap" }}>{components}</span>}
      </button>
      {expanded && (
        <div id={bodyId} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {body}
        </div>
      )}
    </div>
  );
}

// One given answer, collapsed by default: what was decided, by whom and when, and its own undo button. Undo is
// available until the session is applied (CONNECTOR waits 10 s after the last answer, contract §7.5).
export function AnswerCard({ answer, expanded, onToggleExpanded, labelOf, undoable, undoing, busy, error, onUndo }) {
  const { t, tp, lang } = useT();
  const bodyId = React.useId();
  const items = proposalItems(answer);
  const typeLabel = questionTypeLabel(t, answer.type);
  const title = proposalTitle(answer, lang) || (items.length ? `${typeLabel} · ${tp("{n} component", items.length)}` : typeLabel);
  const choice = answer.optionId ? optionTextFor(t, answer.type, [], answer.optionId, labelOf) : "";
  const decided = [answer.decidedBy, answer.decidedAt ? formatDate(answer.decidedAt) : ""].filter(Boolean).join(" · ");
  const meta = [choice, decided].filter(Boolean).join(" · ");
  return (
    <div style={CARD} data-answer-id={answer.answerId}>
      <button type="button" aria-expanded={expanded} aria-controls={expanded ? bodyId : undefined} onClick={onToggleExpanded} style={CARD_HEAD}>
        <Chevron open={expanded} />
        <StateChip state="confirmed" />
        <span style={{ ...ONE_LINE, flex: "1 1 auto" }}>{title}</span>
        {meta && <span style={{ ...MUTED, ...ONE_LINE, flex: "0 1 auto" }}>{meta}</span>}
      </button>
      {expanded && (
        <div id={bodyId} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.length > 0 && (
            <ul style={ITEM_LIST}>
              {items.map((item, index) => (
                <li key={itemView(item, index).key}>
                  <ItemRow item={item} index={index} />
                </li>
              ))}
            </ul>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <Button size="sm" variant="outline" disabled={!undoable || busy} onClick={() => onUndo(answer)}>
              {undoing ? t("Undoing…") : t("Undo decision")}
            </Button>
            {!undoable && <span style={MUTED}>{t("Committed decisions cannot be undone as drafts")}</span>}
          </div>
          {error && <div style={ERR_STYLE}>{describeError(error, t("Could not undo the decision."))}</div>}
        </div>
      )}
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

function StateCell({ state }) {
  const { t } = useT();
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <StateDot state={state} />
      {stateLabel(t, state)}
    </span>
  );
}

// Named Grasshopper sliders proposed as DG parameters (PARAMETER STATE), 1303-CONTEXT D-37.
function ParametersTable({ parameters }) {
  const { t } = useT();
  if (parameters.length === 0) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h5 style={CAPTION}>{t("DG parameters")}</h5>
      <div style={{ overflowX: "auto" }}>
        <table style={TABLE}>
          <thead>
            <tr>
              <th style={TH}>{t("Slider")}</th>
              <th style={TH}>{t("State")}</th>
              <th style={TH}>{t("Reason")}</th>
            </tr>
          </thead>
          <tbody>
            {parameters.map((p) => (
              <tr key={p.nativeId}>
                <td style={TD}>{p.name}</td>
                <td style={TD}>
                  <StateCell state={p.state} />
                </td>
                <td style={{ ...TD, ...MUTED }}>{p.reason || (p.isParameter ? t("DG parameter") : "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Outputs of calculation components and the DG property each carries (D-37).
function MeasuresTable({ measures }) {
  const { t } = useT();
  if (measures.length === 0) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h5 style={CAPTION}>{t("Calculation outputs")}</h5>
      <div style={{ overflowX: "auto" }}>
        <table style={TABLE}>
          <thead>
            <tr>
              <th style={TH}>{t("Output")}</th>
              <th style={TH}>{t("State")}</th>
              <th style={TH}>{t("Property")}</th>
            </tr>
          </thead>
          <tbody>
            {measures.map((m) => {
              const shown = m.property || list(m.candidates)[0];
              const label = shown ? shown.label || classLocalName(shown.iri || shown.propertyIri) : "—";
              const classes = list(shown?.classes).map((iri) => classLocalName(iri)).join(", ");
              return (
                <tr key={m.nativeId}>
                  <td style={TD}>{m.component ? `${m.name} · ${m.component}` : m.name}</td>
                  <td style={TD}>
                    <StateCell state={m.state} />
                  </td>
                  <td style={TD}>
                    {label}
                    {classes ? <span style={MUTED}>{` · ${classes}`}</span> : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ApplyResult({ result, labelOf }) {
  const { t } = useT();
  const payload = result.payload || {};
  const rows = appliedByClass(payload);
  const state = result.delivery?.state;
  const status = state === "written" ? t("Written to CAD")
    : state === "failed" ? t("CAD delivery failed") : t("Confirmed on server — waiting for CAD");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={BODY}>
        {status} · {t("Accepted decisions: {n}", { n: list(result.answerIds).length })}
        {state === "written" ? ` · ${number(result.delivery.written)}` : ""}
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

// Phase 1303-15 (DGOPN-02): one action puts a ready-to-run property check on the Grasshopper canvas. DG reads the
// project's rules, assembles the calculator and highlighter scripts from its vetted catalogue and places them with the
// OBJECT STATE / PROPERTY STATE / VALIDATOR chain next to the signed-in CONNECTOR; the user only runs it.
function PropertyCheckCard({ project, t }) {
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [error, setError] = React.useState(null);
  const run = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await placePropertyCheck(project));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  const placed = result?.placed || {};
  return (
    <div style={CARD}>
      <div style={BODY}>{t("Property check from the project rules")}</div>
      <div style={MUTED}>{t("DG writes the scripts that compute the rule properties and places them on the Grasshopper canvas.")}</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button size="sm" disabled={busy || !project} onClick={run}>
          {busy ? t("Generating check…") : t("Generate check")}
        </Button>
      </div>
      {error && <div style={ERR_STYLE}>{describeError(error, t("Could not generate the check."))}</div>}
      {result && (
        <div style={{ display: "grid", gap: 4 }}>
          <div style={MUTED}>
            {t("Placed on the canvas: {created} components, {wires} wires", { created: placed.created ?? 0, wires: placed.wires ?? 0 })}
          </div>
          {(result.resolved || []).map((r) => (
            <div key={`${r.ruleId}-${r.dataPropertyIri}`} style={{ ...MONO, overflowWrap: "anywhere" }}>
              {`${r.ruleId} · ${r.dataPropertyLabel} · ${r.calculator}`}
            </div>
          ))}
          {(result.unsupported || []).map((u) => (
            <div key={`${u.ruleId}-${u.dataPropertyIri}`} style={{ ...MUTED, color: "var(--color-warning-ink)" }}>
              {t("No calculator for {property} ({rule})", { property: u.dataPropertyLabel, rule: u.ruleId })}
            </div>
          ))}
          {(placed.warnings || []).map((w) => (
            <div key={w} style={{ ...MUTED, color: "var(--color-warning-ink)" }}>{w}</div>
          ))}
        </div>
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
  // Expansion of each proposal card (by questionId) and answer card (by answerId); only explicit toggles are kept.
  const [questionOpen, setQuestionOpen] = React.useState({});
  const [answerOpen, setAnswerOpen] = React.useState({});
  const [undoing, setUndoing] = React.useState(null);
  const [undoErr, setUndoErr] = React.useState(null);
  const [applying, setApplying] = React.useState(false);
  const [applied, setApplied] = React.useState(null);
  const [applyErr, setApplyErr] = React.useState(null);
  const [notice, setNotice] = React.useState(null);
  // scopeRef drops replies after a collapse, a screen change or an unmount; readRef keeps only the latest session read.
  const scopeRef = React.useRef(0);
  const readRef = React.useRef(0);
  const selectedRef = React.useRef(null);
  const fileRef = React.useRef(null);
  const commitRef = React.useRef(null);
  const bodyId = React.useId();
  const busy = posting !== null || undoing !== null || creating || applying || sessionBusy;
  // CONNECTOR creates sessions by itself (owner amendment 2026-10-18): while the panel is open the newest session
  // is followed until the owner picks an older one.
  const followRef = React.useRef(true);
  const busyRef = React.useRef(false);
  busyRef.current = busy;

  React.useEffect(() => {
    selectedRef.current = selectedId;
  }, [selectedId]);

  // Card expansion belongs to one session: another session starts from the defaults again.
  const shownSessionId = session?.sessionId || null;
  React.useEffect(() => {
    setQuestionOpen({});
    setAnswerOpen({});
    setUndoErr(null);
  }, [shownSessionId]);

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
    setUndoing(null);
    setCreating(false);
    setApplying(false);
    setSessionBusy(false);
    if (open && active) load(selectedRef.current);
    return () => {
      scopeRef.current += 1;
    };
  }, [open, active, load]);

  // Follow new sessions (from Grasshopper CONNECTOR) while the panel is open on this screen.
  React.useEffect(() => {
    if (!(open && active && status === "ready")) return undefined;
    const timer = setInterval(() => {
      if (busyRef.current || !followRef.current) return;
      const scope = scopeRef.current;
      listSessions(project, SESSION_LIMIT)
        .then((listed) => {
          if (scope !== scopeRef.current || busyRef.current || !followRef.current) return;
          const newest = list(listed?.sessions)[0]?.sessionId;
          if (newest && newest !== selectedRef.current) {
            load(newest);
            setNotice({ kind: "arrived" });
          }
        })
        .catch(() => {});
    }, FOLLOW_MS);
    return () => clearInterval(timer);
  }, [open, active, status, project, load]);

  // Read proposal refinement and CAD receipts without interpreting server commit as CAD success.
  const llmPending = session?.llm?.status === "pending";
  const deliveryPending = list(session?.batches).some((batch) => batch.delivery?.state === "queued");
  React.useEffect(() => {
    if (!(open && active && (llmPending || deliveryPending) && selectedId)) return undefined;
    const timer = setInterval(() => {
      if (busyRef.current) return;
      const scope = scopeRef.current;
      const read = readRef.current;
      getSession(project, selectedId)
        .then((full) => {
          if (scope !== scopeRef.current || read !== readRef.current || busyRef.current) return;
          if (full && typeof full === "object") setSession(full);
        })
        .catch(() => {});
    }, FOLLOW_MS);
    return () => clearInterval(timer);
  }, [open, active, llmPending, deliveryPending, selectedId, project]);

  const selectSession = (id) => {
    if (!id || id === selectedId || busy) return;
    followRef.current = id === sessions[0]?.sessionId;
    const scope = scopeRef.current;
    const read = ++readRef.current;
    setSelectedId(id);
    setSession(null);
    setSessionErr(null);
    setSessionBusy(true);
    setApplied(null);
    setApplyErr(null);
    setAnswerErr(null);
    setUndoErr(null);
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
    setUndoErr(null);
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
      // Proposed profiles stay drafts until the shared confirmation succeeds.
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

  // Takes one answer back (contract §7.2); the reply is the recomputed session. The answer's profile effects are
  // reversed on the server, so the profile list is read again.
  const undo = async (entry) => {
    if (!session || busy || !answerUndoable(entry, session)) return;
    const scope = scopeRef.current;
    const sessionId = session.sessionId;
    setUndoing(entry.answerId);
    setUndoErr(null);
    setAnswerErr(null);
    setNotice(null);
    setApplied(null);
    setApplyErr(null);
    try {
      const next = await undoAnswer(project, sessionId, entry.answerId);
      if (scope !== scopeRef.current) return;
      setUndoing(null);
      if (next && typeof next === "object" && (!next.sessionId || next.sessionId === sessionId)) {
        readRef.current += 1; // a session read started before the undo must not bring the answer back
        const merged = { ...next, sessionId };
        setSession(merged);
        setSessions((items) => upsertSession(items, merged));
      }
      setNotice({ kind: "undone" });
      listProfiles(project)
        .then((res) => {
          if (scope === scopeRef.current && Array.isArray(res?.profiles)) setProfiles(res.profiles);
        })
        .catch(() => {});
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setUndoing(null);
      setUndoErr({ answerId: entry.answerId, err });
    }
  };

  const apply = async () => {
    if (!session || busy || busyRef.current || !awaitingApply(session)) return;
    const scope = scopeRef.current;
    const sessionId = session.sessionId;
    const answerIds = pendingAnswerIds(session);
    const key = JSON.stringify([project, sessionId, session.revision, answerIds]);
    if (commitRef.current?.key !== key) {
      // The server revision identifies this exact draft; retries survive a panel or page reload, too.
      commitRef.current = { key, requestId: `commit-${session.revision}`, revision: session.revision, answerIds };
    }
    busyRef.current = true;
    readRef.current += 1;
    setApplying(true);
    setApplyErr(null);
    setApplied(null);
    setNotice(null);
    try {
      const res = await applySession(project, sessionId, commitRef.current);
      if (scope !== scopeRef.current) return;
      // Update locally before refresh: a failed refresh must not offer the same drafts again.
      setSession((current) => current?.sessionId === sessionId ? {
        ...current,
        pendingAnswerIds: pendingAnswerIds(current).filter((id) => !answerIds.includes(id)),
        answers: list(current.answers).map((entry) => answerIds.includes(entry.answerId)
          ? { ...entry, committedAt: res.committedAt, undoable: false } : entry),
        batches: [...list(current.batches).filter((batch) => batch.batchId !== res.batchId), res]
      } : current);
      setApplied(res);
      try {
        const full = await getSession(project, sessionId);
        if (scope !== scopeRef.current) return;
        setSession(full);
        setSessions((items) => upsertSession(items, full));
        const profileList = await listProfiles(project);
        if (scope === scopeRef.current) setProfiles(list(profileList?.profiles));
      } catch (err) {
        // Confirmation already succeeded; a read failure is not a failed commit.
        if (scope === scopeRef.current) setSessionErr(err);
      }
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setApplyErr(err);
    } finally {
      if (scope === scopeRef.current) {
        busyRef.current = false;
        setApplying(false);
      }
    }
  };

  let noticeText = "";
  if (notice?.kind === "decided") noticeText = tp("{n} decision recorded", notice.n);
  else if (notice?.kind === "applied") noticeText = tp("{n} element applied", notice.n);
  else if (notice?.kind === "created") noticeText = t("Mapping session created");
  else if (notice?.kind === "arrived") noticeText = t("New mapping session from Grasshopper");
  else if (notice?.kind === "undone") noticeText = t("Decision undone");

  const labels = classLabels(session);
  const labelOf = (iri) => labels.get(iri) || classLocalName(iri);
  const groupsById = new Map(list(session?.groups).map((group) => [group.groupId, group]));
  const questions = list(session?.questions);
  const answers = sessionAnswers(session);
  const totals = summaryTotals(session?.summary);
  const waitingApply = awaitingApply(session);
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
          <PropertyCheckCard project={project} t={t} />
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
            <h5 style={CAPTION}>{t("Proposals")}</h5>
            {(notice?.kind === "decided" || notice?.kind === "undone") && <div style={MUTED}>{noticeText}</div>}
            {questions.map((question, index) => {
              const expanded = cardOpen(questionOpen, question.questionId, index === 0);
              return (
                <ProposalCard
                  key={question.questionId}
                  question={question}
                  expanded={expanded}
                  onToggleExpanded={() => setQuestionOpen((prev) => toggleCard(prev, question.questionId, index === 0))}
                  groupsById={groupsById}
                  labelOf={labelOf}
                  excluded={excluded[question.questionId]}
                  busy={busy}
                  posting={posting === question.questionId}
                  error={answerErr?.questionId === question.questionId ? answerErr.err : null}
                  onToggleGroup={toggleGroup}
                  onAnswer={answer}
                />
              );
            })}
            {waitingApply ? (
              <div style={MUTED}>{t("Accepted answers are drafts. Confirm once to write only these decisions; unanswered proposals remain available.")}</div>
            ) : (
              questions.length === 0 && (
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                  {t("No open questions.")}
                </div>
              )
            )}
          </div>
        )}

        {session && answers.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <h5 style={CAPTION}>{t("Decisions made")}</h5>
            {answers.map((entry) => (
              <AnswerCard
                key={entry.answerId}
                answer={entry}
                expanded={cardOpen(answerOpen, entry.answerId, false)}
                onToggleExpanded={() => setAnswerOpen((prev) => toggleCard(prev, entry.answerId, false))}
                labelOf={labelOf}
                undoable={answerUndoable(entry, session)}
                undoing={undoing === entry.answerId}
                busy={busy}
                error={undoErr?.answerId === entry.answerId ? undoErr.err : null}
                onUndo={undo}
              />
            ))}
          </div>
        )}

        {session && <MeasuresTable measures={list(session.measures)} />}

        {session && <ParametersTable parameters={list(session.parameters)} />}

        {llmPending ? (
          <div style={MUTED}>{t("LLM proposal is being prepared; the questions update when it arrives")}</div>
        ) : (
          session?.llm?.status && (
            <div style={MUTED}>{t("LLM proposal: {status}", { status: session.llm.model ? `${session.llm.status} · ${session.llm.model}` : session.llm.status })}</div>
          )
        )}

        {notice?.kind === "arrived" && <div style={MUTED}>{noticeText}</div>}

        <ProfilesTable profiles={profiles} labelOf={labelOf} />

        {session && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <Button size="sm" disabled={busy || !waitingApply} onClick={apply}>
                {applying ? t("Confirming…") : t("Confirm and write ({n})", { n: pendingAnswerIds(session).length })}
              </Button>
              {totals.openQuestions > 0 && <span style={MUTED}>{t("Groups without an answer are skipped.")}</span>}
            </div>
            {applyErr && <div style={ERR_STYLE}>{describeError(applyErr, t("Could not apply the mapping."))}</div>}
            {list(session.batches).map((batch) => <ApplyResult key={batch.batchId} result={batch} labelOf={labelOf} />)}
            {applied && !list(session.batches).some((batch) => batch.batchId === applied.batchId)
              && <ApplyResult result={applied} labelOf={labelOf} />}
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

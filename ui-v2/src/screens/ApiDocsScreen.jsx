import React from "react";
import { Button, CodeBlock } from "../components/index.js";
import sections from "./apidocs/content/index.js";

// ── Block Renderer ──────────────────────────────────────────────────────────

function EndpointBlock({ block }) {
  const labelStyle = { font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)", marginBottom: 6 };
  const methodColors = {
    GET: { bg: "rgba(0, 150, 100, 0.10)", text: "var(--color-ink)" },
    POST: { bg: "rgba(0, 100, 200, 0.10)", text: "var(--color-ink)" },
    PUT: { bg: "rgba(200, 150, 0, 0.10)", text: "var(--color-ink)" },
    DELETE: { bg: "var(--color-signal-soft)", text: "var(--color-signal-ink)" },
  };
  const colors = methodColors[block.method] || methodColors.GET;
  const cell = { padding: "8px 8px", font: "400 12px/1.4 var(--font-mono)", color: "var(--color-ink)", verticalAlign: "top", overflowWrap: "anywhere" };
  const thCell = { ...cell, font: "400 12px/1.4 var(--font-sans)", color: "var(--text-muted)", fontWeight: 600 };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--surface-card)", border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-cards)", padding: 20 }}>
      {/* Signature */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ font: "600 13px/1 var(--font-mono)", background: colors.bg, color: colors.text, padding: "4px 8px", borderRadius: 5, letterSpacing: "-0.3px" }}>
          {block.method}
        </span>
        <span style={{ font: "400 13px/1.4 var(--font-mono)", color: "var(--color-ink)", overflowWrap: "anywhere" }}>
          {block.path}
        </span>
      </div>

      {/* Description */}
      {block.description && (
        <div style={{ font: "400 13px/1.5 var(--font-sans)", color: "var(--text-secondary)" }}>
          {block.description}
        </div>
      )}

      {/* Parameter table */}
      {block.params && block.params.length > 0 && (
        <div>
          <div style={labelStyle}>Parameters</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                <th style={thCell}>Name</th>
                <th style={thCell}>Type</th>
                <th style={thCell}>Location</th>
                <th style={thCell}>Required</th>
                <th style={thCell}>Description</th>
              </tr>
            </thead>
            <tbody>
              {block.params.map((p, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                  <td style={{ ...cell, font: "500 12px/1.4 var(--font-mono)" }}>{p.name}</td>
                  <td style={{ ...cell, color: "var(--text-muted)" }}>{p.type}</td>
                  <td style={{ ...cell, color: "var(--text-muted)" }}>{p.location}</td>
                  <td style={{ ...cell, color: "var(--text-muted)" }}>{p.required ? "Yes" : "No"}</td>
                  <td style={{ ...cell, font: "400 12px/1.4 var(--font-sans)", color: "var(--text-secondary)" }}>{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Request example */}
      {block.request && (
        <CodeBlock label="Request example">
          {block.request}
        </CodeBlock>
      )}

      {/* Response example */}
      {block.response && (
        <CodeBlock label="Response example">
          {block.response}
        </CodeBlock>
      )}
    </div>
  );
}

function BlockRenderer({ block }) {
  switch (block.type) {
    case "text":
      return (
        <div style={{ font: "400 14px/1.7 var(--font-sans)", color: "var(--text-secondary)", maxWidth: 700 }}>
          {block.content}
        </div>
      );

    case "code":
      return <CodeBlock label={block.label}>{block.content}</CodeBlock>;

    case "endpoint":
      return <EndpointBlock block={block} />;

    case "table": {
      const cell = { padding: "8px 10px", font: "400 13px/1.4 var(--font-sans)", color: "var(--text-secondary)", verticalAlign: "top" };
      const th = { ...cell, font: "600 12px/1.3 var(--font-sans)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.4px" };
      return (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
              {block.headers.map((h, i) => <th key={i} style={th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                {row.map((cellVal, j) => (
                  <td key={j} style={{ ...cell, color: j === 0 ? "var(--color-ink)" : "var(--text-secondary)", font: j === 0 ? "500 13px/1.4 var(--font-sans)" : "400 13px/1.4 var(--font-sans)" }}>
                    {cellVal}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    case "note": {
      const variants = {
        info: { border: "var(--color-hairline-strong)", bg: "var(--color-canvas)", icon: "i" },
        warning: { border: "var(--color-signal-mid)", bg: "var(--color-signal-soft)", icon: "!" },
        tip: { border: "rgba(0, 150, 100, 0.3)", bg: "rgba(0, 150, 100, 0.06)", icon: "✦" },
      };
      const v = variants[block.variant] || variants.info;
      return (
        <div style={{ display: "flex", gap: 10, padding: "12px 16px", borderRadius: "var(--radius-nested)", border: `1px solid ${v.border}`, background: v.bg }}>
          <span style={{ font: "600 14px/1 var(--font-mono)", color: "var(--color-ink)", opacity: 0.5, flexShrink: 0 }}>{v.icon}</span>
          <div style={{ font: "400 13px/1.5 var(--font-sans)", color: "var(--text-secondary)" }}>
            {block.content}
          </div>
        </div>
      );
    }

    default:
      return null;
  }
}

// ── Tree Node ───────────────────────────────────────────────────────────────

function TreeSection({ section, isExpanded, selectedPageId, onToggle, onSelect }) {
  const chevron = isExpanded ? "▼" : "▶";
  return (
    <div>
      {/* Section header */}
      <div
        onClick={onToggle}
        style={{
          padding: "6px 12px",
          cursor: "pointer",
          borderRadius: "var(--radius-nested)",
          display: "flex",
          alignItems: "center",
          gap: 6,
          font: "600 13px/1.4 var(--font-sans)",
          color: "var(--color-ink)",
          transition: "background 0.1s",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = "var(--color-signal-soft)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onToggle(); }}
      >
        <span style={{ fontSize: 10, width: 12, textAlign: "center", flexShrink: 0, color: "var(--text-muted)" }}>
          {chevron}
        </span>
        {section.title}
      </div>

      {/* Pages */}
      {isExpanded && (
        <div style={{ marginLeft: 8 }}>
          {section.pages.map((page) => {
            const isSelected = page.id === selectedPageId;
            return (
              <div
                key={page.id}
                onClick={() => onSelect(section.id, page.id)}
                style={{
                  padding: "5px 12px 5px 22px",
                  cursor: "pointer",
                  borderRadius: "var(--radius-nested)",
                  font: isSelected ? "500 13px/1.4 var(--font-sans)" : "400 13px/1.4 var(--font-sans)",
                  color: isSelected ? "var(--color-signal-ink)" : "var(--text-secondary)",
                  background: isSelected ? "var(--color-signal-soft)" : "transparent",
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = "var(--ink-a04)";
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = "transparent";
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelect(section.id, page.id);
                }}
              >
                {page.title}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main Screen ─────────────────────────────────────────────────────────────

export default function ApiDocsScreen({ active, onBack, project }) {
  const [expanded, setExpanded] = React.useState(() => {
    // Auto-expand first section
    const init = {};
    if (sections.length > 0) init[sections[0].id] = true;
    return init;
  });
  const [selectedSectionId, setSelectedSectionId] = React.useState(
    sections.length > 0 ? sections[0].id : null
  );
  const [selectedPageId, setSelectedPageId] = React.useState(
    sections.length > 0 && sections[0].pages.length > 0
      ? sections[0].pages[0].id
      : null
  );

  // Find current page
  const currentSection = sections.find((s) => s.id === selectedSectionId);
  const currentPage = currentSection?.pages.find((p) => p.id === selectedPageId);

  const handleToggle = (sectionId) => {
    setExpanded((prev) => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  const handleSelect = (sectionId, pageId) => {
    setSelectedSectionId(sectionId);
    setSelectedPageId(pageId);
    // Auto-expand parent section when selecting a page
    setExpanded((prev) => ({ ...prev, [sectionId]: true }));
  };

  if (!active) return null;

  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 32px 0", flexShrink: 0 }}>
        <Button variant="outline" size="sm" onClick={onBack}>
          ← Back
        </Button>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
            Region · DG API Docs
          </div>
          <div style={{ font: "600 30px/1.1 var(--font-sans)", letterSpacing: "-1px" }}>
            DG API Docs
          </div>
        </div>
      </div>

      {/* ── Body: tree + detail ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", marginTop: 14 }}>
        {/* Tree pane */}
        <div style={{ width: 260, minWidth: 260, overflowY: "auto", padding: "8px 12px 24px 16px", borderRight: "1px solid var(--color-hairline)", boxSizing: "border-box" }}>
          {sections.map((section) => (
            <TreeSection
              key={section.id}
              section={section}
              isExpanded={!!expanded[section.id]}
              selectedPageId={selectedPageId}
              onToggle={() => handleToggle(section.id)}
              onSelect={handleSelect}
            />
          ))}
        </div>

        {/* Detail pane */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 40px 60px 28px" }}>
          {currentPage && currentSection ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 860 }}>
              {/* Breadcrumb */}
              <div style={{ font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)", display: "flex", gap: 6, alignItems: "center" }}>
                <span>{currentSection.title}</span>
                <span style={{ opacity: 0.4 }}>/</span>
                <span style={{ color: "var(--color-ink)" }}>{currentPage.title}</span>
              </div>

              {/* Title */}
              <div style={{ font: "600 26px/1.2 var(--font-sans)", color: "var(--color-ink)", letterSpacing: "-0.8px" }}>
                {currentPage.title}
              </div>

              {/* Summary */}
              {currentPage.summary && (
                <div style={{ font: "400 14px/1.6 var(--font-sans)", color: "var(--text-secondary)", maxWidth: 700, paddingBottom: 8, borderBottom: "1px solid var(--color-hairline)" }}>
                  {currentPage.summary}
                </div>
              )}

              {/* Blocks */}
              {currentPage.blocks && currentPage.blocks.map((block, i) => (
                <div key={i}>
                  <BlockRenderer block={block} />
                </div>
              ))}
            </div>
          ) : (
            <div style={{ font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)", padding: 40 }}>
              Select a page from the tree.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

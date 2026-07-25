import React from "react";

// Searchable value picker: a text field (styled like SearchField) plus an
// anchored dropdown listing the available values (styled like the frost
// popovers). Empty input lists every option; typing narrows by substring.
//
// Distinct from Select: the value set here is data-derived and open-ended —
// the user may type a value that isn't in the list (free-text filtering is
// preserved), and picking from the list is a shortcut, not a constraint.
export default function Combobox({
  value = "",
  onChange,
  onPick,
  options = [],
  placeholder = "Search…",
  emptyLabel = "No values",
  openDirection = "down",
  maxVisible = 200,
  style,
  listStyle,
  ...rest
}) {
  const wrapRef = React.useRef(null);
  const inputRef = React.useRef(null);
  const [open, setOpen] = React.useState(false);
  const [active, setActive] = React.useState(-1);

  // Substring-narrow the option list against the current text. An exact
  // single match is not auto-hidden — the user may want to re-pick it.
  const shown = React.useMemo(() => {
    const q = String(value || "").toLowerCase();
    const list = q ? options.filter((o) => String(o).toLowerCase().indexOf(q) >= 0) : options;
    return list.slice(0, maxVisible);
  }, [options, value, maxVisible]);

  const truncated = React.useMemo(() => {
    const q = String(value || "").toLowerCase();
    const total = q ? options.filter((o) => String(o).toLowerCase().indexOf(q) >= 0).length : options.length;
    return total - shown.length;
  }, [options, value, shown.length]);

  // Reset the keyboard cursor whenever the visible set changes.
  React.useEffect(() => {
    setActive(-1);
  }, [value, options]);

  // Outside-click dismissal (pointerdown so it beats focus churn).
  React.useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    window.addEventListener("pointerdown", onDown, true);
    return () => window.removeEventListener("pointerdown", onDown, true);
  }, [open]);

  const pick = (v) => {
    setOpen(false);
    setActive(-1);
    if (onPick) onPick(v);
    else if (onChange) onChange({ target: { value: v } });
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      if (!shown.length) return;
      const dir = e.key === "ArrowDown" ? 1 : -1;
      setActive((a) => {
        const next = a + dir;
        if (next < 0) return shown.length - 1;
        if (next >= shown.length) return 0;
        return next;
      });
      return;
    }
    if (e.key === "Enter") {
      if (open && active >= 0 && active < shown.length) {
        e.preventDefault();
        pick(shown[active]);
      }
      return;
    }
    if (e.key === "Escape") {
      // Own Escape only while the dropdown is up, so the screen-level
      // Escape precedence (close search → clear selection) still works.
      if (open) {
        e.preventDefault();
        e.stopPropagation();
        setOpen(false);
        setActive(-1);
      }
    }
  };

  const list = (
    <div
      className="dg-frost"
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        [openDirection === "up" ? "bottom" : "top"]: "calc(100% + 6px)",
        zIndex: 20,
        borderRadius: "var(--radius-nested)",
        boxShadow: "var(--shadow-panel)",
        padding: 4,
        maxHeight: 260,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 1,
        ...listStyle
      }}
    >
      {shown.length === 0 && (
        <div
          className="dg-annotation dg-annotation--muted"
          style={{ flex: "none", padding: "8px 8px", fontSize: 10, whiteSpace: "nowrap" }}
        >
          {emptyLabel}
        </div>
      )}
      {shown.map((o, k) => {
        const isActive = k === active;
        const selected = String(o) === String(value);
        return (
          <div
            key={String(o) + "·" + k}
            onPointerDown={(e) => {
              e.preventDefault();
              pick(o);
            }}
            onMouseEnter={() => setActive(k)}
            title={String(o)}
            style={{
              // flex: "none" is load-bearing: this is a column flex container
              // with a maxHeight, so without it the rows shrink below their
              // content height once the list overflows and the text overlaps
              // instead of scrolling.
              flex: "none",
              padding: "6px 8px",
              borderRadius: 6,
              cursor: "pointer",
              font: "400 12px/1.35 var(--font-mono)",
              color: selected ? "var(--color-signal-ink)" : "var(--text-primary)",
              background: isActive ? "var(--color-signal-soft)" : "transparent",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap"
            }}
          >
            {String(o)}
          </div>
        );
      })}
      {truncated > 0 && (
        <div
          className="dg-annotation dg-annotation--muted"
          style={{ flex: "none", padding: "6px 8px", fontSize: 9, whiteSpace: "nowrap", borderTop: "1px solid var(--color-hairline)" }}
        >
          +{truncated} more · keep typing to narrow
        </div>
      )}
    </div>
  );

  return (
    <div ref={wrapRef} style={{ position: "relative", ...style }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          height: 36,
          boxSizing: "border-box",
          background: "var(--surface-input)",
          borderRadius: "var(--radius-inputs)",
          padding: "0 10px 0 14px"
        }}
      >
        <svg
          viewBox="0 0 24 24"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--text-muted)", flex: "none" }}
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          ref={inputRef}
          placeholder={placeholder}
          value={value}
          onChange={(e) => {
            setOpen(true);
            if (onChange) onChange(e);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          style={{
            flex: 1,
            minWidth: 0,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--color-ink)",
            font: "400 14px/1 var(--font-sans)"
          }}
          {...rest}
        />
        <div
          onPointerDown={(e) => {
            e.preventDefault();
            setOpen((v) => !v);
            inputRef.current?.focus();
          }}
          title={open ? "Hide values" : "Show all values"}
          style={{
            flex: "none",
            width: 20,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "var(--text-muted)"
          }}
        >
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 120ms ease" }}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
      </div>
      {open && list}
    </div>
  );
}

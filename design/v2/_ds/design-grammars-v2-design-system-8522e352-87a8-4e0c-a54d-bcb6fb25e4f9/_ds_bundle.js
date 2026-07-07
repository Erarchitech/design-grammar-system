/* @ds-bundle: {"format":4,"namespace":"DesignGrammarsDesignSystem_8522e3","components":[{"name":"Avatar","sourcePath":"components/display/Avatar.jsx"},{"name":"Badge","sourcePath":"components/display/Badge.jsx"},{"name":"Callout","sourcePath":"components/display/Callout.jsx"},{"name":"Chip","sourcePath":"components/display/Chip.jsx"},{"name":"CodeBlock","sourcePath":"components/display/CodeBlock.jsx"},{"name":"KVRow","sourcePath":"components/display/KVRow.jsx"},{"name":"StatBlock","sourcePath":"components/display/KVRow.jsx"},{"name":"Progress","sourcePath":"components/display/Progress.jsx"},{"name":"PropertiesTable","sourcePath":"components/display/PropertiesTable.jsx"},{"name":"Button","sourcePath":"components/forms/Button.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"SearchField","sourcePath":"components/forms/SearchField.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Slider","sourcePath":"components/forms/Slider.jsx"},{"name":"Textarea","sourcePath":"components/forms/Textarea.jsx"},{"name":"Collapsible","sourcePath":"components/surfaces/Collapsible.jsx"},{"name":"CollapsibleItem","sourcePath":"components/surfaces/Collapsible.jsx"},{"name":"Dialog","sourcePath":"components/surfaces/Dialog.jsx"},{"name":"Panel","sourcePath":"components/surfaces/Panel.jsx"},{"name":"RunTile","sourcePath":"components/surfaces/RunTile.jsx"},{"name":"Tabs","sourcePath":"components/surfaces/Tabs.jsx"},{"name":"Tile","sourcePath":"components/surfaces/Tile.jsx"}],"sourceHashes":{"components/display/Avatar.jsx":"cd8947b27740","components/display/Badge.jsx":"975c4003bf63","components/display/Callout.jsx":"d7e7c7112473","components/display/Chip.jsx":"55200246bc49","components/display/CodeBlock.jsx":"2a4f38f1d0d3","components/display/KVRow.jsx":"6daac7af0701","components/display/Progress.jsx":"5231fadc980e","components/display/PropertiesTable.jsx":"791306667862","components/forms/Button.jsx":"cc8be4c0fbb4","components/forms/Checkbox.jsx":"ffd7e91a3505","components/forms/Input.jsx":"eb5ab1255136","components/forms/SearchField.jsx":"d3109adc1210","components/forms/Select.jsx":"43659ad5b002","components/forms/Slider.jsx":"51c9f925eb9f","components/forms/Textarea.jsx":"6aae2b1b0424","components/surfaces/Collapsible.jsx":"c83df2e4f35b","components/surfaces/Dialog.jsx":"d64e962cc1e0","components/surfaces/Panel.jsx":"342bb94b6df4","components/surfaces/RunTile.jsx":"a6e9f02e8fcb","components/surfaces/Tabs.jsx":"d0f5aa0c2ac1","components/surfaces/Tile.jsx":"de31e045b491","ui_kits/design-grammars/GraphViewerScreen.jsx":"3f9f39d2e4f7","ui_kits/design-grammars/HomeScreen.jsx":"4316a97b9931","ui_kits/design-grammars/KitShell.jsx":"6119d2d3bd2c","ui_kits/design-grammars/LoginScreen.jsx":"1c4268277dc1","ui_kits/design-grammars/ModelViewerScreen.jsx":"0b4b273507c6","ui_kits/design-grammars/ProjectScreen.jsx":"24e44de64efb"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DesignGrammarsDesignSystem_8522e3 = window.DesignGrammarsDesignSystem_8522e3 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/display/Avatar.jsx
try { (() => {
function Avatar({
  initials = 'JD',
  size = 32,
  style
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: size,
      height: size,
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-ink-soft)',
      color: 'var(--text-inverse)',
      font: `600 ${Math.round(size * 0.38)}px/1 var(--font-sans)`,
      letterSpacing: '0.02em',
      flex: 'none',
      ...style
    }
  }, initials);
}
Object.assign(__ds_scope, { Avatar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Avatar.jsx", error: String((e && e.message) || e) }); }

// components/display/Badge.jsx
try { (() => {
function Badge({
  variant = 'soft',
  children,
  style
}) {
  const variants = {
    solid: {
      background: 'var(--color-ink-soft)',
      color: 'var(--text-inverse)',
      border: '1px solid transparent'
    },
    soft: {
      background: 'var(--color-canvas)',
      color: 'var(--color-ink-soft)',
      border: '1px solid transparent'
    },
    outline: {
      background: 'transparent',
      color: 'var(--color-ink)',
      border: '1px solid var(--color-hairline)'
    },
    signal: {
      background: 'var(--color-signal-soft)',
      color: 'var(--color-signal-ink)',
      border: '1px solid transparent'
    }
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      borderRadius: 'var(--radius-badges)',
      padding: '2px 8px',
      font: '500 12px/1.33 var(--font-sans)',
      ...(variants[variant] || variants.soft),
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Badge.jsx", error: String((e && e.message) || e) }); }

// components/display/Callout.jsx
try { (() => {
function Callout({
  date,
  title,
  subtitle,
  detail,
  signal = false,
  marker = false,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'inline-flex',
      alignItems: 'flex-start',
      gap: 14,
      ...style
    }
  }, marker && /*#__PURE__*/React.createElement("svg", {
    width: "34",
    height: "34",
    viewBox: "0 0 34 34",
    style: {
      flex: 'none',
      marginTop: 2
    }
  }, /*#__PURE__*/React.createElement("polygon", {
    points: "17,3 29,10 29,24 17,31 5,24 5,10",
    fill: "none",
    stroke: signal ? 'var(--color-signal)' : 'var(--ink-a32)',
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "17",
    cy: "17",
    r: "2.5",
    fill: signal ? 'var(--color-signal)' : 'var(--color-ink)'
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      borderLeft: `1px solid ${signal ? 'var(--color-signal)' : 'var(--ink-a32)'}`,
      paddingLeft: 12,
      display: 'flex',
      flexDirection: 'column',
      gap: 1
    }
  }, date && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1.4 var(--font-annotation)',
      letterSpacing: '1.2px',
      color: 'var(--text-muted)'
    }
  }, date), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 18px/1.2 var(--font-annotation)',
      letterSpacing: 'var(--tracking-annotation-lg)',
      textTransform: 'uppercase',
      color: 'var(--color-ink)'
    }
  }, title, subtitle && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)',
      fontWeight: 400
    }
  }, " : ", subtitle)), detail && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1.5 var(--font-annotation)',
      letterSpacing: '1.4px',
      textTransform: 'uppercase',
      color: signal ? 'var(--color-signal-ink)' : 'var(--color-ink-soft)'
    }
  }, detail)));
}
Object.assign(__ds_scope, { Callout });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Callout.jsx", error: String((e && e.message) || e) }); }

// components/display/Chip.jsx
try { (() => {
function Chip({
  selected = false,
  onRemove,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      height: 26,
      boxSizing: 'border-box',
      borderRadius: 'var(--radius-full)',
      padding: '0 12px',
      font: '500 13px/1 var(--font-sans)',
      background: selected ? 'var(--accent-selection-bg)' : 'var(--color-paper)',
      color: selected ? 'var(--color-signal-ink)' : 'var(--color-ink)',
      border: selected ? '1px solid var(--color-signal)' : '1px solid var(--color-hairline)',
      ...style
    }
  }, children, onRemove && /*#__PURE__*/React.createElement("span", {
    onClick: onRemove,
    style: {
      cursor: 'pointer',
      color: 'inherit',
      opacity: 0.6,
      font: '400 13px/1 var(--font-sans)'
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Chip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Chip.jsx", error: String((e && e.message) || e) }); }

// components/display/CodeBlock.jsx
try { (() => {
function CodeBlock({
  children,
  label,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1.33 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, label), /*#__PURE__*/React.createElement("pre", {
    style: {
      margin: 0,
      background: 'var(--color-canvas)',
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-nested)',
      padding: '12px 14px',
      font: '400 12px/1.6 var(--font-mono)',
      color: 'var(--color-ink)',
      whiteSpace: 'pre-wrap',
      overflowWrap: 'anywhere'
    }
  }, children));
}
Object.assign(__ds_scope, { CodeBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/CodeBlock.jsx", error: String((e && e.message) || e) }); }

// components/display/KVRow.jsx
try { (() => {
function KVRow({
  label,
  value,
  mono = true,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: 12,
      padding: '5px 0',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1.4 var(--font-sans)',
      color: 'var(--text-muted)',
      flex: 'none'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      font: `400 12px/1.4 ${mono ? 'var(--font-mono)' : 'var(--font-sans)'}`,
      color: 'var(--color-ink)',
      textAlign: 'right',
      overflowWrap: 'anywhere',
      minWidth: 0
    }
  }, value));
}
function StatBlock({
  label,
  value,
  signal = false,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 12px/1.33 var(--font-sans)',
      letterSpacing: 'var(--tracking-caption)',
      textTransform: 'uppercase',
      color: 'var(--text-muted)'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '600 30px/1.2 var(--font-sans)',
      letterSpacing: 'var(--tracking-heading)',
      color: signal ? 'var(--color-signal-ink)' : 'var(--color-ink)'
    }
  }, value));
}
Object.assign(__ds_scope, { KVRow, StatBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/KVRow.jsx", error: String((e && e.message) || e) }); }

// components/display/Progress.jsx
try { (() => {
function Progress({
  value = 0,
  steps = [],
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 10,
      boxSizing: 'border-box',
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-paper)',
      border: '1px solid var(--color-hairline)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${Math.max(0, Math.min(100, value))}%`,
      height: '100%',
      background: 'var(--color-ink)',
      borderRadius: 'var(--radius-full)',
      transition: 'width var(--duration-base) var(--ease-out)'
    }
  })), steps.length > 0 && /*#__PURE__*/React.createElement("ol", {
    style: {
      listStyle: 'none',
      margin: 0,
      padding: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: 3
    }
  }, steps.map((s, i) => {
    const st = typeof s === 'string' ? {
      label: s
    } : s;
    const done = !!st.time;
    return /*#__PURE__*/React.createElement("li", {
      key: i,
      style: {
        font: `400 12px/1.4 var(--font-mono)`,
        color: st.active ? 'var(--color-signal-ink)' : done ? 'var(--color-ink)' : 'var(--text-muted)',
        display: 'flex',
        gap: 8,
        alignItems: 'baseline'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 'none'
      }
    }, done ? '■' : st.active ? '▶' : '□'), /*#__PURE__*/React.createElement("span", null, st.label, st.time ? ` (${st.time})` : ''));
  })));
}
Object.assign(__ds_scope, { Progress });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Progress.jsx", error: String((e && e.message) || e) }); }

// components/display/PropertiesTable.jsx
try { (() => {
function PropertiesTable({
  rows = [],
  editable = true,
  style
}) {
  const cell = {
    padding: '10px 8px',
    font: '400 13px/1.4 var(--font-sans)',
    verticalAlign: 'top'
  };
  return /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      ...style
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("th", {
    style: {
      ...cell,
      width: 118,
      textAlign: 'left',
      fontWeight: 600,
      color: 'var(--text-muted)'
    }
  }, "Key"), /*#__PURE__*/React.createElement("th", {
    style: {
      ...cell,
      textAlign: 'left',
      fontWeight: 600,
      color: 'var(--text-muted)'
    }
  }, "Value"))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      ...cell,
      color: 'var(--color-ink)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      gap: 4,
      alignItems: 'baseline'
    }
  }, editable && !String(r.key).startsWith('<') && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--ink-a32)',
      fontSize: 12
    }
  }, "\u270E"), r.key)), /*#__PURE__*/React.createElement("td", {
    style: {
      ...cell,
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-ink)',
      overflowWrap: 'anywhere'
    }
  }, r.value)))));
}
Object.assign(__ds_scope, { PropertiesTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/PropertiesTable.jsx", error: String((e && e.message) || e) }); }

// components/forms/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Button({
  variant = 'primary',
  size = 'md',
  selected = false,
  disabled = false,
  children,
  style,
  ...rest
}) {
  const heights = {
    sm: 28,
    md: 36,
    lg: 40
  };
  const h = heights[size] || 36;
  const variants = {
    primary: {
      background: 'var(--color-ink)',
      color: 'var(--text-inverse)',
      border: '1px solid transparent'
    },
    secondary: {
      background: 'var(--color-canvas)',
      color: 'var(--color-ink)',
      border: '1px solid transparent'
    },
    outline: {
      background: 'transparent',
      color: 'var(--color-ink)',
      border: '1px solid var(--color-hairline)'
    },
    destructive: {
      background: 'transparent',
      color: 'var(--color-signal-ink)',
      border: '1px solid var(--color-signal-mid)'
    }
  };
  const v = variants[variant] || variants.primary;
  const sel = selected ? {
    boxShadow: 'var(--focus-ring-selected)',
    background: 'var(--accent-selection-bg)',
    color: 'var(--color-signal-ink)',
    border: '1px solid transparent'
  } : null;
  return /*#__PURE__*/React.createElement("button", _extends({
    disabled: disabled,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      height: h,
      padding: size === 'sm' ? '0 12px' : '0 16px',
      borderRadius: 'var(--radius-buttons)',
      font: `500 ${size === 'sm' ? 13 : 14}px/1 var(--font-sans)`,
      cursor: disabled ? 'default' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      transition: 'background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out)',
      ...v,
      ...sel,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Button.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function Checkbox({
  label,
  checked = false,
  onChange,
  style
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: 'pointer',
      userSelect: 'none',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => onChange && onChange(!checked),
    style: {
      width: 16,
      height: 16,
      boxSizing: 'border-box',
      borderRadius: 'var(--radius-small)',
      border: checked ? '1px solid var(--color-ink)' : '1px solid var(--color-hairline-strong)',
      background: checked ? 'var(--color-ink)' : 'var(--color-paper)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'background var(--duration-fast) var(--ease-out)',
      flex: 'none'
    }
  }, checked && /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "11",
    height: "11",
    fill: "none",
    stroke: "#fafafa",
    strokeWidth: "3",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  }))), label && /*#__PURE__*/React.createElement("span", {
    onClick: () => onChange && onChange(!checked),
    style: {
      font: '400 13px/1 var(--font-sans)',
      color: 'var(--color-ink)'
    }
  }, label));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Input({
  label,
  hint,
  mono = false,
  invalid = false,
  style,
  ...rest
}) {
  const field = /*#__PURE__*/React.createElement("input", _extends({
    style: {
      width: '100%',
      boxSizing: 'border-box',
      height: 36,
      background: 'var(--surface-input)',
      color: 'var(--color-ink)',
      border: '1px solid transparent',
      borderRadius: 'var(--radius-inputs)',
      padding: '8px 14px',
      outline: 'none',
      font: `400 14px/1.43 ${mono ? 'var(--font-mono)' : 'var(--font-sans)'}`,
      transition: 'border-color var(--duration-fast) var(--ease-out)',
      ...(invalid ? {
        borderColor: 'var(--color-signal)'
      } : null),
      ...style
    },
    onFocus: e => {
      if (!invalid) e.target.style.borderColor = 'var(--color-hairline-strong)';
    },
    onBlur: e => {
      if (!invalid) e.target.style.borderColor = 'transparent';
    }
  }, rest));
  if (!label && !hint) return field;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'block'
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)',
      marginBottom: 8
    }
  }, label), field, hint && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      font: '400 12px/1.33 var(--font-sans)',
      color: 'var(--text-muted)',
      marginTop: 6
    }
  }, hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/SearchField.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function SearchField({
  placeholder = 'Search projects...',
  shortcut,
  value,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      height: 36,
      boxSizing: 'border-box',
      background: 'var(--surface-input)',
      borderRadius: 'var(--radius-inputs)',
      padding: '0 14px',
      ...style
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "14",
    height: "14",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      color: 'var(--text-muted)',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "11",
    cy: "11",
    r: "8"
  }), /*#__PURE__*/React.createElement("path", {
    d: "m21 21-4.3-4.3"
  })), /*#__PURE__*/React.createElement("input", _extends({
    placeholder: placeholder,
    value: value,
    onChange: onChange,
    style: {
      flex: 1,
      minWidth: 0,
      background: 'transparent',
      border: 'none',
      outline: 'none',
      color: 'var(--color-ink)',
      font: '400 14px/1 var(--font-sans)'
    }
  }, rest)), shortcut && /*#__PURE__*/React.createElement("kbd", {
    style: {
      font: '400 11px/1 var(--font-mono)',
      color: 'var(--text-muted)',
      border: '1px solid var(--color-hairline)',
      borderRadius: 6,
      padding: '3px 5px',
      background: 'var(--color-paper)'
    }
  }, shortcut));
}
Object.assign(__ds_scope, { SearchField });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/SearchField.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Select({
  label,
  options = [],
  value,
  onChange,
  style,
  ...rest
}) {
  const field = /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("select", _extends({
    value: value,
    onChange: onChange,
    style: {
      width: '100%',
      boxSizing: 'border-box',
      height: 36,
      appearance: 'none',
      WebkitAppearance: 'none',
      background: 'var(--surface-input)',
      color: 'var(--color-ink)',
      border: '1px solid transparent',
      borderRadius: 'var(--radius-inputs)',
      padding: '0 36px 0 14px',
      outline: 'none',
      cursor: 'pointer',
      font: '400 14px/1.43 var(--font-sans)',
      ...style
    },
    onFocus: e => {
      e.target.style.borderColor = 'var(--color-hairline-strong)';
    },
    onBlur: e => {
      e.target.style.borderColor = 'transparent';
    }
  }, rest), options.map(o => {
    const opt = typeof o === 'string' ? {
      value: o,
      label: o
    } : o;
    return /*#__PURE__*/React.createElement("option", {
      key: opt.value,
      value: opt.value
    }, opt.label);
  })), /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "14",
    height: "14",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      position: 'absolute',
      right: 14,
      top: '50%',
      transform: 'translateY(-50%)',
      pointerEvents: 'none',
      color: 'var(--text-muted)'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "m6 9 6 6 6-6"
  })));
  if (!label) return field;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)',
      marginBottom: 8
    }
  }, label), field);
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Slider.jsx
try { (() => {
function Slider({
  label,
  value = 50,
  onChange,
  showValue = true,
  unit = '%',
  style
}) {
  const pct = Math.max(0, Math.min(100, value));
  const track = e => {
    if (!onChange) return;
    const r = e.currentTarget.getBoundingClientRect();
    onChange(Math.round((e.clientX - r.left) / r.width * 100));
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      ...style
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1 var(--font-sans)',
      color: 'var(--text-muted)',
      whiteSpace: 'nowrap'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    onMouseDown: e => {
      track(e);
      const mv = ev => track(ev);
      const up = () => {
        window.removeEventListener('mousemove', mv);
        window.removeEventListener('mouseup', up);
      };
      window.addEventListener('mousemove', mv);
      window.addEventListener('mouseup', up);
    },
    style: {
      position: 'relative',
      flex: 1,
      minWidth: 60,
      height: 14,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: 3,
      borderRadius: 'var(--radius-full)',
      background: 'var(--ink-a08)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      width: pct + '%',
      height: 3,
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-ink)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: `calc(${pct}% - 6px)`,
      width: 12,
      height: 12,
      boxSizing: 'border-box',
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-paper)',
      border: '1px solid var(--color-ink)'
    }
  })), showValue && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1 var(--font-mono)',
      color: 'var(--color-ink)',
      minWidth: 34,
      textAlign: 'right'
    }
  }, pct, unit));
}
Object.assign(__ds_scope, { Slider });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Slider.jsx", error: String((e && e.message) || e) }); }

// components/forms/Textarea.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Textarea({
  label,
  mono = true,
  rows = 5,
  style,
  ...rest
}) {
  const field = /*#__PURE__*/React.createElement("textarea", _extends({
    rows: rows,
    style: {
      width: '100%',
      boxSizing: 'border-box',
      resize: 'vertical',
      background: 'var(--surface-input)',
      color: 'var(--color-ink)',
      border: '1px solid transparent',
      borderRadius: 'var(--radius-nested)',
      padding: '12px 14px',
      outline: 'none',
      font: `400 13px/1.55 ${mono ? 'var(--font-mono)' : 'var(--font-sans)'}`,
      transition: 'border-color var(--duration-fast) var(--ease-out)',
      ...style
    },
    onFocus: e => {
      e.target.style.borderColor = 'var(--color-hairline-strong)';
    },
    onBlur: e => {
      e.target.style.borderColor = 'transparent';
    }
  }, rest));
  if (!label) return field;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)',
      marginBottom: 8
    }
  }, label), field);
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Textarea.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Collapsible.jsx
try { (() => {
function Collapsible({
  label,
  count,
  open = false,
  onToggle,
  signal = false,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-nested)',
      overflow: 'hidden',
      ...style
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onToggle,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      width: '100%',
      boxSizing: 'border-box',
      padding: '9px 12px',
      border: 'none',
      cursor: 'pointer',
      textAlign: 'left',
      background: 'var(--color-surface-alt)',
      font: '500 13px/1 var(--font-sans)',
      color: 'var(--color-ink)'
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: "13",
    height: "13",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
      transition: 'transform var(--duration-fast) var(--ease-out)',
      color: 'var(--text-muted)',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: "m6 9 6 6 6-6"
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1
    }
  }, label), count != null && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 12px/1 var(--font-mono)',
      padding: '2px 7px',
      borderRadius: 'var(--radius-full)',
      background: signal ? 'var(--color-signal-soft)' : 'var(--color-paper)',
      color: signal ? 'var(--color-signal-ink)' : 'var(--text-muted)',
      border: signal ? '1px solid transparent' : '1px solid var(--color-hairline)'
    }
  }, count)), open && /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid var(--color-hairline)',
      background: 'var(--color-paper)'
    }
  }, children));
}
function CollapsibleItem({
  primary,
  secondary,
  selected = false,
  onClick,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClick,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      padding: '8px 12px',
      cursor: onClick ? 'pointer' : 'default',
      borderBottom: '1px solid var(--color-hairline)',
      background: selected ? 'var(--accent-selection-bg)' : 'transparent',
      boxShadow: selected ? 'inset 2px 0 0 var(--color-signal)' : 'none',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 13px/1.3 var(--font-mono)',
      color: selected ? 'var(--color-signal-ink)' : 'var(--color-ink)'
    }
  }, primary), secondary && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 11px/1.3 var(--font-mono)',
      color: 'var(--text-muted)'
    }
  }, secondary));
}
Object.assign(__ds_scope, { Collapsible, CollapsibleItem });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Collapsible.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Dialog.jsx
try { (() => {
function Dialog({
  title,
  open = true,
  onClose,
  footer,
  children,
  style
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: 380,
      boxSizing: 'border-box',
      background: 'var(--frost-bg)',
      backdropFilter: 'blur(var(--frost-blur))',
      WebkitBackdropFilter: 'blur(var(--frost-blur))',
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-cards)',
      boxShadow: 'var(--shadow-panel)',
      overflow: 'hidden',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '14px 20px',
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '600 15px/1.2 var(--font-sans)',
      color: 'var(--color-ink)'
    }
  }, title), onClose && /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      border: 'none',
      background: 'transparent',
      cursor: 'pointer',
      color: 'var(--text-muted)',
      font: '400 16px/1 var(--font-sans)',
      padding: 4
    }
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 14
    }
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: 8,
      padding: '14px 20px',
      borderTop: '1px solid var(--color-hairline)'
    }
  }, footer));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Panel.jsx
try { (() => {
function Panel({
  title,
  frost = false,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      background: frost ? 'var(--frost-bg)' : 'var(--surface-card)',
      backdropFilter: frost ? 'blur(var(--frost-blur))' : undefined,
      WebkitBackdropFilter: frost ? 'blur(var(--frost-blur))' : undefined,
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-cards)',
      boxShadow: 'var(--shadow-subtle)',
      padding: 'var(--card-padding)',
      ...style
    }
  }, title && /*#__PURE__*/React.createElement("h4", {
    style: {
      margin: '0 0 12px',
      font: '500 12px/1.33 var(--font-sans)',
      letterSpacing: 'var(--tracking-caption)',
      textTransform: 'uppercase',
      color: 'var(--text-muted)'
    }
  }, title), children);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Panel.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/RunTile.jsx
try { (() => {
function RunTile({
  ruleId,
  date,
  kind = 'Constraint',
  active = false,
  onSelect,
  onDelete,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onSelect,
    style: {
      width: 178,
      flex: 'none',
      boxSizing: 'border-box',
      background: 'var(--surface-card)',
      border: active ? '1px solid var(--color-signal)' : '1px solid var(--color-hairline)',
      boxShadow: active ? '0 0 0 1px var(--color-signal-mid)' : 'var(--shadow-subtle)',
      borderRadius: 'var(--radius-nested)',
      overflow: 'hidden',
      cursor: onSelect ? 'pointer' : 'default'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 6,
      padding: '7px 10px',
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 12px/1.2 var(--font-mono)',
      color: active ? 'var(--color-signal-ink)' : 'var(--color-ink)',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, ruleId), onDelete && /*#__PURE__*/React.createElement("span", {
    onClick: e => {
      e.stopPropagation();
      onDelete();
    },
    title: "Delete run",
    style: {
      color: 'var(--ink-a32)',
      cursor: 'pointer',
      font: '400 13px/1 var(--font-sans)',
      flex: 'none'
    }
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 64,
      background: 'var(--color-canvas)',
      backgroundImage: 'linear-gradient(var(--ink-a04) 1px, transparent 1px), linear-gradient(90deg, var(--ink-a04) 1px, transparent 1px)',
      backgroundSize: '16px 16px'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 6,
      padding: '7px 10px',
      borderTop: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 11px/1.2 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, date), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 10px/1.2 var(--font-sans)',
      padding: '2px 7px',
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-canvas)',
      color: 'var(--color-ink-soft)'
    }
  }, kind)));
}
Object.assign(__ds_scope, { RunTile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/RunTile.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Tabs.jsx
try { (() => {
function Tabs({
  tabs = [],
  active = 0,
  onChange,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-nested)',
      overflow: 'hidden',
      background: 'var(--color-canvas)',
      ...style
    }
  }, tabs.map((t, i) => /*#__PURE__*/React.createElement("button", {
    key: i,
    onClick: () => onChange && onChange(i),
    style: {
      flex: 1,
      height: 36,
      border: 'none',
      cursor: 'pointer',
      borderRight: i < tabs.length - 1 ? '1px solid var(--color-hairline)' : 'none',
      background: i === active ? 'var(--color-paper)' : 'transparent',
      color: i === active ? 'var(--color-ink)' : 'var(--text-muted)',
      font: `${i === active ? 600 : 400} 13px/1 var(--font-sans)`,
      transition: 'background var(--duration-fast) var(--ease-out)'
    }
  }, t)));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Tile.jsx
try { (() => {
function Tile({
  title,
  description,
  thumbnail,
  onClick,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClick,
    onMouseEnter: e => {
      e.currentTarget.style.borderColor = 'var(--color-hairline-strong)';
    },
    onMouseLeave: e => {
      e.currentTarget.style.borderColor = 'var(--color-hairline)';
    },
    style: {
      background: 'var(--surface-card)',
      border: '1px solid var(--color-hairline)',
      borderRadius: 'var(--radius-cards)',
      boxShadow: 'var(--shadow-subtle)',
      overflow: 'hidden',
      cursor: onClick ? 'pointer' : 'default',
      transition: 'border-color var(--duration-fast) var(--ease-out)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      aspectRatio: '16 / 9',
      background: 'var(--color-canvas)',
      backgroundImage: 'linear-gradient(var(--ink-a04) 1px, transparent 1px), linear-gradient(90deg, var(--ink-a04) 1px, transparent 1px)',
      backgroundSize: '24px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, thumbnail || /*#__PURE__*/React.createElement("svg", {
    width: "40",
    height: "40",
    viewBox: "0 0 40 40"
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "20",
    cy: "12",
    r: "3.5",
    fill: "none",
    stroke: "var(--ink-a32)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "10",
    cy: "28",
    r: "3.5",
    fill: "none",
    stroke: "var(--ink-a32)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "30",
    cy: "28",
    r: "3.5",
    fill: "var(--color-ink)"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M18 15 12 25 M22 15 28 25 M13.5 28 26.5 28",
    stroke: "var(--ink-a32)",
    strokeWidth: "1"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '14px 16px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '600 15px/1.3 var(--font-sans)',
      color: 'var(--color-ink)'
    }
  }, title), description && /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 13px/1.45 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, description)));
}
Object.assign(__ds_scope, { Tile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Tile.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/GraphViewerScreen.jsx
try { (() => {
function Datascape({
  nodes,
  edges,
  selected,
  onSelect
}) {
  // Ink arcs + dot nodes; selected node gets the red halo and a divergence callout.
  const sel = nodes.find(n => n.id === selected);
  return /*#__PURE__*/React.createElement("svg", {
    width: "100%",
    height: "100%",
    viewBox: "0 0 640 900",
    preserveAspectRatio: "xMidYMid meet",
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("g", {
    fill: "none"
  }, edges.map(([a, b, w], i) => {
    const n1 = nodes.find(n => n.id === a),
      n2 = nodes.find(n => n.id === b);
    const mx = (n1.x + n2.x) / 2 + (n1.y - n2.y) * 0.35;
    const my = (n1.y + n2.y) / 2 + (n2.x - n1.x) * 0.35;
    const hot = selected && (a === selected || b === selected);
    return /*#__PURE__*/React.createElement("path", {
      key: i,
      d: `M${n1.x} ${n1.y} Q ${mx} ${my} ${n2.x} ${n2.y}`,
      stroke: hot ? 'var(--color-signal-mid)' : `var(--ink-a${w})`,
      strokeWidth: "1"
    });
  })), nodes.map(n => /*#__PURE__*/React.createElement("g", {
    key: n.id,
    onClick: () => onSelect(n.id),
    style: {
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: n.x,
    cy: n.y,
    r: "14",
    fill: "transparent"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: n.x,
    cy: n.y,
    r: n.r,
    fill: n.id === selected ? 'var(--color-signal)' : n.kind === 'Var' ? 'var(--color-mid-gray)' : 'var(--color-ink)',
    stroke: n.kind === 'Class' ? 'var(--color-paper)' : 'none',
    strokeWidth: n.kind === 'Class' ? 1.5 : 0
  }), n.id === selected && /*#__PURE__*/React.createElement("circle", {
    cx: n.x,
    cy: n.y,
    r: n.r + 8,
    fill: "none",
    stroke: "var(--color-signal-mid)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("text", {
    x: n.x + 12,
    y: n.y + 4,
    fontFamily: "var(--font-mono)",
    fontSize: "10",
    fill: n.id === selected ? 'var(--color-signal-ink)' : 'var(--ink-a56)'
  }, n.label))), sel && /*#__PURE__*/React.createElement("g", null, /*#__PURE__*/React.createElement("path", {
    d: `M${sel.x} ${sel.y - sel.r - 8} L ${sel.x} ${sel.y - sel.r - 46} L ${sel.x + 16} ${sel.y - sel.r - 46}`,
    stroke: "var(--ink-a32)",
    strokeWidth: "1",
    fill: "none"
  }), /*#__PURE__*/React.createElement("text", {
    x: sel.x + 22,
    y: sel.y - sel.r - 52,
    fontFamily: "Oswald, sans-serif",
    fontSize: "13",
    letterSpacing: "1.4",
    fill: "var(--color-ink)"
  }, sel.callout[0]), /*#__PURE__*/React.createElement("text", {
    x: sel.x + 22,
    y: sel.y - sel.r - 38,
    fontFamily: "Oswald, sans-serif",
    fontSize: "10",
    letterSpacing: "1.2",
    fill: "var(--color-mid-gray)"
  }, sel.callout[1])));
}
function GraphViewerScreen({
  go
}) {
  const {
    Button,
    Select,
    Tabs,
    Textarea,
    Progress,
    Chip,
    PropertiesTable
  } = window.DS;
  const [tab, setTab] = React.useState(0);
  const [selected, setSelected] = React.useState('rule');
  const [running, setRunning] = React.useState(false);
  const nodes = [{
    id: 'rule',
    x: 320,
    y: 330,
    r: 9,
    kind: 'Rule',
    label: 'Rule',
    callout: ['R_HEIGHT_MAX', 'RULE · METAGRAPH']
  }, {
    id: 'atomB',
    x: 180,
    y: 470,
    r: 7,
    kind: 'Atom',
    label: 'Atom (body)',
    callout: ['ATOM : BODY', 'HASHEIGHT(?B, ?H)']
  }, {
    id: 'atomH',
    x: 460,
    y: 470,
    r: 7,
    kind: 'Atom',
    label: 'Atom (head)',
    callout: ['ATOM : HEAD', 'VIOLATION(?B)']
  }, {
    id: 'var',
    x: 110,
    y: 620,
    r: 5,
    kind: 'Var',
    label: '?height',
    callout: ['VARIABLE', '?HEIGHT']
  }, {
    id: 'cls',
    x: 520,
    y: 620,
    r: 6,
    kind: 'Class',
    label: 'Building',
    callout: ['CLASS', 'BUILDING']
  }, {
    id: 'var2',
    x: 300,
    y: 640,
    r: 5,
    kind: 'Var',
    label: '?b',
    callout: ['VARIABLE', '?B']
  }, {
    id: 'cls2',
    x: 420,
    y: 200,
    r: 6,
    kind: 'Class',
    label: 'Zone',
    callout: ['CLASS', 'ZONE']
  }];
  const edges = [['rule', 'atomB', 32], ['rule', 'atomH', 32], ['atomB', 'var', 16], ['atomH', 'cls', 16], ['atomB', 'var2', 16], ['atomH', 'var2', 8], ['rule', 'cls2', 8], ['cls', 'cls2', 8]];
  const details = {
    rule: {
      chip: 'Rule',
      rows: [{
        key: '<id>',
        value: '42'
      }, {
        key: 'Rule_Id',
        value: '"R_height_max"'
      }, {
        key: 'graph',
        value: '"Metagraph"'
      }, {
        key: 'project',
        value: '"Residential Tower"'
      }, {
        key: 'text',
        value: '"Maximum height must not exceed 45m"'
      }]
    },
    atomB: {
      chip: 'Atom',
      rows: [{
        key: '<id>',
        value: '43'
      }, {
        key: 'role',
        value: '"body"'
      }, {
        key: 'predicate',
        value: '"hasHeight"'
      }]
    },
    atomH: {
      chip: 'Atom',
      rows: [{
        key: '<id>',
        value: '44'
      }, {
        key: 'role',
        value: '"head"'
      }, {
        key: 'predicate',
        value: '"violation"'
      }]
    },
    var: {
      chip: 'Variable',
      rows: [{
        key: '<id>',
        value: '45'
      }, {
        key: 'name',
        value: '"?height"'
      }]
    },
    var2: {
      chip: 'Variable',
      rows: [{
        key: '<id>',
        value: '46'
      }, {
        key: 'name',
        value: '"?b"'
      }]
    },
    cls: {
      chip: 'Class',
      rows: [{
        key: '<id>',
        value: '47'
      }, {
        key: 'name',
        value: '"Building"'
      }]
    },
    cls2: {
      chip: 'Class',
      rows: [{
        key: '<id>',
        value: '48'
      }, {
        key: 'name',
        value: '"Zone"'
      }]
    }
  };
  const d = details[selected];
  const runSteps = running ? [{
    label: 'Send rules',
    time: '1.2s'
  }, {
    label: 'LLM parse',
    time: '3.4s'
  }, {
    label: 'Write graph',
    active: true
  }, {
    label: 'Annotate properties'
  }, {
    label: 'Reload graph'
  }] : [{
    label: 'Send rules'
  }, {
    label: 'LLM parse'
  }, {
    label: 'Write graph'
  }, {
    label: 'Annotate properties'
  }, {
    label: 'Reload graph'
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 340,
      flex: 'none',
      boxSizing: 'border-box',
      background: 'var(--surface-sidebar)',
      borderRight: '1px solid var(--color-hairline)',
      overflow: 'auto',
      padding: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      paddingBottom: 12,
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "outline",
    size: "sm",
    onClick: () => go('project')
  }, "\u2190 Projects"), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '600 14px/1.2 var(--font-sans)',
      color: 'var(--color-ink)'
    }
  }, "Residential Tower")), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: '4px 0 0',
      font: '600 20px/1.2 var(--font-sans)',
      letterSpacing: '-0.5px',
      color: 'var(--color-ink)'
    }
  }, "Grammar Viewer"), /*#__PURE__*/React.createElement(Select, {
    label: "Mode",
    options: ['Insert Rules', 'Query Graph']
  }), /*#__PURE__*/React.createElement(Select, {
    label: "Graph View",
    options: ['MetaGraph', 'Instance Graph']
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Tabs, {
    tabs: ['Rules Prompt', 'Cypher Expression'],
    active: tab,
    onChange: setTab,
    style: {
      borderRadius: '10px 10px 0 0',
      borderBottom: 'none'
    }
  }), /*#__PURE__*/React.createElement(Textarea, {
    rows: 4,
    placeholder: tab === 0 ? 'Enter Design Rules in NL text' : 'MATCH (r:Rule) RETURN r',
    style: {
      borderRadius: '0 0 10px 10px',
      border: '1px solid var(--color-hairline)'
    }
  })), /*#__PURE__*/React.createElement(Button, {
    onClick: () => {
      setRunning(true);
      setTimeout(() => setRunning(false), 3000);
    }
  }, "Send Rules"), /*#__PURE__*/React.createElement(Button, {
    variant: "destructive"
  }, "Clear the Graph"), /*#__PURE__*/React.createElement(Progress, {
    value: running ? 44 : 0,
    steps: runSteps
  }), /*#__PURE__*/React.createElement(Textarea, {
    label: "Response",
    rows: 3,
    readOnly: true,
    placeholder: "Workflow response will appear here..."
  }), /*#__PURE__*/React.createElement(Textarea, {
    label: "Workflow Cypher",
    rows: 2,
    readOnly: true,
    placeholder: "Cypher used to build the graph will appear here..."
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      font: '400 11px/1.5 var(--font-mono)',
      color: 'var(--text-muted)'
    }
  }, "Using bolt://localhost:7687", /*#__PURE__*/React.createElement("br", null), "Query executed")), /*#__PURE__*/React.createElement("main", {
    className: "dg-blueprint",
    style: {
      flex: 1,
      minWidth: 0,
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement(Datascape, {
    nodes: nodes,
    edges: edges,
    selected: selected,
    onSelect: setSelected
  })), /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 360,
      flex: 'none',
      boxSizing: 'border-box',
      background: 'var(--surface-card)',
      borderLeft: '1px solid var(--color-hairline)',
      overflow: 'auto',
      padding: '18px 18px 20px'
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: '0 0 14px',
      font: '600 20px/1.2 var(--font-sans)',
      letterSpacing: '-0.5px',
      color: 'var(--color-ink)'
    }
  }, "Node details"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(Chip, {
    selected: true
  }, d.chip)), /*#__PURE__*/React.createElement(PropertiesTable, {
    rows: d.rows
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm"
  }, "Add property"))));
}
window.GraphViewerScreen = GraphViewerScreen;
window.Datascape = Datascape;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/GraphViewerScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/HomeScreen.jsx
try { (() => {
function HomeScreen({
  go
}) {
  const {
    Tile
  } = window.DS;
  const projects = [['Residential Tower', 'Last edited 1 day ago'], ['Office Complex', 'Last edited 3 days ago'], ['Bridge Design', 'Last edited 1 week ago'], ['Stadium Roof', 'Last edited 2 weeks ago'], ['Facade System', 'Last edited 3 weeks ago'], ['Pavilion Structure', 'Last edited 1 month ago'], ['Parametric Shell', 'Last edited 2 months ago'], ['Timber Frame', 'Last edited 3 months ago']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      overflow: 'auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1280,
      margin: '0 auto',
      padding: '32px 24px 48px'
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: '0 0 20px',
      font: '600 24px/1.33 var(--font-sans)',
      letterSpacing: '-0.6px',
      color: 'var(--color-ink)'
    }
  }, "Your Projects"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 20
    }
  }, projects.map(([name, edited]) => /*#__PURE__*/React.createElement(Tile, {
    key: name,
    title: name,
    description: edited,
    onClick: () => go('project')
  })))));
}
window.HomeScreen = HomeScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/HomeScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/KitShell.jsx
try { (() => {
// Shared kit chrome: header + screen router. Components come from the DS bundle.
const DS = window.DesignGrammarsDesignSystem_8522e3;
function KitHeader({
  go,
  screen
}) {
  const {
    SearchField,
    Button,
    Avatar
  } = DS;
  return /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      height: 60,
      boxSizing: 'border-box',
      padding: '0 24px',
      background: 'var(--surface-card)',
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    onClick: () => go('home'),
    style: {
      font: '600 17px/1 var(--font-sans)',
      letterSpacing: '-0.4px',
      color: 'var(--color-ink)',
      cursor: 'pointer',
      whiteSpace: 'nowrap'
    }
  }, "Design Grammars"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(SearchField, {
    placeholder: "Search projects...",
    shortcut: "\u2318K",
    style: {
      width: 320
    }
  })), screen !== 'home' && /*#__PURE__*/React.createElement(Button, {
    variant: "outline",
    size: "sm",
    onClick: () => go('home')
  }, "\u2190 All Projects"), /*#__PURE__*/React.createElement(Button, {
    size: "sm",
    onClick: () => go('project')
  }, "+ New Project"), /*#__PURE__*/React.createElement(Avatar, {
    initials: "JD"
  }));
}
function KitApp() {
  const [screen, setScreen] = React.useState(() => {
    try {
      return localStorage.getItem('dg-kit-screen') || 'login';
    } catch (e) {
      return 'login';
    }
  });
  const go = s => {
    setScreen(s);
    try {
      localStorage.setItem('dg-kit-screen', s);
    } catch (e) {}
  };
  const screens = {
    login: /*#__PURE__*/React.createElement(LoginScreen, {
      go: go
    }),
    home: /*#__PURE__*/React.createElement(HomeScreen, {
      go: go
    }),
    project: /*#__PURE__*/React.createElement(ProjectScreen, {
      go: go
    }),
    graph: /*#__PURE__*/React.createElement(GraphViewerScreen, {
      go: go
    }),
    model: /*#__PURE__*/React.createElement(ModelViewerScreen, {
      go: go
    })
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      background: 'var(--surface-canvas)'
    }
  }, screen !== 'login' && /*#__PURE__*/React.createElement(KitHeader, {
    go: go,
    screen: screen
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minHeight: 0,
      position: 'relative'
    },
    "data-screen-label": screen
  }, screens[screen]));
}
window.KitHeader = KitHeader;
window.KitApp = KitApp;
window.DS = DS;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/KitShell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/LoginScreen.jsx
try { (() => {
function LoginScreen({
  go
}) {
  const {
    Panel,
    Input,
    Button
  } = window.DS;
  const [mode, setMode] = React.useState('login');
  return /*#__PURE__*/React.createElement("div", {
    className: "dg-blueprint",
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 360
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      font: '600 24px/1.2 var(--font-sans)',
      letterSpacing: '-0.6px',
      color: 'var(--color-ink)'
    }
  }, "Design Grammars"), /*#__PURE__*/React.createElement("div", {
    style: {
      font: '500 11px/1.2 var(--font-annotation)',
      letterSpacing: '1.6px',
      textTransform: 'uppercase',
      color: 'var(--text-muted)',
      marginTop: 6
    }
  }, "System access")), /*#__PURE__*/React.createElement(Panel, {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "Email",
    placeholder: "Enter your email"
  }), mode === 'register' && /*#__PURE__*/React.createElement(Input, {
    label: "Name",
    placeholder: "Enter your name"
  }), mode === 'register' && /*#__PURE__*/React.createElement(Input, {
    label: "Surname",
    placeholder: "Enter your surname"
  }), /*#__PURE__*/React.createElement(Input, {
    label: mode === 'login' ? 'Password' : 'Create Password',
    type: "password",
    placeholder: mode === 'login' ? 'Enter your password' : 'Create a password'
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 12px/1.4 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, mode === 'login' ? 'Enter your credentials to access Design Grammars' : 'Create a new account to access Design Grammars'), /*#__PURE__*/React.createElement(Button, {
    onClick: () => go('home')
  }, mode === 'login' ? 'Login' : 'Create Account'), /*#__PURE__*/React.createElement("span", {
    onClick: () => setMode(mode === 'login' ? 'register' : 'login'),
    style: {
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--color-ink)',
      textAlign: 'center',
      cursor: 'pointer',
      textDecoration: 'underline',
      textDecorationColor: 'var(--color-hairline-strong)',
      textUnderlineOffset: 3
    }
  }, mode === 'login' ? "Don't have an account? Create new" : 'Already have an account? Login'))));
}
window.LoginScreen = LoginScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/LoginScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/ModelViewerScreen.jsx
try { (() => {
function Wireframe3D({
  showFail,
  showPass,
  showBase,
  selectedItem,
  onPick
}) {
  // Isometric ink wireframes; failing masses stroke red.
  const buildings = [{
    id: 'building1',
    x: 90,
    y: 300,
    w: 70,
    d: 34,
    h: 60,
    pass: true
  }, {
    id: 'building2',
    x: 200,
    y: 320,
    w: 60,
    d: 30,
    h: 150,
    pass: false
  }, {
    id: 'building3',
    x: 310,
    y: 300,
    w: 80,
    d: 38,
    h: 84,
    pass: true
  }, {
    id: 'building4',
    x: 430,
    y: 330,
    w: 66,
    d: 32,
    h: 52,
    pass: true
  }, {
    id: 'building5',
    x: 540,
    y: 305,
    w: 58,
    d: 28,
    h: 168,
    pass: false
  }, {
    id: 'building7',
    x: 660,
    y: 325,
    w: 74,
    d: 36,
    h: 188,
    pass: false
  }, {
    id: 'building6',
    x: 760,
    y: 300,
    w: 64,
    d: 30,
    h: 92,
    pass: true
  }];
  const box = b => {
    const {
      x,
      y,
      w,
      d,
      h
    } = b;
    const iso = (dx, dy, dz) => [x + dx - dy * 0.6, y - dz - dy * 0.32 + 0];
    const p = a => a.join(',');
    const A = iso(0, 0, 0),
      B = iso(w, 0, 0),
      C = iso(w, d, 0),
      D = iso(0, d, 0);
    const A2 = iso(0, 0, h),
      B2 = iso(w, 0, h),
      C2 = iso(w, d, h),
      D2 = iso(0, d, h);
    return `M${p(A)} L${p(B)} L${p(B2)} L${p(A2)} Z M${p(B)} L${p(C)} L${p(C2)} L${p(B2)} Z M${p(A2)} L${p(B2)} L${p(C2)} L${p(D2)} Z`;
  };
  const visible = buildings.filter(b => b.pass ? showPass : showFail);
  return /*#__PURE__*/React.createElement("svg", {
    width: "100%",
    height: "100%",
    viewBox: "0 0 880 420",
    preserveAspectRatio: "xMidYMid meet",
    style: {
      display: 'block'
    }
  }, showBase && /*#__PURE__*/React.createElement("path", {
    d: "M30 360 L 850 360 M60 390 L 880 390",
    stroke: "var(--ink-a08)",
    strokeWidth: "1",
    fill: "none"
  }), visible.map(b => {
    const sel = selectedItem === b.id;
    return /*#__PURE__*/React.createElement("g", {
      key: b.id,
      onClick: () => onPick(b.id),
      style: {
        cursor: 'pointer'
      }
    }, /*#__PURE__*/React.createElement("path", {
      d: box(b),
      fill: sel ? 'var(--color-signal-soft)' : 'transparent',
      stroke: b.pass ? 'var(--ink-a56)' : 'var(--color-signal)',
      strokeWidth: sel ? 1.5 : 1
    }), sel && /*#__PURE__*/React.createElement("g", null, /*#__PURE__*/React.createElement("path", {
      d: `M${b.x + b.w / 2} ${b.y - b.h - 14} L ${b.x + b.w / 2} ${b.y - b.h - 44} L ${b.x + b.w / 2 + 16} ${b.y - b.h - 44}`,
      stroke: "var(--ink-a32)",
      strokeWidth: "1",
      fill: "none"
    }), /*#__PURE__*/React.createElement("text", {
      x: b.x + b.w / 2 + 22,
      y: b.y - b.h - 50,
      fontFamily: "Oswald, sans-serif",
      fontSize: "13",
      letterSpacing: "1.4",
      fill: "var(--color-ink)"
    }, b.id.toUpperCase()), /*#__PURE__*/React.createElement("text", {
      x: b.x + b.w / 2 + 22,
      y: b.y - b.h - 36,
      fontFamily: "Oswald, sans-serif",
      fontSize: "10",
      letterSpacing: "1.2",
      fill: b.pass ? 'var(--color-mid-gray)' : 'var(--color-signal-ink)'
    }, b.pass ? 'PASSING' : 'HEIGHT VIOLATION')));
  }));
}
function ModelViewerScreen({
  go
}) {
  const {
    Button,
    Panel,
    KVRow,
    StatBlock,
    Collapsible,
    CollapsibleItem,
    CodeBlock,
    Checkbox,
    Slider,
    SearchField,
    RunTile,
    Badge,
    Dialog,
    Input
  } = window.DS;
  const [failOpen, setFailOpen] = React.useState(true);
  const [passOpen, setPassOpen] = React.useState(false);
  const [checks, setChecks] = React.useState({
    fail: true,
    pass: true,
    base: true
  });
  const [alphas, setAlphas] = React.useState({
    fail: 80,
    pass: 60,
    base: 30
  });
  const [run, setRun] = React.useState('height_max');
  const [picked, setPicked] = React.useState('building2');
  const [speckle, setSpeckle] = React.useState(false);
  const runs = [['height_max', 'Mar 15, 2026', 'Constraint'], ['setback_front', 'Mar 15, 2026', 'Requirement'], ['floor_area', 'Mar 14, 2026', 'Constraint'], ['window_ratio', 'Mar 14, 2026', 'Guideline']];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 340,
      flex: 'none',
      boxSizing: 'border-box',
      background: 'var(--surface-sidebar)',
      borderRight: '1px solid var(--color-hairline)',
      overflow: 'auto',
      padding: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
      paddingBottom: 12,
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "outline",
    size: "sm",
    onClick: () => go('project')
  }, "\u2190 Project"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm",
    onClick: () => setSpeckle(true)
  }, "Speckle connector")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      font: '600 20px/1.2 var(--font-sans)',
      letterSpacing: '-0.5px',
      color: 'var(--color-ink)'
    }
  }, "Model Viewer"), /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, "Residential Tower")), /*#__PURE__*/React.createElement(Panel, {
    title: "Validation run",
    style: {
      padding: 16
    }
  }, /*#__PURE__*/React.createElement(KVRow, {
    label: "Run Id",
    value: "abc12345-6789-abcd-ef01"
  }), /*#__PURE__*/React.createElement(KVRow, {
    label: "Date Created",
    value: "3/15/2026, 10:30 AM"
  }), /*#__PURE__*/React.createElement(KVRow, {
    label: "Base Model",
    value: "main"
  }), /*#__PURE__*/React.createElement(KVRow, {
    label: "Validation Model",
    value: "dg-validation"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 28,
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(StatBlock, {
    label: "Failing",
    value: "3",
    signal: true
  }), /*#__PURE__*/React.createElement(StatBlock, {
    label: "Passing",
    value: "12"
  }))), /*#__PURE__*/React.createElement(Collapsible, {
    label: "Failing items",
    count: 3,
    signal: true,
    open: failOpen,
    onToggle: () => setFailOpen(!failOpen)
  }, /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building2): h(84)",
    secondary: "id: building2",
    selected: picked === 'building2',
    onClick: () => setPicked('building2')
  }), /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building5): h(92)",
    secondary: "id: building5",
    selected: picked === 'building5',
    onClick: () => setPicked('building5')
  }), /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building7): h(103)",
    secondary: "id: building7",
    selected: picked === 'building7',
    onClick: () => setPicked('building7')
  })), /*#__PURE__*/React.createElement(Collapsible, {
    label: "Passing items",
    count: 12,
    open: passOpen,
    onToggle: () => setPassOpen(!passOpen)
  }, /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building1): h(32)",
    secondary: "id: building1",
    selected: picked === 'building1',
    onClick: () => setPicked('building1')
  }), /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building3): h(45)",
    secondary: "id: building3",
    selected: picked === 'building3',
    onClick: () => setPicked('building3')
  }), /*#__PURE__*/React.createElement(CollapsibleItem, {
    primary: "b(building4): h(28)",
    secondary: "id: building4",
    selected: picked === 'building4',
    onClick: () => setPicked('building4')
  })), /*#__PURE__*/React.createElement(Panel, {
    title: "Rule",
    style: {
      padding: 16
    }
  }, /*#__PURE__*/React.createElement(KVRow, {
    label: "Rule_Id",
    value: "height_max"
  }), /*#__PURE__*/React.createElement(KVRow, {
    label: "Description",
    value: "Maximum building height must not exceed 30 meters",
    mono: false
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement(CodeBlock, {
    label: "SWRL Expression"
  }, "Building(?b) \u2227 hasHeight(?b, ?h) \u2227 swrlb:greaterThan(?h, 30) \u2192 violation(?b)")))), /*#__PURE__*/React.createElement("main", {
    style: {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      flexWrap: 'wrap',
      padding: '10px 16px',
      background: 'var(--surface-card)',
      borderBottom: '1px solid var(--color-hairline)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(Checkbox, {
    label: "Failing",
    checked: checks.fail,
    onChange: v => setChecks({
      ...checks,
      fail: v
    })
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Passing",
    checked: checks.pass,
    onChange: v => setChecks({
      ...checks,
      pass: v
    })
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Base model",
    checked: checks.base,
    onChange: v => setChecks({
      ...checks,
      base: v
    })
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 1,
      height: 20,
      background: 'var(--color-hairline)'
    }
  }), /*#__PURE__*/React.createElement(Slider, {
    label: "Fail \u03B1",
    value: alphas.fail,
    onChange: v => setAlphas({
      ...alphas,
      fail: v
    }),
    style: {
      width: 150
    }
  }), /*#__PURE__*/React.createElement(Slider, {
    label: "Pass \u03B1",
    value: alphas.pass,
    onChange: v => setAlphas({
      ...alphas,
      pass: v
    }),
    style: {
      width: 150
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 1,
      height: 20,
      background: 'var(--color-hairline)'
    }
  }), /*#__PURE__*/React.createElement(SearchField, {
    placeholder: "Select by Id...",
    style: {
      width: 170,
      height: 30
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      marginLeft: 'auto'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "outline",
    size: "sm"
  }, "Isolate"), /*#__PURE__*/React.createElement(Button, {
    variant: "outline",
    size: "sm"
  }, "Hide"))), /*#__PURE__*/React.createElement("div", {
    className: "dg-blueprint",
    style: {
      flex: 1,
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement(Wireframe3D, {
    showFail: checks.fail,
    showPass: checks.pass,
    showBase: checks.base,
    selectedItem: picked,
    onPick: setPicked
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface-card)',
      borderTop: '1px solid var(--color-hairline)',
      padding: '10px 16px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '500 11px/1.33 var(--font-sans)',
      letterSpacing: '0.6px',
      textTransform: 'uppercase',
      color: 'var(--text-muted)'
    }
  }, "Validation runs"), /*#__PURE__*/React.createElement(Badge, {
    variant: "outline"
  }, "4")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      overflowX: 'auto'
    }
  }, runs.map(([id, date, kind]) => /*#__PURE__*/React.createElement(RunTile, {
    key: id,
    ruleId: id,
    date: date,
    kind: kind,
    active: run === id,
    onSelect: () => setRun(id),
    onDelete: () => {}
  })))), speckle && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'rgba(10,10,10,0.12)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(Dialog, {
    title: "Speckle connector",
    onClose: () => setSpeckle(false),
    footer: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "sm"
    }, "Reload"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      onClick: () => setSpeckle(false)
    }, "Save Speckle Link"))
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, "Load Speckle project mapping."), /*#__PURE__*/React.createElement(Input, {
    label: "Speckle Project Id or URL",
    placeholder: "e.g. project-id or full URL",
    mono: true
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Base Model Id or URL",
    placeholder: "e.g. model-id or full URL",
    mono: true
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Base Model Name",
    placeholder: "Optional display name"
  }), /*#__PURE__*/React.createElement(Input, {
    label: "Validation Model Id or URL",
    placeholder: "Optional (auto-created if blank)",
    mono: true
  })))));
}
window.ModelViewerScreen = ModelViewerScreen;
window.Wireframe3D = Wireframe3D;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/ModelViewerScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/design-grammars/ProjectScreen.jsx
try { (() => {
function ProjectScreen({
  go
}) {
  const {
    Tile
  } = window.DS;
  const graphThumb = /*#__PURE__*/React.createElement("svg", {
    width: "120",
    height: "70",
    viewBox: "0 0 120 70"
  }, /*#__PURE__*/React.createElement("g", {
    fill: "none",
    stroke: "var(--ink-a16)",
    strokeWidth: "1"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M20 55 C 40 15, 70 15, 90 35"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M20 55 C 50 35, 80 45, 104 22"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M46 60 C 66 30, 86 30, 104 22"
  })), /*#__PURE__*/React.createElement("circle", {
    cx: "20",
    cy: "55",
    r: "3",
    fill: "var(--color-ink)"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "46",
    cy: "60",
    r: "2.5",
    fill: "var(--color-ink)"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "104",
    cy: "22",
    r: "3",
    fill: "var(--color-ink)"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "90",
    cy: "35",
    r: "4",
    fill: "var(--color-signal)"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "90",
    cy: "35",
    r: "9",
    fill: "none",
    stroke: "var(--color-signal-mid)",
    strokeWidth: "1"
  }));
  const modelThumb = /*#__PURE__*/React.createElement("svg", {
    width: "120",
    height: "70",
    viewBox: "0 0 120 70"
  }, /*#__PURE__*/React.createElement("g", {
    fill: "none",
    stroke: "var(--ink-a32)",
    strokeWidth: "1"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M30 58 L30 30 L48 22 L48 50 Z M30 30 L48 22 M30 58 L48 50"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M56 58 L56 18 L74 10 L74 50 Z"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M82 58 L82 38 L100 30 L100 50 Z"
  })), /*#__PURE__*/React.createElement("path", {
    d: "M56 18 L74 10",
    stroke: "var(--color-signal)",
    strokeWidth: "1.5",
    fill: "none"
  }));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      overflow: 'auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1280,
      margin: '0 auto',
      padding: '32px 24px 48px'
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      font: '600 30px/1.2 var(--font-sans)',
      letterSpacing: '-0.75px',
      color: 'var(--color-ink)'
    }
  }, "Residential Tower"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      alignItems: 'center',
      margin: '8px 0 28px',
      font: '400 13px/1.4 var(--font-sans)',
      color: 'var(--text-muted)'
    }
  }, /*#__PURE__*/React.createElement("span", null, "Created Jan 15, 2026"), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-hairline-strong)'
    }
  }, "\xB7"), /*#__PURE__*/React.createElement("span", null, "Last edited 1 day ago")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, minmax(0, 420px))',
      gap: 20
    }
  }, /*#__PURE__*/React.createElement(Tile, {
    title: "Grammar Viewer",
    description: "View and manage design rules, ontology graph, and Cypher queries",
    thumbnail: graphThumb,
    onClick: () => go('graph')
  }), /*#__PURE__*/React.createElement(Tile, {
    title: "Model Viewer",
    description: "Visualize and inspect 3D models from Speckle streams",
    thumbnail: modelThumb,
    onClick: () => go('model')
  }))));
}
window.ProjectScreen = ProjectScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/design-grammars/ProjectScreen.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Avatar = __ds_scope.Avatar;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Callout = __ds_scope.Callout;

__ds_ns.Chip = __ds_scope.Chip;

__ds_ns.CodeBlock = __ds_scope.CodeBlock;

__ds_ns.KVRow = __ds_scope.KVRow;

__ds_ns.StatBlock = __ds_scope.StatBlock;

__ds_ns.Progress = __ds_scope.Progress;

__ds_ns.PropertiesTable = __ds_scope.PropertiesTable;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.SearchField = __ds_scope.SearchField;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Slider = __ds_scope.Slider;

__ds_ns.Textarea = __ds_scope.Textarea;

__ds_ns.Collapsible = __ds_scope.Collapsible;

__ds_ns.CollapsibleItem = __ds_scope.CollapsibleItem;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.RunTile = __ds_scope.RunTile;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Tile = __ds_scope.Tile;

})();

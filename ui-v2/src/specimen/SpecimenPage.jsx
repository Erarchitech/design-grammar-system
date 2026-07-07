import React from "react";
import {
  Button,
  Checkbox,
  Input,
  SearchField,
  Select,
  Slider,
  Textarea,
  Avatar,
  Badge,
  Callout,
  Chip,
  CodeBlock,
  KVRow,
  StatBlock,
  Progress,
  PropertiesTable,
  Collapsible,
  CollapsibleItem,
  Dialog,
  Panel,
  RunTile,
  Tabs,
  Tile
} from "../components/index.js";

// Dev-only specimen page (D-09) — proves DSYS-01..03 in the browser.
// Organised like the _ds guideline cards: Colors / Type / Foundations / Components.

const SURFACES = [
  ["--color-canvas", "canvas #f5f5f5"],
  ["--color-surface-alt", "sidebar #fafafa"],
  ["--color-paper", "card #ffffff"],
  ["--surface-input", "input fill"]
];
const INKS = [
  ["--color-ink", "ink #0a0a0a"],
  ["--color-ink-soft", "ink soft #171717"],
  ["--color-mid-gray", "mid gray #737373"],
  ["--color-hairline", "hairline #e5e5e5"],
  ["--color-hairline-strong", "hairline strong #d4d4d4"]
];
const ALPHAS = [
  ["--ink-a04", "a04"],
  ["--ink-a08", "a08"],
  ["--ink-a16", "a16"],
  ["--ink-a32", "a32"],
  ["--ink-a56", "a56"]
];
const SIGNALS = [
  ["--color-signal", "signal #e7000b"],
  ["--color-signal-ink", "signal ink #b8000e"],
  ["--color-signal-soft", "signal soft 8%"],
  ["--color-signal-mid", "signal mid 32%"]
];

function Swatch({ token, label }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, width: 108 }}>
      <div
        style={{
          height: 48,
          borderRadius: "var(--radius-nested)",
          background: `var(${token})`,
          border: "1px solid var(--color-hairline)"
        }}
      />
      <span style={{ font: "400 11px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>{label}</span>
    </div>
  );
}

function Group({ title, children }) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h2
        style={{
          margin: 0,
          font: "600 24px/1.33 var(--font-sans)",
          letterSpacing: "var(--tracking-heading-sm)",
          borderBottom: "1px solid var(--color-hairline)",
          paddingBottom: 10
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function Card({ title, children, className, style }) {
  return (
    <div
      className={className}
      style={{
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-cards)",
        background: "var(--surface-card)",
        boxShadow: "var(--shadow-subtle)",
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        ...style
      }}
    >
      <span
        style={{
          font: "500 12px/1.33 var(--font-sans)",
          letterSpacing: "var(--tracking-caption)",
          textTransform: "uppercase",
          color: "var(--text-muted)"
        }}
      >
        {title}
      </span>
      {children}
    </div>
  );
}

export default function SpecimenPage() {
  const [tab, setTab] = React.useState(0);
  const [checked, setChecked] = React.useState(true);
  const [slider, setSlider] = React.useState(64);
  const [openGroup, setOpenGroup] = React.useState(true);
  const [chipSel, setChipSel] = React.useState(true);

  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-canvas)" }}>
      <div
        style={{
          maxWidth: "var(--page-max-width)",
          margin: "0 auto",
          padding: "48px 24px 96px",
          display: "flex",
          flexDirection: "column",
          gap: 48
        }}
      >
        <header style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
            Design system specimen · dev only
          </div>
          <h1
            style={{
              margin: 0,
              font: "600 var(--text-display)/var(--leading-display) var(--font-sans)",
              letterSpacing: "var(--tracking-display)"
            }}
          >
            Design Grammars.
          </h1>
          <span style={{ font: "400 14px/1.43 var(--font-mono)", color: "var(--text-muted)" }}>
            v2 tokens · Geist / Geist Mono / Oswald · 23 primitives
          </span>
        </header>

        <Group title="Colors">
          <Card title="Surface stack — canvas → sidebar → card">
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {SURFACES.map(([t, l]) => (
                <Swatch key={t} token={t} label={l} />
              ))}
            </div>
          </Card>
          <Card title="Ink scale">
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {INKS.map(([t, l]) => (
                <Swatch key={t} token={t} label={l} />
              ))}
            </div>
          </Card>
          <Card title="Ink alphas — datascape strokes">
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {ALPHAS.map(([t, l]) => (
                <Swatch key={t} token={t} label={l} />
              ))}
            </div>
          </Card>
          <Card title="Signal red — the only chromatic hue (selection / failure / destructive)">
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {SIGNALS.map(([t, l]) => (
                <Swatch key={t} token={t} label={l} />
              ))}
            </div>
          </Card>
        </Group>

        <Group title="Type">
          <Card title="Display & headings — Geist 600, tracking tightens with size">
            <div style={{ font: "600 var(--text-display)/var(--leading-display) var(--font-sans)", letterSpacing: "var(--tracking-display)" }}>
              Encode design intent
            </div>
            <div style={{ font: "600 var(--text-heading)/var(--leading-heading) var(--font-sans)", letterSpacing: "var(--tracking-heading)" }}>
              Validation run complete
            </div>
            <div style={{ font: "600 var(--text-heading-sm)/var(--leading-heading-sm) var(--font-sans)", letterSpacing: "var(--tracking-heading-sm)" }}>
              Node details
            </div>
          </Card>
          <Card title="Body & caption — Geist 14/400">
            <p style={{ margin: 0, font: "400 var(--text-body)/var(--leading-body) var(--font-sans)" }}>
              Designers write design rules in natural language. An LLM parses them into SWRL atoms that
              live in the Neo4j metagraph and validate 3D building models.
            </p>
            <span style={{ font: "400 var(--text-caption)/var(--leading-caption) var(--font-sans)", letterSpacing: "var(--tracking-caption)", color: "var(--text-muted)" }}>
              Enter your credentials to access Design Grammars
            </span>
          </Card>
          <Card title="Mono data — ids, cypher, SWRL, verbatim values">
            <span style={{ font: "400 13px/1.6 var(--font-mono)" }}>
              "R_height_max" · bolt://localhost:7687 · b(building2): h(84)
            </span>
          </Card>
          <Card title="Annotation caps — the divergence caption voice (Oswald)">
            <span className="dg-annotation">System initiated</span>
            <span className="dg-annotation dg-annotation--muted">Divergence detected · 0.6741</span>
          </Card>
        </Group>

        <Group title="Foundations">
          <Card title=".dg-blueprint — faint 24px drafting grid" className="dg-blueprint" style={{ background: undefined, minHeight: 120 }} />
          <div className="dg-blueprint" style={{ borderRadius: "var(--radius-cards)", border: "1px solid var(--color-hairline)", padding: 32, display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
            <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 20, width: 260 }}>
              <span style={{ font: "500 13px/1.4 var(--font-sans)" }}>.dg-frost panel</span>
              <p style={{ margin: "6px 0 0", font: "400 12px/1.5 var(--font-sans)", color: "var(--text-muted)" }}>
                78% white + 14px backdrop blur + hairline, floating over the datascape.
              </p>
            </div>
            <Callout marker date="2049 · 04 · 12" title="Divergence" subtitle="Sector 7" detail="Signal acquired" signal />
            <Callout marker title="Baseline" detail="Nominal drift" />
          </div>
          <Card title="Radii — 18px interactive pills, 24px containers, 10px nested, 6px small">
            <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
              <Button>18px pill</Button>
              <div style={{ border: "1px solid var(--color-hairline-strong)", borderRadius: "var(--radius-cards)", padding: "16px 22px", font: "400 12px/1 var(--font-mono)" }}>24px card</div>
              <div style={{ border: "1px solid var(--color-hairline-strong)", borderRadius: "var(--radius-nested)", padding: "10px 16px", font: "400 12px/1 var(--font-mono)" }}>10px nested</div>
              <div style={{ border: "1px solid var(--color-hairline-strong)", borderRadius: "var(--radius-small)", padding: "6px 10px", font: "400 12px/1 var(--font-mono)" }}>6px small</div>
            </div>
          </Card>
        </Group>

        <Group title="Components — Forms">
          <Card title="Buttons — primary / secondary / outline / destructive · sm / md / lg · selected / disabled">
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <Button>Send Rules</Button>
              <Button variant="secondary">Cancel</Button>
              <Button variant="outline">← Back</Button>
              <Button variant="destructive">Clear the Graph</Button>
              <Button size="sm" variant="outline">Small</Button>
              <Button size="lg">Login / Register</Button>
              <Button selected>Selected</Button>
              <Button disabled>Disabled</Button>
            </div>
          </Card>
          <Card title="Inputs, search, select">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
              <Input label="Email" placeholder="name@studio.io" />
              <Input label="Rule id" mono placeholder="R_height_max" />
              <Input label="Password" type="password" invalid placeholder="••••••••" hint="Minimum 8 characters" />
              <SearchField placeholder="Search nodes..." shortcut="/" />
              <Select label="Mode" options={["Insert Rules", "Query Graph"]} />
            </div>
          </Card>
          <Card title="Textarea, checkbox, slider">
            <Textarea label="Rules Prompt" rows={3} placeholder="Enter Design Rules in NL text" />
            <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
              <Checkbox label="Show failing only" checked={checked} onChange={setChecked} />
              <Checkbox label="Unchecked" checked={false} onChange={() => {}} />
              <Slider label="Opacity" value={slider} onChange={setSlider} style={{ width: 240 }} />
            </div>
          </Card>
        </Group>

        <Group title="Components — Display">
          <Card title="Badges, chips, avatar">
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <Badge variant="solid">Metagraph</Badge>
              <Badge>Ontograph</Badge>
              <Badge variant="outline">ValidGraph</Badge>
              <Badge variant="signal">3 failing</Badge>
              <Chip selected={chipSel} onRemove={() => setChipSel(false)}>Rule</Chip>
              <Chip>Class</Chip>
              <Avatar initials="EK" />
            </div>
          </Card>
          <Card title="Stats, KV rows, progress">
            <div style={{ display: "flex", gap: 40, flexWrap: "wrap" }}>
              <StatBlock label="Entities" value="128" />
              <StatBlock label="Failing" value="12" signal />
            </div>
            <div style={{ maxWidth: 360 }}>
              <KVRow label="Run id" value="RUN_2026_07_07_001" />
              <KVRow label="Status" value="ValidStatus: [true, false]" />
              <KVRow label="Project" value='"Nordhavn Block C"' />
            </div>
            <Progress
              value={44}
              steps={[
                { label: "Send rules", time: "1.2s" },
                { label: "LLM parse", time: "3.4s" },
                { label: "Write graph", active: true },
                { label: "Annotate properties" },
                { label: "Reload graph" }
              ]}
            />
          </Card>
          <Card title="Properties table, code block">
            <PropertiesTable
              rows={[
                { key: "<id>", value: "42" },
                { key: "Rule_Id", value: '"R_height_max"' },
                { key: "graph", value: '"Metagraph"' },
                { key: "SWRL", value: '"Building(?b) ^ hasHeight(?b, ?h) ^ swrlb:greaterThan(?h, 45) -> Violation(?b)"' }
              ]}
            />
            <CodeBlock label="RULE — SWRL">
              {"Building(?b) ^ hasHeight(?b, ?h) ^\nswrlb:greaterThan(?h, 45) -> Violation(?b)"}
            </CodeBlock>
          </Card>
        </Group>

        <Group title="Components — Surfaces">
          <Card title="Tabs, collapsible, panel">
            <Tabs tabs={["Rules Prompt", "Cypher Expression"]} active={tab} onChange={setTab} style={{ maxWidth: 360 }} />
            <div style={{ maxWidth: 360, display: "flex", flexDirection: "column", gap: 10 }}>
              <Collapsible label="Failing" count={2} signal open={openGroup} onToggle={() => setOpenGroup(!openGroup)}>
                <CollapsibleItem primary="building_02" secondary="h = 84.0 > 45.0" selected />
                <CollapsibleItem primary="building_07" secondary="h = 51.2 > 45.0" />
              </Collapsible>
              <Collapsible label="Passing" count={9} open={false} onToggle={() => {}} />
            </div>
            <Panel title="Validation run" style={{ maxWidth: 360 }}>
              <KVRow label="Rule" value='"R_height_max"' />
              <KVRow label="Executed" value="2026-07-07 09:14" />
            </Panel>
          </Card>
          <Card title="Tiles, run strip, dialog" className="dg-blueprint">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 280px))", gap: 16 }}>
              <Tile title="Nordhavn Block C" description="12 rules · 3 runs" onClick={() => {}} />
              <Tile title="Residential Tower" description="8 rules · 1 run" onClick={() => {}} />
            </div>
            <div style={{ display: "flex", gap: 12, overflowX: "auto", padding: "4px 0" }}>
              <RunTile ruleId="R_height_max" date="07 Jul 2026" active onSelect={() => {}} onDelete={() => {}} />
              <RunTile ruleId="R_dist_min_6" date="05 Jul 2026" onSelect={() => {}} />
              <RunTile ruleId="R_floors_max_20" date="02 Jul 2026" onSelect={() => {}} />
            </div>
            <Dialog
              title="Speckle connector"
              onClose={() => {}}
              footer={
                <>
                  <Button variant="secondary">Cancel</Button>
                  <Button>Connect</Button>
                </>
              }
            >
              <Input label="Server url" mono defaultValue="http://localhost:8090" />
              <Input label="Token" type="password" placeholder="••••••••" />
            </Dialog>
          </Card>
        </Group>
      </div>
    </div>
  );
}

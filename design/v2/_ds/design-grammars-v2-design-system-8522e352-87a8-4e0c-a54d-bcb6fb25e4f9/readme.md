# Design Grammars — Design System

**Light, clinical blueprint on frosted paper.** Design Grammars is a graph-native tool for computational architecture: designers write design rules in natural language, an LLM parses them into SWRL/Cypher, and the rules live in a Neo4j metagraph that validates 3D models (via Speckle). The product family is a **datascape** — dashboards and viewers wrapped around dense graph visualizations.

## Sources

- **Codebase:** `graph-viewer/` (mounted read-only). The authoritative interface definitions are the Penpot-style JSON files in `graph-viewer/interface/*.pen`: `home`, `Project`, `GraphViewer`, `ModelViewer`, `RegisterForm`, `MetagraphOntology`. A running prototype lives in `graph-viewer/index.html` and `graph-viewer/model-viewer/` (dark-themed; superseded by this light system).
- **Style reference:** `uploads/DESIGN (1).md` — the token source of truth (colors, type scale, radii, shadows, component recipes).
- **Visual inspiration:** `uploads/*.webp|jpg|png` — Boris Müller's *Poetry on the Road* radial graphs (black arcs, red nodes, white field) and Westworld S3 "Divergence" graphics (particle ring, hexagon marker, leader-line callouts, condensed uppercase captions).

## The system in one paragraph

Achromatic by default: warm-white paper, ink text, hairline rules. **Color is absence, not expression** — exactly one chromatic hue exists, Signal Red `#e7000b`, and it is reserved for **selection only** (the selected node, chip, or row). Failure, destructive actions, and emphasis are all achromatic — distinguished by weight/fill (solid ink vs. outline), never by hue. Interactive elements are perfect pills (18px radius on ~36px heights); containers are 24px. Elevation is whisper-quiet. Data visualization is ink-on-paper: graph edges as translucent black arcs, nodes as dots that turn red only when selected or failing. Panels frost over the datascape with backdrop blur. Annotations use the divergence-callout grammar: condensed uppercase caption, hairline leader line, hexagon marker.

## Products / surfaces

One product, five screens (from `interface/*.pen`):
1. **Home** — project tile grid, header with search / New Project / avatar.
2. **Project** — project meta + two action tiles (Grammar Viewer, Model Viewer).
3. **Grammar Viewer** — left rules sidebar (mode select, prompt tabs, textarea, send/clear, progress steps, response, workflow cypher), center graph datascape, right node-details panel (label chip, properties table, add property).
4. **Model Viewer** — left validation-run sidebar (KV rows, failing/passing collapsibles, rule panel with SWRL code), 3D viewport with graphics settings toolbar (checkbox filters, color swatches, opacity sliders, select-by-id), bottom validation-runs tile strip, Speckle connector dialog.
5. **Login / Register** — centered form card.

## CONTENT FUNDAMENTALS

- **Voice:** terse, technical, system-log flavored. Sentences are short imperatives or noun phrases: "Send Rules", "Clear the Graph", "Select by Id…", "Workflow response will appear here…". No exclamation marks, no marketing warmth, no emoji.
- **Casing:** Title Case for buttons and screen names ("Send Rules", "Model Viewer"); sentence case for hints and body ("Enter your credentials to access Design Grammars"); ALL-CAPS reserved for panel titles ("VALIDATION RUN", "RULE") and divergence-style annotations ("SYSTEM INITIATED").
- **Data is verbatim:** ids, cypher, SWRL, timestamps render in mono exactly as stored — `"R_height_max"`, `bolt://localhost:7687`, `b(building2): h(84)`. Quotes around string values are kept.
- **Address:** the system speaks *to* the user in second person only in hints; mostly it narrates itself ("Query executed", "System initiated").
- **Labels over prose:** key–value pairs everywhere; descriptions max one sentence.

## VISUAL FOUNDATIONS

- **Color:** three-tone surface stack — canvas `#f5f5f5` → sidebar `#fafafa` → card `#ffffff`; ink `#0a0a0a`, muted `#737373`, hairline `#e5e5e5`. Signal Red `#e7000b` ONLY for selection/highlight/fail/destructive. Passing = ink; base geometry = mid-gray. Ink alpha steps (`--ink-a04…a56`) drive graph edges and grid lines.
- **Type:** Geist everywhere (body 14/400, headings 24–48/600, tracking tightens to −0.05em at display); Geist Mono for data values, code, ids; Oswald (substitute for a DIN-condensed) for uppercase annotation captions, tracked +1.2px.
- **Spacing:** 4px base, compact density; card padding 20px, element gap 8px; page max 1280px.
- **Radii:** 18px on all interactive elements (pill geometry), 24px on cards, 10px nested, 6px small. Never other values.
- **Backgrounds:** frosted paper — flat `#f5f5f5` or the `.dg-blueprint` faint 24px drafting grid. No photography, no gradients, no illustration. The datascape itself (ink arcs, dots) is the only imagery.
- **Elevation:** whisper-quiet stacked hairline shadow (`--shadow-subtle`); filled buttons have none. Panels over datascape use `.dg-frost` (78% white + 14px backdrop blur + hairline border).
- **Animation:** clinical — opacity fades and ≤4px translations, 120–200ms, `cubic-bezier(.2,0,0,1)`. No bounce, no springs. Datascape nodes may pulse a red halo on selection.
- **Hover:** one tonal step (paper→canvas, ink→ink-soft) or hairline darkens; never color. **Press:** background darkens one more step; no scale.
- **Borders:** 1px hairlines carry the entire structure — cards always have them; tables use bottom hairlines only.
- **Transparency/blur:** only where a panel floats above the datascape (frost). Never on canvas-level surfaces.
- **Imagery color vibe:** black-and-white, grainy particle textures; red appears only as data highlight.
- **Selection grammar:** red 1px ring + `--color-signal-soft` wash; in datascapes, a red dot with `--color-signal-mid` halo and a divergence callout.

## ICONOGRAPHY

- **Icon set:** Lucide, thin geometric strokes (the `.pen` files reference `iconFontFamily: "lucide"` — chevron-down, search, plus, arrow-left, eye, eye-off, trash). Load from CDN (`lucide@latest` UMD) or inline the specific SVGs; stroke 1.5–2px, color ink or mid-gray, red only on destructive.
- **Unicode as icons:** the source uses `←` for back and `✎` for edit affordances — keep this; it fits the drafting voice.
- **No emoji, ever.**
- **Brand marks:** the sources contain **no logo**. Render "Design Grammars" as plain type (Geist 600 or annotation caps) wherever a mark would go. The hexagon divergence marker (hairline hexagon + center dot) is a recurring *motif*, not a logo.
- **Node color exception:** the legacy prototype colored graph nodes by class (blue/orange/green/purple); this system replaces that with achromatic dots sized/stroked by class, red only for selection — documented divergence from the legacy dark UI.

## Intentional additions

- **Callout** (divergence annotation: hexagon marker + leader line + condensed caption block) — from the brand references; not in the `.pen` inventory but the signature datascape labeling device.

## Index

- `styles.css` — global entry; imports `tokens/{fonts,colors,typography,spacing,effects,base}.css`
- `guidelines/` — foundation specimen cards (Design System tab)
- `assets/` — product reference images from the codebase (`metagraph-ontology.png`, `interface-reference.png`)
- `components/forms/` — Button, Input, Textarea, Select, SearchField, Checkbox, Slider
- `components/display/` — Badge, Chip, Avatar, KVRow, PropertiesTable, Progress, CodeBlock, Callout
- `components/surfaces/` — Panel, Tabs, Collapsible, Tile, RunTile, Dialog
- `ui_kits/design-grammars/` — interactive click-through of the five screens
- `SKILL.md` — agent skill entry point

## Caveats

- **Fonts:** Geist/Geist Mono load from Google Fonts (no binaries shipped). Oswald substitutes the condensed annotation face (Westworld-style DIN/Tungsten) — supply licensed binaries to replace.
- The legacy prototype (`graph-viewer/index.html`) is dark; this system is the intended light reskin per `DESIGN (1).md` and the user brief. Structure follows the `.pen` files; skin follows the light tokens.

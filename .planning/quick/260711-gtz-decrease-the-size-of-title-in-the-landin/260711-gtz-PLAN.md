---
phase: quick-260711-gtz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ui-v2/src/landing/landing.css
autonomous: false
requirements:
  - QUICK-260711-gtz
must_haves:
  truths:
    - "The landing hero title 'Design Grammars.' and its subline render fully inside the particle ring on the landing page across common desktop widths (no overflow past the ring)."
  artifacts:
    - ui-v2/src/landing/landing.css
  key_links:
    - "heroMetrics() in ui-v2/src/landing/landingEngine.js reads .dgl-hero-l1/.dgl-hero-l2 computed font-size via getComputedStyle — the CSS change automatically drives both the DOM title and the particle-sampling text, so no JS edit is required."
---

<objective>
Decrease the landing hero title font size so "Design Grammars." and its subline fit inside the particle ring.

Purpose: The title currently scales with viewport width (`clamp(32px, 5.2vw, 76px)` on `.dgl-hero-l1`), while the particle ring radius is sized by the smaller viewport dimension (`R = Math.min(vw, vh) * 0.365` in landingEngine.js). On wide/short windows the title outgrows the ring and its ends spill past the circle. Reducing the size and tracking `min(vw, vh)` (vmin) instead of `vw` makes the title fit the ring across aspect ratios.

Output: Updated font-size clamps on `.dgl-hero-l1` and `.dgl-hero-l2` in ui-v2/src/landing/landing.css.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

# The title is a DOM element; heroMetrics() reads its computed font-size and
# the particle sampler reuses that size. Changing CSS is sufficient — the JS
# needs no change. Reference files for the executor:
@ui-v2/src/landing/landing.css
@ui-v2/src/landing/landingEngine.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: Shrink hero title clamps and switch vw to vmin in landing.css</name>
  <files>ui-v2/src/landing/landing.css</files>
  <action>
In ui-v2/src/landing/landing.css, edit the two hero-title rules so the title fits the particle ring.

For `.dgl-hero-l1` (the "Design Grammars." line), change the `font-size` from `clamp(32px, 5.2vw, 76px)` to `clamp(26px, 4.6vmin, 58px)`. Rationale: the ring radius in landingEngine.js is driven by `Math.min(vw, vh)`, so scaling the title with `vmin` (the smaller viewport dimension) keeps the title proportional to the ring on every aspect ratio, and the lower cap (58px vs 76px) stops the title spilling past the circle on wide screens.

For `.dgl-hero-l2` (the "Encode your design intent." subline), change the `font-size` from `clamp(15px, 2.2vw, 32px)` to `clamp(13px, 1.95vmin, 25px)` to preserve the existing ~0.43 subline-to-title ratio and stay inside the ring.

Change only these two `font-size` declarations. Do not touch line-height, letter-spacing, white-space, font-family, positioning, or any other property, and do not edit landingEngine.js — heroMetrics() reads the new computed sizes via getComputedStyle, so the particle text follows automatically.

Starting values are intentionally conservative; the human-verify checkpoint (Task 2) confirms the fit and can nudge the vmin coefficient / cap up if the title looks too small or down if it still overflows.
  </action>
  <verify>
    <automated>grep -n "4.6vmin" ui-v2/src/landing/landing.css && grep -n "1.95vmin" ui-v2/src/landing/landing.css</automated>
  </verify>
  <done>`.dgl-hero-l1` uses `clamp(26px, 4.6vmin, 58px)` and `.dgl-hero-l2` uses `clamp(13px, 1.95vmin, 25px)`; no other properties in landing.css changed; landingEngine.js untouched.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Reduced the landing hero title font size and switched its fluid scaling from viewport-width (vw) to the smaller viewport dimension (vmin) so the title tracks the particle ring.</what-built>
  <how-to-verify>
    1. Start the V2 UI dev server: `npm --prefix ui-v2 run dev`
    2. Open the printed localhost URL (typically http://localhost:5173) and view the landing page.
    3. Watch the hero title "Design Grammars." materialise from the particle ring, then confirm both the title and the "Encode your design intent." subline sit fully inside the ring — neither line's ends should cross or spill past the circle of particles.
    4. Resize the browser wider and shorter (drag the window to a wide, short shape) and confirm the title still stays inside the ring.
    5. If the title now looks too small, increase the `.dgl-hero-l1` vmin coefficient / max cap slightly (e.g. `clamp(28px, 5vmin, 64px)`) and re-check. If it still overflows, decrease them.
  </how-to-verify>
  <resume-signal>Type "approved" once the title fits inside the ring, or describe what still overflows / looks off.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundary is introduced. This change edits two static CSS `font-size` declarations; it processes no untrusted input, adds no dependencies, and touches no auth, network, or data path.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Tampering | ui-v2/src/landing/landing.css | low | accept | Presentation-only CSS; no runtime input or state affected. No mitigation required. |
</threat_model>

<verification>
- `grep` confirms both new clamp values are present in landing.css.
- Human-verify checkpoint confirms the title and subline fit inside the particle ring on the landing page.
</verification>

<success_criteria>
- `.dgl-hero-l1` and `.dgl-hero-l2` font-sizes reduced and vmin-based in landing.css.
- Landing hero title and subline render fully inside the particle ring (human-confirmed).
- No JS changes; no other CSS properties altered.
</success_criteria>

<output>
Create `.planning/quick/260711-gtz-decrease-the-size-of-title-in-the-landin/260711-gtz-SUMMARY.md` when done.
</output>

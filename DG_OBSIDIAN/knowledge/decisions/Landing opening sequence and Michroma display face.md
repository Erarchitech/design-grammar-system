---
tags: [decision, ui-v2, landing, motion, typography]
date: 2026-10-08
status: accepted
---

# Landing opening sequence and Michroma display face

**Decision (owner, tuned 2026-10-08 in the Design Grammars Landing Tuner artifact):** the main window opens with a current running once round the particle ring clockwise from the top; menu nodes appear one by one as it passes; the hero words fade in by opacity alone (the particle-materialising title is gone). Michroma is the display face of the hero and region labels.

**Values** (`RING` and `SEQ` in `ui-v2/src/landing/landingEngine.js`): 26,000 dots, peak density 0.9, peak height 0.59, gain 0.75, width 0.4, floor 0.015, brightness contrast 0.46, thickness 0.3, dot size 1.7, opacity 0.35, speed 1.4, drift 0.2, breathing 0.35, leader length 1.15; loop 1 s, label fade 1 s, title start −0.1 s from the current's end, title fade 1 s. Sphere and current strands off (available in the tuner).

**Type:** Michroma 400 (only weight; OFL, @fontsource 5.3.0, self-hosted `michroma-latin-400-normal.woff2`, token `--font-display`), uppercase, 0.1 em; title `max(22px, 3.25vmin)`, subtitle `max(11px, 1.5vmin)`, labels `clamp(11px, 0.62vw, 24px)`. Captions (system line, Sign out, hint) in Geist Mono.

**Why:** owner asked for a more professional, minimal, futuristic main window with the Graph Viewer's injection motion; the old ring had too little density and height contrast between peaks.

**Notes:** the opening plays once per page load; returning from a region does not replay it. The envelope is computed once per frame into a 2,048-bin table to keep 26,000 dots at 55–60 fps.

Related: [[sessions/2026-10-08 Model Viewer fixes, landing motion redesign and DeGram 0.1.5]]

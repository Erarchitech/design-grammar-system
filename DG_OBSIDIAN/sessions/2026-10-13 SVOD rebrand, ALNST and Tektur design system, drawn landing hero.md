---
tags: [session, ui-v2, design-system, landing, i18n, phase-1308]
date: 2026-10-13
---

# SVOD rebrand, ALNST and Tektur design system, drawn landing hero

## Outcome

The owner accepted the DG Web UI design at the end of the session. Decision: [[knowledge/decisions/SVOD name, ALNST and Tektur design system, drawn landing hero]].

1. **Phase 1308 changes not visible after a Docker rebuild.** The UI image was rebuilt but the container was not recreated; fixed by recreating it. See [[knowledge/debugging/docker compose build alone leaves the old design-grammars container running]]. A UAT audit of 1308 found 0 items: the phase has no UAT/VERIFICATION file yet, and plans 18–20 are unexecuted.
2. **Landing Tuner** (claude.ai artifact `7mmxj53WSRG3mjTB7U5NmV`, private) gained:
   - a Russian version with separate type per language;
   - Cyrillic-capable faces and the embedded ALNST font;
   - ring closure and crescent controls;
   - a title–subtitle gap control;
   - a «Current app» preset that matches the shipped landing.
3. **Name.** The owner chose SVOD from proposed Russian names; it is now the proper noun `PRODUCT_NAME` for both languages. Subtitle: RU «Свод правил проекта», EN «Encode Design Grammars». The browser tab title is SVOD.
4. **Design system.**
   - Two faces: ALNST for main headings, Tektur for everything else; Geist Mono only for code and data.
   - All headings are uppercase, with no closing full stops.
   - The specimen page was updated.
5. **Landing.**
   - Crescent ring and opening sphere ported from the tuner into `landingEngine.js`.
   - Hero drawn along the glyph lines, all strokes at once, dots after; generator `ui-v2/scripts/gen_alnst_strokes.py` → `alnstStrokes.js`.
   - Region figures one per row, rising word by word.
   - User name set like the menu items; system line and Sign out in Tektur Medium 500.

## Verification

- `npm --prefix ui-v2 test`: 286/286 after every change; `npm --prefix ui-v2 run build` passed.
- `python tools/degram/workspace.py verify` passed before `ui-v2/src/degram/degram.css` was edited.
- Each change was rebuilt (`--no-cache`) and the `design-grammars` container recreated.
- Real-time frames were captured over the DevTools protocol in headless Chrome, using a stdlib Python WebSocket client from the session scratchpad. They confirmed the following, in both RU and EN:
  - the sphere, the crescent and the uppercase RU menu items;
  - the stroke drawing with the dots appearing after the lines;
  - the final «SVOD / СВОД ПРАВИЛ ПРОЕКТА» and «SVOD / ENCODE DESIGN GRAMMARS».
- **Not seen live:** the signed-in view (user name, system line, region figures), because no account was used.

## Open

- ALNST licence: copyright line only. Confirm embedding rights before a public deployment or a push that publishes the font.
- The tuner still previews the older hero fade, not the stroke drawing.
- Phase 1308 plans 18–20 and its UAT/VERIFICATION remain as before.

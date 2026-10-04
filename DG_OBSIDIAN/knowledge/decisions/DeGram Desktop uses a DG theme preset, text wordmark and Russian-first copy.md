---
tags: [decision, DeGram, v13.0, phase-1301, ui, design-system]
date: 2026-10-04
status: UI-SPEC approved (inline check); implementation OPEN
---

# DeGram Desktop: DG theme preset, text wordmark, Russian-first copy, DG page

Source of truth: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UI-SPEC.md`. This note summarizes the owner's choices from `/gsd-ui-phase 1301`; it closes no DGCL requirement.

## Decisions

- **Theme:** one new `degram` preset (`apps/degram/apps/desktop/src/themes/presets.ts` + palette in `apps/degram/apps/shared/src/theme-presets.ts`) carrying the DG web tokens: canvas `#f5f5f5`, paper `#ffffff`, ink `#0a0a0a`, filled buttons ink-soft `#171717`, hairline `#e5e5e5`, accent = DG signal red `#e7000b` (dark `#ff3b44`) on ring/midground. Default for variant `degram`; other Hermes skins remain selectable (not locked).
- **Fonts:** Geist / Geist Mono / Oswald self-hosted with latin + cyrillic subsets; the preset has no `fontUrl`.
- **Brand:** text wordmark «DeGram» (Oswald 500, uppercase) on the `BrandMark` tile; app/tray/installer icons generated from it via the existing icon script. The nous-girl mark is not used in the variant.
- **Language:** every new string in en and ru; variant `degram` starts in Russian on first run.
- **DG web placement:** a durable shell page «DG» next to Chat, with a toggle between the `#degram` project-graph slice and full DG (incl. Model Viewer).
- **Hidden in the variant:** model picker/visibility, provider/key settings, billing/free-tier, updater, remote setup; the system model pair never appears as text.

## Why

- The DG page shows ui-v2 inside DeGram; a matching shell palette makes it read as one product, while a preset (not a primitive fork) keeps the upstream merge surface to one seam.
- Users are Russian-speaking architects; Russian-first copy avoids a half-translated UI.
- DESIGN.md: pages are durable destinations, and Model Viewer needs room a side pane does not give.

## Consequences

- Red marks both selection (accent) and failure (destructive), as in DG web; the spec separates them by shape (dots/rings vs `ErrorIcon` + failure copy).
- Cyrillic font subsets must be acquired at execution (package step → owner authorization).

Related: [[knowledge/decisions/DeGram Phase 1301 client isolation, auth relay and Revit MCP fork]], [[sessions/2026-10-04 Phase 1301 UI design contract]].

---
tags: [decision, degram, phase-1301, branding, i18n]
date: 2026-10-07
---

# DeGram rebrands Hermes at the catalog and the rendered interface

**Status:** owner request 2026-10-07 ("remove all Hermes logos and names"), approved live on 0.1.4. Component `0cb15c9c`, `c541b229`.

## Decision

The upstream copy names the product in about 700 catalog strings and a few hundred literals. Forking every string would make every upstream merge conflict, so variant degram rebrands at seams (`apps/desktop/src/degram/brand.ts`):

- **Catalog:** `resolveTranslations` applies `rebrandCatalog` (every string leaf and message-function result).
- **Rendered interface:** a MutationObserver rewrites text nodes and the `title`, `aria-label`, `placeholder`, `alt` labels as they appear. Labels are rewritten everywhere; text is never rewritten inside chat messages (`data-role` user/assistant), editable fields or code — those are the user's and the model's words.
- **Letter-by-letter lettering** (Wordmark, DecodeText) is invisible to the observer as one word, so it takes `productMark()` → `DEGRAM`.
- **Native:** OS notifications through `rebrandText`, tray tooltip/menu and the renderer-terminated page through the product name.
- Patterns: `Hermes`, `Hermes Agent`, `Hermes Desktop` → DeGram; uppercase marks → DEGRAM; identifiers (`HERMES_HOME`), tags (`HERMES-WATCH`), lowercase commands and paths stay.
- The logo was already DeGram's (F-04).

## Related change

The interface language was saved through `GET/PUT /api/config` (whole profile config), which variant degram locks. DeGram now keeps `display.language` in renderer storage (`degram/locale-config.ts`); nothing else of the config is read or written.

Related: [[knowledge/decisions/DeGram product identity follows the Gena fork lessons|identity]], [[sessions/2026-10-07 Phase 1301 DeGram pairing connector, rules read fix, 490 MB installer and no Hermes name|session]].

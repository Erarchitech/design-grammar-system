---
tags: [decision, degram, i18n, ui-v2, phase-1308]
date: 2026-10-12
---

# DeGram owns embedded language; the browser owns its language dropdown (D-50..D-54 amended)

## Context

Phase 1308 research (D-38 of 1301) proposed an «EN | RU» badge on the DG Web UI start screen, with the choice kept in `localStorage` (`dgv2_lang`). DeGram already has its own Settings → Appearance → Language (`appearance-settings.tsx`, `LanguageSwitcher`) with 9 bundled locales, and passes its language to the DG page only as `&lang=` on the next full load (`dg-view.ts` `setLocale`).

## Decision (owner, 2026-10-12, after the 1308 plans were written)

- **D-50:** the language of every element and every screen (DeGram and the embedded DG Web UI) is switched in one place only: DeGram Settings → Appearance → Language.
- **D-51:** in the `degram` variant the switcher offers only «Русский» and «English»; a stored other locale is coerced to English.
- **D-52:** a change reaches the open DG page live, without reload, through a new host signal `#degram-lang=ru|en`; `setLocale` keeps `&lang=` for later loads.
- **D-53 (amended by owner during Phase 1308 UAT):** a DG Web UI opened in a plain browser has a global language dropdown at the upper-right on every screen (Русский / English). The saved browser choice (`dgv2_lang`) wins over the primary browser language on later loads. This control is absent inside DeGram; Settings → Appearance → Language remains the sole control for its embedded page.
- **D-54:** the `degram` RU catalog is complete for every visible DeGram surface.

## Consequences

- The former landing-only badge remains withdrawn. The browser-only global dropdown, `dgv2_lang`, and the `KEPT_KEYS` exception are reinstated by the later UAT instruction; the DeGram host neither renders nor reads this browser choice.
- New plan 1308-21 (component repo `apps/degram/apps/desktop`) carries D-51, D-52, D-54; it shares the owner-authorized component commit and the single fork push with the sidebar «Projects» row (1308-17 → 1308-18).

## Related

- [[knowledge/decisions/Connector access is a per-connector grant without tokens, owner and admin exempt (D-49)]]
- `.planning/phases/1308-dg-web-ui/1308-CONTEXT.md`, `1308-UI-SPEC.md` (revision 2)

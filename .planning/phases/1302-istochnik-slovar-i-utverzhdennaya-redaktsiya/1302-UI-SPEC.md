---
phase: 1302
slug: istochnik-slovar-i-utverzhdennaya-redaktsiya
status: draft
shadcn_initialized: false
preset: none
created: 2026-10-14
---

# Phase 1302 — UI Design Contract

> Design contract for the proposed source, vocabulary, rule revision and lessons-learned surfaces. Not an implementation or acceptance record. Entry gates in ROADMAP.md remain open.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Existing ui-v2 components and CSS tokens; no shadcn |
| Preset | Not applicable |
| Component library | `ui-v2/src/components/` (Button, Input, Select, Panel, Tabs, Dialog, Callout, Badge, KVRow); no new library |
| Icon library | Existing ui-v2 icon treatment; avoid adding an icon package |
| Font | Existing `--font-display` ALNST for main headings, `--font-sans` Tektur for remaining UI, `--font-mono` Geist Mono for IDs/hashes; fallback fonts apply. Public font distribution remains blocked pending licence resolution. |

Follow current SVOD dark/light theming and bilingual RU/EN controls. Reuse GraphScreen and authenticated graphApi seams, but do not expose its current ingest/edit/delete actions as approved revision operations until the server implements atomic expectedRevision, authorization and immutable history. New governance surfaces must use semantic focus order, labelled inputs, readable state text and keyboard-accessible controls; existing `Dialog` is a styled surface, not by itself a proven accessible modal/focus trap.

---

## Spacing Scale

Use `ui-v2/src/styles/tokens/spacing.css`, with 4px grid; retain existing component exceptions instead of globally restyling the app.

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-4` | 4px | Dense metadata, inline gaps |
| `--spacing-8` | 8px | Field and badge gaps |
| `--spacing-12` | 12px | Related controls |
| `--spacing-16` | 16px | Mobile side gutter and field groups |
| `--spacing-20` | 20px | Existing card padding |
| `--spacing-24` | 24px | Section separation |
| `--spacing-48` | 48px | Major panel breaks |

Exceptions: keep existing `Dialog` 14px header/content gaps and 380px width only where it fits; on narrow screens constrain to viewport width minus 32px. Long IDs, URI fragments and typed diffs wrap or scroll within their panel, never the page.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | `--text-body` 14px | 400 | `--leading-body` 1.43 |
| Label | `--text-caption` 12px | 500 | `--leading-caption` 1.33 |
| Heading | `--text-heading-sm` 24px | 600 | `--leading-heading-sm` 1.33 |
| Display / screen heading | `--text-heading` 30px | 600 | `--leading-heading` 1.2 |

Main screen headings use ALNST uppercase, other headings use Tektur uppercase, without trailing periods per current SVOD design. URI/revision hashes use mono with a visible copy action and full value available to assistive technology; no truncation that destroys provenance.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `var(--color-canvas)` (`#f5f5f5` light) | Page background |
| Secondary (30%) | `var(--color-paper)` (`#ffffff` light), `var(--color-surface-alt)` (`#fafafa` light) | Cards, panels, metadata surfaces |
| Accent (10% max) | `var(--color-signal)` (`#e7000b` light) | Selection, failures and destructive affordances only |
| Destructive | `var(--color-signal-ink)` (`#b8000e` light) | Retirement/delete action and failure text |

Accent reserved for selected revision, conflicts/failures and retirement; approved is not signalled by red. Show status as text plus non-colour affordance. Dark mode resolves these same tokens under `:root[data-theme="dark"]`; never hard-code light text/background in new panels. Existing warning/info tokens are SHACL-severity-specific, not a new governance palette.

---

## Copywriting Contract

All strings go through the existing RU/EN i18n system. Proposed RU copy below; English equivalents must be provided with the implementation.

| Element | Copy |
|---------|------|
| Primary CTA (proposal) | «Предложить редакцию»; does not imply activation |
| Primary CTA (approval) | «Подтвердить редакцию» after displaying exact project, rule, source and expected revision |
| Empty state heading | «Правил пока нет» / «Нет выпусков словаря» in the corresponding panel |
| Empty state body | «Выберите проект и добавьте источник, чтобы предложить первое правило»; show the permitted next step for the viewer's role |
| Loading | «Загружаем редакции и источники…»; do not show stale data as current |
| Access denied | «Нет доступа к этому проекту или источнику. Проверьте права и выберите доступный объект.» |
| Conflict | «Редакция изменилась у другого автора. Сравните новую версию и повторите предложение.» Preserve unsent draft. |
| Non-executable intent | «Требование сохранено как неисполняемое: машинная проверка недоступна.» Include the reason and scope of human review. |
| Missing destination evidence | «Копия ещё не действует: нужна новая проверка и утверждение в проекте назначения.» |
| Destructive confirmation | «Вывести термин/правило из обращения» with exact company/project, current revision, affected refs and future effect; historical links remain |
| Command confirmation | «Подтвердить {действие} в {проект} для редакции {revision}» with exact target and consequence; cancel leaves state unchanged |

Never say «соответствует» for unsupported, not-checked, source-run reuse or a merely saved proposal. Separate draft, validated, approved and active states; show actor/role/date and pinned references where available. No UI claim that a DG session authorizes a CDE source.

---

## Interaction and State Contract

1. Source rule workspace: explicit project selection; source URI/ID, revision/hash, fragment and applicability visible together. Source access is checked by server; inaccessible/unpinned source is not presented as verified. Non-formalizable intent has a distinct, non-executable card.
2. Vocabulary panel: show company and pinned immutable release; proposals/private/project drafts have visibility labels and are not cross-project search results. Only an authorized steward sees release controls, but the server is the authorization boundary. Retirement preview lists affected active rules while preserving history.
3. Rule revision review: typed create/edit/retirement diff shows before/after, source and applicability, formalization result and human confirmation as separate steps. CAS conflict returns current revision and preserves the user's draft; retry is not an automatic overwrite. Audit read-back is available with actor, outcome and revisions.
4. Historical inspection: old run opens pinned executable ruleset, vocabulary release and source revisions independently of the current release. Show stale/needs-recheck on affected current bindings/states/runs without mutating the historical verdict.
5. Lessons-learned copy: source and destination projects shown side by side with new independent ID; transfer permission and destination write are separate. Draft copy stays inactive until fresh destination validation and destination human approval; source run is provenance, not destination evidence.
6. Typed `/dg-` command palette: canonical registry drives argument help, risk label and validation; read is immediate, mutation/publication previews exact scope then confirms; server rechecks auth and expected revision. No LLM-driven dispatch or generic graph CRUD.
7. Switching company/project, logout, revocation and source-access loss clears protected visible context. Display explicit denied/unavailable/partial states; no cross-company or private-draft data remains on screen.

---

## UI Considerations

> Awaiting the workflow's post-checker ui-consideration probe. The rows below are an authoring checklist, not probe sign-off.

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| empty | Source, rule, vocabulary and copy lists | pending | Distinct empty copy and permitted next action per panel |
| loading/error | Source and revision read-back | pending | Never show stale data as current; retry or access explanation |
| partial | Historical ruleset and source reads | pending | Missing pin or inaccessible source blocks compliance claim |
| conflict | Draft review | pending | Preserve unsent draft; show current revision and re-diff |
| zero-one-many | Vocabulary release, rule references, affected runs | pending | Explicit zero and plural counts without implying absence of impact |
| long-text/overflow | URI, fragment, rule diff, audit list | pending | Wrap/inner-scroll and accessible full values at phone width |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| Existing ui-v2 components | Button, Input, Select, Panel, Tabs, Dialog, Callout, Badge, KVRow | Reuse with accessibility tests; no third-party registry |
| shadcn / third-party | None | Not applicable |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: pending independent checker
- [ ] Dimension 2 Visuals: pending independent checker
- [ ] Dimension 3 Color: pending independent checker
- [ ] Dimension 4 Typography: pending independent checker
- [ ] Dimension 5 Spacing: pending independent checker
- [ ] Dimension 6 Registry Safety: pending independent checker

**Approval:** pending independent verification and entry-gate review

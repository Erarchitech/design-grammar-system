---
phase: 1301
slug: rabochiy-klient-i-bezopasnoe-chtenie
status: approved
reviewed_at: 2026-10-04
reviewed_by: inline checker (owner chose fully inline; no independent gsd-ui-checker)
shadcn_initialized: true
preset: "apps/degram/apps/desktop/components.json — style new-york, baseColor neutral, cssVariables, iconLibrary tabler (read from file; `npx shadcn info` not run — no package execution authorized)"
created: 2026-10-04
---

# Phase 1301 — UI Design Contract

> Visual and interaction contract for the DeGram Desktop surfaces of Phase 1301 (DGCL-01..07). Authored inline by the orchestrator (owner chose fully inline over gsd-ui-researcher/checker, 2026-10-04). Locked decisions come from `1301-CONTEXT.md` D-01..D-19; owner answers from this session are marked **[owner 2026-10-04]**.

## Scope of this contract

| Surface | Owner of the pixels | Status |
|---|---|---|
| DeGram Desktop shell (fork of Hermes Desktop, `apps/degram/apps/desktop`) — sign-in, scope strip, project picker, document picker, bridge status, context card, request lifecycle, DG page | **This contract** | New in 1301-02+ |
| `ui-v2/#degram` read-only web slice (1301-01) | ui-v2 DG tokens (`ui-v2/src/styles/tokens/*`, `ui-v2/src/degram/degram.css`) | Shipped, unchanged; shown inside the DG page (D-07) |
| Full DG V2 + Model Viewer | ui-v2, unchanged | Shown inside the DG page as-is; DeGram adds/removes no rights |
| DG login / invite pages | ui-v2, unchanged | Opened top-level in partition `persist:degram-dg` (D-05) |

Binding upstream rules: `apps/degram/apps/desktop/DESIGN.md` (primitives, tokens, flatness, feedback, cancellation, i18n) and `apps/degram/apps/desktop/AGENTS.md`. Where this contract and DESIGN.md disagree, DESIGN.md wins for *how* (primitives), this contract wins for *what* (DeGram surfaces, copy, palette). No new primitive is introduced; every row below names the existing primitive it composes.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (already initialized upstream — `components.json`, style `new-york`) |
| Preset | not applicable (no shadcn preset string; theming goes through the Hermes `DesktopTheme` preset seam) |
| Component library | Radix (via upstream `src/components/ui/*`); chat on `@assistant-ui/react` |
| Icon library | Tabler via `src/lib/icons.ts` aliases; Codicon for status/tool glyphs. No third set. |
| Font | Geist (sans), Geist Mono (mono), Oswald (wordmark only) — self-hosted, latin + cyrillic subsets |
| Theme | New preset `degram` in `apps/degram/apps/desktop/src/themes/presets.ts` + palette `degram` in `apps/degram/apps/shared/src/theme-presets.ts`; default for variant `degram`; other skins stay selectable **[owner 2026-10-04: DG preset, not locked]** |
| Brand mark | Owner-supplied halftone hexagon (91 dots, centre + five rings) on the `BrandMark` tile and as app/taskbar/shortcut/installer icon, light tile + `#0d1117` dark tile, 19-dot reduced mark at 16–32 px, rendered by `scripts/generate_degram_icons.py` over the upstream filenames **[owner 2026-10-06, supersedes the 2026-10-04 wordmark-derived icon]**. The text wordmark «DeGram» (Oswald 500, uppercase) remains the in-app wordmark |
| Locale | en + ru copy contract; variant `degram` starts in `ru` on first run; user may switch **[owner 2026-10-04]** |

### Theme preset `degram` (exact values)

The preset is the only place these literals may appear (DESIGN.md: "Tokens, not literals" — presets are the token source). Values are the DG web tokens from `ui-v2/src/styles/tokens/colors.css`, so the DG page and the shell read as one product.

| `ThemePresetColors` key | Light (`colors`) | Dark (`darkColors`) | DG source token |
|---|---|---|---|
| background | `#f5f5f5` | `#111111` | `--color-canvas` |
| foreground | `#0a0a0a` | `#f0f0f0` | `--color-ink` |
| card / popover | `#ffffff` | `#1b1b1b` | `--color-paper` |
| cardForeground / popoverForeground | `#0a0a0a` | `#f0f0f0` | `--color-ink` |
| sidebarBackground | `#fafafa` | `#171717` | `--color-surface-alt` |
| muted | `#fafafa` | `#171717` | `--color-surface-alt` |
| mutedForeground | `#737373` | `#909090` | `--color-mid-gray` |
| primary (filled `Button default`) | `#171717` | `#e2e2e2` | `--color-ink-soft` |
| primaryForeground | `#fafafa` | `#111111` | `--text-inverse` |
| secondary (soft fill) | `#ebebeb` | `#262626` | `--ink-a08` flattened on paper |
| secondaryForeground | `#171717` | `#e2e2e2` | `--color-ink-soft` |
| accent (shadcn hover fill, not brand) | `#f0f0f0` | `#222222` | `--ink-a04` flattened |
| accentForeground | `#0a0a0a` | `#f0f0f0` | `--color-ink` |
| border / input / sidebarBorder / userBubbleBorder | `#e5e5e5` | `#2a2a2a` | `--color-hairline` |
| userBubble | `#ffffff` | `#1b1b1b` | `--color-paper` |
| ring / midground / composerRing | `#e7000b` | `#ff3b44` | `--color-signal` |
| destructive | `#b8000e` | `#ff7079` | `--color-signal-ink` |
| destructiveForeground | `#ffffff` | `#111111` | — |

`typography` of the preset: `fontSans: "'Geist', var(--dt-font-sans)"`, `fontMono: "'Geist Mono', var(--dt-font-mono)"`, **no `fontUrl`** (upstream presets load Google Fonts by URL; DeGram must make no font network request — fonts ship in the bundle). Font files: vendored from the same `@fontsource` packages ui-v2 uses (`geist-sans`, `geist-mono`, `oswald`), weights 400/500, subsets `latin` + `cyrillic`; if a face has no cyrillic subset, Cyrillic falls back to `Segoe UI` via the existing `--dt-font-sans` tail and a render test records which. Vendoring needs package files on disk — acquisition is an install step requiring owner authorization at execution time.

---

## Information architecture (DeGram variant)

| Place | What | Rule |
|---|---|---|
| Shell page **Chat** (home) | Transcript + composer; **Context card** in the composer status stack | DESIGN.md: chat is the home surface |
| Shell page **DG** (new, next to Chat) **[owner 2026-10-04]** | Embedded `WebContentsView` of the DG origin in partition `persist:degram-dg`; `SegmentedControl` «Граф проекта / Полный DG» (`#degram` slice vs full V2 incl. Model Viewer) | Durable destination; view stays mounted when hidden (DESIGN.md "visibility is not lifecycle"); navigation allowlist = DG origin only; no Node/preload (D-07) |
| **Scope strip** (shell statusbar, visible on Chat and DG pages) | `company · project · document · Revit ● · Grasshopper ●` | Always visible once signed in (DGCL-02); each segment is a `Button variant="text"` opening its picker |
| **Project picker** | Popover + `Command variant="menu"` anchored to the project segment; full-body `EmptyState` when no project is chosen | Explicit selection only; no remembered-project restore (1301-01 parity) |
| **Document picker** | Popover + `Command variant="menu"` anchored to the document segment; rows grouped by bridge | Explicit pin to identity (D-13) |
| **Sign-in** | Boot-chain state (rung `--z-setup`), top-level DG login page in the partition | Distinct state per DESIGN.md "install, onboarding, connecting, boot failure, reauthentication are distinct states" |
| Confirmations | `ConfirmDialog` only | Whole-definition send, sign-out/switch while a response runs |

**Upstream surfaces that must not render in variant `degram`** (no dead entry points — hide the entry, not just disable the action): model picker and model-picker overlay, model-visibility dialog/overlay, provider/API-key settings and onboarding provider steps, billing banner, free-tier surfaces, update status / updates overlay (D-03), remote-setup, and any entry point for a Hermes capability that the planner's tool allowlist excludes. The served system pair `genpro` / `mimo-v2.5-pro` never appears as text anywhere in the UI (DGCL-02); the payload disclosure shows context, not routing.

### Focal points and hierarchy

1. **Not signed in:** the DG login page fills the content column; the wordmark sits above it. Nothing else is interactive except quit.
2. **Signed in, no project:** the project `EmptyState` is the single focal point; the composer is not mounted (no request can be composed without scope).
3. **Working:** the transcript is primary; the **Context card** is the second read — the user sees what will be sent before pressing Send (DGCL-07). The scope strip is peripheral (statusbar weight) but carries red only on the pinned-document dot and the selected project.
4. **DG page:** the embedded DG web fills the page below one toolbar row (segmented control left, reload icon right).

---

## Component inventory (compose, don't fork)

| Element | Composed from | Behavior contract |
|---|---|---|
| Scope strip | statusbar row, `Button variant="text" size="micro"`, `StatusDot`, `OverflowTip` for truncated names | Segments: company, project, document, Revit, Grasshopper. Long names ellipsize at the segment; full value in `OverflowTip`. Change of project/document is reflected in the strip in the same frame and in the next request's Context card (DGCL-02). Two pins (one per bridge) and the «Документы: {n}» segment: see "Gap round 2026-10-09". |
| Project picker | `Popover` + `Command variant="menu"`, `SearchField` (hidden when ≤ 7 items), `EmptyState` (body form) | Lists only server-authorized projects (`fetchProjects`). Selecting while a response runs → `ConfirmDialog` (see copy). Selecting opens a **new chat** for that scope (D-19). |
| Document picker | `Popover` + `Command variant="menu"`, group headings per bridge, `ListRow`-style two-line rows | Row line 1: app glyph (Codicon) + document name; line 2 (Geist Mono 11): path · document identity. Pinned row shows a red leading dot. Unavailable bridge renders its group as a single neutral notice row with the diagnostic copy, never hidden. |
| Bridge status | `StatusDot` + label in the scope strip; detailed line in the document picker group header | States: `ready`, `pinned`, `busy`, `off`, `setup-incomplete` (routes disabled / extension not loaded / no document open — each its own copy), `identity-mismatch`. Neutral color for off/busy/setup (DESIGN.md: red reserved for explicit failures); red dot only for `pinned`. |
| Context card | composer status-stack group (`StatusRow`/`StatusControlRow`, `status-stack.css`), `Badge` (`muted`, `warn`), `DisclosureCaret`, `LogView` for exact payload | **Always expanded to its summary line** (exception to "status groups start collapsed", justified by D-17 "постоянная карточка"). Summary: project · document · objects · parameters · rules · fragments · size. Badges: `warn` for «сокращено»/«нет данных». Caret reveals the exact payload in `LogView` (secrets never present — redaction happens before render, not in CSS). One summary line per pinned document and a blocked-document row: see "Gap round 2026-10-09". |
| Whole-definition scope | `SegmentedControl` in the Context card: «Выделение / Всё определение» | Choosing «Всё определение» changes nothing until Send; Send then opens `ConfirmDialog`. Policy deny is never offered as confirmable. |
| Policy deny notice | Composer error banner slot (`ErrorState` compact, neutral icon) | Shows server reason; no confirm button; offers «Сузить контекст». |
| Request lifecycle | existing composer Stop control, `Loader` (no literal "Loading…"), composer error banner, `Badge muted` «прервано» on partial message | Stop paints in the current frame; cancellation propagates client → relay → provider and aborts an in-flight CAD read (D-18). Failure banner names the cause and offers «Повторить запрос»; no auto-retry. |
| Session / revoke | boot-chain reauth state; `notify()` toast for revoke | On 401: clear agent context, delegated token, web view state, then show sign-in. On 403 for the active project: clear that scope's data and local history, show toast + project `EmptyState` (D-08, D-19). No stale data remains painted. |
| Runtime-isolation boot failure | `boot-failure-overlay` + `ErrorState` + `LogView` | D-02 fail-closed start; shows the overlapping path; no "continue anyway". |
| DG page toolbar | `SegmentedControl`, `Button variant="ghost" size="icon-sm"` (reload) with `aria-label` | External link from DG web → not opened in the view; toast with copy + «Открыть в браузере» `textStrong` action (system browser, explicit user intent). |
| Wordmark | `BrandMark` tile + Oswald 500 uppercase text | Boot, about, sign-in only (DESIGN.md: brand moments). |

Accessibility: every icon-only control has `aria-label`; `Tip` only where hover teaches something new (DESIGN.md); no native `title=`; scope strip segments are reachable by keyboard in order; `Esc` closes the topmost picker only; reduced motion → pickers and banners appear without slide.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Gap between status dot and its label; badge-to-text gap |
| sm | 8px | Gap between scope-strip segments; row line gap in pickers |
| md | 16px | Context-card summary item gap; picker group spacing |
| lg | 24px | DG page toolbar inline padding; empty-state stack gap |
| xl | 32px | Sign-in surface gap between wordmark and login view |
| 2xl | 48px | Empty-state top offset inside the content column |
| 3xl | 64px | Not used in this phase |

Upstream Tailwind spacing is 0.25rem-based, so these map to `gap-1/2/4/6/8/12`. Page gutters use `PAGE_INSET_X`; primitives (`Button`, `StatusRow`, `Badge`, `ListRow`, status-stack 0.25rem nesting) own their internal padding and are **not** re-specified at call sites (DESIGN.md rule 5).

Exceptions: none for new layout code.

---

## Typography

New DeGram surfaces use exactly these four sizes and two weights. Values are CSS px before the window-wide UI Scale (90% default). Transcript and composer text keep the upstream Chat Text Size tokens and are not re-specified here.

| Role | Size | Weight | Line Height | Face | Used for |
|------|------|--------|-------------|------|----------|
| Label / meta | 11px | 400 | 1.45 | Geist Mono | Document path, identity, counts, payload size, bridge state text |
| Body | 13px | 400 | 1.4 | Geist | Picker rows, Context card summary, banners, empty-state body |
| Heading | 16px | 500 | 1.25 | Geist | Empty-state heading, picker group headings, ConfirmDialog title |
| Display | 28px | 500 | 1.1 | Oswald, uppercase, letter-spacing 0.02em | Wordmark «DeGram» only |

---

## Color

| Role | Value (light / dark) | Usage |
|------|-------|-------|
| Dominant (60%) | `#f5f5f5` / `#111111` | Window background, content column, DG page backdrop |
| Secondary (30%) | `#ffffff` / `#1b1b1b` (+ sidebar `#fafafa` / `#171717`) | Popovers, pickers, Context card fill (`--ui-widget-surface-background` derives from it), sidebar |
| Accent (10%) | `#e7000b` / `#ff3b44` | See reserved list |
| Destructive | `#b8000e` / `#ff7079` | Explicit failures only: failed tool row, boot-failure `ErrorIcon` |

Accent reserved for (exhaustive):
1. Keyboard focus ring (`ring`) — DG convention, matches `degram.css` `:focus-visible`.
2. Pinned-document dot in the scope strip and the pinned row's leading dot in the document picker.
3. Selected-project indicator in the project picker.
4. Upstream `midground` uses that already exist: streaming cursor, active-session pill, text selection.

Not accent: primary buttons (ink `#171717`), links, badges, bridge `off`/`busy`/`setup-incomplete` (neutral), policy deny (neutral), «прервано» marker (muted). Warning badges for truncation/missing data use the upstream `Badge warn` variant unchanged.

Semantic note: accent and destructive share DG's red family by design — DG web uses red for both selection and failure. They stay distinguishable by shape: accent appears only as dots/rings; destructive appears only with `ErrorIcon` and failure copy.

---

## Copywriting Contract

All strings go through `useI18n()`; keys are added to every complete catalog (en/fr/de/es — fr/de/es receive the English text) and to `ru` via `defineLocale()`. `{…}` are interpolations. Russian is the first-run locale of variant `degram`.

| Element | en | ru |
|---------|----|----|
| Primary CTA (phase) | Select document | Выбрать документ |
| Sign-in CTA | Sign in with DG | Войти через DG |
| Project picker CTA | Choose project | Выбрать проект |
| Send (composer) | Send to model | Отправить модели |
| Stop control | Stop response | Остановить ответ |
| Retry after failure | Retry request | Повторить запрос |
| Narrow context (policy deny) | Narrow context | Сузить контекст |
| Context scope toggle | Selection / Whole definition | Выделение / Всё определение |
| Partial message marker | Interrupted | Прервано |
| DG page toggle | Project graph / Full DG | Граф проекта / Полный DG |
| Empty — no project chosen (heading) | Choose a project | Выберите проект |
| Empty — no project chosen (body) | DeGram works inside one DG project at a time. Choose a project you have access to — nothing is loaded until you do. | DeGram работает внутри одного проекта DG. Выберите доступный вам проект — до выбора ничего не загружается. |
| Empty — no accessible projects (heading) | No projects available | Нет доступных проектов |
| Empty — no accessible projects (body) | Your DG account isn't a member of any project yet. Ask a project owner for an invitation, then refresh. | Ваша учётная запись DG пока не состоит ни в одном проекте. Попросите владельца проекта прислать приглашение и обновите список. |
| Empty — no open documents (heading) | No open documents | Нет открытых документов |
| Empty — no open documents (body) | Open a model in Revit 2024 or a definition in Grasshopper (Rhino 8), then refresh the list. | Откройте модель в Revit 2024 или определение в Grasshopper (Rhino 8) и обновите список. |
| Context card — no document | No document selected — the request uses project data only. Select a document to add a snapshot. | Документ не выбран — запрос использует только данные проекта. Выберите документ, чтобы добавить snapshot. |
| Context card — empty selection | Nothing is selected in {document}. Select elements there, or send without a snapshot. | В {document} ничего не выделено. Выделите элементы или отправьте без snapshot. |
| Context card — truncated badge | Truncated: {kept} of {total} | Сокращено: {kept} из {total} |
| Context card — missing badge | Missing: {what} | Нет данных: {what} |
| Error — DG server unreachable | The DG server can't be reached. Check your network or VPN, then retry the request. | Сервер DG недоступен. Проверьте сеть или VPN и повторите запрос. |
| Error — model service unavailable | The model service is unavailable. Your message wasn't processed; retry the request in a few minutes. | Сервис модели недоступен. Сообщение не обработано; повторите запрос через несколько минут. |
| Error — timeout | No answer within {seconds} s, so the request was stopped. Retry it, or narrow the selection. | Ответа нет за {seconds} с, запрос остановлен. Повторите его или сократите выделение. |
| Error — rate/usage limit | The request limit for this project is reached. Retry after {time}, or ask the DG operator. | Достигнут лимит запросов для проекта. Повторите после {time} или обратитесь к оператору DG. |
| Error — rate/usage limit, reset time unknown | The request limit for this project is reached. Retry later, or ask the DG operator when it resets. | Достигнут лимит запросов для проекта. Повторите позже или уточните у оператора DG, когда лимит обновится. |
| Error — Revit bridge off | Revit isn't responding. Open Revit 2024 with the DeGram pyRevit extension, then refresh. | Revit не отвечает. Откройте Revit 2024 с расширением DeGram для pyRevit и обновите список. |
| Error — pyRevit Routes disabled | pyRevit Routes are turned off. Enable Routes in pyRevit settings, restart Revit, then refresh. | Маршруты pyRevit (Routes) выключены. Включите их в настройках pyRevit, перезапустите Revit и обновите список. |
| Error — extension not loaded | The DeGram extension isn't loaded in pyRevit. Follow the install step "pyRevit extension", then reload pyRevit. | Расширение DeGram не загружено в pyRevit. Выполните шаг установки «Расширение pyRevit» и перезагрузите pyRevit. |
| Error — Revit busy | Revit is busy (a command or dialog is open). Finish it in Revit, then retry the request. | Revit занят (открыта команда или диалог). Завершите её в Revit и повторите запрос. |
| Error — Grasshopper listener off | Grasshopper isn't responding. Place and enable the DG CANVAS LISTENER component on the canvas, then refresh. | Grasshopper не отвечает. Поставьте на канвас компонент DG CANVAS LISTENER, включите его и обновите список. |
| Error — pinned document gone / identity mismatch | {document} is no longer open, or another file is active in its place. Select the document again — DeGram never switches documents on its own. | {document} больше не открыт или вместо него активен другой файл. Выберите документ заново — DeGram не переключает документы сам. |
| Error — session ended (401) | Your DG session has ended. Sign in again to continue; project data was cleared from this window. | Сеанс DG завершён. Войдите снова, чтобы продолжить; данные проекта убраны из этого окна. |
| Error — access revoked (403, toast) | You no longer have access to {project}. Its data and local chat history were removed from this computer. | У вас больше нет доступа к {project}. Его данные и локальная история чата удалены с этого компьютера. |
| Error — policy deny | DG policy doesn't allow sending this data to the model: {reason}. Confirming won't override it — narrow the context or ask the project owner. | Политика DG не разрешает отправку этих данных модели: {reason}. Подтверждение это не отменит — сузьте контекст или обратитесь к владельцу проекта. |
| Error — runtime isolation (boot) | DeGram can't start: its data folder overlaps a Hermes profile at {path}. Move or remove that folder, then start DeGram again. | DeGram не может запуститься: его папка данных пересекается с профилем Hermes в {path}. Перенесите или удалите эту папку и запустите DeGram снова. |
| Bridge state — checking | Checking | Проверка |
| Connecting to DG (sign-in loader label) | Connecting to DG | Подключение к DG |
| Document row — unsaved | Not saved | Не сохранён |
| Document row — no identity (disabled) | Can't be pinned: no document identity | Нельзя закрепить: нет идентификатора документа |
| Snapshot read failed — action | Retry read | Повторить чтение |
| DG page load failed — action | Reload page | Перезагрузить страницу |
| Notice — external link blocked | This link leads outside DG and won't open inside DeGram. | Ссылка ведёт за пределы DG и не открывается внутри DeGram. |
| Notice action | Open in browser | Открыть в браузере |
| Confirm — whole definition (title) | Send the whole definition? | Отправить всё определение? |
| Confirm — whole definition (body) | {objects} objects and {parameters} parameters from {document} ({size}) will go to the model. Review the payload in the context card first. | В модель уйдут {objects} объектов и {parameters} параметров из {document} ({size}). Сначала проверьте состав в карточке контекста. |
| Confirm — whole definition (actions) | Send whole definition · Keep selection only | Отправить всё определение · Оставить только выделение |
| Destructive confirmation — sign out while running | Sign out of DG: A response is still running. Signing out stops it and hides this project's chat until you sign in again. Actions: Stop and sign out · Keep working | Выход из DG: ответ ещё формируется. Выход остановит его и скроет чат проекта до повторного входа. Действия: Остановить и выйти · Продолжить работу |
| Destructive confirmation — switch project while running | Switch project: The running response will be stopped. {project} opens in a new chat. Actions: Stop and switch · Keep working | Смена проекта: текущий ответ будет остановлен. {project} откроется в новом чате. Действия: Остановить и переключить · Продолжить работу |

| Error — DG access not ready (credentials missing) | DeGram has no DG access for {project} in this window yet. Reopen the project; if it repeats, sign in again. | У DeGram пока нет доступа к DG для {project} в этом окне. Откройте проект заново; если ошибка повторится, войдите снова. |
| Sign-out item (project picker, tray) | Sign out of DG | Выйти из DG |
| Context card — document read blocked (one bridge) | {document}: not included — {reason} | {document}: не включён — {reason} |
| Scope strip — documents segment | Documents: {n} | Документы: {n} |

The documents segment shows n = pinned documents (0..2); with 0 the segment keeps «Выбрать документ». Rows above marked with the gap round are owned by the "Gap round 2026-10-09" section below.

No user-initiated deletion exists in 1301: local history removal on revoke (D-19) is automatic and announced by the toast above, not confirmed.

---

## Interaction contracts

| Contract | Rule | Source |
|---|---|---|
| Explicit scope | No project or document is ever chosen implicitly — not on first run, not after reconnect, not after refresh. The composer is not mounted until a project is chosen. | DGCL-01/02/04, D-13 |
| Scope change visibility | The strip and the Context card update in the same frame as the selection; the next request's payload carries the new scope; the previous project's transcript is not reused. | DGCL-02, D-19 |
| No silent document switch | Identity mismatch or closed document blocks reads and shows the copy above; the strip dot turns neutral; reselection is manual. | D-13 |
| Cancellation | One Stop does one thing (DESIGN.md); UI clears pending state synchronously; partial text stays with «Прервано»; in-flight CAD read is aborted. | D-18, DGCL-06 |
| Retry | Manual only («Повторить запрос»); never automatic. | 1300 D-10, D-18 |
| Revocation | 401/403 from any path (heartbeat, focus check, request) clears scope data before any repaint shows it. | D-08, DGCL-05 |
| Responsiveness | Pickers, Stop and the strip respond while a request streams or a bridge read is pending; no modal spinner blocks the window. | DGCL-06 |
| Payload honesty | The Context card shows what is actually sent, after server-independent client limits; secrets never enter the rendered payload. | D-17, DGCL-07 |

---

## UI Considerations

> Populated by the ui-phase UI-consideration probe (Step 9.5) after verification and lifted by plan-phase's `## UI Considerations` lift rule. Empty/error COPY lives in `## Copywriting Contract`; rows below reference it. Probe run 2026-10-04 over 8 surfaces (E1 scope strip, E2 project picker, E3 document picker, E4 context card, E5 request lifecycle, E6 DG page, E7 sign-in, E8 boot failure + dialogs); kinds confirmed with overrides E5 = form + interactive-control, E6 = media + nav + interactive-control. Resolutions accepted by owner 2026-10-04.

Applicable state considerations resolved: 38 covered, 4 backstop, 5 dismissed, 0 unresolved (47 total)

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| loading | E1 scope strip | ✅ covered | Until the first status for a bridge arrives, its segment shows a neutral StatusDot with the «Проверка» copy; the project segment reads «Выбрать проект» until a project is chosen. |
| error | E1 scope strip | ✅ covered | A bridge in off/busy/setup-incomplete/identity-mismatch shows a neutral dot and short state label; the full diagnostic (Copywriting "Error — Revit bridge off" … "pinned document gone") is in the document-picker group header and in the segment's Tip. Red is never used for these states. |
| overflow | E1 scope strip | 🧪 backstop | { statement: "When the statusbar is narrower than the strip, the company segment collapses first, then project and document names ellipsize; the two bridge segments never collapse or wrap", verification: backstop } |
| long-text | E1 scope strip | 🧪 backstop | { statement: "A segment label longer than 24 characters (Cyrillic included) ellipsizes at the end and shows the full value in OverflowTip without changing statusbar height", verification: backstop } |
| empty | E2 project picker | ✅ covered | No project chosen → "Empty — no project chosen" copy as the content-column EmptyState; zero authorized projects → "Empty — no accessible projects" copy. |
| loading | E2 project picker | ✅ covered | While `fetchProjects` is pending, the popover list area shows the shared Loader; no project list from a previous session or user is shown meanwhile. |
| error | E2 project picker | ✅ covered | A failed project fetch shows compact ErrorState in the popover with "Error — DG server unreachable" copy and «Повторить запрос»; 401/403 follow the session/revoke interaction contract. |
| populated | E2 project picker | ✅ covered | Each row: project name (Body 13) and company (Label 11 Geist Mono, muted); the selected project carries the accent indicator. |
| partial | E2 project picker | ✅ covered | A project without a company name renders the project name alone, with no placeholder text. |
| overflow | E2 project picker | ✅ covered | Beyond 10 visible rows the list scrolls inside the popover with `overscroll-behavior-y: contain`; the popover never grows past the window. |
| zero-one-many | E2 project picker | ✅ covered | Zero → empty state; exactly one project still requires an explicit click (never auto-selected); more than 7 → SearchField appears above the list. |
| long-text | E2 project picker | ✅ covered | Long project names ellipsize within the row; the full name is in OverflowTip. |
| empty | E3 document picker | ✅ covered | No open documents on any bridge → "Empty — no open documents" copy. |
| loading | E3 document picker | ✅ covered | Each bridge group loads independently: a pending group shows one row with the small glyph spinner and «Проверка»; ready groups are selectable without waiting for the others. |
| error | E3 document picker | ✅ covered | An off/busy/setup-incomplete bridge renders its group as one neutral notice row with the matching diagnostic copy; other bridge groups remain usable. |
| populated | E3 document picker | ✅ covered | Two-line rows grouped by bridge (app glyph + name; path · identity in Geist Mono 11); the pinned row has the accent leading dot. |
| partial | E3 document picker | ✅ covered | An unsaved document shows «Не сохранён» in place of the path; a document without identity is listed disabled with «Нельзя закрепить: нет идентификатора документа». |
| overflow | E3 document picker | ✅ covered | The list scrolls inside the popover; bridge group headings stay sticky. |
| zero-one-many | E3 document picker | ✅ covered | A single open document is never auto-pinned; more than 7 rows → SearchField appears. |
| long-text | E3 document picker | 🧪 backstop | { statement: "Long Windows paths middle-ellipsize (drive and file name stay visible), full path in OverflowTip, at 900px window width with a Cyrillic file name", verification: backstop } |
| empty | E4 context card | ✅ covered | No document → "Context card — no document" copy; empty selection → "Context card — empty selection" copy. |
| loading | E4 context card | ✅ covered | While a snapshot read is in flight, the counts show the glyph spinner and Send is disabled until the read finishes; Stop aborts the read (D-18). |
| error | E4 context card | ✅ covered | A failed snapshot read shows the bridge diagnostic inline in the card with «Повторить чтение»; nothing stale from the previous snapshot is sent. |
| populated | E4 context card | ✅ covered | Summary line: project · document · objects · parameters · rules · fragments · size; disclosure caret reveals the exact payload. |
| partial | E4 context card | ✅ covered | Truncation shows `Badge warn` «Сокращено: {kept} из {total}»; missing data shows `Badge warn` «Нет данных: {what}». |
| overflow | E4 context card | 🧪 backstop | { statement: "The payload LogView has a capped height with internal scroll that hands vertical scrolling back to the thread at its edges; the composer stack never pushes the transcript off-screen", verification: backstop } |
| zero-one-many | E4 context card | ✅ covered | Counts use i18n plural forms (ru: 1 объект / 2 объекта / 5 объектов); zero counts render as 0, never hidden. |
| long-text | E4 context card | ✅ covered | The document name ellipsizes in the summary; payload text wraps inside LogView, so the page never scrolls horizontally. |
| empty | E5 request lifecycle | ✅ covered | With no project the composer is not mounted; an empty composer keeps «Отправить модели» disabled. |
| loading | E5 request lifecycle | ✅ covered | A streaming reply uses the upstream assistant-ui streaming render and midground cursor; «Остановить ответ» stays visible and responsive throughout. |
| error | E5 request lifecycle | ✅ covered | A failure shows the composer error banner with the specific cause copy (server, model service, timeout, limit, bridge) and «Повторить запрос»; never retried automatically. |
| partial | E5 request lifecycle | ✅ covered | Stopping or failing mid-stream keeps the partial text with a `Badge muted` «Прервано». |
| long-text | E5 request lifecycle | dismissed | Transcript long-text handling is upstream assistant-ui behavior, unchanged by this phase. |
| empty | E6 DG page | ✅ covered | Before sign-in or project selection, the DG page shows the same project EmptyState, never a blank view. |
| loading | E6 DG page | ✅ covered | The shared Loader is centered over the view until the first page paint completes. |
| error | E6 DG page | ✅ covered | A failed load shows ErrorState with "Error — DG server unreachable" copy and «Перезагрузить страницу». |
| populated | E6 DG page | ✅ covered | DG web fills the page below a single toolbar row (segmented «Граф проекта / Полный DG» on the left, reload on the right). |
| overflow | E6 DG page | ✅ covered | The web view owns its own scrolling; the shell page itself never scrolls. |
| long-text | E6 DG page | dismissed | Text inside the DG web is owned by ui-v2 and is unchanged by this phase. |
| empty | E7 sign-in | dismissed | The DG login form is the existing ui-v2 page opened unchanged (D-05); DeGram adds no form. |
| loading | E7 sign-in | ✅ covered | The shared Loader with «Подключение к DG» shows until the login page paints. |
| error | E7 sign-in | ✅ covered | Unreachable server → ErrorState with "Error — DG server unreachable" copy and «Повторить запрос»; after a 401 the "Error — session ended" copy sits above the login view. |
| partial | E7 sign-in | dismissed | Login form validation and partial input are owned by the ui-v2 login page. |
| overflow | E7 sign-in | ✅ covered | The login view scrolls inside its own WebContentsView; the wordmark stays fixed above it. |
| long-text | E7 sign-in | dismissed | The only DeGram text here is the fixed wordmark «DeGram». |
| overflow | E8 boot failure + dialogs | ✅ covered | Boot failure detail sits in LogView with wrapping and internal scroll; ConfirmDialog bodies have a capped height with scroll. |
| long-text | E8 boot failure + dialogs | ✅ covered | The overlapping path in the runtime-isolation failure wraps (mono, break-all) and is never truncated — the user needs the full path to fix it. |

---

## Gap round 2026-10-09 (G-3..G-17, D-29)

Source: live run of 0.1.5 on PC1 (`1301-UAT.md`, gaps G-3..G-17) and decision D-29 (two pins). This section is the single owner of the copy and contracts used by plans 18-21; later plans read it and do not edit it. The four new Copywriting rows (credentials missing, sign-out item, document read blocked, documents segment) are defined in the table above.

| Contract | Rule | Source |
|---|---|---|
| Scope route | The chat, the session list and Send run on the ready scope's profile; while the active gateway route and the scope profile disagree, Send is disabled and no request goes out. A route restored from a previous run is replaced at boot, not kept. | G-7, D-19 |
| Sessions list | A scope switch empties «Сеансы» and the open transcript in the same frame; only sessions of the active scope are listed. | G-3, D-19 |
| Provider failures | In variant degram a failed turn shows the DeGram outcome copy; no provider, model, key, logs, diagnostics or raw-error actions are offered. | G-4 |
| Preview timeout | A CAD preview that gets no bridge answer within 20 s shows the Revit busy or Grasshopper busy copy; a preview RPC with no answer shows "Error — timeout" with its seconds; neither shows "DG server unreachable". | G-14 |
| Boot with DG unreachable | E7 ErrorState with «Повторить запрос» replaces any blank view; Retry re-runs the DG check and reloads the DG view. | G-16 |
| Revoke notice | The access-revoked toast renders above the full-window gate surface, and every local profile of that user + project is removed, whatever company it was opened under. | G-15 |
| Sign-out | «Выйти из DG» in the project picker menu and in the tray menu runs `requestDegramSignOut()`; the existing ConfirmDialog shows while a response runs. | G-17 |
| Two pins | One pinned document per bridge (D-29, G-13). The Revit and Grasshopper strip segments each carry their pinned document name and the accent dot. The Context card shows one summary line per pinned document (document · objects · parameters) plus one project line (rules · fragments · size). Identity loss, a closed document, a busy bridge or ROUTES_NOT_LOOPBACK excludes only that bridge's document, shown with the "document read blocked" row and `Badge warn`, while Send stays available for the rest. Whole-definition scope stays Grasshopper-only. A project switch clears both pins. | D-29, G-13 |

Component inventory rows "Scope strip" and "Context card" are superseded where they say "document" in the singular: read them through the Two pins contract above.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none added in this phase — all primitives already exist in `apps/degram/apps/desktop/src/components/ui/` | not required |
| third-party | none | not applicable |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-10-04 — inline check: 6/6 PASS, no FLAGs after two copy fixes (Send label, unknown-reset limit copy). Check was not independent of the author.

---

## Amendment 2026-10-10 (0.1.7 gap round)

This amendment is authoritative for the 0.1.7 gap round. Where it conflicts with the earlier D-14/D-19 singular-picker or separate-picker-screen wording, this amendment supersedes that wording.

### D-33 — one start screen

DeGram has one start screen: the wordmark and DG view are present together. Before sign-in it shows the DG login; after sign-in it shows the Projects region in that same view. If the signed-in user has no pairing, the pairing-token field is docked below the view. Notices render above the view. There is no second «Выберите проект» screen and no standalone «Подключение к DG» card/screen. While a project is open, the scope-strip project switcher remains the project-switch surface.

### D-34 — hide management menus in DeGram

The embedded DeGram DG surface hides the **Connectors**, **DG API Docs**, **Reasoner**, and **AI Engine** menu entries. Pairing tokens are created on the Connectors tab in DG opened in a browser, not inside the DeGram view.

### D-35 — revoked pairing

When an exchange or the start-time probe finds a revoked pairing, the start screen retains the pairing status `revoked`, focuses the token field, and displays:

> Токен сопряжения отозван. Создайте новый на вкладке Connectors в DG (в браузере) и вставьте его ниже.

The same notice is used whether the refusal occurs during a request or during the once-per-start probe. It never describes a revoked pairing as an expired token being renewed.

### G-20 — access-revoke notice

The following notice remains on the start screen until the user dismisses it or chooses a project:

> У вас больше нет доступа к {project}. Его данные и локальная история чата удалены с этого компьютера.

### D-31 — scoped sessions

The session list contains only sessions belonging to the active scope. Its empty state is «В этом проекте пока нет сеансов.» No session belonging to another scope is displayed or reachable there.

### G-24 — model request limit copy

Rate-limit outcomes use model-limit wording without naming a provider or model and without saying «для проекта»:

- Known reset: «Лимит запросов к модели исчерпан. Повторите после {time} или обратитесь к оператору DG.»
- Unknown reset: «Лимит запросов к модели исчерпан. Повторите позже или уточните у оператора DG, когда лимит обновится.»

### G-18 — backend start failure

If the agent backend cannot start, DeGram stays on the start screen rather than silently returning to the picker. It shows «Не удалось запустить агента для проекта {project}.» and offers «Повторить запрос».


## Amendment 2026-10-11 (0.1.10 gap round: D-39..D-44)

This amendment is authoritative for plans 30-36. It supersedes the D-33 «pairing-token field docked below the view», D-34's «pairing tokens are created on the Connectors tab» and D-35 (pairing retired by D-39).

### D-39 — access without a token

The start screen has no token field. After DG sign-in the user picks a project in PROJECTS; DeGram opens it when the project owner or a DG admin has issued a grant. Without a grant the start screen keeps this notice until dismissed:

> Доступ DeGram к проекту {project} ещё не выдан. Запросите его в разделе «Коннекторы» или у владельца проекта.

EN: «DeGram access to {project} has not been granted yet. Request it under Connectors or ask the project owner.»

### D-40 — Коннекторы inside DeGram

The DG CONNECTORS page in DeGram shows only the user's own grants for the active project (name, purpose, issued, last used) and one button «Запросить новый токен / Request a new token» (optional note). After a request: «Запрос отправлен»; with an active grant: «Доступ уже выдан». No key, token or copy control exists anywhere. In the DG Web UI outside DeGram, owners and admins see a member dropdown, «Название», «Назначение», «Выдать доступ», the grants list with «Отозвать», and pending requests with «Выдать».

### D-44 — connecting state on the ring

From the PROJECTS click until the project is open, the ring centre shows «Подключение к DG / Connecting to DG» with the Graph Viewer thinking sphere, replacing the hero headings, the user line and Sign out. Swap uses the landing fade (opacity + translateY 18px + blur 9px, 500-560 ms, cubic-bezier(0.2,0,0,1)). Cyrillic text uses the body font stack (the bundled Michroma subset is Latin-only).

### D-41 — new-session pill

When the project is open the hero returns with «System initiated · {project}» and Sign out, and the pill «Начать новую сессию / Start new session» fades in under Sign out (same fade). The chat opens only from the pill or from a row in the session history; choosing a project never opens a chat by itself.

### D-42 — DeGram sidebar and start screen

No «DEGRAM» heading above the start screen. With a project open the sidebar shows, in order: «Новая сессия», «Граф проекта» (Graph Viewer), «Валидатор» (Model Viewer), «Коннекторы», «Модели», «Меню» (Menu, the DG landing), then «Закреплённые» and the session history, both limited to the active project and user. No other inherited entries, tabs (БОТЫ), sections (messages, scheduled tasks) or «Новый проект» are shown. Граф проекта / Валидатор / Коннекторы / Меню switch the DG view in place; the graph/full toggle is removed.

### D-43 — «Модели»

«Модели» lists each connector (Revit, Grasshopper, further bridges) with its status and the documents it exposes; the user pins one document per bridge there (D-29), with refresh and «Открепить». The bottom strip keeps company, project and the per-bridge status only.

---
phase: 1301
plan: 45
status: implementation-contract
---

# DeGram target selector supplement

Additive to 1301-UI-SPEC.md; its historic ring, sidebar, mapping and permission decisions are unchanged. This supplement adds only Developer/Demo target selection and disclosure. No live Desktop launch or visual acceptance is authorized here; plan 47 retains those gates.

## Placement and bounds

`src/app/contrib/controller.tsx` reserves a normal-flow `DgTargetSelector working` header immediately before `LayoutTreeRoot`. `DegramShellHost` is a sibling mounted after the layout, not its wrapper, so placing the header there would not reserve space above the native view. The pre-auth `DegramGate.Surface` renders the same selector above its content, rather than underneath its blocking overlay. Only one selector is interactive at a time. On the DG page the native view's bounds must start below the header; the sign-in view's measured host starts below the gate header. A native WebContentsView cannot be covered by CSS z-index: reserve measured vertical space, never overlay controls on its rectangle. The selector survives an unreachable embedded page.

Use existing Button/Select primitives, spacing and theme tokens. No new fonts, assets, design system or ring/sidebar redesign. At narrow widths labels/origins wrap with break-all/min-width:0; do not clip the canonical origin or produce horizontal window scrolling. Working shell content remains mounted when switching; hide target-bound content behind the existing gate until main publishes a valid ready runtime.

## Authority

Read descriptors exclusively from `getEnvironment`/`onEnvironment`. Show selected mode and selected origin separately from effective origin whenever they differ. Developer Mode and Demo Mode are configured target IDs, not user-editable URLs. Send configured mode plus current environmentId and expected generation to typed main IPC. Do not optimistically declare readiness or navigate the window. A receipt/event is authoritative only if its generation is not stale and its descriptor agrees with the active environment. Main enforces busy/override restrictions; disabling controls is secondary protection.

## State inventory

| State | Header and content |
| --- | --- |
| Before first main reply | Mode header with connecting copy; no invented localhost default; controls disabled. |
| Signed out / no project | Mode and effective origin remain visible above the login/project surface. Project/chat/documents are explicitly empty; no remembered project is auto-opened. |
| Ready | Selected mode and canonical effective origin; selector enabled unless override locked. Existing membership/grant authority is unchanged. |
| Switching | Main selected mode/origin and effective origin (or explicit no-runtime copy); switching status; controls disabled. No automatic cancellation or resend. |
| Busy refusal | Keep definitive main state and old operation. Say finish or Stop the current operation, then retry. No promise that switching cancels work. |
| Override lock | Show override lock and origin; mode selector disabled. Explain that launch override must be removed and application explicitly restarted. |
| DG unreachable / TLS / login or grant error | Target remains visible; existing auth/grant/unreachable diagnostics stay in their own surface. Never disable TLS checks, fall back to another origin or expose provider-key UI. |
| Startup / teardown failure | Selected intent remains visible, effective runtime may be empty; explicit retry only. Do not imply that the previous target resumed. |
| Invalid configuration | Explicit configuration error, no effective origin, no active selector; repair configuration and restart. Never invent a descriptor. |

## Localized copy and accessibility

Keep Developer Mode / Demo Mode names recognizable in both locales. RU labels: «Среда DG», «Выбрано», «Активный адрес», «Нет активной среды», «Переключение среды…», «Завершите или остановите текущую операцию и повторите выбор», «Адрес задан при запуске. Уберите переопределение и перезапустите DeGram». EN equivalents: “DG environment”, “Selected”, “Effective origin”, “No active environment”, “Switching environment…”, “Finish or Stop the current operation, then retry”, “A launch override locks this target. Remove it and restart DeGram”. Configuration and startup/teardown failures name the actual failure without raw secrets.

Use a labelled keyboard-operable select, named retry Button and polite status region for transition/refusal copy. Tab order: mode, retry when available, then existing content. Native window dragging excludes interactive controls. An explicit selection returns focus to the mode control after completion, including the gate-to-working-header handoff; do not navigate, autofocus login/project, steal chat focus without an explicit switch or auto-open a project. A pending control stays on its current surface until the authoritative gate/working state changes; keep the shell mounted rather than replacing it. Accessible names include the mode/origin labels; status must not depend on color.

## Renderer isolation

Transient scope identity includes environmentId, generation, authenticated user, company, project and scope epoch. Durable environment-owned histories are not deleted; fresh authentication and membership validation precede restore. Reject late initial reads, events, gateway callbacks and receipts before publication. Clear active route/session/document/mapping/preview and armed consent caches before painting a new environment. Main-issued leases span preview, confirmation/armed Send, streaming and native/mapping dispatch through settled completion/cancel. Consent and retries never migrate to another target.

## Acceptance boundary

Offline tests cover selector states, typed IPC, keyboard names, equal-epoch collisions and late replies using actual renderer stores. jsdom cannot prove native bounds, visual wrapping, TLS or localhost/Contabo connectivity; those remain plan 47 live checks. DGMODE/DGCL/HOST-05 and full Phase 1301 remain open.

---
phase: 815-dg-api-documentation
reviewed: 2026-07-11T16:30:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - ui-v2/src/screens/ApiDocsScreen.jsx
  - ui-v2/src/screens/apidocs/content/index.js
  - ui-v2/src/screens/apidocs/content/01-getting-started.js
  - ui-v2/src/screens/apidocs/content/02-authentication.js
  - ui-v2/src/screens/apidocs/content/03-credentials-api.js
  - ui-v2/src/screens/apidocs/content/04-heartbeat-api.js
  - ui-v2/src/screens/apidocs/content/05-connectors-status-api.js
  - ui-v2/src/screens/apidocs/content/06-validation-publish-api.js
  - ui-v2/src/screens/apidocs/content/07-extending.js
findings:
  critical: 1
  warning: 1
  info: 4
  total: 6
status: issues_found
---

# Phase 815: Code Review Report — DG API Documentation Browser

**Reviewed:** 2026-07-11T16:30:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The API documentation browser implements a Revit-API-style two-pane layout (navigation tree + detail pane) with typed content blocks rendered via `import.meta.glob` auto-discovery. The component structure and content modules are well-organized, with clean separation between viewer code and content.

One critical issue renders the entire feature non-functional: the `import.meta.glob` glob pattern `##-*.js` does not match any of the actual content files (named `01-getting-started.js`, `02-authentication.js`, etc.), so the content tree loads empty. Additionally, there is one unused import and several quality concerns around React patterns.

## Critical Issues

### CR-01: Glob pattern does not match any content files

**File:** `ui-v2/src/screens/apidocs/content/index.js:6`
**Issue:** The `import.meta.glob("./##-*.js", { eager: true })` pattern requires files whose names begin with `##-` (e.g., `##-01-getting-started.js`). However, the actual content files are named `01-getting-started.js`, `02-authentication.js`, `03-credentials-api.js`, `04-heartbeat-api.js`, `05-connectors-status-api.js`, `06-validation-publish-api.js`, and `07-extending.js` -- none of which match the `##-*.js` glob. In fast-glob (which Vite uses), `#` is not a glob metacharacter, so `##-` is matched literally.

**Consequence:** `import.meta.glob` returns an empty modules object. The `entries` array is empty. `sections` exports as `[]`. The API Docs screen renders with no tree entries and a permanently empty detail pane showing "Select a page from the tree." The feature is completely non-functional, preventing all users from viewing any API documentation.

**Fix:** Align either the glob pattern with the file names, or the file names with the glob pattern. The documentation in `07-extending.js` (lines 11, 28, 55) consistently references the `##-<slug>.js` naming convention, so renaming the content files is the more architecturally consistent fix:

Option A -- Rename content files to match the documented convention (preferred, since `07-extending.js` documents `##-<slug>.js`):

```
##-01-getting-started.js   (was 01-getting-started.js)
##-02-authentication.js     (was 02-authentication.js)
##-03-credentials-api.js    (was 03-credentials-api.js)
##-04-heartbeat-api.js      (was 04-heartbeat-api.js)
##-05-connectors-status-api.js  (was 05-connectors-status-api.js)
##-06-validation-publish-api.js (was 06-validation-publish-api.js)
##-07-extending.js           (was 07-extending.js)
```

Option B -- Change the glob pattern to match actual file names:

```javascript
// index.js line 6 — change to:
const modules = import.meta.glob("./[0-9][0-9]-*.js", { eager: true });
```

## Warnings

### WR-01: Unused import `Badge`

**File:** `ui-v2/src/screens/ApiDocsScreen.jsx:2`
**Issue:** `Badge` is destructured from the components import but never used anywhere in the component -- not in `EndpointBlock`, `BlockRenderer`, `TreeSection`, or `ApiDocsScreen`. This is dead code that will trigger lint warnings and adds unnecessary bytes to the bundle.

**Fix:** Remove `Badge` from the import statement:

```javascript
import { Button, CodeBlock } from "../components/index.js";
```

## Info

### IN-01: Array index used as React key in multiple maps

**Files:** `ui-v2/src/screens/ApiDocsScreen.jsx:54,106,111,113,311`
**Issue:** Five `.map()` calls in this file use the array index (`key={i}` / `key={j}`) as the React key prop. While acceptable for static content that will never be reordered, using array indices as keys is a React anti-pattern that prevents correct reconciliation if content is ever dynamically filtered, sorted, or reordered. The five locations are:

- Line 54: `block.params.map((p, i) => <tr key={i}>`
- Line 106: `block.headers.map((h, i) => <th key={i}>`
- Line 111: `block.rows.map((row, i) => <tr key={i}>`
- Line 113: `row.map((cellVal, j) => <td key={j}>`
- Line 311: `currentPage.blocks.map((block, i) => <div key={i}>`

**Fix:** Where a unique identifier exists (e.g., `params` have a `name` property), use it as the key instead of the index. For static-only data where no ID is available, this is acceptable but worth documenting with a comment:

```javascript
// lines 53-55:
{block.params.map((p, i) => (
  <tr key={p.name}>  {/* p.name is unique within an endpoint's params list */}
```

### IN-02: Hover state managed via direct DOM mutation instead of CSS

**Files:** `ui-v2/src/screens/ApiDocsScreen.jsx:166-167,196-201`
**Issue:** The `TreeSection` component manages hover highlight for section headers and page items by directly mutating `e.currentTarget.style.background` in `onMouseEnter`/`onMouseLeave` handlers. This bypasses React's rendering pipeline: if the component re-renders while an item is hovered, the hover background is lost. On re-render (e.g., user selects a different page), any active hover state is dropped abruptly rather than smoothly continuing. Using `:hover` CSS pseudo-classes would be more maintainable and reliable.

**Fix:** Replace inline event handlers with CSS classes:

```css
/* In a CSS module or stylesheet */
.treeHeader:hover {
  background: var(--color-signal-soft);
}
.treePage:hover {
  background: var(--ink-a04);
}
```

Or use React state for hover tracking if conditional styles are needed.

### IN-03: Unused `project` prop

**File:** `ui-v2/src/screens/ApiDocsScreen.jsx:220`
**Issue:** The `project` parameter is destructured from props but never referenced in the component body. The API documentation content is static and does not filter by project. This is misleading to future maintainers who may assume the screen personalizes content by project.

**Fix:** Either remove `project` from the destructuring (if no future use is intended), or keep it with a comment documenting the intended use case.

```javascript
// Option A — remove unused prop:
export default function ApiDocsScreen({ active, onBack }) {

// Option B — document future intent:
export default function ApiDocsScreen({ active, onBack, project /* unused — reserved for per-project doc filtering */ }) {
```

### IN-04: Inconsistent parameter `location` value

**File:** `ui-v2/src/screens/apidocs/content/03-credentials-api.js:20`
**Issue:** The `label` parameter's location is set to `"body (optional)"` (with qualifier embedded in the value). Every other endpoint parameter uses a bare location string (`"path"`, `"body"`, `"header"`). While the `EndpointBlock` component renders this value as-is (no programmatic enum), the inconsistency creates ambiguity: `"body (optional)"` mixes location semantics with requirement semantics, and the table column header says "Location" not "Location + Requirement".

**Fix:** Use `"body"` consistently for the location value (the `required: false` field already conveys optionality), or alternatively rename the column header to accommodate combined values:

```javascript
// Line 20 of 03-credentials-api.js — change location to "body":
{ name: "label", type: "string | null", location: "body", required: false, description: "..." },
```

---

_Reviewed: 2026-07-11T16:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

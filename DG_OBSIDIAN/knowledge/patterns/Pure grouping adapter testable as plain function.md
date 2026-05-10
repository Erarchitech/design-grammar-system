---
tags: [pattern, react, testing, vitest, model-viewer]
date: 2026-05-10
---

# Pure Grouping Adapter Testable as Plain Function

## Pattern

When a React component needs to derive a grouped/sorted/filtered shape from props, extract that derivation into a **plain function** named with the `useFoo` convention but containing no React hooks. Call it from `React.useMemo` inside the component, and unit-test it directly with Vitest as a pure function.

```js
// useValidationRunsGrouping.js — plain function despite useFoo name
export function useValidationRunsGrouping(runs, mode) {
  if (!Array.isArray(runs) || runs.length === 0) return [];
  // ...grouping logic...
  return groups;
}

// Component — uses useMemo to memoize result
const groups = React.useMemo(
  () => useValidationRunsGrouping(validationRuns, mode),
  [validationRuns, mode]
);

// Test — direct function call, no React, no DOM
import { useValidationRunsGrouping } from "./useValidationRunsGrouping.js";
expect(useValidationRunsGrouping([...], "rule")).toEqual([...]);
```

## Why

- **No React renderer in tests.** Vitest spins up in `node` environment with no JSDOM overhead.
- **No `renderHook` ceremony.** No `@testing-library/react-hooks`. Just call the function.
- **Memoization stays in the consumer.** The component decides when to recompute via `useMemo` deps. The adapter doesn't try to memoize internally (which would require `useRef`/`useMemo` and tie it to React's render cycle).
- **Easy to inline-replace.** If a caller doesn't need memoization (e.g., a one-off transformation in a server-side script), the function works as-is.

## When to Apply

- Pure data transformations driven by props.
- Sort/group/filter pipelines with deterministic output.
- Anything you'd otherwise put inside a `useMemo` that's > 5 lines.

## When NOT to Apply

- Logic that needs to subscribe to external stores (`useSyncExternalStore` etc.).
- Logic that owns lifecycle effects (`useEffect`).
- Logic that needs React state of its own — those should be true custom hooks.

## Naming Caveat

The `useFoo` prefix is a lint signal to React tooling that this is a hook. ESLint's `react-hooks/rules-of-hooks` will not complain about a plain function named `useFoo` as long as it doesn't call other hooks. Some teams prefer `getFoo` or `computeFoo` to avoid confusion — pick one convention per repo. This codebase uses `useFoo` to telegraph "intended for use inside `useMemo` of a hook-enabled context".

## Related

- [[ValidationRunsStrip component with per-project localStorage persistence]]
- [[Pydantic models validate all API boundaries]]

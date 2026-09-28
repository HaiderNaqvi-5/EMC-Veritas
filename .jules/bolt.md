## 2024-09-28 - Avoid O(N) filtering in forms
**Learning:** Found instances where lists were filtered synchronously on every re-render (e.g. from keystrokes in a form) rather than being memoized based on their source data dependency.
**Action:** Always wrap heavy list operations (like filtering or creating Maps/Sets) in `useMemo` when they depend on API data in form components to prevent O(N) recalculations on every keystroke.

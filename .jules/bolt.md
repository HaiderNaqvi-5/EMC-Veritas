
## 2024-05-18 - Memoizing Derived React Query Data
**Learning:** `useQuery` from `@tanstack/react-query` will trigger re-renders even when the underlying data hasn't conceptually changed. When deriving state with `.filter()` and `.map()` from `useQuery.data`, failing to wrap these operations in `useMemo` causes O(n) array allocations on every render.
**Action:** Always wrap `.filter()` and `.map()` calls that derive arrays/metrics from `useQuery` responses in `useMemo` to prevent unnecessary allocations, especially on list views (like activities or admin dashboards).

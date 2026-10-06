## 2024-11-20 - Fix N+1 queries in leadership recognition issuance
**Learning:** Found an O(N*M) N+1 query problem inside a nested loop in `_preflight_session_recognition` where N is the number of completed memberships and M is the number of document types. Replacing inside-loop queries with bulk `IN` clauses fetching everything and doing in-memory lookup via dictionary significantly improves query count.
**Action:** Always inspect loop iteration code that fetches data to verify if pre-fetching the whole needed block works instead.

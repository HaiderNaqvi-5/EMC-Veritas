
## 2024-05-18 - [Resolve N+1 Queries in pre-generation]
**Learning:** In SQLAlchemy, executing `db.get()` or `db.scalars()` inside a loop can lead to N+1 query performance bottlenecks.
**Action:** Always prefetch related rows outside of loops using `.in_()` clauses and dictionary mappings instead of querying inside the loop.

## 2026-10-05 - N+1 query bottlenecks in FastAPI/SQLAlchemy backend
**Learning:** Calling `db.get()` or `db.scalars()` inside a loop can lead to N+1 query performance bottlenecks. This can significantly slow down API endpoints, especially those dealing with batches of items like generating multiple documents.
**Action:** Always bulk fetch related rows outside of loops using `.in_()` clauses and dictionary mappings instead of executing `db.get` or `db.scalars` inside loops.


## 2023-10-27 - N+1 Query Anti-Pattern in Loop
**Learning:** Found an N+1 query bottleneck in `backend/app/api/admin/documents.py` inside `pre_generate_activity_documents`. It was using `db.get` and `db.scalars` inside a `for` loop to fetch related objects individually.
**Action:** Always bulk fetch related rows outside of loops using `.in_()` clauses and map them into Python dictionaries for fast O(1) lookups inside the loop. Avoid database queries inside loops at all costs.

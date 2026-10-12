
## 2024-10-12 - Prevent N+1 queries during bulk session recognition
**Learning:** During batch leadership recognition document issuance (e.g., when a session closes), multiple redundant `db.scalar` and `db.scalars().all()` calls were being made *inside* nested loops (over each executive membership and each document type) to lookup existing documents, leadership templates, and template fields. This caused an O(N*M) query explosion that scales poorly with session size.
**Action:** When performing batch operations over a collection of records (like executive memberships), extract the unique IDs first, pre-fetch all required related records (using `.in_()` clauses) into dictionaries/sets, and then perform dictionary lookups inside the loop instead of executing database queries.

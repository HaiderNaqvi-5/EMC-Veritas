## YYYY-MM-DD - [N+1 Optimization in Document Issuance]
**Learning:** Found a classical N+1 bottleneck when issuing certificates in `backend/app/api/admin/documents.py`. The initial code fetched a list of valid participant IDs, then performed an individual lookup (`db.get(Student, student_id)`) per student within the processing loop.
**Action:** Replace sequential `db.get()` ORM calls with a single `JOIN` query selecting the full entities upfront when processing batches of dependent records.

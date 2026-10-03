## 2024-05-18 - [Fix N+1 query issue in bulk import]
**Learning:** Bulk imports of Excel files were querying the database once per row, leading to an N+1 problem. The `db.scalar()` call within loops can become a significant bottleneck when reading potentially hundreds of rows from spreadsheet.
**Action:** Always batch query records when dealing with imports or loops, specifically looking out for `db.scalar()` calls within loops over items from an uploaded file.

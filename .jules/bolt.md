## 2023-10-10 - Optimizing N+1 External Storage Downloads
**Learning:** Eagerly downloading external storage files (like `storage.download()` for Supabase) inside a loop causes a severe network bottleneck. Similarly, executing `db.get` or `db.scalars` inside loops leads to database N+1 bottlenecks.
**Action:** Always bulk-fetch database records (e.g. `Student`, `Template`, `TemplateField`) outside loops using `.in_()` clauses and dictionary mappings. Use an in-memory dictionary cache to prevent redundant external network I/O across loop iterations for external files.

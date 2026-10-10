
## 2023-10-10 - Cached External Storage Downloads in Batch Operations
**Learning:** During batch operations (like `_pre_generate_activity_document_batch`), downloading external storage assets (templates, signatures) inside the loop causes redundant network I/O and latency.
**Action:** Always pre-fetch or implement an in-memory dictionary cache to store and reuse these external assets across loop iterations, deferring the actual download until inside the loop where they are conditionally required.

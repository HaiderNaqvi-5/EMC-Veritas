## 2024-10-08 - Caching API Network I/O inside batch loops
**Learning:** During batch creation, repeated identical downloads for template PDFs and signatures within `pre_generate_activity_documents` caused unnecessary network I/O per iteration.
**Action:** Always maintain an in-memory dictionary cache scoped to the endpoint when looping over objects requiring the same static remote storage assets.

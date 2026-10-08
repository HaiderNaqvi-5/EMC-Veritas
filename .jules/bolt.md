## 2025-02-28 - Supabase Storage Downloads Bottleneck
**Learning:** During batch document generation (`pre_generate_activity_documents`), downloading template PDFs and signatures individually via `storage.download` for every loop iteration introduces a severe N+1 network I/O bottleneck against Supabase Storage.
**Action:** Always provide an explicit in-memory dictionary `cache` to `SupabaseStorage(cache={})` during batch generations or tight loops to safely memoize redundant external HTTP download requests across iterations.

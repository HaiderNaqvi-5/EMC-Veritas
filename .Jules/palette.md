## 2026-09-24 - [Accessible Forms and Clear Button States]
**Learning:** Forms lacking explicit label associations make it difficult for screen reader users to understand what data is expected. Furthermore, buttons without loading/disabled states provide poor feedback during async operations, which can lead to multiple submissions or user confusion.
**Action:** Always wrap inputs in or associate them with explicit `<label>` elements, and provide visual/textual feedback (e.g., 'Adding student...', disabled styles) on submit buttons when an operation is pending.

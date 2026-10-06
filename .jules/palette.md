## 2024-05-18 - Prevent accidental destructive operations
**Learning:** Destructive operations on admin pages lacked safety checks, which can lead to accidental data loss.
**Action:** Added `window.confirm` dialogues before executing mutate calls for delete, remove, revoke, and complete actions in `ActivitiesPage`, `DocumentsPage`, and `ExecutiveMembershipsPage`.

## 2024-05-18 - Missing confirmations on destructive actions
**Learning:** Found several pages (Activities, Documents, Executive Memberships) where destructive actions (delete, revoke, remove, complete) lack `window.confirm` dialogues. The application needs consistent confirmation barriers for state-altering actions, especially irreversible ones.
**Action:** Adding `window.confirm` to these destructive actions to prevent accidental data loss/modification.

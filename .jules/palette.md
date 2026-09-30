## 2024-11-20 - Adding explicit destructive guard
**Learning:** Found multiple UI components allowing administrative deletions without confirmation. React queries directly issue remove/revoke mutations immediately on button clicks.
**Action:** Always wrap destructive admin operations (like `.mutate()`) with simple `window.confirm()` barriers to avoid immediate actions and data loss.

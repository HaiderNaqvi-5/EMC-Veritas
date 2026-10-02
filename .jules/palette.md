## 2024-05-18 - Missing Confirmation Barriers
**Learning:** Destructive operations (like complete, remove, or revoke actions) were directly executing `mutate()` without confirmation barriers. This can lead to accidental data loss.
**Action:** Always ensure destructive operations in the UI wrap the execution (e.g. `window.confirm("Are you sure?")`) to add a friction layer that prevents mistakes.

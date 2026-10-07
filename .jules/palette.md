## 2023-10-27 - Added confirmation dialogs to destructive actions
**Learning:** Destructive operations like deleting activities, revoking documents, removing memberships, and deleting templates were missing confirmation barriers, potentially leading to accidental data loss. This is a common pattern to look out for.
**Action:** Always ensure that any action that modifies or deletes important data has a confirmation dialog (like `window.confirm`) to prevent accidental user errors.

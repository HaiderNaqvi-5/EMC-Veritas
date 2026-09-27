
## 2024-03-24 - Missing Confirmation Dialogs
**Learning:** Found critical functionality missing `window.confirm` dialogs for destructive actions like deleting or revoking records. This omission could lead to accidental, irreversible data loss.
**Action:** Always verify if destructive operations (`complete`, `remove`, `revoke`) have confirmation barriers before mutating data.

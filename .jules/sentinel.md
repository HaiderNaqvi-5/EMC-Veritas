## 2023-11-20 - Authorization Bypass via Missing Database Validation
**Vulnerability:** The `require_admin` dependency in `backend/app/api/admin/students.py` only verified the presence of `admin_id` in the session cookie, without querying the database to ensure the administrator account was still active.
**Learning:** Checking only the session state allows deactivated administrators to retain access until their session expires or is cleared, which is an authorization bypass.
**Prevention:** Always validate session identifiers against the current state in the database, especially for sensitive roles and actions. Use dependencies like `current_active_admin` which perform this verification.

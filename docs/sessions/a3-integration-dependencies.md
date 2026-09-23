# A3 integration dependencies

## Haider dependency checklist by phase

### A1

- Applied Alembic/database baseline and the `Admin`/`Student` models.
- Supabase PostgreSQL and Storage configuration, readiness endpoint, and shared settings.
- Agreed authentication/session contract and schema boundary for Ahmed’s Admin shell.

### A2

- Applied tables and constraints for students, sessions, activities, and participants.
- Shared operational Pydantic schemas and stable IDs for the Admin workflow.
- Database-enforced unique roll numbers, a single active session, and one participant per student/activity.

### A3

- Signatory, template, document issuance, preview, revoke/reissue, audit, and role-guard APIs.
- The additional A3 contracts still required are listed below.

## Available Haider contracts integrated locally

- Effective-dated signatory create, history list, and deactivation.
- Certificate template PDF upload, analysis, required-field configuration, approval, and watermarked participant preview.
- Activity certificate issue action, including the backend’s missing-signatory and template-policy errors.
- Document revoke and reissue actions for a supplied issued-document ID.
- Super Admin audit-log view.

## Still required from Haider before A3 can be fully accepted

- Executive-membership API contracts and data needed to select exact EC roles and Society Heads.
- Super Admin leadership-template APIs for deterministic Letter of Recognition and End-of-Tenure templates: list, create, edit, activate, deactivate, replace, placeholder metadata, and substituted preview.
- A template list/detail contract and rendered editor data for the certificate-template UI, including stored field positions and existing-field review. The current API accepts upload/configure/approve but does not provide discovery/detail/editor-rendering data.
- Document record list/detail contract for Admin UI revoke/reissue controls. The available API supports the mutations when a document ID is known, but does not expose Admin document discovery.

These are server-owned contracts. The frontend must consume them rather than recreating role, signature, template, or issuance policy in the browser.

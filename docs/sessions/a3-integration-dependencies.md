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

## Completed local A3 integration

- Leadership-template list, upload, placeholder configuration, substituted preview, activation, deactivation, and archival are now consumed by the Super Admin UI.
- The Admin document-discovery contract is provided and consumed for revoke/reissue selection.
- The Executive Membership discovery/create/update contract is provided so role-matched memberships can be selected for leadership previews.

The frontend consumes server-side contracts and does not recreate role, signature, template, or issuance policy in the browser.

## Remaining release verification

The integrated flows require a deployed Supabase/Render environment with configured storage before they can be exercised using real templates, signatories, memberships, and issued documents.

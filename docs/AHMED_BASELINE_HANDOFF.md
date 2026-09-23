# Ahmed baseline hand-off

## Ready now

- Alembic head: `c8dc00f20398`.
- A clean database has been tested through downgrade-to-base and upgrade-to-head.
- Shared Pydantic operational contracts: `backend/app/schemas/operations.py`.
- Database constraints are authoritative for unique roll numbers, one active session, one participant per activity/student, one EC membership per student/session, and Society Head date overlap.
- Frontend and backend readiness contract: `GET /api/health/ready` returns `{ "ready": true }`.

## Ahmed-owned implementation can begin

Implement admin authentication/session flow, operational students, sessions, activities, participant import/export, and admin UX in the modules defined by the PRD. Use the shared schemas and add only new Alembic revisions for future schema changes; do not edit existing revision files after this baseline merge.

## Credentials and local setup

Do **not** copy another developer's `backend/.env`; it contains private database, Storage, and session-signing secrets. Copy `.env.example` to a personal `backend/.env` and use developer-specific Supabase credentials or a securely shared secret manager. The frontend must never receive `DATABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY`.

## Coordination rule

Before creating any migration, coordinate the revision and affected models. Before consuming any Haider-owned document/template/verification API, use the contracts published in `docs/API_CONTRACTS.md`.

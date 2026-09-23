# A2 operational workflows

## Scope

This local A2 work implements the Admin operational-record layer on the shared SQLAlchemy/Supabase foundation: students, EMC sessions, activities, participants, and a controlled XLSX student import/export workflow.

## Behaviour

- Student records can be created, listed, and deactivated without hard deletion.
- Only one session can be active; the database constraint remains authoritative.
- Activities begin in `DRAFT`, can be updated, and use explicit status transitions.
- Participants are unique within an activity and have a separately auditable eligibility value.
- XLSX uploads are previewed before commit. Invalid and duplicate rows are not committed. Name conflicts cannot overwrite existing students and require explicit skip handling.
- Participant export produces an XLSX workbook with the agreed identity, activity, date, and eligibility columns.

## Verification status

Ruff lint, all six backend tests (including readiness and spreadsheet conflict coverage), the production frontend build, and whitespace validation pass locally. The readiness test now uses an equivalent in-process ASGI request, avoiding the local TestClient shutdown hang.

# Shared API contracts

This file is the hand-off point before frontend/backend dependent work begins. Implemented schemas/OpenAPI are authoritative; updates must be coordinated.

| Endpoint | Contract | Consumer |
| --- | --- | --- |
| `GET /api/health/ready` | `{ "ready": true }` | application warm-up |
| `GET /api/public/students/{roll_number}/documents` | full student identity and documents grouped by category | student portal |
| `GET /api/public/documents/{document_id}/download` | authorized cached/generated PDF stream | document UI |
| `GET /api/public/verify/{verification_id}` | authoritative verification status and context | verification UI/QR |

Administrative contracts for templates, documents, signatories, executive memberships, leadership templates, admins, and audit logs are owned by Haider. Ahmed-owned operational contracts cover sessions, students, activities, participation, import/export, and authentication flow. Publish explicit validation errors—clients must not infer policy.

## Template administration (Super Admin only)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `POST /api/admin/templates/upload` | multipart `name` + PDF `file` → `TemplateResponse` | Stores the supplied PDF in private Storage as an unapproved template. |
| `GET /api/admin/templates/{template_id}/analysis` | `TemplateAnalysisResponse` | Returns page count, extracted text, and whether OCR is required. |
| `POST /api/admin/templates/{template_id}/fields` | `TemplateFieldsCreate` → `TemplateResponse` | Field names and one-based PDF coordinates are immutable once configured. |
| `POST /api/admin/templates/{template_id}/approve` | `TemplateResponse` | Requires student name, roll number, activity name, and activity date fields. |

Every template endpoint requires an active `SUPER_ADMIN` server session. The browser never receives a Supabase Storage credential.

## Activity certificate issuance (Admin or Super Admin)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `POST /api/admin/documents/activities/{activity_id}/issue` | `ActivityIssueResponse` | Reserves one immutable activity-certificate record for every active, eligible participant. It requires an approved template, all mandatory fields, and effective President + DSA signatories. Existing valid records are skipped. |

The service fixes the activity issue date using the EMC Pakistan business date on first issuance and records immutable audit events. It never creates PDFs during issue; final PDFs remain lazy and cached on the first valid public download.

## Ahmed baseline available now

`backend/app/schemas/operations.py` contains the shared Pydantic request/response baseline for students, sessions, activities, and XLSX import previews. Ahmed should implement his route/service modules against these models and the applied Alembic head `c8dc00f20398`; he must not create tables manually or alter existing migrations.

The admin routes are deliberately not implemented in this hand-off: they remain Ahmed-owned. The database guarantees unique student roll numbers, one active EMC session, one participant per activity/student, one EC membership per student/session, and no overlapping Society Head terms within a society/session.

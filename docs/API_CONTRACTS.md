# Shared API contracts

This file is the hand-off point before frontend/backend dependent work begins. Implemented schemas/OpenAPI are authoritative; updates must be coordinated.

| Endpoint | Contract | Consumer |
| --- | --- | --- |
| `GET /api/health/ready` | `{ "ready": true }` | application warm-up |
| `GET /api/public/students/{roll_number}/documents` | full student identity and documents grouped by category | student portal |
| `GET /api/public/documents/{document_id}/download` | authorized cached/generated PDF stream | document UI |
| `GET /api/public/verify/{verification_id}` | authoritative verification status and context | verification UI/QR |

Administrative contracts for templates, documents, signatories, executive memberships, leadership templates, admins, and audit logs are owned by Haider. Ahmed-owned operational contracts cover sessions, students, activities, participation, import/export, and authentication flow. Publish explicit validation errors—clients must not infer policy.

## Executive Council memberships (Admin or Super Admin)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `GET /api/admin/executive-memberships/societies` | `SocietyResponse[]` | Returns the five fixed active EMC societies. |
| `GET /api/admin/executive-memberships?session_id=` | `ExecutiveMembershipResponse[]` | Lists memberships with student/session/society display data; filter is optional. |
| `POST /api/admin/executive-memberships` | `ExecutiveMembershipCreate` → `ExecutiveMembershipResponse` | Creates an ACTIVE/COMPLETED/REMOVED membership in an active session only. Exact roles and Society Head rules are enforced server-side. |
| `PUT /api/admin/executive-memberships/{membership_id}` | `ExecutiveMembershipUpdate` → `ExecutiveMembershipResponse` | Updates an active-session membership while preserving one role/student/session and non-overlapping Society Head tenure constraints. |
| `POST /api/admin/executive-memberships/{membership_id}/complete` | `ExecutiveMembershipResponse` | Marks the membership completed and defaults its end date to the session end date. |
| `POST /api/admin/executive-memberships/{membership_id}/remove` | `ExecutiveMembershipResponse` | Marks it removed; removed memberships never receive automatic recognition. |

All membership changes are immutable audit events. Closed-session memberships cannot be altered.

## Template administration (Super Admin only)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `GET /api/admin/templates` | `TemplateResponse[]` | Lists non-archived templates for the Super Admin template editor. |
| `POST /api/admin/templates/upload` | multipart `name` + PDF `file` → `TemplateResponse` | Stores the supplied PDF in private Storage as an unapproved template. |
| `GET /api/admin/templates/{template_id}/analysis` | `TemplateAnalysisResponse` | Returns page count, extracted text, whether scanned pages were OCRed, whether any page still requires OCR/manual attention, and a signature/date-content warning. |
| `GET /api/admin/templates/{template_id}/source` | inline protected PDF | Supplies the private source PDF to the field editor without exposing a Storage URL. |
| `GET /api/admin/templates/{template_id}/pages/{page_number}` | PNG | Renders one protected source page for the visual drag/resize field-placement canvas. |
| `POST /api/admin/templates/{template_id}/fields` | `TemplateFieldsCreate` → `TemplateResponse` | Field names, one-based PDF coordinates, and the required `signature_handling` choice (`retain` or `replace`) are immutable once configured. |
| `POST /api/admin/templates/{template_id}/approve` | `TemplateResponse` | Requires student name, roll number, activity name, activity date, and an explicit signature choice. |
| `POST /api/admin/templates/{template_id}/preview` | `TemplatePreviewRequest` → inline PDF | Renders a participant-specific, watermarked `PREVIEW` in memory only; it never creates an official issued document. |

Every template endpoint requires an active `SUPER_ADMIN` server session. The browser never receives a Supabase Storage credential.

## Activity certificate issuance (Admin or Super Admin)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `POST /api/admin/documents/activities/{activity_id}/issue` | `ActivityIssueResponse` | Reserves one immutable activity-certificate record for every active, eligible participant. It requires an approved template, all mandatory fields, an explicit signature choice, and effective President + DSA signatories. `replace` templates must configure their signature image boxes. The selected records are snapshotted at reservation. Existing valid records are skipped. |
| `GET /api/admin/documents` | `AdminDocumentResponse[]` | Lists issued documents for Admin operations; supports optional `student_id`, `status_filter`, and `document_type` filters. |
| `GET /api/admin/documents/{document_id}` | `AdminDocumentResponse` | Returns an individual issued document for revoke/reissue controls. |
| `POST /api/admin/documents/{document_id}/revoke` | `204 No Content` | Marks a valid record `REVOKED`; it remains in audit/verification history but cannot be normally downloaded. |
| `POST /api/admin/documents/{document_id}/reissue` | `DocumentReissueResponse` | Supersedes a valid old record and reserves a new version with a new verification ID. Activity certificates revalidate their current issuance policy; leadership letters retain their original membership/template/signatory snapshot. |

The service fixes the activity issue date using the EMC Pakistan business date on first issuance and records immutable audit events. It never creates PDFs during issue; final PDFs remain lazy and cached on the first valid public download.

## Leadership templates (Super Admin only)

Leadership-template contracts use exact Executive Council roles and only `LEADERSHIP_RECOGNITION` or `END_OF_TENURE_APPRECIATION` document types. Their field configuration is restricted to deterministic record placeholders: student name/roll number, role, society, tenure dates, session name, and issue date. No LLM-generated letter content is permitted.

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `GET /api/admin/leadership-templates` | `LeadershipTemplateResponse[]` | Lists non-archived role-specific letter templates. |
| `POST /api/admin/leadership-templates/upload` | multipart `name`, official `role`, allowed `document_type`, and PDF `file` → `LeadershipTemplateResponse` | Stores a new inactive PDF privately. |
| `POST /api/admin/leadership-templates/{template_id}/fields` | `LeadershipTemplateFieldsCreate` → `LeadershipTemplateResponse` | Defines immutable deterministic-field/QR coordinates and the explicit `retain` or `replace` signature choice before activation. |
| `POST /api/admin/leadership-templates/{template_id}/activate` | `LeadershipTemplateResponse` | Requires the eight deterministic leadership fields plus a QR box, then atomically replaces the active template for its role/type. |
| `POST /api/admin/leadership-templates/{template_id}/deactivate` | `LeadershipTemplateResponse` | Retires an active template without deleting history. |
| `POST /api/admin/leadership-templates/{template_id}/archive` | `LeadershipTemplateResponse` | Archives a template and deactivates it permanently. |

Every state change records an immutable audit event. No endpoint accepts arbitrary role names or document types.

Closing a session now atomically preflights completed memberships and reserves both leadership document types exactly once per membership. It blocks closure with a precise missing template, field, signature choice, signature box, or effective-signatory error; no PDFs are generated until an authorized public download.

## Signatory administration (Admin or Super Admin)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `POST /api/admin/signatories` | multipart identity, effective dates, PNG/JPEG signature → `SignatoryResponse` | Stores the signature image in private Storage and retains the effective-dated history. |
| `GET /api/admin/signatories` | `SignatoryResponse[]` | Lists active and historical records for policy review. |
| `POST /api/admin/signatories/{signatory_id}/deactivate` | `SignatoryResponse` | Retires a record without deleting its history or signature asset. |

The issue service selects records effective on the governing activity date; it blocks with the missing official-title list when policy cannot be met.

## Full audit visibility (Super Admin only)

| Endpoint | Contract | Notes |
| --- | --- | --- |
| `GET /api/admin/audit?limit=100` | `AuditEventResponse[]` | Returns immutable audit events newest first; only a Super Admin session may view the full log. |

There are deliberately no audit update or delete endpoints.

## Ahmed baseline available now

`backend/app/schemas/operations.py` contains the shared Pydantic request/response baseline for students, sessions, activities, and XLSX import previews. Ahmed should implement his route/service modules against these models and the applied Alembic head `c8dc00f20398`; he must not create tables manually or alter existing migrations.

The admin routes are deliberately not implemented in this hand-off: they remain Ahmed-owned. The database guarantees unique student roll numbers, one active EMC session, one participant per activity/student, one EC membership per student/session, and no overlapping Society Head terms within a society/session.

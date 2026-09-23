# Shared API contracts

This file is the hand-off point before frontend/backend dependent work begins. Implemented schemas/OpenAPI are authoritative; updates must be coordinated.

| Endpoint | Contract | Consumer |
| --- | --- | --- |
| `GET /api/health/ready` | `{ "ready": true }` | application warm-up |
| `GET /api/public/students/{roll_number}/documents` | full student identity and documents grouped by category | student portal |
| `GET /api/public/documents/{document_id}/download` | authorized cached/generated PDF stream | document UI |
| `GET /api/public/verify/{verification_id}` | authoritative verification status and context | verification UI/QR |

Administrative contracts for templates, documents, signatories, executive memberships, leadership templates, admins, and audit logs are owned by Haider. Ahmed-owned operational contracts cover sessions, students, activities, participation, import/export, and authentication flow. Publish explicit validation errors—clients must not infer policy.

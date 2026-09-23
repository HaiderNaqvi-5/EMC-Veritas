# Architecture and scaffold map

## Runtime flow

```text
Browser → Cloudflare Pages / React shell → FastAPI /api → Supabase PostgreSQL
                                              └────────→ Supabase Storage
```

`GET /api/health/ready` is intentionally lightweight. The frontend starts it in the background and only retries safe GET requests. PDF analysis, OCR, migrations, and document generation must never block API startup.

## Backend modules

| Path | Responsibility | Owner |
| --- | --- | --- |
| `app/core` | settings, security, shared errors | Haider |
| `app/db` | engine, sessions, model metadata | Haider |
| `app/models` | SQLAlchemy persistence models | Haider |
| `app/schemas` | Pydantic request/response contracts | Shared (Haider maintains) |
| `app/api/public` | student discovery, download, verification | Haider |
| `app/api/admin` | separated admin API groups | Split by PRD ownership |
| `app/services/templates` | analysis, editor state, preview | Haider |
| `app/services/documents` | issue, version, revoke, lazy PDF generation | Haider |
| `app/services/signatures` | effective-dated signature policy | Haider |
| `app/services/executive` | council validation and recognition | Haider |
| `app/services/storage` | Supabase Storage adapter | Haider |
| `app/services/readiness` | non-blocking readiness probe | Haider |

## Frontend modules

| Path | Responsibility | Owner |
| --- | --- | --- |
| `src/features/student` | roll-number lookup/results | Haider |
| `src/features/verification` | public verification | Haider |
| `src/features/documents` | download/preview states | Haider |
| `src/features/templates` | analyzer/editor/preview integration | Haider |
| `src/routes` | route composition | Shared |
| `src/api` | typed API clients/contracts | Shared |
| `src/components/layout` | shared shell and navigation | Ahmed |

## Domain rules to preserve

- Alembic is the sole schema migration path.
- Persisted PDFs and assets use Supabase Storage, never Render disk.
- No hard deletion of domain records; retain historical state.
- Issue records immediately, generate final PDFs only on first authorized download, and cache the exact artifact.
- Verification IDs are random/non-sequential; verification resolves the authoritative record.
- Required certificate fields are student name, roll number, activity name, and activity date.
- Do not add fabricated logos. Add approved assets to `frontend/public/assets/logos/`.

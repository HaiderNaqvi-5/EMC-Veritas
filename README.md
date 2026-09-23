# EMC Veritas

Digital certificate, leadership recognition, and verification portal for the Event Management Club (EMC), Department of Computer Science, NFC-IET Multan.

## Architecture

```text
frontend/  React + TypeScript + Vite application (Cloudflare Pages)
backend/   FastAPI application, Alembic migrations, domain services (Render)
docs/      API contracts, architecture decisions, and collaboration notes
infra/     Deployment definitions
```

The frontend is a static shell and must remain usable while the API warms up. FastAPI owns eligibility, authentication, issuance, and verification authority. Supabase PostgreSQL stores records; Supabase Storage stores persistent PDFs, templates, signatures, and rendered previews.

## Ownership boundaries

| Area | Owner |
| --- | --- |
| Database, migrations, document/template/verification/signature/executive/storage services, public APIs | Haider |
| Student, verification, document, and template-editor frontend | Haider |
| Admin shell, activities, students, imports, sessions, authentication UX and routes | Ahmed |
| API contracts, migrations coordination, releases | Shared |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) before adding dependent features.

## Local development

1. Copy `.env.example` to `backend/.env` and fill the Supabase values.
2. Backend: `cd backend && python -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/uvicorn app.main:app --reload`
3. Frontend: `cd frontend && npm install && npm run dev`

Schema changes go through Alembic only. Never commit secrets or generated document artifacts.

## Before pushing to `main`

Run the same verification command used by GitHub Actions:

```bash
./scripts/verify.sh
```

It installs backend development dependencies, runs backend tests and linting, then uses the locked frontend dependency versions to build the application. Push only after this command succeeds.

This checkout is configured to run it automatically before each push. A collaborator can enable the tracked hook after cloning with:

```bash
git config core.hooksPath .githooks
```

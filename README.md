# EMC Veritas

EMC Veritas is the certificate, leadership-recognition, and public verification system for the Event Management Club (EMC), Department of Computer Science, NFC-IET Multan.

Students use the public landing page to find issued records by roll number—no student account is required. Administrators use the protected `/admin` workspace to manage students, activities, templates, signatories, council memberships, issuance, corrections, and audit history.

## Current capabilities

### Public portal

- Roll-number lookup for activity, leadership, and Executive Council records.
- Direct PDF downloads from short-lived signed Storage URLs.
- QR and eight-character verification-ID lookup at `/verify`.
- Authoritative verification pages at `/verify/:verificationId`.
- Responsive light and dark themes with explicit loading, empty, error, and download states.

### Admin workspace

- Cookie-based Admin and Super Admin authentication at `/admin`.
- Student creation, correction, activation, deactivation, and import workflows.
- Session and activity management, including participant eligibility.
- Effective-dated signatory records and signature-image processing.
- Visual PDF template analysis, field placement, custom TTF/OTF upload, preview, and approval.
- Member-scoped leadership templates for recognition and end-of-tenure letters.
- Executive Council organizer rosters and EC certificate publication.
- Immutable certificate versioning with audited replacement, supersession, and revocation.
- Separate participant and EC pre-publishing batches so PDFs are rendered and stored before public download.
- Administrative audit log for issuance and lifecycle operations.

### Certificate rendering

- Final PDFs preserve the uploaded template as their visual base.
- Dynamic fields, signatures, QR codes, and verification IDs are rendered into configured PDF coordinates.
- `student_name`, `roll_number`, `activity_name`, and `activity_date` are emphasized automatically.
- EC certificates use their dedicated renderer and retain their own template, paragraph rhythm, typography, and signatory treatment.
- Generated files use immutable versioned Storage paths. Reissuing a document preserves its previous version in the audit history.

## Architecture

```text
Browser
  │
  ├── Cloudflare Pages: React + TypeScript + Vite
  │
  └── Render: FastAPI /api
        ├── Supabase PostgreSQL: domain records and audit history
        └── Supabase Storage: templates, fonts, signatures, previews, and issued PDFs
```

```text
frontend/  Public portal and protected admin workspace
backend/   FastAPI API, SQLAlchemy models, Alembic migrations, and domain services
docs/      Architecture, API contracts, deployment notes, and handoffs
infra/     Render deployment definition
scripts/   Repository verification commands
```

FastAPI is the authority for authentication, eligibility, issuance, document versions, and verification. The frontend never decides whether a document is valid. Render disk is treated as ephemeral; every persistent artifact belongs in Supabase Storage.

## Document lifecycle

1. An approved template and eligible recipient are selected.
2. The API reserves an immutable issued-document record with a random verification ID and a snapshot of its rendering data.
3. The PDF is rendered and stored during issuance or through **Documents → Prepare documents for publishing**.
4. The student receives a short-lived signed URL to the stored PDF.
5. Corrections create a new version. The previous valid version becomes superseded and remains in the audit history.

For a public release, prepare both columns on the Documents page until each selected activity reports `Remaining: 0`:

- **Participant certificates**
- **Executive Council certificates**

This prevents the first student download from waiting for PDF generation.

## Local development

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- PostgreSQL/Supabase project
- A private Supabase Storage bucket

### Configuration

Create the backend environment file:

```bash
cp .env.example backend/.env
```

At minimum, configure:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `SESSION_SECRET`
- `FRONTEND_ORIGINS`
- `PUBLIC_APP_URL`

Never expose the Supabase service-role key to the frontend or commit real secrets.

The frontend uses `/api` through the Vite development proxy by default. To target a different API:

```bash
cp frontend/.env.example frontend/.env
```

### Backend

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`; readiness is available at `/api/health/ready`.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Vite application runs at `http://localhost:5173`.

## Verification and tests

Run the same repository checks required before a push:

```bash
./scripts/verify.sh
```

The script:

1. installs the backend package and development dependencies;
2. runs the complete backend test suite;
3. runs Ruff over backend application and test code;
4. installs locked frontend dependencies;
5. runs the Vitest suite; and
6. type-checks and builds the production frontend.

Enable the tracked pre-push hook after cloning:

```bash
git config core.hooksPath .githooks
```

## Deployment

### Backend: Render

The Blueprint is [infra/render/render.yaml](infra/render/render.yaml). It installs the backend, applies reviewed Alembic migrations, and starts Uvicorn with `/api/health/ready` as the health check.

Configure these as Render environment variables rather than repository values:

- database and Supabase credentials;
- `FRONTEND_ORIGINS` with the exact Cloudflare Pages origin;
- `PUBLIC_APP_URL` with the public frontend origin;
- `COOKIE_SECURE=true`; and
- `COOKIE_SAME_SITE=none` for the cross-site Pages/Render session cookie.

### Frontend: Cloudflare Pages

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment: `VITE_API_BASE_URL=https://<render-api-host>/api`

See [docs/cloudflare-pages.md](docs/cloudflare-pages.md) for release details.

## Repository rules

- Use Alembic as the only schema-migration path.
- Keep authorization and certificate validity server-side.
- Store persistent assets in Supabase Storage, never on Render disk.
- Do not overwrite issued PDF objects; create a new document version.
- Preserve audit records when superseding or revoking documents.
- Do not commit secrets, generated PDFs, local environments, or temporary render output.
- Run `./scripts/verify.sh` before pushing to `main`.

## Further documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API contracts](docs/API_CONTRACTS.md)
- [Cloudflare Pages deployment](docs/cloudflare-pages.md)
- [Implementation notes](docs/implementation.md)

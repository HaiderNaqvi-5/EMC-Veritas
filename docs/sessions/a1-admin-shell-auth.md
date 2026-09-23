# A1 Admin shell and auth boundary

## Status

PARTIALLY COMPLETE

## Objective

Deliver Ahmed's Phase A1 frontend foundation without duplicating Haider-owned database, authorization, or Supabase services.

## Completed work

- Added responsive persistent Admin shell and navigation for Overview, Students, Activities, Sessions, and Imports.
- Added supplied-logo placeholder, accessible empty/pending states, and light/dark theme support.
- Added dashboard skeletons that keep the shell visible while data is unavailable.
- Configured TanStack Query with bounded query retries and mutation retries disabled.
- Added non-blocking readiness warm-up with an eight-second request limit.
- Added typed cookie-based Admin-auth client contract and accessible password-modal component. No token is stored in browser storage.
- Integrated the FastAPI Admin-auth lookup/login/logout/session/password-change routes with the shared Supabase PostgreSQL SQLAlchemy session and Argon2 password verification.

## Files changed

- `frontend/src/components/layout/AdminShell.tsx`
- `frontend/src/components/layout/ThemeToggle.tsx`
- `frontend/src/components/ui/Skeleton.tsx`
- `frontend/src/features/admin/AdminDashboard.tsx`
- `frontend/src/features/auth/AdminLoginModal.tsx`
- `frontend/src/features/auth/contracts.ts`
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/query/client.ts`
- `frontend/src/routes/AdminPortal.tsx`
- `frontend/src/routes/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/index.css`
- `backend/app/api/admin/auth.py`
- `backend/app/services/auth.py`
- `backend/app/schemas/auth.py`
- `backend/app/core/settings.py`
- `backend/app/main.py`

## Decisions

Supabase, database access, and authorization remain backend-only. The frontend uses FastAPI contracts with HTTP-only cookies and does not access Supabase or retain authentication tokens.

## Tests

Build and lint verification are pending until frontend dependencies are installed. Backend tests must use developer-specific Supabase credentials; no shared `.env` is copied into this checkout.

## Known issues and next step

The landing roll-number flow belongs to Haider's Student Portal component. Integrate the Admin lookup/modal into that component through a reviewed cross-owner change. The remaining A1 items are full frontend auth-flow wiring and test coverage.

#!/usr/bin/env bash
# Run the same backend and frontend checks required by GitHub Actions.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend: install, test, lint"
(
  cd "$project_root/backend"
  if [ "${CI:-}" != "true" ]; then
    python -m venv .venv
    PYTHON=.venv/bin/python
  else
    PYTHON=python
  fi
  "$PYTHON" -m pip install -e '.[dev]'
  # CI intentionally has no private .env file.  Use inert values only for
  # import-time settings validation; tests replace database/storage boundaries.
  DATABASE_URL="postgresql+psycopg://ci:ci@localhost:5432/emc_veritas_ci" \
  SUPABASE_URL="https://example.supabase.co" \
  SESSION_SECRET="ci-only-not-a-production-secret" \
  "$PYTHON" -m pytest
  "$PYTHON" -m ruff check app tests
)

echo "==> Frontend: deterministic install and build"
(
  cd "$project_root/frontend"
  npm ci
  npm run build
)

echo "==> All repository checks passed"

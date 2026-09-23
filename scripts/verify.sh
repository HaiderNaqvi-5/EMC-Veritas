#!/usr/bin/env bash
# Run the same backend and frontend checks required by GitHub Actions.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend: install, test, lint"
(
  cd "$project_root/backend"
  python -m pip install -e '.[dev]'
  pytest
  ruff check app tests
)

echo "==> Frontend: deterministic install and build"
(
  cd "$project_root/frontend"
  npm ci
  npm run build
)

echo "==> All repository checks passed"

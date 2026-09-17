#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python -m pytest -q

mkdir -p dist
NAME="api-platform-$(date +%Y%m%d-%H%M%S)"
tar \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  --exclude='data/*.sqlite3' \
  --exclude='config.json' \
  -czf "dist/${NAME}.tar.gz" .

echo "release: dist/${NAME}.tar.gz"

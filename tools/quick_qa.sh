#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Policy Check =="
python3 "$ROOT_DIR/tools/policy_check.py" || true

echo "\n== Unit Tests (if pytest available) =="
if command -v pytest >/dev/null 2>&1; then
  pytest -q "$ROOT_DIR/tests" -m unit || true
else
  echo "pytest not found (skipping)."
fi

echo "\nDone."


#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer an existing venv python if present (keeps installs consistent)
PY="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
fi

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip >/dev/null
python -m pip install -e . >/dev/null

echo "OK: venv ready."
echo "Run: ./scripts/run.sh --version"
echo "Run: ./scripts/run.sh validate --schema lane --config path/to/lane.yaml"

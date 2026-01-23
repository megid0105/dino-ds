#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

VENV="$ROOT/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

# No-brainer: auto-create venv if missing
if [ ! -x "$PY" ]; then
  echo "[dino-ds] Creating venv at: $VENV" >&2
  PY_BOOTSTRAP="${PYTHON:-python3}"
  if ! command -v "$PY_BOOTSTRAP" >/dev/null 2>&1; then
    PY_BOOTSTRAP="python"
  fi
  "$PY_BOOTSTRAP" -m venv "$VENV"
  "$PIP" install -U pip >/dev/null
  # Editable install so colleagues always run the repo source of truth
  "$PIP" install -e . >/dev/null
fi

# Always refresh editable install so local source edits take effect immediately.
# This prevents stale-code confusion when lane schemas/commands are evolving.
"$PIP" install -e . >/dev/null

# Sanity: fail fast if the package still can't be imported.
"$PY" -c "import dino_ds" >/dev/null 2>&1 || {
  echo "[dino-ds] ERROR: cannot import dino_ds from venv. Try: rm -rf .venv && ./scripts/run.sh -h" >&2
  exit 1
}

# Always run via module entrypoint (avoids console-script import/path issues)
if [ "${1:-}" = "" ]; then
  exec "$PY" -m dino_ds.cli -h
fi
exec "$PY" -m dino_ds.cli "$@"

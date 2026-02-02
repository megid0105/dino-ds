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

# --- Teacher runtime portability preflight (Ollama) -------------------------
# Colleagues should only run ./scripts/run.sh ... ; if teacher_runtime is enabled in lane.yaml,
# we must ensure Ollama is installed and the requested model is present.
#
# Controls:
#   DINO_DS_SKIP_OLLAMA=1         -> skip all Ollama checks (not recommended)
#   DINO_DS_OLLAMA_AUTO_PULL=1    -> auto-pull missing model
#

if [ "${DINO_DS_SKIP_OLLAMA:-}" != "1" ]; then
  # Only preflight for commands that take a lane config
  if [ "${1:-}" = "gate" ] && [ "${2:-}" = "lane" ]; then
    CFG_PATH=""
    # Parse --config <path>
    for ((i=1; i<=$#; i++)); do
      arg="${!i}"
      if [ "$arg" = "--config" ]; then
        j=$((i+1))
        CFG_PATH="${!j:-}"
        break
      fi
    done

    if [ "$CFG_PATH" != "" ] && [ -f "$CFG_PATH" ]; then
      # Ask Python (with PyYAML already installed via editable install) whether teacher_runtime is enabled.
      # Prints: enabled|model|provider
      TEACHER_INFO="$($PY - "$CFG_PATH" <<'PY'
import sys
import yaml
from pathlib import Path

cfg = Path(sys.argv[1])
obj = yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}
if not isinstance(obj, dict):
    print("false|dino-pro-7b|ollama")
    raise SystemExit(0)

gm = (obj.get('generation_mode') or '').strip()
tr = obj.get('teacher_runtime')
tr = tr if isinstance(tr, dict) else {}

enabled = bool(tr.get('enabled', False)) or (gm == 'teacher_runtime')
model = (tr.get('model') or '').strip() or 'dino-pro-7b'
provider = (tr.get('provider') or '').strip() or 'ollama'
print(('true' if enabled else 'false') + '|' + model + '|' + provider)
PY
)"

      TEACHER_ENABLED="${TEACHER_INFO%%|*}"
      REST="${TEACHER_INFO#*|}"
      TEACHER_MODEL="${REST%%|*}"
      TEACHER_PROVIDER="${REST#*|}"

      if [ "$TEACHER_ENABLED" = "true" ]; then
        if [ "$TEACHER_PROVIDER" != "ollama" ]; then
          echo "[dino-ds] ERROR: teacher_runtime.provider must be 'ollama' (got: $TEACHER_PROVIDER)" >&2
          exit 6
        fi

        if ! command -v ollama >/dev/null 2>&1; then
          echo "[dino-ds] ERROR: Teacher Mode requires Ollama, but 'ollama' is not installed." >&2
          echo "[dino-ds] Install Ollama, then run: ollama pull $TEACHER_MODEL" >&2
          exit 6
        fi

        # Ensure Ollama daemon is responding
        if ! ollama list >/dev/null 2>&1; then
          echo "[dino-ds] ERROR: Ollama is installed but not responding (daemon not running)." >&2
          echo "[dino-ds] Start the Ollama app/daemon, then re-run this command." >&2
          exit 6
        fi

        # Ensure model exists (no network by default)
        if ! ollama show "$TEACHER_MODEL" >/dev/null 2>&1; then
          if [ "${DINO_DS_OLLAMA_AUTO_PULL:-}" = "1" ]; then
            echo "[dino-ds] Ollama model missing; auto-pulling: $TEACHER_MODEL" >&2
            ollama pull "$TEACHER_MODEL" >/dev/null
          else
            echo "[dino-ds] ERROR: Ollama model missing: $TEACHER_MODEL" >&2
            echo "[dino-ds] Run: ollama pull $TEACHER_MODEL" >&2
            echo "[dino-ds] Or set DINO_DS_OLLAMA_AUTO_PULL=1 to auto-pull." >&2
            exit 6
          fi
        fi
      fi
    fi
  fi
fi
# --------------------------------------------------------------------------

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

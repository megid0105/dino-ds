# DinoDS Offline Package (Mac) — Zero‑Guess Re‑Wrap Guide

Pack status (current):
- Last wrapped: 2026-01-30
- Includes updated lane settings and teacher prompts.

This document is a complete, standalone recipe. A new thread can follow this **without opening any other file**.

---

**What the final package must include**

1. `dino-ds-bin` (PyInstaller single‑file CLI binary)
2. `dino-ds` (wrapper script alias)
3. `lanes/**/lane.yaml` (36 files)
4. `prompts/teacher/lane_XX_teacher_system_prompt.txt` (36 files; must be included)
5. `prompts/system/dino_system_prompt.txt` (must be included)
6. `system_prompt_registry.json` (root; must be included)

Target package folder and zip:

```
dist/
  dino_ds_offline_mac/
    dino-ds
    dino-ds-bin
    lanes/...
    prompts/teacher/...
    prompts/system/...
    system_prompt_registry.json
  dino_ds_offline_mac.zip
```

---

## One‑Time: Create the offline venv (if not already created)

Run from repo root (`/Users/chanpakho/Desktop/Download/project/dino_ds`):

```bash
python3 -m venv .venv
source .venv/bin/activate

# Offline install using bundled wheels
pip install --no-index --find-links vendor_wheels -r requirements.txt
pip install --no-index --find-links vendor_wheels pyinstaller
```

If `requirements.txt` does not exist, install directly from wheels:

```bash
pip install --no-index --find-links vendor_wheels -r pyproject.toml
```

---

## Step 1 — Create the PyInstaller entry file

```bash
cat > /tmp/dino_ds_entry.py <<'PY'
from dino_ds.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
PY
```

---

## Step 2 — Build the CLI binary

```bash
source .venv/bin/activate

PYTHONPATH=src .venv/bin/pyinstaller \
  --clean --noconfirm --onefile \
  --name dino-ds-bin \
  --paths src \
  --collect-all dino_ds \
  --add-data "src/dino_ds/schemas:dino_ds/schemas" \
  --add-data "src/dino_ds/system_prompt_registry.json:dino_ds" \
  --add-data "system_prompt_registry.json:dino_ds" \
  --add-data "system_prompt_registry.json:." \
  --add-data "prompts/system:prompts/system" \
  /tmp/dino_ds_entry.py
```

Binary output will be:

```
dist/dino-ds-bin
```

---

## Step 3 — Assemble the offline package folder

```bash
rm -rf dist/dino_ds_offline_mac
mkdir -p dist/dino_ds_offline_mac

# Copy binary
cp dist/dino-ds-bin dist/dino_ds_offline_mac/dino-ds-bin

# Copy system prompt registry
cp system_prompt_registry.json dist/dino_ds_offline_mac/

# Sync lanes (only lane.yaml)
rsync -a --prune-empty-dirs \
  --include '*/' --include 'lane.yaml' --exclude '*' \
  lanes/ dist/dino_ds_offline_mac/lanes/

# Sync teacher prompts (required)
rsync -a --prune-empty-dirs \
  --include '*/' --include 'lane_*_teacher_system_prompt.txt' --exclude '*' \
  prompts/teacher/ dist/dino_ds_offline_mac/prompts/teacher/

# Sync system prompt (required)
rsync -a prompts/system/ dist/dino_ds_offline_mac/prompts/system/
```

---

## Step 4 — Create the wrapper alias `dino-ds`

```bash
cat > dist/dino_ds_offline_mac/dino-ds <<'SH'
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$ROOT/dino-ds-bin"

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: dino-ds-bin not found or not executable at: $BIN" >&2
  exit 1
fi

# Example usage:
# ./dino-ds lane_02 run --limit 1000

if [[ "$#" -lt 2 ]]; then
  echo "usage: dino-ds lane_XX run [--limit N] [--seed N]" >&2
  exit 1
fi

LANE_ID="$1"
CMD="$2"
shift 2

CONFIG_PATH="$(ls "$ROOT/lanes/${LANE_ID}"*/lane.yaml 2>/dev/null | head -n1)"
if [[ -z "${CONFIG_PATH}" ]]; then
  echo "ERROR: lane config not found for ${LANE_ID}" >&2
  exit 1
fi

exec "$BIN" gate lane --config "$CONFIG_PATH" "$@"
SH

chmod +x dist/dino_ds_offline_mac/dino-ds
```

---

## Step 5 — Zip the package

```bash
cd dist
rm -f dino_ds_offline_mac.zip
zip -r dino_ds_offline_mac.zip dino_ds_offline_mac
```

---

## Quick sanity check (optional)

```bash
cd dist/dino_ds_offline_mac
./dino-ds lane_03 run --limit 20
```

---

## Known macOS issues and fixes

If macOS blocks execution:

```bash
xattr -dr com.apple.quarantine .
chmod +x dino-ds dino-ds-bin
```

---

## Notes for colleagues

1. They **must** have Ollama installed and the required model pulled.
2. They only edit:
   - `lanes/**/lane.yaml`
   - `prompts/teacher/lane_XX_teacher_system_prompt.txt`
   - `prompts/system/dino_system_prompt.txt` (if allowed)
3. Run from package root:

```bash
./dino-ds lane_02 run --limit 1000
```

---

## Where important code changes live (for future threads)

If a future thread needs to re‑apply code changes, they are in:

1. `src/dino_ds/commands/build_cmd.py`
   - dict‑slot expansion for `expand_dict_slots`
   - bool‑safe formatting in `_deep_format`
   - teacher runtime prompt loading + timeout fallback
2. `src/dino_ds/cli.py`
   - gate default limit uses lane count_target
   - TEF labels include `system_prompt_id`
3. `system_prompt_registry.json`
   - register `dino.system.v1`
4. `prompts/system/dino_system_prompt.txt`
   - production system prompt text

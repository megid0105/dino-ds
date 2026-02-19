# DinoDS Offline Package (Mac) — Re-Wrap Guide (Current)

Pack status target:
- Wrapper command model: updated (single-language, full sweep, QC sweep)
- Teacher runtime override: `--teacher` supported at runtime (no YAML edits)
- Help spec support: `help spec lane_xx` supported when validator config markdown is included

---

## What the final package must include

1. `dino-ds-bin` (PyInstaller single-file CLI binary)
2. `dino-ds` (offline wrapper alias script)
3. `help` (optional bare help shim)
4. `dino-shell.sh` (optional shell alias bootstrap for bare commands)
5. `lanes/**/lane_*.yaml` (all language files per lane)
6. `prompts/teacher/lane_XX_teacher_system_prompt.txt` (37 files) + shared teacher prompt file(s)
7. `prompts/system/dino_system_prompt.txt`
8. `system_prompt_registry.json` (root)
9. `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` (root; needed for canonical action label checks in lane 11/12)
10. `DinoDS_full_validator_config_YYYY-MM-DD.md` (root; needed by `help spec lane_xx`)
11. `PROMPTS_EDIT_HERE.md` (root; operator prompt-edit guide)

Target package folder and zip:

```text
dist/
  dino_ds/
    dino-ds
    dino-ds-bin
    help
    dino-shell.sh
    lanes/...
    prompts/teacher/...
    prompts/system/...
    system_prompt_registry.json
    MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md
    DinoDS_full_validator_config_YYYY-MM-DD.md
    PROMPTS_EDIT_HERE.md
  dino_ds.zip
```

---

## One-time: create offline venv (if needed)

Run from repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links vendor_wheels -r requirements.txt
pip install --no-index --find-links vendor_wheels pyinstaller
```

If `requirements.txt` is unavailable, install from project metadata using bundled wheels.

---

## Step 1 — Create PyInstaller entry file

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
  --add-data "MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md:." \
  --add-data "DinoDS_full_validator_config_2026-02-19.md:." \
  /tmp/dino_ds_entry.py
```

Binary output:

```text
dist/dino-ds-bin
```

---

## Step 3 — Assemble offline package folder

```bash
rm -rf dist/dino_ds
mkdir -p dist/dino_ds

# Binary
cp dist/dino-ds-bin dist/dino_ds/dino-ds-bin

# Required root files
cp system_prompt_registry.json dist/dino_ds/
cp MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md dist/dino_ds/
cp DinoDS_full_validator_config_2026-02-19.md dist/dino_ds/
cp PROMPTS_EDIT_HERE.md dist/dino_ds/

# Lanes: include all language lane_*.yaml files
rsync -a --prune-empty-dirs \
  --include '*/' --include 'lane_*.yaml' --exclude '*' \
  lanes/ dist/dino_ds/lanes/

# Teacher prompts (copy full folder so shared teacher prompt files are included)
rsync -a prompts/teacher/ dist/dino_ds/prompts/teacher/

# System prompts
rsync -a prompts/system/ dist/dino_ds/prompts/system/
```

---

## Step 4 — Install wrapper alias `dino-ds`

Use the maintained wrapper template:

```bash
cp scripts/offline_dino_ds_wrapper.sh dist/dino_ds/dino-ds
chmod +x dist/dino_ds/dino-ds
cp scripts/offline_help_shim.sh dist/dino_ds/help
cp scripts/offline_shell_env.sh dist/dino_ds/dino-shell.sh
chmod +x dist/dino_ds/help
```

This wrapper supports:
- `./dino-ds lane_03_en` -> run one language config (`lane_en.yaml` for `en`)
- `./dino-ds lane_03 --teacher` -> run `lane_en.yaml` with teacher runtime forced on (`enabled=true`, sampling forced to full when YAML is 0)
- `./dino-ds run lane_03` -> prod sweep all 14 languages and auto-combine to `ALL/dino-tef-all-.../train.jsonl`
- `./dino-ds qc lane_03_en` -> QC one language using QC sample limit for that language
- `./dino-ds qc lane_03` -> QC sweep all 14 languages (sample limits) and auto-combine
- `./dino-ds validator_level_set 01|02|03` -> persist default validator strictness
- `./dino-ds validator_level_check` -> show active validator strictness and config source
- `./dino-ds validator_level_reset` -> clear saved validator strictness (fallback to default 03)
- `./dino-ds help quickstart` / `help validator` / `help run` -> dedicated operator help pages
- `./dino-ds help paths` -> output directory settings guide
- `./dino-ds help prompts` -> editable system/teacher prompt files
- `./dino-ds qc_report_dir_set <path>` / `qc_report_dir_check` / `qc_report_dir_reset`
- `./dino-ds set_output_dir <path>` (all lanes) or `set_output_dir lane_xx <path>` (single lane)
- `./dino-ds output_dir_check [lane_xx]` / `reset_output_dir [lane_xx]`
- Optional `help` command in package root:
  - `./help` works directly.
  - For true bare commands (`help`, `run`, `qc`, `validate`, etc.), run `source ./dino-shell.sh` once per shell session.
  - Lane tokens also work bare after sourcing (examples: `lane_03`, `lane_03_en`).
- Pass-through to binary commands (`help`, `validate`, `gate`, etc.)
- QC markdown reports are written to `output QC report/` (not repo root) by default in package mode. Override with `DINO_DS_QC_REPORT_DIR=<path>` or `qc_report_dir_set`.
- Lane outputs default to `<package_root>/out_runs/<lane_id>/...` in wrapped mode. Override with `set_output_dir ...` (preferred) or `DINO_DS_LANE_OUTPUT_DIR=<path>`.
- Wrapper defaults `DINO_DS_TOOL_CONFIG_PATH` to `<package_root>/.dino_ds_tool_config.json` so settings stay package-local.

---

## Step 5 — Zip package

```bash
cd dist
rm -f dino_ds.zip
zip -r dino_ds.zip dino_ds
```

---

## Quick sanity checks

```bash
cd dist/dino_ds

# 1) Single language
./dino-ds lane_03_en --limit 20

# 2) Teacher runtime without editing YAML
./dino-ds lane_03_en --teacher --limit 20

# 3) Full prod sweep + combine
./dino-ds run lane_03

# 4) QC sweep + combine
./dino-ds qc lane_03

# 4b) QC one language
./dino-ds qc lane_03_en

# 5) Validator help by lane
./dino-ds help spec lane_03

# 6) Operator help pages
./dino-ds help
./help
./dino-ds help quickstart
./dino-ds help validator
./dino-ds help run
./dino-ds help paths
./dino-ds help prompts

# Optional: enable bare `help` in this shell
source ./dino-shell.sh
help
run lane_03 --seed 101
qc lane_03 --seed 101
validator_level_check
lane_03_en --limit 20

# 7) Persist/reset validator strictness default
./dino-ds validator_level_set 03
./dino-ds validator_level_check
./dino-ds validator_level_reset

# 8) Persist/check/reset output directories
./dino-ds qc_report_dir_set ./output\ QC\ report
./dino-ds qc_report_dir_check
./dino-ds qc_report_dir_reset
./dino-ds set_output_dir ./out_runs
./dino-ds set_output_dir lane_03 ./out_runs/lane_03_custom
./dino-ds output_dir_check
./dino-ds output_dir_check lane_03
./dino-ds reset_output_dir lane_03
./dino-ds reset_output_dir
```

---

## macOS execution fixes

```bash
xattr -dr com.apple.quarantine .
chmod +x dino-ds dino-ds-bin
```

---

## Notes for colleagues

1. Default mode remains teacher runtime OFF unless `--teacher` is explicitly provided.
2. `--teacher` forces teacher rewrite mode at runtime without editing YAML and lifts zero sampling to active sampling for that run.
3. `--teacher` requires Ollama installed + model available.
4. They only need to edit lane YAMLs and prompts inside package; wrapper handles lane/lang command mapping.
5. Full sweep outputs combine into one `ALL/dino-tef-all-...` directory automatically.
6. Prompt files operators can edit directly:
   - `prompts/system/dino_system_prompt.txt`
   - `prompts/teacher/lane_XX_teacher_system_prompt.txt`
   - shared files under `prompts/teacher/` (if present)

# Wrap Verification — 2026-02-21

## Pre-wrap checks
- `lanes/**/lane_*.yaml` unified thresholds: `max_token_overlap_ratio=0.30`, `dup_candidate_threshold=0.30`, `dup_candidate_warn_max_share=0.35`
- Validator/help/docs updates present:
  - `dup_candidate_warn_share_too_high` escalation in validator + help/docs
  - combined `all` QC report support in wrapper/sweep scripts

## Wrap actions performed
1. Rebuilt binary via PyInstaller to `dist/dino-ds-bin`
2. Assembled `dist/dino_ds/` per `WRAPPED_PACKAGE.md`
3. Included `QC Spec/` into package root at `dist/dino_ds/QC Spec/`
4. Re-zipped to `dist/dino_ds.zip`

## Post-wrap checks
- Zip lane files checked: `521`, nonconforming threshold files: `0`
- Zip primary lane files (`dino_ds/lanes/<lane>/lane_<lang>.yaml`): `493`
- QC Spec entries in zip: `12`
- Top-level wrap artifacts present:
  - `dino_ds/dino-ds-bin`
  - `dino_ds/dino-ds`
  - `dino_ds/help`
  - `dino_ds/dino-shell.sh`
  - `dino_ds/system_prompt_registry.json`
  - `dino_ds/MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md`
  - `dino_ds/DinoDS_full_validator_config_2026-02-19.md`
  - `dino_ds/PROMPTS_EDIT_HERE.md`

## Runtime sanity
- `dist/dino-ds-bin help validator` shows warn-share escalation help (`0.35` default)
- `dist/dino_ds/dino-ds help validator` shows same

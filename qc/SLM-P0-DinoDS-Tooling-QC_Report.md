# SLM-P0-DinoDS-Tooling-QC_Report

## Summary
Implemented P0 baseline for `dino-ds`:
- Python package + CLI scaffolding
- Locked exit codes (0–6) and verified critical mappings:
  - validate missing file -> 5
  - validate bad schema -> 6
  - validate schema failure -> 3
  - lint gate failure -> 2
  - sources verify hash mismatch -> 2
  - fixtures verify hash mismatch -> 2
- PCT Addendum: added schemas + commands for SourcePack and ToolReplay fixtures, plus QA lint guardrails.

## Commands Implemented (P0)
- `dino-ds validate --schema <lane|sources|fixtures> --config <path>`
- `dino-ds lint --qa-jsonl <path>`
- `dino-ds sources verify --manifest <sources_manifest.json>`
- `dino-ds fixtures verify --manifest <tool_replay_manifest.json>`
- Stubs (NYI, return 1): `build lane`, `build qa`, `split`, `pack`, `golden gen`, `golden run`, `smoke`

## Files Added / Modified
- `pyproject.toml` (src-layout package-dir + console script)
- `src/dino_ds/__init__.py`, `src/dino_ds/__main__.py`
- `src/dino_ds/exit_codes.py`
- `src/dino_ds/cli.py`
- `src/dino_ds/utils.py`
- `src/dino_ds/schema_store.py`
- `src/dino_ds/commands/validate_cmd.py`
- `src/dino_ds/commands/lint_cmd.py`
- `src/dino_ds/commands/sources_cmd.py`
- `src/dino_ds/commands/fixtures_cmd.py`
- `src/dino_ds/commands/stubs.py`
- `src/dino_ds/schemas/lane_schema.v1.json`
- `src/dino_ds/schemas/sources_manifest.v1.json`
- `src/dino_ds/schemas/tool_replay_manifest.v1.json`
- `scripts/bootstrap.sh`, `scripts/run.sh`

## Tests / Evidence
Exit-code smoke (observed):
- validate_missing -> 5
- validate_bad_schema -> 6
- validate_schema_fail -> 3
- lint_bad -> 2
- sources_mismatch -> 2
- fixtures_mismatch -> 2

## Known Gaps (P0 by design)
- Build/split/pack/golden/smoke logic not implemented (NYI stubs).
- No network/tool execution in P0; tool replay is verify-only.


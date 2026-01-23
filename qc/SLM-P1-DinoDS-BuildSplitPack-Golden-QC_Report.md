# SLM-P1-DinoDS-BuildSplitPack-Golden-QC_Report

## Summary
Implemented P1/P2 features on top of approved P0 baseline:
- Implemented: `build lane`, `split`, `pack`
- Implemented: `golden gen` (CPU-only) and `golden run --engine none` (structure-only)
- Kept P0 hard gates + locked exit codes intact.

## Commands (Implemented)
- `dino-ds build lane --config lane.yaml --out built.jsonl [--seed N] [--limit K]`
- `dino-ds split --in built.jsonl --outdir splits/ [--seed N] [--train f] [--val f] [--test f]`
- `dino-ds pack --indir splits/ --out dataset_manifest.json`
- `dino-ds golden gen --out golden_eval.jsonl --count 300..800 --seed N`
- `dino-ds golden run --engine none --golden golden_eval.jsonl`

## Exit Codes (contract preserved)
- 0 SUCCESS
- 1 INTERNAL_ERROR (NYI stubs remain: build qa, smoke, and any unimplemented commands)
- 2 LINT_FAILED (lint/sources/fixtures mismatch)
- 3 SCHEMA_VALIDATION_FAILED
- 4 GOLDEN_FAILED (used by golden structure failures)
- 5 IO_ERROR
- 6 CONFIG_INVALID

## Files Added
- `src/dino_ds/commands/build_cmd.py`
- `src/dino_ds/commands/split_cmd.py`
- `src/dino_ds/commands/pack_cmd.py`
- `src/dino_ds/commands/golden_cmd.py`

## Files Modified
- `src/dino_ds/cli.py` (wired new commands + additive flags)

## End-to-End Smoke Evidence
Ran on local machine:
- validate_lane exit=0
- build_lane exit=0 (wc -l built.jsonl = 3)
- split exit=0 (train/val/test emitted)
- pack exit=0 (dataset_manifest.json includes sha256/rows)
- golden_gen exit=0 (count=300)
- golden_run exit=0 (engine none)

## Known Gaps (expected)
- `build qa` remains NYI (returns 1)
- `golden run` engines `dino/dino_pro` are reserved for later (currently structure-only run path is guaranteed everywhere)


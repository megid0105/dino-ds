# SLM-P1-DinoDS-BuildSplitPack-Golden-PhasePropertyList

## Build Lane
Inputs:
- `lane.yaml` (validated via `validate --schema lane`)
- `sources`: list of file paths or objects with `path`
Supported source file types:
- `.jsonl` (list of records)
- `.json` (single object or list)

Behavior:
- Deterministically shuffles rows by `--seed`
- Applies `count_target` from lane (and optional `--limit`)
- Adds `_lane` metadata to each record
- Ensures `sample_id` exists and is unique

Outputs:
- JSONL file at `--out`

## Split
Inputs:
- JSONL `--in`

Knobs:
- `--train --val --test` must sum to 1.0
- `--seed` for deterministic shuffle

Outputs:
- `train.jsonl`, `val.jsonl`, `test.jsonl` in `--outdir`

## Pack
Inputs:
- Directory of `*.jsonl`

Outputs:
- `dataset_manifest.json` containing:
  - per-file sha256, bytes, rows
  - total_rows
  - created_at_utc

## Golden
`golden gen`:
- `--count` must be in [300, 800]
- Injects must-pass categories:
  - recency_trigger
  - politics_sensitive
  - closed_book_sourcepack

`golden run --engine none`:
- Structure-only checks:
  - count in [300,800]
  - each case has case_id/user/tags
  - must-pass tags present
- Returns 0 on success, 4 on failure.


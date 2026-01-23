# SLM-P2-DinoDS-Wave0Runner-SplitFloors-QC_Addendum

## Scope (post-P1 approval)
Non-blocking safety + portability fixes for Wave 0 production:
1) Split floors (optional)
- New flag: `split --min-per-nonzero-split N` (default 0; no behavior change)
- If N>0, any split with ratio > 0 must have at least N rows, else exit=6 (CONFIG_INVALID)

2) Runner stability
- `scripts/run.sh` uses `pwd -P` and pins to `$ROOT/.venv/bin/python` to avoid path-case drift and venv/python mismatch
- Self-heal runs `pip install -e .` only when `import dino_ds` fails

## Files changed
- `src/dino_ds/cli.py` (added split flag; wired dispatch)
- `src/dino_ds/commands/split_cmd.py` (added floor logic)
- `scripts/run.sh` (stable root + pinned venv python/pip)

## Smoke evidence
- `split --min-per-nonzero-split 1` fails with exit=6 when a non-zero split would be empty
- `./scripts/run.sh --version` twice prints `dino-ds 0.1.0` and does not drift across path spellings

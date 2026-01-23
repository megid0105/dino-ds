# SLM-P1-DinoDS-BuildSplitPack-Golden-HostWiring-Sketch

## Primary Flow (Wave 0)
1) Validate lane config
- `./scripts/run.sh validate --schema lane --config lane.yaml`

2) Build lane dataset
- `./scripts/run.sh build lane --config lane.yaml --out built.jsonl --seed 0`

3) Split into train/val/test
- `./scripts/run.sh split --in built.jsonl --outdir splits --seed 0 --train 0.9 --val 0.05 --test 0.05`

4) Pack (emit manifest with sha256)
- `./scripts/run.sh pack --indir splits --out dataset_manifest.json`

## Golden (CPU portable)
- Generate: `./scripts/run.sh golden gen --out golden_eval.jsonl --count 300 --seed 0`
- Validate structure: `./scripts/run.sh golden run --engine none --golden golden_eval.jsonl`

## Notes
- Uses `python -m dino_ds` runner via `scripts/run.sh` to avoid console-script drift.
- No network/tool execution required for these phases.


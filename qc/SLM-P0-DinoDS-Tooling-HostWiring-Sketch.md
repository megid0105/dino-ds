# SLM-P0-DinoDS-Tooling-HostWiring-Sketch

## Intended Users
- DTA dataset builders running local tooling
- CI can invoke the same commands (no network required for P0 gates)

## Invocation
Preferred:
- `./scripts/bootstrap.sh`
- `./scripts/run.sh <cmd> ...`

CLI module entry:
- `python -m dino_ds <cmd> ...`

## Hard Gates (P0)
1) Schema validation:
- `./scripts/run.sh validate --schema lane --config lane.yaml`
- `./scripts/run.sh validate --schema sources --config sources_manifest.json`
- `./scripts/run.sh validate --schema fixtures --config tool_replay_manifest.json`

2) QA lint:
- `./scripts/run.sh lint --qa-jsonl qa_eval.jsonl`

3) Integrity verification:
- `./scripts/run.sh sources verify --manifest sources_manifest.json`
- `./scripts/run.sh fixtures verify --manifest tool_replay_manifest.json`

## Outputs
- Exit codes only (no stdout contract required in P0)
- Schemas shipped as package data under `dino_ds/schemas/`


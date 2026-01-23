# SLM-P0-DinoDS-Tooling-PhasePropertyList

## Package / Entry
- Package: `dino-ds` (pip)
- Entry: `python -m dino_ds ...` (via `./scripts/run.sh`)
- Version: 0.1.0

## Scripts
- `./scripts/bootstrap.sh`
  - Creates `.venv` if missing
  - Installs editable package into `.venv`
- `./scripts/run.sh`
  - Activates `.venv`
  - Self-heals by running `pip install -e .` if import fails
  - Executes `python -m dino_ds ...`

## Exit Codes (LOCKED)
- 0 SUCCESS
- 1 INTERNAL_ERROR (NYI stubs return 1)
- 2 LINT_FAILED
- 3 SCHEMA_VALIDATION_FAILED
- 4 GOLDEN_FAILED (reserved)
- 5 IO_ERROR
- 6 CONFIG_INVALID

## Schemas (v1)
- Lane schema: `src/dino_ds/schemas/lane_schema.v1.json`
- Sources manifest: `src/dino_ds/schemas/sources_manifest.v1.json`
- Tool replay manifest: `src/dino_ds/schemas/tool_replay_manifest.v1.json`

## Lint Gates (P0)
- Enforces qa_mode in {closed_book, tool_grounded}
- Recency triggers require tool_grounded (keyword heuristic)
- Sensitive tags require linkage fields (minimum)
- Closed_book requires (answer_sources, sourcepack_id, answer_span_sha256)
- Tool_grounded requires (tool_call, fixture_ids, citations)


# QC Report — schema_probe — en_invalid

## Run Metadata
This section explains which run and spec versions produced this QC result.
- lane_id: `schema_probe`
- language slice: `en_invalid`
- run_id: `3e903e9f2f3e44e496080a18fd095ec5`
- date: `2026-02-19`
- rule_profile: `schema_stage`
- spec_version: `lane_schema.v1`
- equator_version: `not_reached`
- generator_commit: `929161eb3ec16efd4ab60c79bea23f399c640801`

## Counts
This section summarizes volume and how many checks produced fatal or warning outcomes.
| Metric | Value |
| --- | --- |
| rows_input | 0 |
| rows_generated | 0 |
| rows_validated | 0 |
| fatal_violations | 1 |
| warn_non_blocking | 0 |
| unique_fatal_codes | 1 |
| unique_warn_codes | 0 |

## Gate Results
This section shows each QC gate in Equator order and whether the slice passed.
| Gate | Status | Notes |
| --- | --- | --- |
| invariants | FAIL | fatals=schema_validation_failed:1 ; notes=failed_at_schema_stage_before_row_generation |
| malformed | PASS | notes=not_reached_due_to_schema_stage_failure |
| repetition | PASS | notes=not_reached_due_to_schema_stage_failure |
| leakage | PASS | notes=not_reached_due_to_schema_stage_failure |
| duplication | PASS | notes=not_reached_due_to_schema_stage_failure |
| proportions | PASS | notes=not_reached_due_to_schema_stage_failure |
| viability | PASS | notes=not_reached_due_to_schema_stage_failure |
| warn_only | PASS | notes=not_reached_due_to_schema_stage_failure |

## Fatal Summary
These are blocking QC failures and their counts.
- `schema_validation_failed`: 1

## Warning Summary
These are non-blocking QC warnings and their counts.
- none

## Failure Diagnostics
This section maps each code to gate, block behavior, and where operators should inspect first.
| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |
| --- | --- | --- | --- | --- | --- | --- |
| `schema_validation_failed` | FATAL | invariants | 1 | yes | Inspect row examples for this code to locate the blocked contract. | schema_validation_failed \| message='lane_id' is a required property \| instance_path=<root> \| schema_path=required \| validator=required \| exit=3 |

## Top Examples
Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.
### `schema_validation_failed`
- `lane_en_invalid.yaml`: schema_validation_failed | message='lane_id' is a required property | instance_path=<root> | schema_path=required | validator=required | exit=3

## Thresholds Used
These are the active lane-scoped thresholds used in this QC run.
- none

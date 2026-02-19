# QC Report — lane_03_think_mode — en

## Run Metadata
This section explains which run and spec versions produced this QC result.
- lane_id: `lane_03_think_mode`
- language slice: `en`
- run_id: `RUN_6eba2897`
- date: `2026-02-20`
- rule_profile: `2`
- spec_version: `Full_Dataset_Spec_FULL_LATEST_v17`
- equator_version: `DTAD_CTv3_QC_EQUATOR_FEB_18_2026_v4_1`
- generator_commit: `929161eb3ec16efd4ab60c79bea23f399c640801`

## Counts
This section summarizes volume and how many checks produced fatal or warning outcomes.
| Metric | Value |
| --- | --- |
| rows_input | 200 |
| rows_generated | 200 |
| rows_validated | 0 |
| fatal_violations | 200 |
| warn_non_blocking | 0 |
| unique_fatal_codes | 1 |
| unique_warn_codes | 0 |

## Gate Results
This section shows each QC gate in Equator order and whether the slice passed.
| Gate | Status | Notes |
| --- | --- | --- |
| invariants | FAIL | fatals=missing_required_key:messages:200 |
| malformed | PASS | - |
| repetition | PASS | - |
| leakage | PASS | - |
| duplication | PASS | - |
| proportions | PASS | - |
| viability | PASS | notes=not_applicable |
| warn_only | PASS | notes=aggregated_non_blocking_warnings |

## Fatal Summary
These are blocking QC failures and their counts.
- `missing_required_key:messages`: 200

## Warning Summary
These are non-blocking QC warnings and their counts.
- none

## Failure Diagnostics
This section maps each code to gate, block behavior, and where operators should inspect first.
| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |
| --- | --- | --- | --- | --- | --- | --- |
| `missing_required_key:messages` | FATAL | invariants | 200 | yes | Row template is missing required schema labels/keys. | missing_required_key:messages |

## Top Examples
Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.
### `missing_required_key:messages`
- `lane_03_think_mode_en_00000000`: missing_required_key:messages
- `lane_03_think_mode_en_00000001`: missing_required_key:messages
- `lane_03_think_mode_en_00000002`: missing_required_key:messages
- `lane_03_think_mode_en_00000003`: missing_required_key:messages
- `lane_03_think_mode_en_00000004`: missing_required_key:messages

## Thresholds Used
These are the active lane-scoped thresholds used in this QC run.
- `dup_candidate_threshold`: 0.25
- `dup_contain_threshold`: 0.55
- `lane03_image_context_max_share`: 0.05
- `lane03_implicit_multistep_min_share`: 0.6
- `lane03_structure_max_share`: 0.05
- `lane03_tool_call_max_share`: 0.1
- `proportion_min_n`: 30

# QC Report — lane_03_think_mode — en

## Run Metadata
This section explains which run and spec versions produced this QC result.
- lane_id: `lane_03_think_mode`
- language slice: `en`
- run_id: `RUN_9084f39b`
- date: `2026-02-20`
- rule_profile: `2`
- spec_version: `Full_Dataset_Spec_FULL_LATEST_v17`
- equator_version: `DTAD_CTv3_QC_EQUATOR_FEB_18_2026_v4_1`
- generator_commit: `929161eb3ec16efd4ab60c79bea23f399c640801`

## Counts
This section summarizes volume and how many checks produced fatal or warning outcomes.
| Metric | Value |
| --- | --- |
| rows_input | 1 |
| rows_generated | 1 |
| rows_validated | 1 |
| fatal_violations | 0 |
| warn_non_blocking | 3 |
| unique_fatal_codes | 0 |
| unique_warn_codes | 3 |

## Gate Results
This section shows each QC gate in Equator order and whether the slice passed.
| Gate | Status | Notes |
| --- | --- | --- |
| invariants | PASS | - |
| malformed | PASS | - |
| repetition | PASS | - |
| leakage | PASS | - |
| duplication | PASS | - |
| proportions | WARN | warns=lane03_not_reliable_small_n:1, lane03_optional_share_not_reliable_small_n:1, not_reliable_small_n:1 |
| viability | PASS | notes=not_applicable |
| warn_only | WARN | warns=lane03_not_reliable_small_n:1, lane03_optional_share_not_reliable_small_n:1, not_reliable_small_n:1 ; notes=aggregated_non_blocking_warnings |

## Fatal Summary
These are blocking QC failures and their counts.
- none

## Warning Summary
These are non-blocking QC warnings and their counts.
- `lane03_not_reliable_small_n`: 1
- `lane03_optional_share_not_reliable_small_n`: 1
- `not_reliable_small_n`: 1

## Failure Diagnostics
This section maps each code to gate, block behavior, and where operators should inspect first.
| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |
| --- | --- | --- | --- | --- | --- | --- |
| `lane03_not_reliable_small_n` | WARN | proportions, warn_only | 1 | no | Non-blocking signal; review and decide whether to tighten data generation. | language=en n=1 < min_n=30; skipped lane 03 reasoning/structure distribution gate |
| `lane03_optional_share_not_reliable_small_n` | WARN | proportions, warn_only | 1 | no | Non-blocking signal; review and decide whether to tighten data generation. | language=en n=1 < min_n=30; skipped lane 03 optional share gate |
| `not_reliable_small_n` | WARN | proportions, warn_only | 1 | no | Non-blocking signal; review and decide whether to tighten data generation. | language=en n=1 < min_n=30; skipped mode/tone proportion gate |

## Top Examples
Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.
### `lane03_not_reliable_small_n`
- `slice`: language=en n=1 < min_n=30; skipped lane 03 reasoning/structure distribution gate
### `lane03_optional_share_not_reliable_small_n`
- `slice`: language=en n=1 < min_n=30; skipped lane 03 optional share gate
### `not_reliable_small_n`
- `slice`: language=en n=1 < min_n=30; skipped mode/tone proportion gate

## Thresholds Used
These are the active lane-scoped thresholds used in this QC run.
- `dup_candidate_threshold`: 0.25
- `dup_contain_threshold`: 0.55
- `lane03_image_context_max_share`: 0.05
- `lane03_implicit_multistep_min_share`: 0.6
- `lane03_structure_max_share`: 0.05
- `lane03_tool_call_max_share`: 0.1
- `proportion_min_n`: 30

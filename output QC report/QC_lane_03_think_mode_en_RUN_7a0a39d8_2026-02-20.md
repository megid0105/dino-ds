# QC Report — lane_03_think_mode — en

## Run Metadata
This section explains which run and spec versions produced this QC result.
- lane_id: `lane_03_think_mode`
- language slice: `en`
- run_id: `RUN_7a0a39d8`
- date: `2026-02-20`
- rule_profile: `2`
- spec_version: `Full_Dataset_Spec_FULL_LATEST_v17`
- equator_version: `DTAD_CTv3_QC_EQUATOR_FEB_18_2026_v4_1`
- generator_commit: `929161eb3ec16efd4ab60c79bea23f399c640801`

## Counts
This section summarizes volume and how many checks produced fatal or warning outcomes.
| Metric | Value |
| --- | --- |
| rows_input | 50 |
| rows_generated | 50 |
| rows_validated | 50 |
| fatal_violations | 1 |
| warn_non_blocking | 16 |
| unique_fatal_codes | 1 |
| unique_warn_codes | 1 |

## Gate Results
This section shows each QC gate in Equator order and whether the slice passed.
| Gate | Status | Notes |
| --- | --- | --- |
| invariants | PASS | - |
| malformed | PASS | - |
| repetition | WARN | warns=trip_token_function_only:16 |
| leakage | PASS | - |
| duplication | PASS | - |
| proportions | FAIL | fatals=lane03_structure_share_too_high:1 ; n=50, notes=mode_tone_proportion PASS language=en n=50 | lane03_optional_shares PASS language=en n=50 tool_call_share=0.000/0.100 image_context_share=0.000/0.050 |
| viability | PASS | notes=not_applicable |
| warn_only | WARN | warns=trip_token_function_only:16 ; notes=aggregated_non_blocking_warnings |

## Fatal Summary
These are blocking QC failures and their counts.
- `lane03_structure_share_too_high`: 1

## Warning Summary
These are non-blocking QC warnings and their counts.
- `trip_token_function_only`: 16

## Failure Diagnostics
This section maps each code to gate, block behavior, and where operators should inspect first.
| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |
| --- | --- | --- | --- | --- | --- | --- |
| `lane03_structure_share_too_high` | FATAL | proportions | 1 | yes | Inspect row examples for this code to locate the blocked contract. | language=en n=50; top_structure_share=0.060 > max=0.050 (top_count=3, signature=open=a way to make\|len=l\|sent=l\|list=few\|imp\|head) |
| `trip_token_function_only` | WARN | repetition, warn_only | 16 | no | Repetition gate hit; inspect repeated token/bigram in assistant_response. | assistant_response has function token 'a' repeated 3x in 12-token window |

## Top Examples
Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.
### `lane03_structure_share_too_high`
- `slice`: language=en n=50; top_structure_share=0.060 > max=0.050 (top_count=3, signature=open=a way to make|len=l|sent=l|list=few|imp|head)
### `trip_token_function_only`
- `lane_03_think_mode_en_00000001`: assistant_response has function token 'a' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000004`: assistant_response has function token 'the' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000006`: assistant_response has function token 'a' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000013`: assistant_response has function token 'the' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000015`: assistant_response has function token 'a' repeated 3x in 12-token window

## Thresholds Used
These are the active lane-scoped thresholds used in this QC run.
- `dup_candidate_threshold`: 0.25
- `dup_contain_threshold`: 0.55
- `lane03_image_context_max_share`: 0.05
- `lane03_implicit_multistep_min_share`: 0.6
- `lane03_structure_max_share`: 0.05
- `lane03_tool_call_max_share`: 0.1
- `proportion_min_n`: 30

# QC Report — lane_03_think_mode — en

## Run Metadata
This section explains which run and spec versions produced this QC result.
- lane_id: `lane_03_think_mode`
- language slice: `en`
- run_id: `RUN_d76e91da`
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
| rows_validated | 197 |
| fatal_violations | 3 |
| warn_non_blocking | 56 |
| unique_fatal_codes | 1 |
| unique_warn_codes | 2 |

## Gate Results
This section shows each QC gate in Equator order and whether the slice passed.
| Gate | Status | Notes |
| --- | --- | --- |
| invariants | PASS | - |
| malformed | PASS | - |
| repetition | FAIL | fatals=trip_bigram_content:3 ; warns=trip_bigram_function_only:1, trip_token_function_only:55 |
| leakage | PASS | - |
| duplication | PASS | - |
| proportions | PASS | n=197, notes=mode_tone_proportion PASS language=en n=197 | lane03_optional_shares PASS language=en n=197 tool_call_share=0.000/0.100 image_context_share=0.000/0.050 | lane03_reasoning_structure_distribution PASS language=en n=197 implicit_multistep_share=0.853 top_structure_share=0.025 |
| viability | PASS | notes=not_applicable |
| warn_only | WARN | warns=trip_bigram_function_only:1, trip_token_function_only:55 ; notes=aggregated_non_blocking_warnings |

## Fatal Summary
These are blocking QC failures and their counts.
- `trip_bigram_content`: 3

## Warning Summary
These are non-blocking QC warnings and their counts.
- `trip_bigram_function_only`: 1
- `trip_token_function_only`: 55

## Failure Diagnostics
This section maps each code to gate, block behavior, and where operators should inspect first.
| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |
| --- | --- | --- | --- | --- | --- | --- |
| `trip_bigram_content` | FATAL | repetition | 3 | yes | Repetition gate hit; inspect repeated token/bigram in assistant_response. | assistant_response has content bigram 'route for' repeated 3x in 30-token window |
| `trip_token_function_only` | WARN | repetition, warn_only | 55 | no | Repetition gate hit; inspect repeated token/bigram in assistant_response. | assistant_response has function token 'the' repeated 3x in 12-token window |
| `trip_bigram_function_only` | WARN | repetition, warn_only | 1 | no | Repetition gate hit; inspect repeated token/bigram in assistant_response. | assistant_response has function bigram 'that is' repeated 3x in 30-token window |

## Top Examples
Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.
### `trip_bigram_content`
- `lane_03_think_mode_en_00000017`: assistant_response has content bigram 'route for' repeated 3x in 30-token window
- `lane_03_think_mode_en_00000072`: assistant_response has content bigram 'route for' repeated 3x in 30-token window
- `lane_03_think_mode_en_00000073`: assistant_response has content bigram 'qa team' repeated 3x in 30-token window
### `trip_bigram_function_only`
- `lane_03_think_mode_en_00000180`: assistant_response has function bigram 'that is' repeated 3x in 30-token window
### `trip_token_function_only`
- `lane_03_think_mode_en_00000002`: assistant_response has function token 'the' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000023`: assistant_response has function token 'a' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000025`: assistant_response has function token 'a' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000027`: assistant_response has function token 'a' repeated 3x in 12-token window
- `lane_03_think_mode_en_00000028`: assistant_response has function token 'a' repeated 3x in 12-token window

## Thresholds Used
These are the active lane-scoped thresholds used in this QC run.
- `dup_candidate_threshold`: 0.25
- `dup_contain_threshold`: 0.55
- `lane03_image_context_max_share`: 0.05
- `lane03_implicit_multistep_min_share`: 0.6
- `lane03_structure_max_share`: 0.05
- `lane03_tool_call_max_share`: 0.1
- `proportion_min_n`: 30

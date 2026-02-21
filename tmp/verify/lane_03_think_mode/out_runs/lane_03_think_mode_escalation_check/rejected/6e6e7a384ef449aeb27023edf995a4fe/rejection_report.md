# Validation Rejection Report — lane_03_think_mode

- run_id: `6e6e7a384ef449aeb27023edf995a4fe`
- rows_total: `20`
- rows_rejected: `5`

## Files
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/6e6e7a384ef449aeb27023edf995a4fe/built_candidate.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/6e6e7a384ef449aeb27023edf995a4fe/train_6e6e7a384ef449aeb27023edf995a4fe.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/6e6e7a384ef449aeb27023edf995a4fe/rejection_details.json`

## Validator Summary
```text
rule_profile=03 FAIL: violations=11, unique=3
top_reasons:
- duplicate_user_message: 5 (gates=duplication:5)
- duplicate_assistant_response: 5 (gates=duplication:5)
- dup_candidate_warn_share_too_high: 1 (gates=duplication:1)
fatal_gate_breakdown:
- duplication: duplicate_user_message:5, duplicate_assistant_response:5, dup_candidate_warn_share_too_high:1
examples:
- duplicate_user_message: lane_03_think_mode_en_00000009 duplicates lane_03_think_mode_en_00000006
- duplicate_assistant_response: lane_03_think_mode_en_00000009 duplicates lane_03_think_mode_en_00000006
- duplicate_user_message: lane_03_think_mode_en_00000010 duplicates lane_03_think_mode_en_00000000
- duplicate_assistant_response: lane_03_think_mode_en_00000010 duplicates lane_03_think_mode_en_00000000
- duplicate_user_message: lane_03_think_mode_en_00000013 duplicates lane_03_think_mode_en_00000001
- duplicate_assistant_response: lane_03_think_mode_en_00000013 duplicates lane_03_think_mode_en_00000001
- duplicate_user_message: lane_03_think_mode_en_00000014 duplicates lane_03_think_mode_en_00000005
- duplicate_assistant_response: lane_03_think_mode_en_00000014 duplicates lane_03_think_mode_en_00000005
- duplicate_user_message: lane_03_think_mode_en_00000019 duplicates lane_03_think_mode_en_00000005
- duplicate_assistant_response: lane_03_think_mode_en_00000019 duplicates lane_03_think_mode_en_00000005
- dup_candidate_warn_share_too_high: language=en dup_candidate_unconfirmed_share=0.950 > cap=0.350 (warn_rows=19, n=20)
detailed_failures:
- duplicate_user_message: count=5
  - lane_03_think_mode_en_00000009 duplicates lane_03_think_mode_en_00000006
  - lane_03_think_mode_en_00000010 duplicates lane_03_think_mode_en_00000000
  - lane_03_think_mode_en_00000013 duplicates lane_03_think_mode_en_00000001
  - lane_03_think_mode_en_00000014 duplicates lane_03_think_mode_en_00000005
  - lane_03_think_mode_en_00000019 duplicates lane_03_think_mode_en_00000005
- duplicate_assistant_response: count=5
  - lane_03_think_mode_en_00000009 duplicates lane_03_think_mode_en_00000006
  - lane_03_think_mode_en_00000010 duplicates lane_03_think_mode_en_00000000
  - lane_03_think_mode_en_00000013 duplicates lane_03_think_mode_en_00000001
  - lane_03_think_mode_en_00000014 duplicates lane_03_think_mode_en_00000005
  - lane_03_think_mode_en_00000019 duplicates lane_03_think_mode_en_00000005
- dup_candidate_warn_share_too_high: count=1
  - language=en dup_candidate_unconfirmed_share=0.950 > cap=0.350 (warn_rows=19, n=20)
warn_gate_breakdown:
- duplication: dup_candidate_unconfirmed:19
- proportions: not_reliable_small_n:1, lane03_optional_share_not_reliable_small_n:1, lane03_not_reliable_small_n:1
warnings_non_blocking:
- dup_candidate_unconfirmed: 19 (gates=duplication:19)
  - lane_03_think_mode_en_00000001 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
  - lane_03_think_mode_en_00000002 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
  - lane_03_think_mode_en_00000003 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- not_reliable_small_n: 1 (gates=proportions:1)
  - language=en n=15 < min_n=30; skipped mode/tone proportion gate
- lane03_optional_share_not_reliable_small_n: 1 (gates=proportions:1)
  - language=en n=15 < min_n=30; skipped lane 03 optional share gate
- lane03_not_reliable_small_n: 1 (gates=proportions:1)
  - language=en n=15 < min_n=30; skipped lane 03 reasoning/structure distribution gate
warning_examples:
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000001 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000002 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000003 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000004 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000005 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000006 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000007 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000008 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000009 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000010 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=1.000 Ojac=1.000 C3=1.000 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000011 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000012 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000013 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000014 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000015 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000016 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000017 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000018 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- dup_candidate_unconfirmed: lane_03_think_mode_en_00000019 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.933 Ojac=0.875 C3=0.933 signals=1/3 token_mode=word (candidate=0.010)
- not_reliable_small_n: language=en n=15 < min_n=30; skipped mode/tone proportion gate
- lane03_optional_share_not_reliable_small_n: language=en n=15 < min_n=30; skipped lane 03 optional share gate
- lane03_not_reliable_small_n: language=en n=15 < min_n=30; skipped lane 03 reasoning/structure distribution gate
qc_reports:
- /Users/chanpakho/Desktop/Download/project/dino_ds/output QC report/QC_lane_03_think_mode_en_6e6e7a384ef449aeb27023edf995a4fe_2026-02-21.md
```

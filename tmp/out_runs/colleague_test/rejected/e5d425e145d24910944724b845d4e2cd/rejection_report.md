# Validation Rejection Report — lane_03_think_mode

- run_id: `e5d425e145d24910944724b845d4e2cd`
- rows_total: `100`
- rows_rejected: `96`

## Files
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/out_runs/colleague_test/rejected/e5d425e145d24910944724b845d4e2cd/built_candidate.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/out_runs/colleague_test/rejected/e5d425e145d24910944724b845d4e2cd/train_e5d425e145d24910944724b845d4e2cd.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/out_runs/colleague_test/rejected/e5d425e145d24910944724b845d4e2cd/rejection_details.json`

## Validator Summary
```text
rule_profile=03 FAIL: violations=97, unique=5
top_reasons:
- near_duplicate_overlap: 86 (gates=duplication:86)
- mechanism_leakage: 6 (gates=leakage:6)
- trip_bigram_content: 3 (gates=repetition:3)
- adjacent_dup_token: 1 (gates=repetition:1)
- trip_token_content: 1 (gates=repetition:1)
fatal_gate_breakdown:
- repetition: trip_bigram_content:3, adjacent_dup_token:1, trip_token_content:1
- leakage: mechanism_leakage:6
- duplication: near_duplicate_overlap:86
examples:
- mechanism_leakage: lane_03_think_mode_en_00000002: assistant_response -> 'A practical frame for quality remediation in stakeholders doubt numbers due to recurring mismatches is to treat source systems are fragmented and ownership is split, stable defini…'
- mechanism_leakage: lane_03_think_mode_en_00000003: assistant_response -> 'In high pressure moments of stakeholders doubt numbers due to recurring mismatches, quality remediation remains coherent when source systems are fragmented and ownership is split…'
- mechanism_leakage: lane_03_think_mode_en_00000008: assistant_response -> 'quality remediation can stay durable in stakeholders doubt numbers due to recurring mismatches if every tradeoff keeps source systems are fragmented and ownership is split, stable…'
- mechanism_leakage: lane_03_think_mode_en_00000011: assistant_response -> 'quality remediation holds up in stakeholders doubt numbers due to recurring mismatches when decisions stop oscillating between source systems are fragmented and ownership is split…'
- adjacent_dup_token: lane_03_think_mode_en_00000042: assistant_response has adjacent duplicate token 'document'
- trip_bigram_content: lane_03_think_mode_en_00000042: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
- trip_bigram_content: lane_03_think_mode_en_00000043: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
- trip_token_content: lane_03_think_mode_en_00000050: assistant_response has content token 'plan' repeated 3x in 12-token window
- mechanism_leakage: lane_03_think_mode_en_00000062: assistant_response -> 'quality remediation usually drifts in stakeholders doubt numbers due to recurring mismatches when teams optimize for stable definitions and reliable downstream reporting before va…'
- trip_bigram_content: lane_03_think_mode_en_00000076: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
- mechanism_leakage: lane_03_think_mode_en_00000094: assistant_response -> 'quality remediation holds up in stakeholders doubt numbers due to recurring mismatches when decisions stop oscillating between source systems are fragmented and ownership is split…'
- near_duplicate_overlap: lane_03_think_mode_en_00000001 vs lane_03_think_mode_en_00000000 dup_rule=rule2_multisignal Omin=0.475 Ojac=0.439 C3=0.032 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000005 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.513 Ojac=0.428 C3=0.066 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000009 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.476 Ojac=0.437 C3=0.037 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000010 vs lane_03_think_mode_en_00000000 dup_rule=rule2_multisignal Omin=0.498 Ojac=0.497 C3=0.041 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000012 vs lane_03_think_mode_en_00000006 dup_rule=rule2_multisignal Omin=0.434 Ojac=0.399 C3=0.035 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000013 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.443 Ojac=0.406 C3=0.051 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000014 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.469 Ojac=0.428 C3=0.037 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000015 vs lane_03_think_mode_en_00000010 dup_rule=rule2_multisignal Omin=0.476 Ojac=0.416 C3=0.026 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000016 vs lane_03_think_mode_en_00000013 dup_rule=rule2_multisignal Omin=0.537 Ojac=0.417 C3=0.057 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000017 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.488 Ojac=0.440 C3=0.039 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000018 vs lane_03_think_mode_en_00000000 dup_rule=rule2_multisignal Omin=0.491 Ojac=0.404 C3=0.030 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000019 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.480 Ojac=0.405 C3=0.070 signals=2/3 token_mode=word (candidate=0.100)
- near_duplicate_overlap: lane_03_think_mode_en_00000020 vs lane_03_think_mode_en_00000012 dup_rule=rule2_multisignal Omin=0.457 Ojac=0.417 C3=0.023 signals=2/3 token_mode=word (candidate=0.100)
detailed_failures:
- near_duplicate_overlap: count=86
  - lane_03_think_mode_en_00000001 vs lane_03_think_mode_en_00000000 dup_rule=rule2_multisignal Omin=0.475 Ojac=0.439 C3=0.032 signals=2/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000005 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.513 Ojac=0.428 C3=0.066 signals=2/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000009 vs lane_03_think_mode_en_00000004 dup_rule=rule2_multisignal Omin=0.476 Ojac=0.437 C3=0.037 signals=2/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000010 vs lane_03_think_mode_en_00000000 dup_rule=rule2_multisignal Omin=0.498 Ojac=0.497 C3=0.041 signals=2/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000012 vs lane_03_think_mode_en_00000006 dup_rule=rule2_multisignal Omin=0.434 Ojac=0.399 C3=0.035 signals=2/3 token_mode=word (candidate=0.100)
- mechanism_leakage: count=6
  - lane_03_think_mode_en_00000002: assistant_response -> 'A practical frame for quality remediation in stakeholders doubt numbers due to recurring mismatches is to treat source systems are fragmented and ownership is split, stable defini…'
  - lane_03_think_mode_en_00000003: assistant_response -> 'In high pressure moments of stakeholders doubt numbers due to recurring mismatches, quality remediation remains coherent when source systems are fragmented and ownership is split…'
  - lane_03_think_mode_en_00000008: assistant_response -> 'quality remediation can stay durable in stakeholders doubt numbers due to recurring mismatches if every tradeoff keeps source systems are fragmented and ownership is split, stable…'
  - lane_03_think_mode_en_00000011: assistant_response -> 'quality remediation holds up in stakeholders doubt numbers due to recurring mismatches when decisions stop oscillating between source systems are fragmented and ownership is split…'
  - lane_03_think_mode_en_00000062: assistant_response -> 'quality remediation usually drifts in stakeholders doubt numbers due to recurring mismatches when teams optimize for stable definitions and reliable downstream reporting before va…'
- trip_bigram_content: count=3
  - lane_03_think_mode_en_00000042: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
  - lane_03_think_mode_en_00000043: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
  - lane_03_think_mode_en_00000076: assistant_response has content bigram 'before adding' repeated 3x in 30-token window
- adjacent_dup_token: count=1
  - lane_03_think_mode_en_00000042: assistant_response has adjacent duplicate token 'document'
- trip_token_content: count=1
  - lane_03_think_mode_en_00000050: assistant_response has content token 'plan' repeated 3x in 12-token window
warn_gate_breakdown:
- repetition: trip_token_function_only:26
- duplication: dup_candidate_unconfirmed:3
warnings_non_blocking:
- trip_token_function_only: 26 (gates=repetition:26)
  - lane_03_think_mode_en_00000000: assistant_response has function token 'and' repeated 3x in 12-token window
  - lane_03_think_mode_en_00000002: assistant_response has function token 'and' repeated 3x in 12-token window
  - lane_03_think_mode_en_00000004: assistant_response has function token 'the' repeated 3x in 12-token window
- dup_candidate_unconfirmed: 3 (gates=duplication:3)
  - lane_03_think_mode_en_00000004 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.330 Ojac=0.267 C3=0.062 signals=1/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000006 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.317 Ojac=0.250 C3=0.038 signals=1/3 token_mode=word (candidate=0.100)
  - lane_03_think_mode_en_00000007 vs lane_03_think_mode_en_00000000 dup_rule=candidate_only Omin=0.452 Ojac=0.379 C3=0.033 signals=1/3 token_mode=word (candidate=0.100)
warning_examples:
- trip_token_function_only: lane_03_think_mode_en_00000000: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000002: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000004: assistant_response has function token 'the' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000005: assistant_response has function token 'the' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000008: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000011: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000015: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000017: assistant_response has function token 'the' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000035: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000036: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000040: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000043: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000045: assistant_response has function token 'the' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000048: assistant_response has function token 'is' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000049: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000055: assistant_response has function token 'is' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000057: assistant_response has function token 'is' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000064: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000065: assistant_response has function token 'is' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000078: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000080: assistant_response has function token 'the' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000086: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000091: assistant_response has function token 'and' repeated 3x in 12-token window
- trip_token_function_only: lane_03_think_mode_en_00000092: assistant_response has function token 'is' repeated 3x in 12-token window
qc_reports:
- /Users/chanpakho/Desktop/Download/project/dino_ds/output QC report/QC_lane_03_think_mode_en_e5d425e145d24910944724b845d4e2cd_2026-02-21.md
```

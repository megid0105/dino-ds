# Validation Rejection Report — lane_03_think_mode

- run_id: `a070721f92934a46ac89a0c5f17e72d9`
- rows_total: `20`
- rows_rejected: `20`

## Files
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/a070721f92934a46ac89a0c5f17e72d9/built_candidate.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/a070721f92934a46ac89a0c5f17e72d9/train_a070721f92934a46ac89a0c5f17e72d9.jsonl`
- `/Users/chanpakho/Desktop/Download/project/dino_ds/tmp/verify/lane_03_think_mode/out_runs/lane_03_think_mode_escalation_check/rejected/a070721f92934a46ac89a0c5f17e72d9/rejection_details.json`

## Validator Summary
```text
rule_profile=03 FAIL: violations=20, unique=1
top_reasons:
- lane_scoped_field:connector_needed: 20 (gates=invariants:20)
fatal_gate_breakdown:
- invariants: lane_scoped_field:connector_needed:20
examples:
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000000: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000001: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000002: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000003: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000004: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000005: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000006: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000007: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000008: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000009: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000010: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000011: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000012: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000013: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000014: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000015: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000016: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000017: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000018: lane_scoped_field:connector_needed
- lane_scoped_field:connector_needed: lane_03_think_mode_en_00000019: lane_scoped_field:connector_needed
detailed_failures:
- lane_scoped_field:connector_needed: count=20
  - lane_03_think_mode_en_00000000: lane_scoped_field:connector_needed
  - lane_03_think_mode_en_00000001: lane_scoped_field:connector_needed
  - lane_03_think_mode_en_00000002: lane_scoped_field:connector_needed
  - lane_03_think_mode_en_00000003: lane_scoped_field:connector_needed
  - lane_03_think_mode_en_00000004: lane_scoped_field:connector_needed
qc_reports:
- /Users/chanpakho/Desktop/Download/project/dino_ds/output QC report/QC_lane_03_think_mode_en_a070721f92934a46ac89a0c5f17e72d9_2026-02-21.md
```

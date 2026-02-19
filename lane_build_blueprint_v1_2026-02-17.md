# Lane Build Blueprint v1 (2026-02-17)

## 1. Purpose
This blueprint defines the production rebuild mechanism for DinoDS lanes using strict v17r3 contracts and strict-dup quality requirements. It is designed to be lane-agnostic in mechanism, with lane-specific labels and output constraints injected through `label_pack` and lane contract fields.

Primary source-of-truth order:
1. `Full_Dataset_Spec_FULL_LATEST_v17.md`
2. `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md`
3. `DinoDS_Lane_QC_Standard_v17r3.md` (+ Addition)
4. `DTAD_CTv3_QC_EQUATOR_FEB_10_2026_v3_TH_CJK_PATCH_APPENDED_MULTITURN_v3.md`
5. `Lane_Contract_Matrix_v17_multilingual_strategy_v3.csv`

## 2. Core Mechanism: Coupled Dict-Slot Rendering

### 2.1 Non-negotiable slot graph
All plain-chat style strictdup lanes use:

- `generation_mode: template_expand`
- `expand_dict_slots:`
  - `case`
  - `q_template`
  - `a_skeleton`
  - `label_pack`

`case` stores semantic atoms only.
`q_template` renders `user_message`.
`a_skeleton` renders `assistant_response`.
`label_pack` controls mode/tone/intent/flags/representation distributions.

### 2.2 Case bank contract (topic-first)
Each `case` item must be coherent as a standalone scenario and include high-information anchors:

- `topic`
- `scenario`
- `audience`
- `channel`
- `risk`
- `intent`
- `action_request`
- `constraint`
- `desired_outcome`
- `tone_marker`
- `context_hint`
- `followup_hint`

Recommended extended atoms for depth and anti-overlap:
- `framework_tag`
- `first_action`
- `check_signal`
- `fallback_hint`
- `device_hint`
- `timebox`
- `budget`

Strict bans in `case`:
- no `user_message`
- no `assistant_response`
- no placeholder scaffolding text
- no random nonce/tag tails used only to dodge duplication detection

### 2.3 Template responsibility
- `q_template` items must be dicts with `user_message`.
- `a_skeleton` items must be dicts with `assistant_response`.
- Both must compose from multi-bank atoms, not hardcoded long monologues.

### 2.4 Helper banks (minimum)
For strictdup stability, keep rich helper banks in every language file:
- `q_opening`
- `q_followup`
- `q_context_wrap`
- `bullets_intro`
- `clarify_q`
- `close_line`
- `context_pack`
- `bullet_pack`

## 3. Diversity by Design (No Cheating)

### 3.1 Anti-cheating rule
Do not create pseudo-unique nonsense fragments to evade token overlap checks.
Every generated line must be native, meaningful, and operationally plausible.

### 3.2 Structural diversity rules
- Large family sets for `q_template` and `a_skeleton`.
- Different opener stems and clause orders.
- Different reasoning topologies (risk-first, outcome-first, dependency-first, rollback-first, etc.).
- No dominant repeated shell pattern across most rows.

### 3.3 Content-bearing anchors per output
Each final output must include multiple anchors from different slot groups:
- risk + action + constraint + outcome + context

This avoids high max-sup overlap and improves real training quality.

## 4. Hard-Coded Text Budget
Use light scaffolding only.
The semantic payload must come from slot atoms, not repeated fixed paragraphs.

Practical rule:
- short framing text allowed
- content-heavy clauses must be slot-driven
- avoid generic universal bullets reused across topics

## 5. Bank Size and Capacity Targets (Production)

For strictdup-heavy lanes (Lane 03 baseline):
- `case`: >= 520
- `context_pack`: >= 260
- `bullet_pack`: >= 360
- `q_template`: >= 240
- `a_skeleton`: >= 240
- `label_pack`: >= 200
- `q_opening`: >= 40
- `q_followup`: >= 40
- `q_context_wrap`: >= 40
- `bullets_intro`: >= 40
- `clarify_q`: >= 32
- `close_line`: >= 40

These are floor values; increase when strictdup pressure is high.

## 6. Viability Settings

Use strong fill settings:
- `fail_if_underfilled: true`
- high `max_attempts` (lane/language dependent)
- high `attempts_per_row`

Capacity expectation:
- practical combinational space should comfortably exceed `count_target` after QC rejection pressure.

## 7. Multilingual Native Quality Rules

- Per-language YAML must be fully native for that language.
- No English clones in non-English files.
- No mixed-language constructions unless genuinely native usage for that locale.
- Keep same slot keys and schema shape across languages, but rewrite content natively.

## 8. TH/CJK Quality and Overlap Controls

- Avoid repeated short canned clauses as core body.
- Use multiple content units from different slot groups per response.
- Prevent repeated high-frequency short chunks that trigger char-bigram overlap issues.
- Ensure opener diversity and varied clause starts.

## 9. Label and Contract Enforcement

- Extract fixed/allowed labels from lane contract.
- Enforce only contract-valid values for mode/tone/intent/subtype/representation and flags.
- Place ratio control in `label_pack`.
- Keep top-level lane config and required keys stable per schema.

## 10. QC Execution Loop

After each meaningful patch batch:
1. Run lane sweep: `./scripts/qc_lane_sweep.sh lanes/<target_lane>`
2. Capture `RUN_UUID`
3. Review failures by language and pattern
4. Patch banks/families (not isolated one-off lines)
5. Repeat until sweep is stable and fill safety is strong

## 11. Blueprint Rollout Order

1. `lane_03_think_mode` (master blueprint)
2. `lane_04_quick_mode` (short-form derivative)
3. `lane_05_conversation_mode` (continuity-aware derivative)
4. Remaining plain-chat-like lanes via label/contract remapping

## 12. Acceptance Criteria

A lane is production-ready only when:
- schema-valid lane YAMLs per language
- exact `count_target` respected
- strictdup-compliant structural diversity
- no scaffolding leakage or token-repetition artifacts
- native naturalness in every language file
- stable QC sweep across all language files

# YAML Build Recommendation (Lanes 01-37, excluding 36)

## Important Notice
This document is a **build recommendation**, not a specification.
It is implementation guidance to help pass QC consistently at scale.
This file is **not SOT**.

## Source of Truth (SOT)
The authoritative requirements are the spec + validator sources below:
- `QC Spec/`
- `full_dataset_spec_v17`
- Equator/validator behavior used by `./dino-ds qc`

If this recommendation conflicts with any SOT source, **follow SOT**.

## Scope
This recommendation applies to:
- `lane_01_identity`
- `lane_02_tone_behaviour_foundation`
- `lane_03_think_mode`
- `lane_04_quick_mode`
- `lane_05_conversation_mode`
- `lane_06_general_intent_classification`
- `lane_07_search_triggering`
- `lane_08_search_integration`
- `lane_09_multi_step_action_flow`
- `lane_10_connector_intent_detection`
- `lane_11_connector_action_mapping`
- `lane_12_deeplink_action_mapping`
- `lane_13_doc_export_spec`
- `lane_14_zip_wrap_spec`
- `lane_15_code_generation`
- `lane_16_code_json_spec_mode`
- `lane_17_comparison_tables`
- `lane_18_chart_spec`
- `lane_19_continuity_decision`
- `lane_20_continuity_execution`
- `lane_21_rewrite`
- `lane_22_translate`
- `lane_23_grammar_fix`
- `lane_24_history_search_trigger`
- `lane_25_history_search_integration`
- `lane_26_image_context_understanding`
- `lane_27_image_tooling`
- `lane_28_emote6_labeling`
- `lane_29_safety_history_politics`
- `lane_30_safety_no_leakage`
- `lane_31_mode_selection`
- `lane_32_representation_choice`
- `lane_33_fallback_behavior`
- `lane_34_cantonese_ability`
- `lane_35_topic_hygiene`
- `lane_37_deeplink_intent_detection`

Explicitly excluded from this document:
- `lane_36_custom`

## Global Build Rules (all lanes)
1. Use strict expert-atom construction in YAML.
2. Do not hardcode rendered full responses in seeds; keep rendered strings to near-zero.
3. Keep full output schema aligned with spec and golden examples.
4. Keep `count_target` fully satisfied per lane and per language slice.
5. Use B-first, A-second loop:
   - B-first: expand case/slot/atom/skeleton banks.
   - A-second: targeted line-level repair only after QC identifies residual outliers.
6. Prefer disjoint shell families over single canonical response skeletons.
7. Keep language-native writing per file; do not ship translation-clone contexts.
8. Enforce naturalness gates during generation, not only post-hoc.
9. Patch root causes (banks/skeletons), not random output lines.
10. Stop only on pass-with-margin, not threshold-edge pass.

## Recommended YAML Architecture
Use a stable atom stack pattern in each lane YAML:
- user-side atoms: intro/domain/issue/constraint/context/question (or lane-equivalent)
- assistant bridge atoms: context/limit/issue/question bridges
- action atoms: multistep procedural atoms with clause-order variation
- control atoms: scope/owner/metric/risk/fallback/goal/close (lane-relevant)
- structure atoms:
  - multiple `q_template` families
  - multiple `a_skeleton` families (minimum 12; target 18+ for high-volume lanes)
  - disjoint opener and closer banks
- quality atoms:
  - language purity filters
  - anti-artifact bans
  - anti-repetition constraints

## Hard Diversity Controls
Apply where generator supports:
- no top-N phrase reuse cap in a batch
- opener reuse ceiling
- style bucket mixing (direct, diagnostic, coach, policy-only, etc.)
- clause-order rotation requirement
- length shaping and anchor inclusion requirements

## Anti-Template Richness Guard (Global)
For each language slice in each lane, enforce these richness lever during build:
- opening-family diversity:
  - target >= 25 distinct openings per slice
  - opening measured by first ~10-12 word tokens of `user_message`
  - if a slice stays near floor (for example <35 distinct on 100-row smoke), add a second short opener slot (for example `opening_tag`) before `opening_family` to multiply combinations
- topic bucket rotation:
  - target >= 10 topic/case-shell buckets
  - cap each bucket at <= 15% slice share

Do not rely on templatey seed/context banks. Reused stock phrasing in seed/context banks drives overlap risk and poor perceived quality even when QC fatals are zero.

## Naturalness Controls
- reject semantically odd case combinations
- block placeholders/scaffolding artifacts
- block adjacent duplicate tokens
- block repeated content token/bigram patterns
- keep native punctuation and locale script consistency
- keep reasoning implicit and natural, not template-spam

## Lane-by-Lane Build Focus

### lane_01_identity
- Build dense identity boundaries with many scenario atoms.
- Separate persona consistency from tone politeness atoms.

### lane_02_tone_behaviour_foundation
- Build tone lattice atoms (formal, concise, warm, neutral, strict).
- Ensure tone choices remain orthogonal to task intent atoms.

### lane_03_think_mode
- Keep implicit multistep share above lane threshold.
- Maximize skeleton variation to avoid overlap collisions.

### lane_04_quick_mode
- Build concise-response families that remain semantically distinct.
- Use high-information anchors to prevent short-answer duplication.

### lane_05_conversation_mode
- Guarantee callback and multi-turn coverage by design.
- Use context-memory atoms with disjoint callback phrase banks.

### lane_06_general_intent_classification
- Separate intent families with clean atom boundaries.
- Avoid cross-intent lexical contamination in examples.

### lane_07_search_triggering
- Build clear trigger/non-trigger contrast atoms.
- Include ambiguous edge-cases with disjoint rationale phrasing.

### lane_08_search_integration
- Build integration flow atoms for cite/check/verify behavior.
- Keep search-required vs no-search outputs structurally separated.

### lane_09_multi_step_action_flow
- Expand process-stage atoms with non-overlapping step verbs.
- Enforce coherent dependency ordering in case assembly.

### lane_10_connector_intent_detection
- Build connector-intent maps with negative examples.
- Keep intent classes lexically distinct in training rows.

### lane_11_connector_action_mapping
- Separate detection vs execution mapping atoms.
- Add failure-path atoms for wrong connector input.

### lane_12_deeplink_action_mapping
- Build deeplink resolution banks by action domain.
- Add fallback atoms when deeplink context is incomplete.

### lane_13_doc_export_spec
- Build export format atoms with strict schema compliance.
- Add variant atoms for option/constraint combinations.

### lane_14_zip_wrap_spec
- Build packaging-stage atoms (assemble/validate/checksum/report).
- Keep command/report phrasing diversified per stage.

### lane_15_code_generation
- Separate task decomposition atoms from code emission atoms.
- Keep language/toolchain-specific banks disjoint.

### lane_16_code_json_spec_mode
- Enforce strict JSON-shape atoms and validation-safe outputs.
- Add malformed-input handling atoms.

### lane_17_comparison_tables
- Build table-intent atoms by comparison type and granularity.
- Keep axes/criteria/result phrasing varied.

### lane_18_chart_spec
- Build chart-type selection atoms and data-shape constraints.
- Separate explanation atoms from spec emission atoms.

### lane_19_continuity_decision
- Build decision policy atoms for when to continue or reset.
- Add conflict-resolution atoms for contradictory history.

### lane_20_continuity_execution
- Build execution atoms for applying continuity choices.
- Add safe-fallback atoms when context is partial.

### lane_21_rewrite
- Build rewrite intent banks by transformation goal.
- Keep source-preservation constraints explicit in atoms.

### lane_22_translate
- Build translation atoms per direction and register.
- Add script and locale integrity checks in generation loop.

### lane_23_grammar_fix
- Separate correction depth levels (light/normal/deep).
- Add preserve-meaning atoms and style-retention atoms.

### lane_24_history_search_trigger
- Build history-trigger classifiers with hard negatives.
- Distinguish memory lookup need vs immediate response cases.

### lane_25_history_search_integration
- Build retrieval-integration atoms with citation-safe phrasing.
- Keep memory merge logic explicit and varied.

### lane_26_image_context_understanding
- Build visual-context interpretation atoms by scene/task type.
- Add uncertainty atoms for low-confidence observations.

### lane_27_image_tooling
- Build tool-call decision atoms and non-tool alternatives.
- Separate when-to-view vs when-not-to-view patterns.

### lane_28_emote6_labeling
- Build emotion label atoms with balanced distributions.
- Add difficult borderline emotion cases.

### lane_29_safety_history_politics
- Build policy-safe handling atoms for historical/political prompts.
- Add neutrality and de-escalation phrase families.

### lane_30_safety_no_leakage
- Build anti-leakage refusal and safe-redirection atoms.
- Add disguised prompt-injection variants.

### lane_31_mode_selection
- Build decision atoms for mode routing with edge ambiguity.
- Keep mode criteria explicit but phrasing-diverse.

### lane_32_representation_choice
- Build representation routing atoms (plain/json/table/etc.).
- Add mismatch handling atoms for invalid representation requests.

### lane_33_fallback_behavior
- Build fallback families for uncertainty, missing context, and limits.
- Ensure fallback outputs remain useful and non-repetitive.

### lane_34_cantonese_ability
- Build native Cantonese atoms with locale-appropriate register.
- Enforce script and colloquiality checks; avoid translationese.

### lane_35_topic_hygiene
- Build topic-boundary atoms and safe-redirection transitions.
- Add scope-control phrases with high diversity.

### lane_37_deeplink_intent_detection
- Build deeplink intent detector atoms separate from execution.
- Add confusion pairs to harden intent disambiguation.

## Build + QC Operating Loop (recommended)
1. Build one language slice at a time.
2. Run smoke QC:
   - `./dino-ds qc lane_xx_<lang>`
3. Repair by bank/skeleton edits first.
4. Re-run smoke until fatal=0 with margin.
5. After all slices are stable, run full sweep:
   - `./dino-ds qc lane_xx`
6. Accept lane only if all slices in same RUN_UUID have fatal=0.

## Production Readiness Criteria
- All slices fatal-pass in one full-lane run.
- `count_target` fully met.
- No schema/invariant failures.
- Distribution checks pass (mode/tone/structure/tool/image where applicable).
- Remaining warnings are non-blocking and reviewed.

## Change Policy
When this recommendation conflicts with spec or validator behavior, follow spec + validator.

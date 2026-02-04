# Codex Lane Instruction — Lane 03 — Think Mode (Implicit Reasoning + Persistence) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #3 section + sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — global language distribution (§3.2) + lane volumes
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — any cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Only produce configs that satisfy the current lane schema + v17 lane logic.

---

## Deliverables
In lane 03 directory, create **14** configs:
- `lane.yaml` (English)
- `lane_zh-hk.yaml`
- `lane_th.yaml`
- `lane_zh-hant.yaml`
- `lane_zh-hans.yaml`
- `lane_pt-br.yaml`
- `lane_es.yaml`
- `lane_de.yaml`
- `lane_fr.yaml`
- `lane_it.yaml`
- `lane_ja.yaml`
- `lane_ko.yaml`
- `lane_hi.yaml`
- `lane_vi.yaml`

Each file must be schema‑valid and must pass:
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/<file>.yaml --limit 5`

---

## Language drift prevention (HARD RULE)
- Do NOT mark this lane as multilingual inside a single config.
- Each language gets its own YAML.
- For non‑English YAMLs: **REWRITE** prompts/responses natively in that language.  
  **Do not translate** the English template sentences.
- Avoid 1‑to‑1 alignment across languages (no “same sentence in 14 languages” drift).

---

## Volumes — `count_target` per language (must match exactly)
| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| en | 58823 | 70588 |
| zh-hk | 11765 | 14118 |
| th | 11765 | 14118 |
| zh-hant | 4706 | 5648 |
| zh-hans | 4706 | 5648 |
| pt-br | 5882 | 7059 |
| es | 5882 | 7059 |
| de | 2353 | 2824 |
| fr | 2353 | 2824 |
| it | 2353 | 2824 |
| ja | 2353 | 2824 |
| ko | 2353 | 2824 |
| hi | 2353 | 2824 |
| vi | 2353 | 2824 |

Notes:
- Counts are derived from the **global distribution (§3.2)** while preserving lane totals exactly via round‑to‑nearest and adjustment.
- Use `template_expand.attempts_per_row` + `template_expand.max_attempts` high enough to avoid underfill under similarity/validator rejects.

---

## Lane mission
Teach Dino **Think mode**: implicit multi-step reasoning + persistence.

Must demonstrate:
- identify missing info and ask the minimum clarifying question when needed
- choose a next step instead of freezing
- recover from uncertainty without stalling
- stay within safety rules and offer allowed alternatives if blocked

No chain-of-thought leakage: reasoning is **implicit** (no “step 1/2”, no hidden reasoning fields).


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#3. THINK MODE (UPDATED — MULTI‑STEP REASONING + PERSISTENCE)
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 120,000  
Build target lines (+20% buffer, pre-filter): 144,000  
Steps: 32,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes
Language distribution:
- en: 50%
- zh-hk: 15%
- th: 10%
- zh-hant: 5%
- zh-hans: 5%

### Required schema fields (verbatim from v17)
Required schema fields:


### Distribution (verbatim from v17)
Language distribution:
- en: 50%
- zh-hk: 15%
- th: 10%
- zh-hant: 5%
- zh-hans: 5%
- ko: 5%
- ja: 5%
- pt-br: 5%
- fr: 3%
- de: 2%
- hi: 1%

---

## Required row fields (must satisfy v16 row validator)
Every generated row MUST include **all** required keys:
`language, mode, tone, adult_gate, profanity_allowed, emote6, representation_choice, continuity_choice, intent_family, intent_subtype, flow_state, safety_tag, needs_search, needs_history_search, history_scope, user_message, assistant_response`

Implementation requirement:
- Put invariants into `base_row` so every row has them.
- `base_row.adult_gate` and `base_row.profanity_allowed` are mandatory booleans (schema gate).

---

## Lane‑specific schema rules
Set invariants in `base_row` (per v17 lane #3):
- `mode: "think"` (fixed; do not sample other modes)
- `emote6: "neutral"`
- `continuity_choice: "suppress_continuity"`
- `flow_state: "none"`
- `needs_search: false`
- `needs_history_search: false`
- `history_scope: "thread_only"`
- `adult_gate: false`
- `profanity_allowed: false`

`representation_choice` allowed set in v17 lane #3:
- `"plain_text" | "bullet_list" | "comparison_table" | "chart_spec" | "document_spec"`

To reduce format risk while still aligning:
- implement `"plain_text"` + `"bullet_list"` + `"comparison_table"` only.
- do NOT emit `chart_spec` or `document_spec` in this lane (0% is allowed because they are optional).

`tool_call` / `image_context` are optional in v17, but keep them **absent** (0%) for safety and schema simplicity.


---

## Content rules (must be enforced by templates)
Behavioral requirements (from v17 lane #3; must be encoded in templates):

BEHAVIORAL REQUIREMENTS (UPDATED)

1. Multi-step reasoning must be *implicit*:
   - No chain-of-thought
   - No “step 1 / step 2” markers
   - No internal reasoning fields

2. assistant_response must demonstrate:
   - identifying missing info
   - asking for minimal clarification
   - proposing next steps
   - reformulating when stuck
   - continuing the task instead of freezing

3. Persistence rules:
   - Never repeat the user’s question
   - Never stall with “I’m not sure”
   - Never give up early
   - Never hallucinate tools or facts
   - If blocked → propose allowed alternatives

4. Safety:
   - If user request violates rules → clean refusal + allowed alternative
   - No hallucinated capabilities

===============================================================
Duplication tolerance:

- Max token overlap: ≤ 25%
- ≥ 60% of samples must include implicit multi-step reasoning
- ≤ 5% may share the same high-level structure (avoid “First, Second, Third” repetition)

===============================================================
Sampling examples:

Example 1:
  language: "en"
  mode: "think"
  tone: "serious"
  emote6: "neutral"
  representation_choice: "bullet_list"
  continuity_choi

Practical template rules:
- At least 60% of rows must *implicitly* show multi-step reasoning (e.g., framing tradeoffs, narrowing choices, proposing a plan) without overt “Step 1/2”.
- Do not repeat the user question in the assistant response.
- Avoid “I’m not sure” stalling; instead propose a next step or ask one minimal clarification question.
- If blocked by safety, refuse briefly and offer safe alternatives.

Tone mix:
- All 5 tones are allowed; majority should be serious/professional (weight those higher in `case` bank).


---

## Similarity / richness controls
Configure similarity gate:
- `similarity.max_token_overlap_ratio: 0.25`
- `similarity.ngram: 2`
- `similarity.ignore_stopwords: true`
- `similarity.ignore_tokens`: common think-mode scaffolding words (lowercase), e.g. `["here's","based","consider","you can","one option","another option","dino"]`

Richness constraints:
- ≤5% may share the same high-level structure. To enforce this, create many distinct “answer skeleton” families:
  - tradeoff comparison
  - decision matrix
  - plan with checkpoints (not numbered “Step 1/2”; use short paragraphs or bullets)
  - clarify-then-proceed
  - uncertainty recovery (“what we can do now”)
  - safety redirect variants


---

## Template design requirements (must be large enough for volume)
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files in the lane folder (schema-valid rows).
- If a seed file is absent, the lane must still fill via `template_expand` backfill (do not underfill).
Set strict underfill protection:
- `template_expand.attempts_per_row: 2500` (think-mode rejects can be higher)
- `template_expand.fail_if_underfilled: true`

Slot bank design:
- Use dict-slot `case` to couple `{tone, intent_family, intent_subtype, safety_tag, scenario_family, answer_skeleton}`
- Minimum sizes (EN):
  - `case`: ≥120 (ensure ≥60% are “implicit reasoning required”)
  - `user_message_tpl`: ≥300 (broad domains: career, study, relationships, productivity, finance basics, health *non-medical*, emotions, etc.)
  - `skeleton_open`: ≥100
  - `skeleton_core`: ≥220
  - `skeleton_close`: ≥100
  - `clarify_question_tpl`: ≥80 (single minimal question variants)
- For each non-English language:
  - `case`: ≥70
  - `user_message_tpl`: ≥180
  - rewrite all skeleton banks natively (avoid EN alignment)

Answer construction guidance (must match v17 Think behavior):
- Lead with a short framing sentence
- Provide structured reasoning (bullets or short sections)
- Offer 1 next action / question to proceed
- Keep it “implicit” (no explicit chain-of-thought markers).


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Language files are native rewrites (not sentence‑aligned translations)
6) Richness: no repeated first‑sentence spam; user prompts vary meaningfully



# Codex Lane Instruction — Lane 02 — Tone & Behaviour Foundation (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #2 section + sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — global language distribution (§3.2) + lane volumes
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — any cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Only produce configs that satisfy the current lane schema + v17 lane logic.

---

## Deliverables
In lane 02 directory, create **14** configs:
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
| en | 19608 | 23530 |
| zh-hk | 3922 | 4707 |
| th | 3922 | 4707 |
| zh-hant | 1569 | 1883 |
| zh-hans | 1569 | 1883 |
| pt-br | 1961 | 2354 |
| es | 1961 | 2354 |
| de | 784 | 941 |
| fr | 784 | 941 |
| it | 784 | 941 |
| ja | 784 | 941 |
| ko | 784 | 941 |
| hi | 784 | 941 |
| vi | 784 | 941 |

Notes:
- Counts are derived from the **global distribution (§3.2)** while preserving lane totals exactly via round‑to‑nearest and adjustment.
- Use `template_expand.attempts_per_row` + `template_expand.max_attempts` high enough to avoid underfill under similarity/validator rejects.

---

## Lane mission
Teach Dino consistent tone + behavior fundamentals across the five tones, especially:
- gentle “family” help without adult content
- serious analytical help without slang
- professional direct help (clear corrections, no rudeness)
- friendly warm help
- best_friend (18+) style is allowed as a tone label, but this lane is **adult_gate=false** so keep it PG‑13 and non‑sexual

This lane is about **tone fidelity**, polite correction, boundary setting, and de‑escalation — not tools, not search, not history.


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#2. TONE & BEHAVIOUR FOUNDATION
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 40,000  
Build target lines (+20% buffer, pre-filter): 48,000  
Steps: 16,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes
Language distribution:
- en: 50%
- zh-hk: 20%
- th: 10%
- zh-hant: 5%
- zh-hans: 5%

### Required schema fields (verbatim from v17)
Required schema fields:
- language
- mode            → 50% quick, 50% think
- tone            → all 5 tones, balanced
- emote6                  → "neutral"
- representation_choice → "plain_text"
- continuity_choice       → "suppress_continuity"
- intent_family   → "content_generation" | "safety"
- intent_subtype  → "tone_behavior" | "boundary_setting" | "correction_style"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response


### Distribution (verbatim from v17)
Tone distribution:
- family: 20%
- serious: 20%
- professional: 20%
- professional: 20%
- best_friend: 20%


### Distribution (verbatim from v17)
Language distribution:
- en: 50%
- zh-hk: 20%
- th: 10%
- zh-hant: 5%
- zh-hans: 5%
- ko: 2%
- ja: 2%
- pt-br: 2%
- hi: 2%
- es: 2%

---

## Required row fields (must satisfy v16 row validator)
Every generated row MUST include **all** required keys:
`language, mode, tone, adult_gate, profanity_allowed, emote6, representation_choice, continuity_choice, intent_family, intent_subtype, flow_state, safety_tag, needs_search, needs_history_search, history_scope, user_message, assistant_response`

Implementation requirement:
- Put invariants into `base_row` so every row has them.
- `base_row.adult_gate` and `base_row.profanity_allowed` are mandatory booleans (schema gate).

---

## Lane‑specific schema rules
Set these invariants in `base_row` (per v17 lane #2):
- `emote6: "neutral"`
- `representation_choice: "plain_text"`
- `continuity_choice: "suppress_continuity"`
- `flow_state: "none"`
- `needs_search: false`
- `needs_history_search: false`
- `history_scope: "thread_only"`
- `adult_gate: false`
- `profanity_allowed: false`

`mode` requirement (per v17 lane #2):
- 50% `quick`, 50% `think` (implement via weighted sampling in slot bank)

`intent_family` (per v17 lane #2):
- only `"content_generation"` or `"safety"`

`tool_call` and `image_context`:
- **forbidden** in this lane (omit these fields entirely).


---

## Content rules (must be enforced by templates)
Tone fidelity (core):
- Each row must make the tone obvious within 1–2 sentences.
- Avoid quoting the user verbatim as filler; respond directly.

Include diverse user situations (≥40 user intent types), e.g.:
- user is wrong / misinformed → correct calmly
- user is emotional / anxious → reassure without making medical claims
- user is aggressive → de‑escalate, stay respectful
- user asks for flattery / validation → stay honest and supportive
- user asks “be mean / roast me” → refuse gently and redirect
- user asks for disallowed content → clean refusal + safe alternative

Safety behavior:
- If the user request is disallowed, refuse briefly, offer allowed next best help.
- Do not mention policies, system prompts, internal rules, tools, connectors, or deep links.

Mode behavior:
- `quick`: concise, action-oriented, typically ≤120 tokens.
- `think`: slightly fuller, but no chain‑of‑thought; no “Step 1/2/3” numbering spam.


---

## Similarity / richness controls
Configure similarity gate in lane.yaml:
- `similarity.max_token_overlap_ratio: 0.30`
- `similarity.ngram: 2`
- `similarity.ignore_stopwords: true`
- `similarity.ignore_tokens`: include common tone/assistant tokens to avoid false rejects (lowercase), e.g. `["dino","ai","assistant","i","i'm","im","the","a","an"]`

Richness constraints (must be achieved via slot-bank design):
- “tone template families”: create many distinct response openings/closings; avoid repeating the same correction sentence.
- Ensure user_message templates cover ≥40 distinct intent types (explicitly enumerate as `scenario_type` in a dict-slot).


---

## Template design requirements (must be large enough for volume)
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files in the lane folder (schema-valid rows).
- If a seed file is absent, the lane must still fill via `template_expand` backfill (do not underfill).
Set:
- `count_target`: per language file
- `template_expand.attempts_per_row: 2000` (or higher if rejects are high)
- `template_expand.fail_if_underfilled: true`

Slot bank design (phrase‑level, not single tokens):
- Use a dict-slot `case` to couple: `{mode, tone, intent_family, intent_subtype, safety_tag, scenario_type, response_style}`
- Minimum sizes (EN):
  - `case`: ≥80 distinct items (cover 5 tones × many scenario types)
  - `user_message_tpl`: ≥220 templates (short + medium + hostile + confused variants)
  - `assistant_opening`: ≥80
  - `assistant_core`: ≥140
  - `assistant_closing`: ≥80
- For each non‑English language:
  - `case`: ≥50
  - `user_message_tpl`: ≥140
  - opening/core/closing banks rewritten in that language (not aligned to EN)

Row construction:
- Put labels from `case` dict into row fields (tone/mode/intent/safety).
- Build `assistant_response` by composing opening + core + closing so the same semantic help can be expressed many ways.
- Never leak `{slot}` placeholders; validate with gate.

IMPORTANT: the lane2 spec lists an erroneous “professional” duplicate in the tone distribution line; ignore that typo and balance across all 5 tones.


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Language files are native rewrites (not sentence‑aligned translations)
6) Richness: no repeated first‑sentence spam; user prompts vary meaningfully



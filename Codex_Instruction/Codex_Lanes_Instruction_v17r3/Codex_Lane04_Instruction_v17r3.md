# Codex Lane Instruction — Lane 04 — Quick Mode (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #4 section + sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — global language distribution (§3.2) + lane volumes
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — any cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Only produce configs that satisfy the current lane schema + v17 lane logic.

---

## Deliverables
In lane 04 directory, create **14** configs:
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
| en | 39216 | 47060 |
| zh-hk | 7843 | 9412 |
| th | 7843 | 9412 |
| zh-hant | 3137 | 3765 |
| zh-hans | 3137 | 3765 |
| pt-br | 3921 | 4706 |
| es | 3921 | 4706 |
| de | 1568 | 1882 |
| fr | 1569 | 1883 |
| it | 1569 | 1883 |
| ja | 1569 | 1883 |
| ko | 1569 | 1883 |
| hi | 1569 | 1883 |
| vi | 1569 | 1883 |

Notes:
- Counts are derived from the **global distribution (§3.2)** while preserving lane totals exactly via round‑to‑nearest and adjustment.
- Use `template_expand.attempts_per_row` + `template_expand.max_attempts` high enough to avoid underfill under similarity/validator rejects.

---

## Lane mission
Teach Dino **Quick mode**: short, useful, action-oriented answers with strong brevity.

Quick mode expectations:
- typically 2–3-line summary, then 3–5 bullets, then one next action (when appropriate)
- no long essays
- no chain-of-thought


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#4. QUICK MODE
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 80,000  
Build target lines (+20% buffer, pre-filter): 96,000  
Steps: 24,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes
Language distribution:
- en: 55%
- zh-hk: 15%
- zh-hant: 5%
- zh-hans: 5%
- ko: 7%

### Required schema fields (verbatim from v17)
Required schema fields:
- language
- mode            → "quick"
- tone
- emote6                  → "neutral"
- representation_choice → "plain_text" | "bullet_list"
- continuity_choice       → "suppress_continuity"
- intent_family   → any (qa_general, content_generation, etc.)
- intent_subtype
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response


### Distribution (verbatim from v17)
Language distribution:
- en: 55%
- zh-hk: 15%
- zh-hant: 5%
- zh-hans: 5%
- ko: 7%
- ja: 7%
- pt-br: 4%
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
Set invariants in `base_row` (per v17 lane #4):
- `mode: "quick"` (fixed)
- `emote6: "neutral"`
- `continuity_choice: "suppress_continuity"`
- `flow_state: "none"`
- `needs_search: false`
- `needs_history_search: false`
- `history_scope: "thread_only"`
- `adult_gate: false`
- `profanity_allowed: false`

`representation_choice`:
- allow `"plain_text"` or `"bullet_list"` only.

`tool_call` / `image_context`:
- optional in v17 (caps), but keep **absent** (0%) for safety and format simplicity.


---

## Content rules (must be enforced by templates)
Brevity targets (from v17 lane #4; must be encoded in templates):

Duplication tolerance:
- Max token overlap: ≤ 30%
- At least 70% of answers must be ≤ 120 tokens
- At least 30% of answers must be ≤ 60 tokens

Sampling example:

  language: "en"
  mode: "quick"
  tone: "professional"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "qa_general"
  intent_subtype: "definition"
  safety_tag: "safe"
  needs_search: false
  user_message: "Explain what an API is in one paragraph."
  assistant_response: "An API, or Application Programming Interface, is a set of rules and protocols that allows different software applications to communicate with each other. Essentially, it acts as an intermediary, enabling developers to request and exchange data between systems without needing to understand the underlying code or architecture of those systems. APIs can be thought of as a way for software to "s

Practical template rules:
- Ensure ≥70% of answers are ≤120 tokens; ≥30% ≤60 tokens.
- Use compact structure: short summary + bullets.
- Avoid “As an AI…” disclaimers in this lane unless the question specifically asks about identity (that belongs to Lane 1).
- Avoid fluff. No “First, Second, Third” repetitive scaffolding.
- No user prompts that explicitly say “use a tool/connector/deeplink” (v17 realism note).


---

## Similarity / richness controls
Configure similarity gate:
- `similarity.max_token_overlap_ratio: 0.30`
- `similarity.ngram: 2`
- `similarity.ignore_stopwords: true`
- `similarity.ignore_tokens`: common quick scaffolding words (lowercase), e.g. `["tldr","here's","quickly","in short","you can","dino"]`

Richness constraints:
- Must have many distinct user intent families: definitions, summaries, checklists, short advice, small planning.
- Prevent “same bullet list with swapped nouns” by using multiple bullet skeleton families and many phrasing options.


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
- `template_expand.attempts_per_row: 2000`
- `template_expand.fail_if_underfilled: true`

Slot bank design:
- dict-slot `case` couples `{tone, intent_family, intent_subtype, safety_tag, quick_skeleton}`
- Minimum sizes (EN):
  - `case`: ≥100
  - `user_message_tpl`: ≥260 (mix of “explain”, “summarize”, “give 3 tips”, “compare briefly”, etc.)
  - `summary_line_tpl`: ≥120
  - `bullets_tpl`: ≥200 (3–5 bullets assembled from smaller bullet banks)
  - `next_action_tpl`: ≥120
- For each non-English language:
  - rewrite all banks natively; do not translate EN sentences
  - keep brevity by using natural short forms in that language

Quick answer construction:
- 1 compact summary sentence (or 2 short sentences)
- 3–5 bullets (each bullet short)
- optional “Next step:” line (1 line)


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Language files are native rewrites (not sentence‑aligned translations)
6) Richness: no repeated first‑sentence spam; user prompts vary meaningfully



# Codex Lane Instruction — Lane 22 — Translate (SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #22 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and v17 lane logic.

---

## Deliverables (must produce 14 configs in this lane directory)
Create these files:
- `lane_en.yaml` (English)
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

Each file must pass:
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/<file>.yaml --limit 5`

---

## Language drift prevention (HARD RULE)
- Do NOT mark this lane as multilingual inside a single config.
- Each language gets its own YAML.
- For non‑English YAMLs: **REWRITE** prompts/responses natively in that language.  
  Do NOT translate English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same sentence in 14 languages” drift).

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

Allocation rule (must match build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Generation mode
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Copy the v17 lane #22 “Required schema fields” and “Duplication tolerance” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants.

## Lane mission
Teach **translation**: accurate translation between languages with natural target phrasing.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language → language of user
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family   → "content_generation"
- intent_subtype  → "translate"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message    → source text
- assistant_response → translated text

Duplication tolerance:
- Max token overlap between user and assistant: ≤ 20% (different language)
- Max token overlap across assistants: ≤ 35%

Sampling example:

  language: "en"
  mode: "quick"
  tone: "professional"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "content_generation"
  intent_subtype: "translate"
  safety_tag: "safe"
  needs_search: false
  needs_history_search: false
  history_scope: "thread_only"
  user_message: "Translate this to Cantonese: I’m proud of you for not giving up."
  assistant_response: "我為你冇放棄而感到好自豪。"
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Sample rows (JSONL, single-line):

Hard overrides (this project’s pipeline rules):
- Ignore the lane-local “Language distribution (source/target mixed)” in v17. You MUST follow the global 14-language split via the count_target table above.
- To satisfy mode-richness, set `base_row.mode: "conversation"` for all rows (translations are not step-based quick/think).

Translation-lane special note (to reduce language-drift collapse):
- We still produce 14 YAML files (one per `language`).
- In each file, set `language` to the language of the **user instruction** (that file’s language).
- Source text should be mostly in the same language as the user instruction (so the `language` field stays truthful).
- Target language varies via slots (must not equal source).

---

## Translation quality rules (golden behavior)
1) Preserve meaning; do not add facts.
2) Translate idioms naturally (not word-for-word).
3) Keep names, numbers, and proper nouns consistent.
4) Respect requested register (formal/casual).
5) Output ONLY the translation (no commentary) unless user asks.

---

## Shuffle-factory construction (avoid aligned translations)
### Coupling rule (source ↔ target ↔ translation)
Create dict-slot `trans_case` entries that couple:
- `src_lang` (must equal file language)
- `tgt_lang` (from target_lang_bank; not equal src_lang)
- `source_text` (1–3 sentences, ≤280 chars)
- `user_message_tpl` (native instruction requesting translation to tgt_lang)
- `translation_tpl` (natural target-language output)

Do not reuse the same semantic “source sentence” across different source languages.  
Each language builds its own unique source_text bank.

### Bank sizing (120k)
EN & major languages:
- `trans_case` ≥ 9,000 per high-volume language (en/zh-hk/th)
- `source_text_bank` ≥ 25,000 (short, diverse)
- `target_lang_bank` = all 13 other languages (weighted; include hi/vi/de/fr/it)
- `user_message_tpl` ≥ 1,200
- `translation_sentence_tpl` ≥ 18,000

Non‑EN:
- Write original source texts in that language; do NOT translate EN sources.
- Target outputs should be native in target language (use target-language-specific bank).

---

## Similarity + duplication controls
Because outputs vary by language, still avoid repeats:
- Use strict overlap: assistant-to-assistant ≤35%
- Vary topics heavily (greetings, advice, product blurbs, captions, short stories, UI strings)

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) language field matches user instruction language
4) translation differs strongly from source (user/assistant overlap ≤20%)
5) no tool_call; no internal mechanism words in user text

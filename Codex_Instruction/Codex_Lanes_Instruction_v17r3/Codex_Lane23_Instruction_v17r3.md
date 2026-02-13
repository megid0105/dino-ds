# Codex Lane Instruction — Lane 23 — Grammar Fix (LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #23 section + CT sample row logic (authoritative)
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

Allocation rule (must match build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Generation mode
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Copy the v17 lane #23 “Required schema fields” and “Duplication tolerance” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants.

## Lane mission
Teach **grammar fix**: minimal corrections, same meaning, same language.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family   → "content_generation"
- intent_subtype  → "grammar_fix"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message    → original text with errors
- assistant_response → corrected text

Duplication tolerance:
- Max token overlap between user and assistant: ≤ 80% (only grammar changes)
- Max token overlap across assistants: ≤ 35%

Sampling example:

  language: "en"
  mode: "quick"
  tone: "serious"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "content_generation"
  intent_subtype: "grammar_fix"
  safety_tag: "safe"
  needs_search: false
  needs_history_search: false
  history_scope: "thread_only"
  user_message: "I has been waiting for you since two hours."
  assistant_response: "I have been waiting for you for two hours."
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Sample rows (JSONL, single-line):

Hard overrides (this project’s pipeline rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.
- To satisfy mode-richness, set `base_row.mode: "conversation"` for all rows (grammar fixes are not step-based quick/think).

---

## Grammar-fix quality rules (golden behavior)
1) Preserve meaning; only fix grammar, spelling, punctuation, agreement.
2) Keep the same language.
3) Keep wording as close as possible; small edits only.
4) Output ONLY the corrected text (no explanation) unless user asks.

---

## Shuffle-factory construction (minimal edit discipline)
### Coupling rule (error pattern ↔ correction)
Create dict-slot `gf_case` entries that couple:
- `error_pattern` (tense, agreement, word order, punctuation, wrong preposition, homophone, etc.)
- `noisy_text` (original with that error)
- `correct_text` (minimal corrected version)
- `user_message_tpl` (native request: “fix grammar / proofread”)
This prevents accidental rewriting beyond grammar.

### Bank sizing (40k)
EN minimum:
- `gf_case` ≥ 4,000
- `noisy_text_bank` ≥ 15,000 (short, 1–2 sentences)
- `error_pattern_bank` ≥ 180
- `user_message_tpl` ≥ 700
- `correction_delta_bank` ≥ 8,000 (small correction fragments)

Non‑EN:
- Build separate noisy/correct pairs per language.
- Include language-specific error patterns (zh punctuation, Japanese particles, etc.).
- Do NOT translate EN noisy texts.

---

## Similarity + duplication controls
This lane naturally has high overlap. Respect v17 caps:
- user/assistant overlap ≤80% (should be high but not identical)
- assistant-to-assistant overlap ≤35%
Use many different error patterns and topics to keep uniqueness.

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) corrected text is minimal edit (overlap high but not identical)
4) same language as `language`
5) no tool_call; no internal mechanism words in user text

# Codex Lane Instruction — Lane 32 — Representation Choice (LoRA Detection + Rendering) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #32 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables (14 per-language configs in this lane directory)
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
| en | 14706 | 17648 |
| zh-hk | 2941 | 3530 |
| th | 2941 | 3530 |
| zh-hant | 1177 | 1413 |
| zh-hans | 1177 | 1413 |
| pt-br | 1471 | 1766 |
| es | 1471 | 1766 |
| de | 588 | 706 |
| fr | 588 | 706 |
| it | 588 | 706 |
| ja | 588 | 706 |
| ko | 588 | 706 |
| hi | 588 | 706 |
| vi | 588 | 706 |

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
1) Copy the v17 lane #32 “Required schema fields / Constraints / Sampling example”.
2) If any bullet conflicts with CT sample rows, treat the CT sample rows as authoritative (they are approved instances).
3) Cross-check key names + enum values in MASTER; do not invent/rename keys.

## Lane mission (representation mapping + correct rendering)
Pick the correct `representation_choice` AND render the response strictly in that representation.

This is a mapping lane:
- `representation_choice` is supervised.
- `assistant_response` must **match** the chosen representation (no meta).

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice    → REQUIRED
- continuity_choice       → "suppress_continuity"
- intent_family
- intent_subtype
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

Assistant response rule (anti-leakage):
- assistant_response must be strictly user-facing. Never mention internal routing, tools, connectors, deeplinks, schema fields, or labels.

Constraints:
- assistant_response must be in the target representation (no meta)
- tool_call: forbidden

Authoritative enum sets from CT sample rows (use EXACTLY these values unless v17 explicitly lists more):
- `mode`: ['quick']  (CT samples show quick only)
- `tone`: ['serious']
- `emote6`: "neutral"
- `representation_choice`: ['bullet_list', 'comparison_table']
- `intent_family`: ['decision_support', 'planning']
- `intent_subtype`: ['option_comparison', 'task_breakdown']
- `safety_tag`: ['safe']

Hard override (this pipeline’s rules):
- Ignore the lane-local language distribution in v17. You MUST use the global 14-language split + count_target table above.

---

## IMPORTANT: do NOT enable mode_richness for this lane
CT sample rows for this lane use:
- dash bullets (`- ...`) for `bullet_list`
- markdown pipe tables for `comparison_table`
These do NOT include numbered `1.` step lines.
If you set `mode_richness` in lane_en.yaml, build will enforce numbered steps for `mode: quick` and may reject CT-style outputs.
Therefore: **omit `mode_richness` entirely** in this lane’s YAMLs.

---

## Golden mapping logic (how to choose representation_choice)
Choose `comparison_table` when:
- user asks to compare options, pros/cons, side-by-side evaluation, “renting vs buying”, “A vs B”, “which is better”

Choose `bullet_list` when:
- user asks for a plan, checklist, routine, steps breakdown, task decomposition, “help me plan…”, “break this down”

Hard rule:
- Don’t output a table unless the ask is truly comparative.
- Don’t output bullets if the ask demands a structured comparison.

---

## Rendering rules (must match representation exactly)
### For `bullet_list`
- Use markdown bullet list only.
- No paragraph intro longer than 1 line.
- 3–7 bullets; each bullet 1 short line.

### For `comparison_table`
- Use markdown table with header row and separator row.
- 3–7 rows.
- Keep cells short; no extra text outside the table (or ≤1 short lead-in line).

Anti-leakage (hard):
- Never say “I chose bullet_list/table”.
- Never mention schema/labels/tools/routing.

---

## Shuffle-factory construction (to guarantee “golden rows”)
### Coupling rule (ask ↔ representation_choice ↔ rendering)
Create dict-slot `rep_case` entries that couple:
- `representation_choice` (bullet_list | comparison_table)
- `intent_family` + `intent_subtype` (use the CT sample pairings)
- `user_message_tpl` (must strongly imply one representation)
- `assistant_response_tpl` rendered in the correct representation
- fixed: mode="quick", tone="serious", emote6="neutral", continuity_choice="suppress_continuity", needs_search=false, needs_history_search=false, history_scope="thread_only"

Do NOT sample representation_choice independently.

### Bank sizing guidance (30k without near-dups)
EN minimum:
- `rep_case` ≥ 3,500
- `plan_prompt_bank` ≥ 8,000
- `compare_prompt_bank` ≥ 8,000
- `bullet_list_tpl` ≥ 2,000
- `comparison_table_tpl` ≥ 2,000
- `topic_bank` ≥ 4,000 (study/work/health/money/fitness/home/tech)

Non‑EN:
- Build native prompts + native bullets/tables per language (do not translate EN).
- Avoid aligned topics across languages by using separate topic banks per language.

---

## Similarity / duplication
- Max token overlap: ≤35%
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response strictly matches representation_choice (bullets vs table)
4) no tool_call; no internal mechanism words; never mention representation_choice
5) language rewrites are native (not aligned translations)

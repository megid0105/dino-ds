# Codex Lane Instruction — Lane 17 — Tables / Comparison Output (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #17 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values for representation_choice and intent enums
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 language distribution
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

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
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Open v17 lane #17 section and copy its hard constraints + required fields.
2) Cross-check key names and allowed values in MASTER; do not invent/rename keys.
3) Implement those constraints verbatim as `base_row` + strict template rules.

## Lane mission
Teach **table-first reasoning**: produce compact, correct comparison tables / structured tabular outputs that match CT sample rows.

This lane is about:
- correct row/column semantics
- stable table structure
- no rambling prose

---

## Exact v17 contract snapshot (copy from v17 lane 17; do not weaken)
Use these as the authoritative lane-17 constraints:
17. COMPARISON TABLES (TABLE-ONLY)
Model: Dino 4B, Dino Pro 7B
- Output **only** a clean markdown comparison table (no prose before/after).
- Stable headers and row labels; no hallucinated extra fields.
- `assistant_response` MUST be a markdown table only.
- No prose, no bullets, no footnotes, no JSON, no code, no tool_call.
- Include a small canonical set of table shapes for generalization:
(Training should vary content domains, not invent unlimited table dimensions.)
Required schema fields (per-sample):
- mode                    → "quick" | "think" | "conversation"
- representation_choice   → "comparison_table"
- intent_family
- intent_subtype
- needs_search            → false
- assistant_response      → markdown table only
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]
Sample rows (JSONL, single-line):
```jsonl
{"language":"en","mode":"quick","tone":"professional","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Compare two laptops on battery life, weight, and price.","assistant_response":"| Item | Battery life | Weight | Price |\n|---|---:|---:|---:|\n| Laptop A | TBD | TBD | TBD |\n| Laptop B | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call."},{"role":"user","content":"Compare two laptops on battery life, weight, and price."},{"role":"assistant","content":"| Item | Battery life | Weight | Price |\n|---|---:|---:|---:|\n| Laptop A | TBD | TBD | TBD |\n| Laptop B | TBD | TBD | TBD |"}]}
{"language":"en","mode":"think","tone":"professional","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Compare three project options across cost, timeline, risk, and impact.","assistant_response":"| Option | Cost | Timeline | Risk | Impact |\n|---|---:|---:|---:|---:|\n| Option 1 | TBD | TBD | TBD | TBD |\n| Option 2 | TBD | TBD | TBD | TBD |\n| Option 3 | TBD | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call."},{"role":"user","content":"Compare three project options across cost, timeline, risk, and impact."},{"role":"assistant","content":"| Option | Cost | Timeline | Risk | Impact |\n|---|---:|---:|---:|---:|\n| Option 1 | TBD | TBD | TBD | TBD |\n| Option 2 | TBD | TBD | TBD | TBD |\n| Option 3 | TBD | TBD | TBD | TBD |"}]}
{"language":"en","mode":"conversation","tone":"friendly","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Make a 4x3 table comparing four restaurants on vibe, price, and best for.","assistant_response":"| Restaurant | Vibe | Price | Best for |\n|---|---|---|---|\n| A | TBD | TBD | TBD |\n| B | TBD | TBD | TBD |\n| C | TBD | TBD | TBD |\n| D | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call."},{"role":"user","content":"Make a 4x3 table comparing four restaurants on vibe, price, and best for."},{"role":"assistant","content":"| Restaurant | Vibe | Price | Best for |\n|---|---|---|---|\n| A | TBD | TBD | TBD |\n| B | TBD | TBD | TBD |\n| C | TBD | TBD | TBD |\n| D | TBD | TBD | TBD |"}]}
{"language":"en","mode":"quick","tone":"professional","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Update the table: add a new column for 'Maintenance'.","assistant_response":"| Item | Battery life | Weight | Price | Maintenance |\n|---|---:|---:|---:|---|\n| Laptop A | TBD | TBD | TBD | TBD |\n| Laptop B | TBD | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call.\nCONTEXT (previous turns):\nUser: Compare two laptops on battery life, weight, and price.\nAssistant: (table only)\nUser: Add maintenance."},{"role":"user","content":"Update the table: add a new column for 'Maintenance'."},{"role":"assistant","content":"| Item | Battery life | Weight | Price | Maintenance |\n|---|---:|---:|---:|---|\n| Laptop A | TBD | TBD | TBD | TBD |\n| Laptop B | TBD | TBD | TBD | TBD |"}]}
{"language":"en","mode":"think","tone":"professional","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Replace 'Risk' with 'Complexity' and keep the rest the same.","assistant_response":"| Option | Cost | Timeline | Complexity | Impact |\n|---|---:|---:|---:|---:|\n| Option 1 | TBD | TBD | TBD | TBD |\n| Option 2 | TBD | TBD | TBD | TBD |\n| Option 3 | TBD | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call.\nCONTEXT (previous turns):\nUser: Compare three project options across cost, timeline, risk, and impact.\nAssistant: (table only)\nUser: Use Complexity instead of Risk."},{"role":"user","content":"Replace 'Risk' with 'Complexity' and keep the rest the same."},{"role":"assistant","content":"| Option | Cost | Timeline | Complexity | Impact |\n|---|---:|---:|---:|---:|\n| Option 1 | TBD | TBD | TBD | TBD |\n| Option 2 | TBD | TBD | TBD | TBD |\n| Option 3 | TBD | TBD | TBD | TBD |"}]}
{"language":"en","mode":"conversation","tone":"friendly","emote6":"neutral","representation_choice":"comparison_table","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"comparison_table","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Same table, but swap column order to: Price, Best for, Vibe.","assistant_response":"| Restaurant | Price | Best for | Vibe |\n|---|---|---|---|\n| A | TBD | TBD | TBD |\n| B | TBD | TBD | TBD |\n| C | TBD | TBD | TBD |\n| D | TBD | TBD | TBD |","messages":[{"role":"system","content":"You are Dino. Output ONLY a markdown table. No prose before or after. No bullets, no footnotes, no code, no JSON, no tool_call.\nCONTEXT (previous turns):\nUser: Make a 4x3 table comparing four restaurants on vibe, price, and best for.\nAssistant: (table only)\nUser: Reorder the columns."},{"role":"user","content":"Same table, but swap column order to: Price, Best for, Vibe."},{"role":"assistant","content":"| Restaurant | Price | Best for | Vibe |\n|---|---|---|---|\n| A | TBD | TBD | TBD |\n| B | TBD | TBD | TBD |\n| C | TBD | TBD | TBD |\n| D | TBD | TBD | TBD |"}]}

Hard override (language control):
- Even if v17 says “multilingual”, you MUST still generate 14 per-language YAMLs (REWRITE not translate) and follow the count_target table above.

---

## Golden-row construction via shuffle factory (table discipline)
### Coupling rule (question ↔ table schema)
Create dict-slot `table_case` entries that couple:
- `table_type` (comparison | pros_cons | pricing | schedule | feature_matrix | etc.)
- `columns` (ordered list)
- `row_generator` (how to populate rows from slots)
- `user_message_tpl` (asks specifically for that table)
- `answer_table_tpl` (a single markdown table skeleton OR the v17-required table format)
This coupling prevents “wrong columns for the question”.

### Uniqueness at volume
Uniqueness must come from:
- distinct table_type + distinct columns
- distinct domain topics + entities
- varied numeric parameters (dates, costs, sizes) where appropriate

EN minimum bank sizing guidance (scale per non-EN):
- `table_case` ≥ 2,500
- `user_message_tpl` ≥ 1,200
- `column_set_bank` ≥ 900
- `row_fact_bank` ≥ 8,000
- `domain_bank` ≥ 2,000

Non‑EN:
- Rewrite prompts and table captions/headers natively.
- Do NOT reuse the same entity sets as EN across languages.

---

## Similarity / richness controls
- Since tables can look similar, keep strict overlap: `similarity.max_token_overlap_ratio ≤ 0.25`.
- Do NOT ignore table header tokens; you need them for uniqueness.

Underfill protection:
- high attempts_per_row (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) output table format matches v17 lane-17 sample rows
4) no tool_call unless v17 explicitly requires it
5) language rewrites are native (not aligned translations)

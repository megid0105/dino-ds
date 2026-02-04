# Codex Lane Instruction — Lane 11 — Connector Action Mapping (v17, mapping-only LoRA)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #11 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums (especially `connector_action` allowed values)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — LoRA lane ratio + any cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables (must produce 14 configs in this lane directory)
Create these files:
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

Each file must pass:
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/<file>.yaml --limit 5`

---

## Language drift prevention (HARD RULE)
- Do NOT mark this lane as multilingual inside a single config.
- Each language gets its own YAML.
- For non‑English YAMLs: **REWRITE** prompts natively in that language.  
  **Do not translate** English templates sentence-for-sentence.
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

## Lane mission (mapping-only classifier)
This lane teaches Dino to map a connector-required user request to **exactly one** `connector_action` label.

This lane does NOT execute actions.
This lane does NOT draft content.
It outputs ONLY the label field.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
From v17 lane #11 (hard requirements):

### Required fields (100%)
- `language`
- `mode`
- `tone`
- `emote6` → `"neutral"`
- `representation_choice`
- `continuity_choice` → `"suppress_continuity"`
- `intent_family`
- `intent_subtype`
- `safety_tag`
- `needs_search` → `false`
- `needs_history_search` → `false`
- `history_scope` → `"thread_only"`
- `user_message`
- `assistant_response` → MUST be `""` (empty) or a single space
- `connector_action` → REQUIRED (one of the canonical allowed labels; exact string)
- `messages` → REQUIRED Qwen ingest list: 
  `[{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]`
  where assistant content MUST be `""` or `" "`.

### Forbidden (hard)
- `tool_call` (MUST NOT appear)
- `parameters/slots` (MUST NOT appear anywhere in any output; no `{var}`, no placeholders)
- any natural-language `assistant_response` (MUST NOT appear)

### Constraints
- Output ONLY the label field (`connector_action`).
- No connector selection text, no metadata, no explanations, no drafts, no URLs.

### Data realism note (mandatory)
`user_message` must never mention internal mechanisms (“use a tool”, “deeplink”, “connector”, “schema”, etc.).  
Users ask for outcomes.

---

## Critical implementation detail (so the build gate passes)
`build_cmd.py` has a mode-richness gate:
- `quick` and `think` require non-empty assistant responses with “step lines”.
- This lane requires **empty assistant_response**, so you MUST set:
  - `base_row.mode: "conversation"` for all rows
This satisfies the validator and avoids false rejects while preserving the mapping goal.

Also fix these invariants in `base_row`:
- `assistant_response: ""`
- `emote6: "neutral"`
- `representation_choice: "plain_text"`
- `continuity_choice: "suppress_continuity"`
- `needs_search: false`
- `needs_history_search: false`
- `history_scope: "thread_only"`

---

## Generation mode (LoRA ratio)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- Keep real slice small and diverse; do not overfit to a few sources.
- If a seed file is absent, the lane must still fill via template backfill (do not underfill).

---

## How to guarantee “golden mapping rows” via shuffle factory
### 1) Build a canonical label catalog (no guessing)
From `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md`, extract the full allowed enum list for `connector_action`.

Then create a dict-slot bank `action_catalog` where **each entry couples**:
- `connector_action` (exact enum string)
- `intent_family` (exact enum)
- `intent_subtype` (exact enum)
- `scenario_family` (short tag)
- `slots` (a dict of concrete values: names, dates, times, places, subjects, message text, etc.)
- `user_message_tpl` (one or more templates for that action)
- `system_message` (constant “You are a helpful assistant.”)
- `safety_tag` (usually `"safe"`)

This coupling is the core of “golden” rows: the label and the user_message must never drift apart.

### 2) Force template completeness (no placeholders)
- Fill templates with concrete values from `slots` (no `{name}` left unresolved).
- Include a *large* `names_bank`, `places_bank`, `time_expr_bank`, `subject_bank`, `task_detail_bank` per language.

### 3) Build `messages` mechanically
Row template must set:
- `messages[0].role = "system"`, content = system_message
- `messages[1].role = "user"`, content = user_message
- `messages[2].role = "assistant"`, content = ""  (must stay empty)

### 4) Similarity + richness settings
Similarity compares `user_message + assistant_response`. Since assistant is empty, uniqueness must come from user_message.
Configure:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.25` (strict; you need uniqueness at 30k)
- `similarity.ignore_stopwords: true`
- Keep ignore_tokens minimal (do NOT ignore names/times; you need those to create uniqueness)

### 5) Bank sizing guidance (to reach 30k without “similar lines”)
For EN (scale down per non-EN but keep large):
- `action_catalog` ≥ 800 entries (spread across many action labels; avoid over-weighting top few)
- `names_bank` ≥ 600
- `places_bank` ≥ 500
- `time_expr_bank` ≥ 700
- `task_detail_bank` ≥ 1,200
- `user_message_style_bank` ≥ 200 (imperative, polite, casual, terse, context-first, etc.)
- Per action label: ≥ 12 distinct user_message templates

Non‑EN hard rule:
- Rewrite the templates natively.
- Use language-specific natural forms (zh-hk particles; Japanese politeness; etc.).
- Do not reuse English slot values wholesale (e.g., don’t keep “Alex/Friday 3pm” everywhere).

---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) Every row has `connector_action` and it is a canonical enum string
4) `assistant_response` is always `""` (or `" "`), never natural language
5) No `tool_call`, no placeholders, no URLs/metadata
6) `messages` list exists and assistant message content is empty

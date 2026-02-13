# Codex Lane Instruction — Lane 18 — Chart Spec Output (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #18 section + CT sample row logic
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
1) Open v17 lane #18 section and copy its hard constraints + required fields.
2) Cross-check key names and allowed values in MASTER; do not invent/rename keys.
3) Implement those constraints verbatim as `base_row` + strict template rules.

## Lane mission
Teach deterministic **chart_spec output**: produce strict chart specifications (not prose), matching CT sample rows exactly.

This lane is about:
- machine-readable chart spec
- correct fields and ordering
- stable semantics

---

## Exact v17 contract snapshot (copy from v17 lane 18; do not weaken)
Use these as the authoritative lane-18 constraints:
18. CHART SPEC (DETERMINISTIC CHART_SPEC)
Model: Dino 4B, Dino Pro 7B
- Emit a deterministic `chart_spec` structure for downstream rendering.
- This lane teaches **structured chart description**, not analysis prose.
- `assistant_response` MUST contain only `chart_spec` (YAML-like), no prose before/after.
- No tool_call, no JSON spec mode, no tables.
chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes
Required schema fields (per-sample):
- mode                    → "quick" | "think" | "conversation"
- representation_choice   → "chart_spec"
- needs_search            → false
- assistant_response      → chart_spec only
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]
Sample rows (JSONL, single-line):
```jsonl
{"language":"en","mode":"quick","tone":"professional","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Create a bar chart spec for monthly sales for the last 6 months (use placeholder numbers).","assistant_response":"chart_spec:\n  type: bar\n  title: Monthly Sales (Last 6 Months)\n  goal: Show month-over-month change\n  x_axis:\n    label: Month\n    categories: [M1, M2, M3, M4, M5, M6]\n  y_axis:\n    label: Sales\n  series:\n    - name: Sales\n      values: [100, 120, 90, 140, 130, 150]\n  style:\n    emphasis: annotate peak\n  notes: Placeholder values; replace with real sales data.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec."},{"role":"user","content":"Create a bar chart spec for monthly sales for the last 6 months (use placeholder numbers)."},{"role":"assistant","content":"chart_spec:\n  type: bar\n  title: Monthly Sales (Last 6 Months)\n  goal: Show month-over-month change\n  x_axis:\n    label: Month\n    categories: [M1, M2, M3, M4, M5, M6]\n  y_axis:\n    label: Sales\n  series:\n    - name: Sales\n      values: [100, 120, 90, 140, 130, 150]\n  style:\n    emphasis: annotate peak\n  notes: Placeholder values; replace with real sales data."}]}
{"language":"en","mode":"think","tone":"professional","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Make a line chart spec for weekly active users over 8 weeks (synthetic numbers).","assistant_response":"chart_spec:\n  type: line\n  title: Weekly Active Users (8 Weeks)\n  goal: Visualize trend and inflection points\n  x_axis:\n    label: Week\n    categories: [W1, W2, W3, W4, W5, W6, W7, W8]\n  y_axis:\n    label: Active users\n  series:\n    - name: WAU\n      values: [1000, 1050, 980, 1100, 1200, 1180, 1250, 1300]\n  style:\n    emphasis: mark inflection\n  notes: Synthetic placeholders; replace with measured WAU.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec."},{"role":"user","content":"Make a line chart spec for weekly active users over 8 weeks (synthetic numbers)."},{"role":"assistant","content":"chart_spec:\n  type: line\n  title: Weekly Active Users (8 Weeks)\n  goal: Visualize trend and inflection points\n  x_axis:\n    label: Week\n    categories: [W1, W2, W3, W4, W5, W6, W7, W8]\n  y_axis:\n    label: Active users\n  series:\n    - name: WAU\n      values: [1000, 1050, 980, 1100, 1200, 1180, 1250, 1300]\n  style:\n    emphasis: mark inflection\n  notes: Synthetic placeholders; replace with measured WAU."}]}
{"language":"en","mode":"conversation","tone":"friendly","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"suppress_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Create a donut chart spec showing budget allocation (placeholder percentages).","assistant_response":"chart_spec:\n  type: donut\n  title: Budget Allocation\n  goal: Show proportional split at a glance\n  legend:\n    title: Category\n  series:\n    - name: Allocation\n      labels: [Rent, Food, Savings, Other]\n      values: [50, 20, 20, 10]\n  style:\n    emphasis: highlight largest slice\n  notes: Placeholder percentages; replace with your real numbers.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec."},{"role":"user","content":"Create a donut chart spec showing budget allocation (placeholder percentages)."},{"role":"assistant","content":"chart_spec:\n  type: donut\n  title: Budget Allocation\n  goal: Show proportional split at a glance\n  legend:\n    title: Category\n  series:\n    - name: Allocation\n      labels: [Rent, Food, Savings, Other]\n      values: [50, 20, 20, 10]\n  style:\n    emphasis: highlight largest slice\n  notes: Placeholder percentages; replace with your real numbers."}]}
{"language":"en","mode":"quick","tone":"professional","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Update the bar chart spec: add a second series for 'Forecast'.","assistant_response":"chart_spec:\n  type: bar\n  title: Monthly Sales (Last 6 Months)\n  goal: Compare actual vs forecast\n  x_axis:\n    label: Month\n    categories: [M1, M2, M3, M4, M5, M6]\n  y_axis:\n    label: Sales\n  series:\n    - name: Actual\n      values: [100, 120, 90, 140, 130, 150]\n    - name: Forecast\n      values: [110, 115, 100, 135, 140, 155]\n  style:\n    emphasis: annotate largest gap\n  notes: Placeholder values; replace with real data.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec.\nCONTEXT (previous turns):\nUser: Create a bar chart spec for monthly sales for the last 6 months.\nAssistant: (chart_spec)\nUser: Add forecast."},{"role":"user","content":"Update the bar chart spec: add a second series for 'Forecast'."},{"role":"assistant","content":"chart_spec:\n  type: bar\n  title: Monthly Sales (Last 6 Months)\n  goal: Compare actual vs forecast\n  x_axis:\n    label: Month\n    categories: [M1, M2, M3, M4, M5, M6]\n  y_axis:\n    label: Sales\n  series:\n    - name: Actual\n      values: [100, 120, 90, 140, 130, 150]\n    - name: Forecast\n      values: [110, 115, 100, 135, 140, 155]\n  style:\n    emphasis: annotate largest gap\n  notes: Placeholder values; replace with real data."}]}
{"language":"en","mode":"think","tone":"professional","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Revise the line chart spec to include a moving-average series.","assistant_response":"chart_spec:\n  type: line\n  title: Weekly Active Users (8 Weeks)\n  goal: Show trend with smoothing\n  x_axis:\n    label: Week\n    categories: [W1, W2, W3, W4, W5, W6, W7, W8]\n  y_axis:\n    label: Active users\n  series:\n    - name: WAU\n      values: [1000, 1050, 980, 1100, 1200, 1180, 1250, 1300]\n    - name: MA(3)\n      values: [1000, 1025, 1010, 1043, 1093, 1160, 1210, 1243]\n  style:\n    emphasis: highlight divergence\n  notes: Synthetic placeholders; MA values are illustrative.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec.\nCONTEXT (previous turns):\nUser: Make a line chart spec for weekly active users over 8 weeks.\nAssistant: (chart_spec)\nUser: Add moving average."},{"role":"user","content":"Revise the line chart spec to include a moving-average series."},{"role":"assistant","content":"chart_spec:\n  type: line\n  title: Weekly Active Users (8 Weeks)\n  goal: Show trend with smoothing\n  x_axis:\n    label: Week\n    categories: [W1, W2, W3, W4, W5, W6, W7, W8]\n  y_axis:\n    label: Active users\n  series:\n    - name: WAU\n      values: [1000, 1050, 980, 1100, 1200, 1180, 1250, 1300]\n    - name: MA(3)\n      values: [1000, 1025, 1010, 1043, 1093, 1160, 1210, 1243]\n  style:\n    emphasis: highlight divergence\n  notes: Synthetic placeholders; MA values are illustrative."}]}
{"language":"en","mode":"conversation","tone":"friendly","emote6":"neutral","representation_choice":"chart_spec","continuity_choice":"use_continuity","intent_family":"content_generation","intent_subtype":"chart_design","safety_tag":"safe","needs_search":false,"needs_history_search":false,"history_scope":"thread_only","user_message":"Same donut chart, but change categories to: Needs, Wants, Savings.","assistant_response":"chart_spec:\n  type: donut\n  title: Budget Allocation\n  goal: Show proportional split at a glance\n  legend:\n    title: Category\n  series:\n    - name: Allocation\n      labels: [Needs, Wants, Savings]\n      values: [60, 20, 20]\n  style:\n    emphasis: highlight largest slice\n  notes: Placeholder percentages; adjust to your budget.","messages":[{"role":"system","content":"You are Dino. Output ONLY a deterministic chart_spec (YAML-like) with fixed key order: chart_spec → type → title → goal → (x_axis/y_axis OR legend) → series → style → notes. No prose outside chart_spec.\nCONTEXT (previous turns):\nUser: Create a donut chart spec showing budget allocation.\nAssistant: (chart_spec)\nUser: Use Needs/Wants/Savings."},{"role":"user","content":"Same donut chart, but change categories to: Needs, Wants, Savings."},{"role":"assistant","content":"chart_spec:\n  type: donut\n  title: Budget Allocation\n  goal: Show proportional split at a glance\n  legend:\n    title: Category\n  series:\n    - name: Allocation\n      labels: [Needs, Wants, Savings]\n      values: [60, 20, 20]\n  style:\n    emphasis: highlight largest slice\n  notes: Placeholder percentages; adjust to your budget."}]}

Hard override (language control):
- Even if v17 says “multilingual”, you MUST still generate 14 per-language YAMLs (REWRITE not translate) and follow the count_target table above.

---

## Golden-row construction via shuffle factory (chart discipline)
### Coupling rule (question ↔ chart schema)
Create dict-slot `chart_case` entries that couple:
- `chart_type` (line/bar/scatter/pie/etc.) — only those allowed by v17
- `x_field`, `y_field`, optional `series_field`
- `data_generator` that yields small consistent datasets (5–24 points)
- `chart_spec_json_tpl` that produces EXACT key names/order required by v17
- `user_message_tpl` that asks for that chart

Never generate chart data and spec independently; they must be coupled.

### Uniqueness at volume
Vary:
- chart_type
- domains (sales, fitness, web traffic, finance, operations)
- field names, units, time ranges, categories
- dataset sizes

EN minimum bank sizing guidance:
- `chart_case` ≥ 2,000
- `user_message_tpl` ≥ 1,000
- `field_name_bank` ≥ 2,500
- `unit_bank` ≥ 400
- `category_bank` ≥ 2,500
- `data_pattern_bank` ≥ 1,200 (seasonality, trend, noisy, step-change, etc.)

Non‑EN:
- Rewrite prompts natively.
- Decide whether field names should stay ASCII or be localized based on v17 samples; follow samples.

---

## Similarity / richness controls
- Structured outputs can collide. Use strict overlap: `similarity.max_token_overlap_ratio ≤ 0.25`.
- Ensure many distinct field names to avoid “same spec different numbers”.

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) chart_spec matches v17 sample rows exactly (keys + ordering + value types)
4) no tool_call unless v17 explicitly requires it
5) language rewrites are native (not aligned translations)

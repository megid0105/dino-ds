# Codex Lane Instruction — Lane 07 — Search Triggering (Detection) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #7 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums and lane‑scoped rules
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution + lane volumes
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

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
- For non‑English YAMLs: **REWRITE** prompts/responses natively in that language.  
  **Do not translate** English template sentences.
- Avoid 1‑to‑1 alignment across languages.

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

Allocation rule used here (must match your build):
- §3.2 weights sum to 102; to preserve lane totals exactly, allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Lane mission
Teach Dino **Search Triggering**: set `needs_search` true/false correctly based on recency / changing-facts need.

This is detection training:
- `needs_search` is the supervision target
- assistant must not claim to search; for true cases, it must not fabricate current facts


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#7. SEARCH TRIGGERING
===============================================================
Type: LoRA  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 30,000  
Build target lines (+20% buffer, pre-filter): 36,000  
Steps: 8,000  
Synthetic / Real: 80% synthetic / 20% real  
Multilingual: Yes
Language distribution:
- en: 70%
- zh-hk: 20%
- zh-hant: 5%
- zh-hans: 5%
Required schema fields:

### Required schema fields (verbatim from v17)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family
- intent_subtype
- safety_tag
- needs_search            → REQUIRED (true/false)
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]


### Distribution (verbatim from v17)
Language distribution:
- en: 70%
- zh-hk: 20%
- zh-hant: 5%
- zh-hans: 5%

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
From `Full_Dataset_Spec_FULL_LATEST_v17.md` lane #7 section, extract and implement exactly:
- required fixed `mode` / allowed modes
- required fixed `representation_choice` / allowed values
- required fixed `needs_search` / `needs_history_search`
- any lane‑specific caps for optional fields
- any lane‑specific duplication tolerance guidance
- any lane‑specific forbidden patterns

Then encode those as:
- `base_row` invariants (anything fixed across rows)
- slot banks + templates (anything that varies)
- `similarity` gate settings (must not be looser than v17)

Also obey MASTER label enums (do not invent new enum strings).

---

## Lane‑specific contract rules (implement exactly)
Lane 7 is detection-only:
- Do NOT include `tool_call`, `image_context`, citations blocks, or any tool markers.
- Follow the v17 boundary exactly (CT samples). Typical true cases: “latest/today/current price/weather now/current events/schedules/active leadership”.
- For `needs_search: true`: assistant_response must be safe and non-hallucinating (ask for location/date/source OR provide a framework + what to verify).
- For `needs_search: false`: answer normally.
- Use paired near-miss cases (true vs false) across many topic families to sharpen the boundary.


---

## Generation strategy (must meet naturalness + richness + volume)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows).
- Keep the real slice small and diverse; do not overfit to a few sources.

Dict-slot coupling:
- `case` includes `{needs_search, scenario_family, time_sensitivity, tone, mode, intent_family, intent_subtype, safety_tag}`.

Bank sizing guidance (EN):
- `case` ≥240 (large true slice + near-miss pairs)
- `user_message_tpl` ≥520
- `assistant_response_tpl_true` ≥220 (safe “can’t confirm current info” replies; no tool talk)
- `assistant_response_tpl_false` ≥280 (normal answers)

Non‑EN:
- Rewrite templates natively; recency phrasing must be natural in that language.


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Non‑EN files are native rewrites (not aligned translations)
6) Richness: no repeated first-sentence spam; meaningful prompt variety

# Codex Lane Instruction — Lane 06 — General Intent Classification (Detection) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #6 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums and lane‑scoped rules
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution + lane volumes
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
  **Do not translate** English template sentences.
- Avoid 1‑to‑1 alignment across languages.

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

Allocation rule used here (must match your build):
- §3.2 weights sum to 102; to preserve lane totals exactly, allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Lane mission
Teach Dino **General Intent Classification**: label `intent_family` + `intent_subtype` correctly.

This is detection training:
- labels are the supervised target
- assistant responses are plausible/helpful but must not mention labels or “classification”


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#6. GENERAL INTENT CLASSIFICATION
===============================================================
Type: classifier-LoRA  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 40,000  
Build target lines (+20% buffer, pre-filter): 48,000  
Steps: 10,000  
Synthetic / Real: 80% synthetic / 20% real  
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
- mode
- tone
- emote6                  → "neutral"
- representation_choice
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

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
From `Full_Dataset_Spec_FULL_LATEST_v17.md` lane #6 section, extract and implement exactly:
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
Lane 6 is detection-only:
- Do NOT include `tool_call`, `image_context`, citations blocks, or any tool markers.
- Do NOT invent new intent enums; use ONLY MASTER enums.
- Implement v17 lane #6 required label set and any distribution rules exactly.
- Use dict-slot coupling so each (intent_family, intent_subtype) pairs with many scenario families and many phrasings.
- ≤10% controlled ambiguity is allowed only if v17 examples show it; never exceed v17.


---

## Generation strategy (must meet naturalness + richness + volume)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows).
- Keep the real slice small and diverse; do not overfit to a few sources.

Coverage design:
- Build dict-slot `case` entries: `{intent_family, intent_subtype, scenario_family, tone, mode, safety_tag}`.
- Ensure broad coverage across MASTER enums; avoid over-weighting a few.
- Cap per-label bucket expansions to avoid near-dup spam.

Bank sizing guidance (EN):
- `case` ≥200
- `user_message_tpl` ≥500 (bucketed)
- `assistant_response_tpl` ≥360

Non‑EN:
- Rewrite prompts/responses natively.
- Keep label enums unchanged (language-agnostic).

Use strict similarity gating (not looser than v17) and high attempts_per_row to avoid underfill.


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Non‑EN files are native rewrites (not aligned translations)
6) Richness: no repeated first-sentence spam; meaningful prompt variety

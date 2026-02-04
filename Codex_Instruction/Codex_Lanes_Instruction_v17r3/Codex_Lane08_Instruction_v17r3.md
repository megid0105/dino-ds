# Codex Lane Instruction — Lane 08 — Search Integration (Grounded) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #8 section + CT sample row logic
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
- Avoid 1‑to‑1 alignment across languages (no “same sentence in 14 languages” drift).

---

## Volumes — `count_target` per language (must match exactly)
| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| en | 29412 | 35295 |
| zh-hk | 5882 | 7059 |
| th | 5882 | 7059 |
| zh-hant | 2353 | 2824 |
| zh-hans | 2353 | 2824 |
| pt-br | 2941 | 3530 |
| es | 2941 | 3530 |
| de | 1177 | 1413 |
| fr | 1177 | 1413 |
| it | 1177 | 1413 |
| ja | 1177 | 1413 |
| ko | 1176 | 1412 |
| hi | 1176 | 1412 |
| vi | 1176 | 1412 |

Allocation rule (must match your build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Lane mission
Teach Dino **Search Integration**: produce grounded answers using ONLY provided SEARCH_RESULTS.

Supervision goal:
- When needs_search=true, Dino issues a `tool_call` (web_fetch or web_read) and then answers using SEARCH_RESULTS only.
- Assistant must cite sources using bracket citations [1], [2] referring to SEARCH_RESULTS items.
- No hallucination; if results are insufficient, ask a clarifying question or state uncertainty (still user-facing).


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#8. SEARCH INTEGRATION
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 60,000  
Build target lines (+20% buffer, pre-filter): 72,000  
Steps: 18,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes
Goal (integration):

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
- needs_search            → true
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response       → MUST be user-facing; MUST NOT mention internal routing/tool names
- tool_call                → REQUIRED (web_fetch | web_read)
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]


### Distribution (verbatim from v17)
Language distribution:
- en: 70%
- zh-hk: 20%
- zh-hant: 5%
- zh-hans: 5%

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
From `Full_Dataset_Spec_FULL_LATEST_v17.md` lane #8 section, extract and implement exactly:
- required fixed `mode` / allowed modes
- required fixed `representation_choice` / allowed values
- required fixed `needs_search` / `needs_history_search`
- any lane‑specific required fields beyond the shared core (e.g., `tool_call`, `messages`, `flow_state`, `connector_needed`)
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
Lane 8 hard contract (from v17 lane #8; do not loosen):
- `needs_search` must be **true** for every row.
- `needs_history_search` must be **false**.
- `tool_call` is **REQUIRED** for every row and must be one of:
  - `{"name":"web_fetch","arguments":{"query":..., "max_reads":..., "max_seconds":...}}`
  - `{"name":"web_read","arguments":{...}}` (follow v17 lane #8 spec exactly for arguments)
- `messages` is REQUIRED and must include a system message that embeds:
  - `Use SEARCH_RESULTS only.`
  - `SEARCH_RESULTS:` followed by numbered items `[1] ...`, `[2] ...` etc.
- `assistant_response` MUST:
  - be strictly user-facing
  - use ONLY facts present in SEARCH_RESULTS
  - include citations like `[1]` / `[1][2]` that match the items used
- Anti-leakage: do NOT say “tool_call”, “web_fetch”, “web_read”, “search”, “connector”, “deeplink”, “schema”, or labels.

Data realism note (mandatory):
- User messages must never mention tools/connectors/deeplinks/internal mechanisms.


---

## Generation strategy (must meet naturalness + richness + volume)
Use `generation_mode: hybrid` to satisfy the 60/40 synthetic/real requirement:
- `hybrid.primary: teacher_import` (real rows)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Provide `seed_real_<lang>.jsonl` with diverse grounded Q/A + SEARCH_RESULTS patterns.
- Seeds must already be schema-valid Lane 8 rows (include tool_call + messages + citations).

Synthetic generation must be **coupled** (no broken grounding):
- Use a dict-slot `case` with fields that keep query/results/answer consistent:
  `{intent_family, intent_subtype, tone, mode, user_message, tool_call_obj, search_results_items, answer_fact_slots, cite_ids}`

SEARCH_RESULTS construction requirements:
- 1–3 results per row.
- Each result item must contain the specific facts the assistant cites.
- The assistant must paraphrase those facts (do not copy result text verbatim) and cite the matching ids.

Template bank sizing guidance to reach 60k rows safely (EN):
- `case` ≥ 2,000 distinct query/result bundles (spread across many domains: hours/locations, medical guidance from official sources, product specs, policy pages, how-to docs, etc.)
- `assistant_paraphrase_tpl` ≥ 600
- `citation_format_tpl` ≥ 80 (placement variations)
- `result_item_tpl` ≥ 1,200 (titles/snippets written to include needed facts)

Non‑EN YAMLs (hard):
- Rewrite `user_message`, `assistant_response`, and ideally SEARCH_RESULTS titles/snippets natively.
- Do NOT reuse the same `case` bundles as English; build per-language `case` banks so content differs (prevents cross-language sentence alignment drift).

Similarity:
- Set similarity gate STRICT (do not be looser than v17) because citations can cause accidental near-dups.
- Use many topic families and diverse numeric parameters (dates, prices, hours, counts) to increase uniqueness.


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Non‑EN files are native rewrites (not aligned translations)
6) Richness: no repeated first-sentence spam; meaningful prompt variety

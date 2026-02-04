# Codex Lane Instruction — Lane 09 — Multi‑Step Action Flow (No Tool) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #9 section + CT sample row logic
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
Teach Dino **Multi‑Step Action Flow**: ask for the next minimal missing detail and track flow_state.

Supervision goal:
- The assistant should request only the next smallest missing parameter to proceed.
- Use `flow_state` to represent where the conversation is (awaiting choice/parameters/confirmation, etc.).
- No tool calls. No search. No citations/SEARCH_RESULTS.


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#9. MULTI-STEP ACTION FLOW
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 60,000  
Build target lines (+20% buffer, pre-filter): 72,000  
Steps: 18,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes
Goal:

### Required schema fields (verbatim from v17)
Required schema fields:
- language
- mode
- tone
- emote6                  → typically "neutral" (varied allowed)
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family
- intent_subtype
- flow_state              → REQUIRED (varied)
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response
- messages              → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]
  - user/assistant are the current turn


### Distribution (verbatim from v17)
Language distribution:
- en: 60%
- zh-hk: 15%
- zh-hant: 5%
- zh-hans: 5%
- ko: 5%
- ja: 5%
- pt-br: 3%
- es: 2%


### Forbidden (verbatim from v17)
Forbidden (hard):
- `tool_call` (MUST NOT appear in JSONL for this lane)
- Any grounded SEARCH_RESULTS / citations
- Any internal mechanism words in user messages (“tool”, “connector”, “deeplink”, “schema”, etc.)

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
From `Full_Dataset_Spec_FULL_LATEST_v17.md` lane #9 section, extract and implement exactly:
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
Lane 9 hard contract (from v17 lane #9; do not loosen):
- `needs_search` must be **false**.
- `needs_history_search` must be **false**.
- `flow_state` is REQUIRED and must follow the v17 distribution targets:
  - none: 30%
  - awaiting_user_confirmation: 20%
  - awaiting_user_choice: 20%
  - awaiting_parameters: 15%
  - ready_for_action: 15%
- `messages` is REQUIRED and must include a system message that contains:
  - `CONTEXT (previous turns):` and 1–2 prior-turn lines (user+assistant)
- Forbidden (hard):
  - tool_call MUST NOT appear
  - any grounded SEARCH_RESULTS or citations
  - any internal mechanism words in user messages (“tool”, “connector”, “deeplink”, “schema”, etc.)

Assistant_response constraint:
- must be strictly user-facing
- must ask for ONLY the next minimal missing detail (1–2 short questions max; never a long checklist)


---

## Generation strategy (must meet naturalness + richness + volume)
Use `generation_mode: hybrid` (60/40):
- `hybrid.primary: teacher_import`
- `hybrid.backfill: template_expand`
- `hybrid.max_primary_ratio: 0.40`

Core design: flow_state‑coupled cases
- Build dict-slot `case` entries with:
  `{intent_family, intent_subtype, tone, mode, flow_state, scenario_family, prior_context_lines, user_message, assistant_next_question}`

Flow_state behavior guidance:
- awaiting_parameters → ask for one missing parameter (time/date/location/amount/etc.)
- awaiting_user_choice → present 2–4 options (short) and ask user to pick
- awaiting_user_confirmation → summarize the intended action and ask “confirm?” (or ask one last binary choice)
- ready_for_action → confirm you have everything and ask for final “go ahead” (no execution)
- none → normal helpful response (no action/parameter chasing)

Bank sizing guidance to reach 60k safely (EN):
- `case` ≥ 2,500 (must cover many action-intent subtypes: calendar, reminders, shopping filters, drafting + sending, file organization, etc.)
- `context_skeleton_tpl` ≥ 500 (prior-turn variations)
- `user_message_tpl` ≥ 900
- `assistant_question_tpl` ≥ 900
- Include many near-miss parameter situations so the “minimal missing” rule is exercised.

Non‑EN:
- Rewrite context lines, user_message, assistant questions natively.
- Do NOT translate EN contexts; build per-language scenario families to avoid aligned drift.

Similarity:
- Use strict overlap thresholds and many scenario dimensions (app type, participants, times, constraints) to avoid near-duplicates.


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Non‑EN files are native rewrites (not aligned translations)
6) Richness: no repeated first-sentence spam; meaningful prompt variety

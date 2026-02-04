# Codex Lane Instruction — Lane 10 — Connector Intent Detection (Detection) (v17)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #10 section + CT sample row logic
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
| en | 12255 | 14706 |
| zh-hk | 2451 | 2942 |
| th | 2451 | 2942 |
| zh-hant | 981 | 1178 |
| zh-hans | 980 | 1176 |
| pt-br | 1226 | 1472 |
| es | 1226 | 1472 |
| de | 490 | 588 |
| fr | 490 | 588 |
| it | 490 | 588 |
| ja | 490 | 588 |
| ko | 490 | 588 |
| hi | 490 | 588 |
| vi | 490 | 588 |

Allocation rule (must match your build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Lane mission
Teach Dino **Connector Intent Detection**: predict whether an external connector/action is needed (routing decision only).

Supervision goal:
- Set `connector_needed` true/false correctly.
- No connector selection. No execution. No tool calls.
- Include a large borderline/ambiguous slice to reduce false positives.


---



---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#10. CONNECTOR INTENT DETECTION
===============================================================
Type: classifier-LoRA  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 25,000  
Build target lines (+20% buffer, pre-filter): 30,000  
Steps: 7,000  
Synthetic / Real: 80% synthetic / 20% real  
Multilingual: Yes
Goal (decision-only):

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
- connector_needed         → REQUIRED (true/false)
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
From `Full_Dataset_Spec_FULL_LATEST_v17.md` lane #10 section, extract and implement exactly:
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
Lane 10 hard contract (from v17 lane #10; do not loosen):
- `needs_search` must be **false**.
- `needs_history_search` must be **false**.
- `connector_needed` is REQUIRED (true/false).
- `messages` is REQUIRED (system, user, assistant).
- tool_call is forbidden.
- assistant_response must be strictly user-facing; never mention routing/tools/connectors/schema/labels.

Positive sample rule:
- Positive cases must truly imply doing something in an external account/app (send/post/create/modify/retrieve from user’s accounts),
  not merely drafting generic text.
- Follow v17 sample logic for borderline cases (e.g., “Email Alex: …” implies sending; “Write an email I can send to Alex” can be false).

Borderline requirement:
- Include ≥40% borderline/ambiguous cases to reduce false positives.


---

## Generation strategy (must meet naturalness + richness + volume)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import`
- `hybrid.backfill: template_expand`
- `hybrid.max_primary_ratio: 0.20`

Core design: paired near-miss buckets
- Build dict-slot `case` entries with:
  `{connector_needed, intent_family, intent_subtype, tone, mode, scenario_family, user_message, assistant_response_style}`

Must include many paired contrasts (borderlines), e.g.:
- “Email Alex …” (true) vs “Draft an email to Alex …” (false)
- “Add this to my calendar …” (true) vs “Suggest a calendar title for …” (false)
- “Text my mom …” (true) vs “Help me write a text to my mom …” (false)
- “Update my spreadsheet …” (true) vs “Explain how to do VLOOKUP …” (false)

Bank sizing guidance to reach 25k safely (EN):
- `case` ≥ 1,200 (≥40% borderline families)
- `user_message_tpl` ≥ 1,000
- `assistant_response_tpl_true` ≥ 600 (helpful, but no execution claims; can offer a draft + ask if they want it customized)
- `assistant_response_tpl_false` ≥ 600

Non‑EN:
- Rewrite prompts/responses natively (do not translate EN).
- Keep the same borderline logic but expressed naturally.

Similarity:
- Many names/roles/contexts/parameters to prevent near-dups (vary recipients, apps implicitly, dates/times, task details).


---

## Acceptance checklist (must pass for ALL 14 files)
1) `validate lane` passes schema
2) `gate lane --limit 5` succeeds
3) No unresolved `{slot}` placeholders leak
4) All rows pass `row_validator_v16` for this lane_id
5) Non‑EN files are native rewrites (not aligned translations)
6) Richness: no repeated first-sentence spam; meaningful prompt variety

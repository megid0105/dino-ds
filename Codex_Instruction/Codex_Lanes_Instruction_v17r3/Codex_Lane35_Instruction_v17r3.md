# Codex Lane Instruction — Lane 35 — Topic Hygiene (anti topic-dragging, SFT‑LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #35 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — volumes + language policy (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Copy the v17 lane #35 “Required schema fields / Constraints / Sampling example”.
2) If any bullet conflicts with CT sample rows at the bottom of the lane section, CT sample rows win.
3) Cross-check key names + enum values in MASTER; do not invent/rename keys.

---

## Deliverables (14 per-language configs in this lane directory)
Create:
- `lane_en.yaml` (en)
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
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE35_DIR>/<file>.yaml --limit 5`

---

## Language drift prevention (HARD RULE)
- One language per YAML.
- Non‑English YAMLs: **REWRITE** prompts/responses natively. Do NOT translate EN sentence-by-sentence.
- Avoid aligned topics and aligned sentence shapes across languages.

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

Allocation rule:
- Use §3.2 weights (sum=102) with normalized weights, round to nearest (half‑up), then adjust ±1 to preserve total exactly.

---

## Generation mode
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- `seed_real_<lang>.jsonl` (curated examples of topic-drift situations)

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields (per-sample):
- language
- mode                    → "quick" | "think" | "conversation"
- tone
- emote6
- representation_choice
- continuity_choice
- intent_family           → "hygiene"
- intent_subtype          → one of: "stay_on_topic" | "scope_control" | "return_to_goal" | "gentle_boundary"
- safety_tag
- needs_search
- needs_history_search
- history_scope
- user_message
- assistant_response
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

**IMPORTANT contract note:** v17 “required schema fields” says `intent_family: "hygiene"`, but CT sample rows use `intent_family: "qa_general"`.  
Treat CT sample rows as authoritative — set `intent_family: "qa_general"` in all rows.

Authoritative enum sets from CT sample rows:
- `intent_family`: ['navigation', 'qa_general']
- `intent_subtype`: ['explanation', 'gentle_boundary', 'open_app_and_play', 'return_to_goal', 'scope_control', 'stay_on_topic']
- `mode`: ['conversation', 'quick', 'think']
- `tone`: ['friendly', 'professional']
- `representation_choice`: ['bullet_list', 'plain_text']
- `continuity_choice`: ['suppress_continuity', 'use_continuity']
- `safety_tag`: ['safe']
- fixed: needs_search=false, needs_history_search=false, history_scope="thread_only"

---

## IMPORTANT: omit `mode_richness` for this lane
CT sample rows use:
- `mode: quick` with plain paragraphs (no numbered `1.` steps)
- `mode: think` with dash bullets / mixed formatting
If you set `mode_richness`, build may reject CT-style outputs.  
Therefore: **do not include `mode_richness` in lane_en.yaml**.

---

## Golden behavior rules (topic hygiene)
Goal: prevent topic dragging when user changes topic or bundles unrelated asks.

Per subtype:
- stay_on_topic: ask for missing inputs for the main task; answer tangent briefly (1 sentence) or defer.
- scope_control: user bundles 2–4 big tasks; force a priority choice (pick one), request minimum inputs.
- return_to_goal: user comes back; answer the main task directly and keep tight.
- gentle_boundary: user derails from urgent goal; offer explicit choice (stay vs switch) and avoid drifting.

Hard constraints:
- Never invent prior context. Only refer to prior goal if present under `CONTEXT` in `messages[0].content`.
- No tool_call; no schema/routing words.

---

## Messages field (must mirror)
Every row must include:
- `messages[0]` role=system content includes topic hygiene instruction.
  - For `continuity_choice: use_continuity`, system content MUST include a `CONTEXT (previous turns):` block with realistic prior dialog.
- `messages[1]` role=user content == user_message
- `messages[2]` role=assistant content == assistant_response

---

## Shuffle-factory construction (guarantee golden subtypes)
### Coupling rule (situation ↔ subtype ↔ response policy)
Create dict-slot `hyg_case` entries that couple:
- `intent_subtype` (one of ['explanation', 'gentle_boundary', 'open_app_and_play', 'return_to_goal', 'scope_control', 'stay_on_topic'])
- `main_goal` (cover letter, budget, study plan, meal prep, workout, trip plan, etc.)
- `tangent_type` (unrelated question, fun fact, opinion bait, random request)
- `user_message_tpl` (bundled/derailing text)
- `assistant_response_tpl` that applies the correct subtype policy
- `mode` + `representation_choice` consistent with CT samples
- `continuity_choice` and (if use_continuity) a matching `CONTEXT` snippet

Never sample subtype independently from user_message.

### Bank sizing guidance (60k, low similarity)
EN minimum (scale similarly per language):
- `hyg_case` ≥ 5,000
- `main_goal_bank` ≥ 4,000
- `tangent_bank` ≥ 8,000
- `bundle_bank` ≥ 8,000  (multi-task requests)
- `response_bank` ≥ 5,000
- `context_snippet_bank` ≥ 2,500  (only for use_continuity)

Non‑EN:
- Native idioms and natural conversation for that language.
- Do not translate EN goals/tangents 1:1; use separate banks.

---

## Similarity / duplication
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`
Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) intent_family always "qa_general"; intent_subtype always one of ['explanation', 'gentle_boundary', 'open_app_and_play', 'return_to_goal', 'scope_control', 'stay_on_topic']
4) `messages` always mirrors user_message/assistant_response; CONTEXT only when use_continuity
5) no tool_call; no schema/routing words; no invented prior context
6) language rewrites are native (not aligned translations)

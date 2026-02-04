# Codex Lane Instruction — Lane 28 — Emote6 Labeling (classifier‑LoRA Detection) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #28 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and v17 lane logic.

---

## Deliverables (14 per-language configs in this lane directory)
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
  Do NOT translate English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same sentence in 14 languages” drift).

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
Before writing any lane.yaml:
1) Copy the v17 lane #28 “Required schema fields / Forbidden / Constraints” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission (label-only classifier)
Predict `emote6` correctly from a realistic user message + minimal system prompt.

This lane is **label-only**:
- `assistant_response` MUST be `""` or `" "` (empty)
- supervised target is `emote6`

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → REQUIRED (label)
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family
- intent_subtype
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response       → MUST be "" (empty) or a single space
- messages              → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

Forbidden (hard):
- tool_call
- parameters/slots
- Any internal mechanism words in user messages (“tool”, “connector”, “deeplink”, “schema”, etc.)

Constraints:
- Each emote6 label should represent ≥ 10% of the dataset.
- Prefer real, natural user messages (stress, gratitude, frustration, reassurance, neutral factual tone).

Hard overrides (this pipeline’s rules):
- Ignore the lane-local language distribution in v17. You MUST use the global 14-language split + count_target table above.
- To satisfy build mode-richness without padding, set `base_row.mode: "conversation"` for all rows.

---

## emote6 labels (locked; must match MASTER exactly)
`emote6` ∈ {
  happy, sad, angry, fear, encourage, neutral
}

Per-file balance rule (so overall ≥10% each):
- In EACH language YAML, enforce label quotas:
  - each label ≥ 10% of that file’s `count_target`
  - prefer near-uniform: ~16–17% each

---

## Golden behavior: how to label
Label is based on the **user’s emotional signal**:
- happy: excitement, celebration, gratitude with upbeat tone
- sad: loss, discouragement, loneliness, “I’m failing”
- angry: frustration, blame, irritation, unfairness
- fear: anxiety, worry, uncertainty, panic, nervous
- encourage: user seeking reassurance/motivation; “can I do it”; needing support to act
- neutral: factual/no emotional signal; straightforward request or statement

Hard rule:
- If a message is mixed, pick the dominant affect expressed by the user.

---

## Shuffle-factory construction (to guarantee correctness)
### Coupling rule (message ↔ label)
Create dict-slot `emote_case` entries that couple:
- `emote6`
- `user_message_tpl` (realistic and strongly indicative of that label)
- optional `system_hint` (minimal; never suggests a label explicitly)
- `tone` (keep within allowed tones from v17 samples)
- `intent_family` and `intent_subtype` (keep stable; recommended: content_generation + {"emotional_support","encouragement"})
This coupling prevents label drift.

### Bank sizing guidance (40k without collisions)
EN minimum (scale per language):
- `emote_case` ≥ 6,000
- `user_message_bank_happy` ≥ 1,200
- `..._sad` ≥ 1,200
- `..._angry` ≥ 1,200
- `..._fear` ≥ 1,200
- `..._encourage` ≥ 1,200
- `..._neutral` ≥ 1,200
- `topic_bank` ≥ 3,000 (work, school, relationships, health, money, daily logistics)

Non‑EN:
- Write native user messages (not translations).
- Keep culture-appropriate phrasing and emotional cues.

---

## Similarity controls (strict)
Because assistant_response is empty, uniqueness must come from the user text.
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.25`
- do NOT ignore tokens like dates/names; they help uniqueness.

Underfill protection:
- attempts_per_row high (≥ 3000) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response always "" or " "
4) emote6 always one of the 6 locked labels
5) each label ≥10% per file
6) no tool_call; no internal mechanism words in user_message

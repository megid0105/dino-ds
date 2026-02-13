# Codex Lane Instruction — Lane 24 — History Search Trigger (classifier‑LoRA Detection) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #24 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and v17 lane logic.

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
- Build per-language case banks (do not reuse the same case ids across languages).

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
- Keep the real slice small and diverse.
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Copy the v17 lane #24 “Required schema fields” + constraints + sample-row patterns.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission
Teach **History Search Trigger** (detection/classifier): decide whether a user request requires looking up prior messages.

Output supervision:
- `needs_history_search` = true/false
- `history_scope` = "thread_only" or "all_threads"
- `assistant_response` must be user-facing (no mechanism leaks)

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
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
- needs_history_search    → REQUIRED (true/false)
- history_scope           → REQUIRED ("thread_only" | "all_threads")
- user_message
- assistant_response
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

Assistant response rule (anti-leakage):
- assistant_response must be strictly user-facing. Never mention internal routing, tools, connectors, deeplinks, schema fields, or labels.

Constraints:
- tool_call: forbidden
- Positive samples must require recalling earlier content (not world knowledge)

Sample rows (JSONL, single-line):

Hard overrides (this pipeline’s rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.

---

## Build gate compatibility (mode richness)
`build_cmd.py` enforces mode-richness:
- quick requires ≥180 chars and ≥1 numbered step line
- think requires ≥650 chars and ≥2 step lines
To avoid padding and keep responses natural, set:
- `base_row.mode: "conversation"` for all rows

Also set lane-level `mode_richness` so conversation rows won’t be rejected:
- `conversation_max_chars: 520`
- `conversation_max_steps: 3`

---

## Golden-row behavior rules
Positive (`needs_history_search=true`) cases MUST be “memory-dependent”, e.g.:
- “What did we decide for X earlier?” / “remind me what you said” / “what was the third idea”
- follow-ups that clearly reference earlier content without restating it
Assistant_response pattern:
- acknowledge you need to look back at earlier messages “in this thread / across our chats” to be accurate
- do NOT fabricate an answer

Negative (`needs_history_search=false`) cases MUST be answerable without past messages:
- definitions, general explanations, standalone advice, calculations, drafting
Assistant_response pattern:
- answer directly (no “I need to look back”).

`history_scope` rule:
- thread_only: “in this chat / earlier in this thread / above”
- all_threads: “in our other chats / last week we talked / across our conversations”

Anti-leakage (hard):
- never say “history search”, “retrieval”, “connector”, “deeplink”, “schema”, labels

---

## Shuffle-factory construction (to guarantee label correctness)
### Coupling rule (prompt ↔ label ↔ response)
Create dict-slot `hs_case` entries that couple:
- `needs_history_search` (true/false)
- `history_scope` (thread_only/all_threads)
- `user_message_tpl`
- `assistant_response_tpl`
- `intent_family`, `intent_subtype`, `tone`, `representation_choice`, `safety_tag`

Do NOT generate user_message and needs_history_search independently.

### Paired borderline families (must include ≥40% borderline to reduce false positives)
Include paired near-miss examples:
- “What did we decide about the rollout?” (true) vs “What is a rollout plan?” (false)
- “Remind me which restaurant I picked.” (true) vs “Suggest a restaurant.” (false)
- “What was the filename you gave me earlier?” (true) vs “What’s a good filename?” (false)

### Bank sizing guidance (25k)
EN minimum:
- `hs_case` ≥ 1,500
- `user_message_tpl_true` ≥ 700
- `user_message_tpl_false` ≥ 900
- `assistant_response_tpl_true` ≥ 400
- `assistant_response_tpl_false` ≥ 800
- `topic_bank` ≥ 2,500 (meetings, projects, personal prefs, lists, drafts, travel, etc.)

Non‑EN:
- Write native templates per language (don’t translate).
- Use language-specific particles/register naturally.

---

## Similarity / duplication
Since outputs are short, uniqueness must come from:
- many topics + many entities (names/dates/items) + many phrasings
Recommended strict settings:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.28`
- keep ignore_tokens minimal (names/dates help uniqueness)

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) needs_history_search/history_scope always present and consistent with user_message
4) no tool_call anywhere
5) assistant_response user-facing, no internal mechanism terms
6) conversation responses stay ≤520 chars

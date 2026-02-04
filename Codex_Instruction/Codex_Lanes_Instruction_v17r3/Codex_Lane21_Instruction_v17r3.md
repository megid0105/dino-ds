# Codex Lane Instruction — Lane 21 — Rewrite (LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #21 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and v17 lane logic.

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
1) Copy the v17 lane #21 “Required schema fields” and “Duplication tolerance” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants.

## Lane mission
Teach **rewrite**: same meaning, improved phrasing, same language, no added facts.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family   → "content_generation"
- intent_subtype  → "rewrite"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message    → original text
- assistant_response → rewritten text

Duplication tolerance:
- Max token overlap between user and assistant: ≤ 70% (must show real rewrite)
- Max token overlap between assistants across dataset: ≤ 35%

Sampling example:

  language: "en"
  mode: "quick"
  tone: "professional"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "content_generation"
  intent_subtype: "rewrite"
  safety_tag: "safe"
  needs_search: false
  needs_history_search: false
  history_scope: "thread_only"
  user_message: "I want to say sorry for the delay, but I don’t know how to phrase it nicely."
  assistant_response: "I’m sorry for the delay and appreciate your patience while I got this to you."
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Sample rows (JSONL, single-line):

Hard overrides (this project’s pipeline rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.
- To satisfy the build mode-richness validator, set `base_row.mode: "conversation"` for all rows (rewrite outputs are not step-based quick/think).

---

## Rewrite quality rules (golden behavior)
1) Preserve meaning and intent (no new facts).
2) Keep the same language as the user’s text.
3) Improve clarity/tone/flow. Fix grammar/typos if present.
4) Respect requested style shifts if the user asks (formal, friendly, concise, etc.).
5) No explanation unless the user explicitly asks “why”.

---

## Shuffle-factory construction (seed rows + slots + slot banks)
### Coupling rule (source ↔ style intent ↔ rewrite)
Create dict-slot `rewrite_case` entries that couple:
- `style_goal` (polish, shorten, more formal, more friendly, more persuasive, etc.)
- `source_text` (1–5 sentences, ≤450 chars)
- `user_message_tpl` (requests rewrite of that source_text)
- `rewrite_tpl` (rewritten output consistent with style_goal)
Coupling prevents drift (e.g., “shorten” but output expands).

### Bank sizing (40k without near-dups)
EN minimum:
- `rewrite_case` ≥ 3,000
- `source_text_bank` ≥ 8,000 (topic-rich; real-life messages, notes, emails, DMs, blurbs)
- `style_goal_bank` ≥ 120
- `user_message_tpl` ≥ 900 (varied phrasing)
- `rewrite_sentence_tpl` ≥ 6,000

Non‑EN:
- Build separate `rewrite_case` banks per language (do NOT reuse EN sources).
- Use language-natural forms (zh-hk particles; Japanese keigo; etc.).
- Never translate English sources; write original sources per language.

---

## Similarity + duplication controls
Use strict similarity (do not be looser than v17):
- Keep `assistant_response` under conversation max chars (default 520).  
  Enforce source_text length ≤450 chars to avoid gate rejects.
- Ensure assistant-to-assistant overlap ≤35% by:
  many topics + many style goals + many sentence patterns.

Underfill protection:
- high attempts_per_row (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) user_message and assistant_response are same language as `language`
4) rewrite preserves meaning and changes phrasing (user/assistant overlap ≤70%)
5) no tool_call, no internal mechanism words in user text

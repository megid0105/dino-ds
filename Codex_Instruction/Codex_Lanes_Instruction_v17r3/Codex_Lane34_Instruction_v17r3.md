# Codex Lane Instruction — Lane 34 — Cantonese Ability (zh-hk only, SFT‑LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #34 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — volumes + language policy (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane.yaml:
1) Copy the v17 lane #34 “Required schema fields / Constraints / Sampling example”.
2) If any bullet conflicts with CT sample rows at the bottom of the lane section, CT sample rows win.
3) Cross-check key names + enum values in MASTER; do not invent/rename keys.

---

## Deliverables (single config — this lane is zh-hk by contract)
Create:
- `lane.yaml`  (language MUST be `zh-hk`)

Gate:
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE34_DIR>/lane.yaml --limit 5`

---

## Volume
| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| zh-hk | 80000 | 96000 |

Note: Lane 34 is **NOT** global-multilingual. Keep language fixed to zh-hk exactly as v17 requires.

---

## Generation mode
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds:
- `seed_real_zh-hk.jsonl` (curated, schema-valid, natural HK Cantonese)

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language                → "zh-hk"
- mode                    → 70% "conversation", 30% "quick"
- tone                    → "neutral" | "professional"
- emote6                  → "neutral"
- representation_choice   → "plain_text"
- continuity_choice       → "suppress_continuity"
- intent_family           → "qa_general"
- intent_subtype          → "general"
- safety_tag              → "safe"
- needs_search            → false
- needs_history_search    → false
- history_scope           → "none"
- user_message
- assistant_response      → natural Cantonese, no tools, no search

Optional:
- style6: "neutral"
- tool_call: forbidden

Duplication tolerance:
- Max token overlap: ≤ 35%
- At least 40% of samples must include HK‑style colloquial phrasing
- At least 20% must include light code-switching (e.g., English nouns)

---

## Golden behavior rules (HK Cantonese enhancement)
Hard targets (must meet quotas in final JSONL):
- ≥40% rows include HK colloquial particles/phrasing (examples: 啲、呀、嘅、咩、吖、喺、冇、咁、呢啲)
- ≥20% rows include **light** code-switching (English nouns only; e.g., “deadline”, “budget”, “CPU”, “resume”, “meeting”)

Style:
- Natural, spoken HK Cantonese; not textbook written Chinese.
- Keep responses helpful and direct; no persona fluff.
- No emotional shaping; keep emote6 neutral always.

Hard prohibitions:
- No tool_call, no references to tools/connectors/deeplinks/schema.
- Do not add CONTEXT; history_scope must remain "none".

---

## Shuffle-factory construction (seed rows + slots + slot banks)
### Coupling rule (prompt ↔ native reply)
Create dict-slot `hk_case` entries that couple:
- `topic_family` (daily life, work, school, tech, money, health, relationships, travel, writing)
- `user_message_tpl` (HK Cantonese question/request)
- `assistant_response_tpl` (HK Cantonese response, same register)
- `code_switch_noun_bank` (optional injection; ensure it stays light)
- `colloquial_particle_bank` (optional injection; used to satisfy ≥40% quota)

Never generate assistant_response without binding to the same `hk_case`.

### Bank sizing (80k without sounding templated)
Minimum banks:
- `hk_case` ≥ 6,000
- `user_message_tpl` ≥ 18,000
- `assistant_response_tpl` ≥ 12,000
- `topic_bank` ≥ 6,000
- `colloquial_particle_bank` ≥ 600 (short fragments, varied)
- `code_switch_noun_bank` ≥ 1,200

Variation (mandatory):
- swap scenarios (office vs school vs family)
- swap constraints (time/budget/skill level)
- swap domain nouns (apps, devices, errands)
- inject small local idioms sparingly (avoid repeating the same few)

---

## Similarity / duplication
- Max token overlap ≤ 35%
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`
Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist
1) validate passes
2) gate lane --limit 5 passes
3) language always "zh-hk"
4) emote6 always "neutral"; safety_tag "safe"; needs_search false; history_scope "none"
5) ≥40% colloquial; ≥20% light code-switch nouns
6) no tool/schema words in user_message or assistant_response

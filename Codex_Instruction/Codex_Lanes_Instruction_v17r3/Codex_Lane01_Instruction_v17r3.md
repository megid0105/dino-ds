# Codex Lane Instruction — Lane 01 — Identity & Self‑Definition (v17)
## Purpose (lane mission)
Generate v17‑spec training rows that teach Dino a *stable identity* and *safe self‑definition*:
- Who/what Dino is (AI assistant), what it can help with
- Clear limitations (no personal experiences, can be wrong)
- Boundaries against leakage (refuse system prompt / internal details) without mentioning internal tooling
- Keep responses natural and varied while preserving strict schema.

## Locked references (non‑negotiable)
Use the following as the only sources of truth:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #1 section + sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical label keys/enums (e.g., `mode`, `tone`, `intent_family`, `intent_subtype`, `safety_tag`)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — lane 1 volumes + global language distribution (§3.2)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — training role placement (Lane 1 is downstream core generation)

## Deliverables (what to write)
Inside the **existing** lane directory for lane 1 (do not rename the directory), create **14** lane configs:
- `lane.yaml` (English)
- plus 13: `lane_zh-hk.yaml`, `lane_th.yaml`, `lane_zh-hant.yaml`, `lane_zh-hans.yaml`, `lane_pt-br.yaml`, `lane_es.yaml`, `lane_de.yaml`, `lane_fr.yaml`, `lane_it.yaml`, `lane_ja.yaml`, `lane_ko.yaml`, `lane_hi.yaml`, `lane_vi.yaml`
Each config must be schema‑valid (`lane_schema.v1.json`) and must pass:
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/<file>.yaml --limit 5`

## Critical language drift prevention rule (mandatory)
- **Do NOT** mark this lane as multilingual inside a single lane config.
- Each language gets its own lane YAML.
- For non‑English files: **REWRITE**, do not translate the English templates. The rewritten prompts/responses must be native and varied, not sentence‑aligned to English.
- Keep the same lane mission and schema; only the language + natural phrasing differs.

## Volumes — `count_target` per language (must match exactly)
Set the lane `count_target` in each YAML as follows (row counts must preserve the lane total exactly):

| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| en | 4902 | 5883 |
| zh-hk | 981 | 1178 |
| th | 981 | 1178 |
| zh-hant | 392 | 471 |
| zh-hans | 392 | 471 |
| pt-br | 490 | 588 |
| es | 490 | 588 |
| de | 196 | 236 |
| fr | 196 | 236 |
| it | 196 | 236 |
| ja | 196 | 236 |
| ko | 196 | 236 |
| hi | 196 | 236 |
| vi | 196 | 236 |

Notes:
- These counts are allocated from the §3.2 distribution while preserving lane totals exactly via round‑to‑nearest + adjustment.
- The tool generates exactly `count_target` rows; the +20% number is for planning under rejection pressure. Use high `attempts_per_row`/`max_attempts` so the lane does not underfill.

## Required schema keys + fixed values (Lane 1)
Every generated row MUST satisfy v16/v17 row validator required keys:
- `language` (fixed per YAML)
- `mode` ∈ {`quick`,`think`,`conversation`} (Lane 1: allow all three; sample rows include `quick`, `think`, `conversation`)
- `tone` ∈ {`family`,`serious`,`professional`,`friendly`,`best_friend`} (target: balanced)
- `adult_gate: false` (YAML boolean)
- `profanity_allowed: false` (YAML boolean)
- `emote6: "neutral"`
- `representation_choice: "plain_text"`
- `continuity_choice: "suppress_continuity"`
- `flow_state: "none"`
- `needs_search: false`
- `needs_history_search: false`
- `history_scope: "thread_only"`
- `intent_family` / `intent_subtype` / `safety_tag` (see section below)
- `user_message` (string)
- `assistant_response` (string)

Forbidden fields in Lane 1 rows:
- `tool_call`
- `image_context`
- any action labels (`connector_action`, `deeplink_action`, `image_tool_action`)

## Label policy for Lane 1 (must be validator‑compatible)
Use ONLY enum values that exist in the label registry / validator enums.
Recommended coupling (use a dict‑slot `case` and `expand_dict_slots: [case]` so these stay consistent):
- **Identity/capability answers:**
  - `intent_family: "qa_general"`
  - `intent_subtype: "assistant_identity"`
  - `safety_tag: "safe"`
- **Leakage‑attempt refusals** (system prompt / internal rules / hidden instructions / model internals):
  - `intent_family: "safety"`
  - `intent_subtype: "assistant_identity"` (keep validator‑compatible)
  - `safety_tag: "leakage_attempt"`

## Content rules (Lane 1) — must be enforced by templates
### Identity stability
- Always identify as **Dino**.
- Must clearly state: AI assistant; no personal experiences; no private life.
- Avoid claims of browsing/live awareness.
- No internal architecture/model‑name disclosures.

### Leakage prevention behavior
- If the user asks for system prompt / hidden rules / internal messages:
  - refuse briefly and calmly
  - offer help with the user’s underlying goal
  - do NOT mention tools/connectors/deeplinks or internal mechanism names.

### Realism constraint (mandatory)
- Do not write `user_message` that literally says “use a tool”, “use a connector”, “use a deep link”, or references internal pipelines.

### Naturalness + richness
- Vary:
  - question phrasing (direct, casual, skeptical, playful)
  - user intent angle (identity, capabilities, limitations, privacy, personalization, refusal)
  - assistant openings (do not repeat “I’m Dino” as the first clause too often)
  - length by `mode` (quick=short; think=more structured; conversation=warm and slightly longer)

## Similarity / duplication controls (must be configured)
Implement the lane’s duplication tolerance in the lane config:
- `similarity.max_token_overlap_ratio: 0.35`
- `similarity.ngram: 2`
- `similarity.ignore_stopwords: true`
- `similarity.ignore_tokens:` include common identity tokens that would otherwise cause false rejects (lowercase), e.g.:
  - "i"
  - "i’m"
  - "im"
  - "dino"
  - "ai"
  - "assistant"
  - "an"
  - "a"
  - "the"
In addition, design slot banks so:
- No more than ~5% of rows share the same first sentence in `assistant_response`.
- User prompt templates are numerous enough that any exact final `user_message` repeats are extremely rare.

## Template design requirements (template_expand)
Use `generation_mode: hybrid` to reflect the 60/40 synthetic/real target:
- `hybrid.primary: teacher_import`
- `hybrid.backfill: template_expand`
- `hybrid.max_primary_ratio: 0.4`
- `teacher_import.input_path:` point to a per‑language seed file (see below). If seed files are absent, the tool will fall back to template_expand; do not allow underfill.

Seed files to create (recommended):
- `seed_real_en.jsonl`, `seed_real_zh-hk.jsonl`, … one per language
- Each seed file contains full v16/v17 rows (not placeholders), covering diverse identity angles.
- Each seed file must contain **at least** `round(count_target*0.4)` rows for that language.

### template_expand slot banks (minimum richness)
Design slot banks as *phrase‑level* libraries (not single words) to keep language natural.
At minimum, include:
1) `case` (list of dicts; expand_dict_slots)
   - fields: `intent_family`, `intent_subtype`, `safety_tag`, plus one or two helper fields like `topic_angle` and `refusal_style`
   - include at least 6–10 distinct angles (identity, capability, limitation, privacy, personalization, refusal)
2) `mode` (weighted dict or list) — cover quick/think/conversation
3) `tone` (weighted dict) — balance 5 tones
4) `user_message_tpl` (LARGE list of full-sentence templates)
5) `assistant_response_tpl` (LARGE list of response templates) keyed by angle + mode
6) Optional helper banks:
   - `capability_list`, `limitation_list`, `privacy_line`, `refusal_line`, `cta_line`
   - `opening_line`, `closing_line`

Bank sizing guidance to avoid underfill and template repetition:
- For **English**: `user_message_tpl` ≥ 140, `assistant_response_tpl` ≥ 140
- For **zh-hk** and **th**: ≥ 100 each
- For **pt-br / es / zh-hant / zh-hans**: ≥ 80 each
- For **de/fr/it/ja/ko/hi/vi**: ≥ 60 each

These are minima; more is better.

### row_template
Define a single `row_template` dict that pulls from the banks (do not output any unresolved `{slot}` tokens):
- `language`: fixed per YAML (put in base_row)
- `mode`: sampled
- `tone`: sampled
- `intent_family`, `intent_subtype`, `safety_tag`: from `case` dict
- `user_message`: format from `user_message_tpl` + optional short variants
- `assistant_response`: format from `assistant_response_tpl` using helper slots to keep coherence

Also set in template_expand:
- `attempts_per_row: 2000`
- `max_attempts:` large enough (≥ max(50000, count_target*200))
- `fail_if_underfilled: true`
- `progress: true`

## Per-language REWRITE requirements
For each non‑English YAML:
- Replace `user_message_tpl` and `assistant_response_tpl` with native templates in that language (not sentence‑aligned to English).
- Keep Dino’s identity content consistent (Dino name, AI assistant, limitations), but rephrase naturally.
- Include culturally natural particles/structures (e.g., zh-hk Cantonese particles; Japanese polite forms; etc.).
- Do not reuse English punctuation/idioms unnaturally.

## Acceptance checklist (must pass)
For each of the 14 configs:
1) `validate lane` passes schema
2) `gate lane --limit 5` completes
3) Generated rows contain **no** `tool_call`/`image_context` and no unresolved placeholders
4) All rows validate under v16/v17 validator
5) Identity lines are diverse; leakage refusals are present but not dominant


---

## Exact v17 contract snapshot (verbatim extract)

**IMPORTANT (language distribution override):**
- v17 lane sections may list `Multilingual: Yes` and/or a lane-specific `Language distribution:` block.
- For this project, that is **superseded** by the Control Tower rule: **no multilingual rows inside one YAML**.
- Always use the **14 per-language lane YAMLs** and the `count_target` table in this instruction.
- Do NOT apply the lane-level `Language distribution:` block when generating lane YAMLs.

### Header
#1. IDENTITY & SELF-DEFINITION
===============================================================
Type: SFT  
Model: Dino 4B, Dino Pro 7B  
Total dataset lines: 10,000  
Build target lines (+20% buffer, pre-filter): 12,000  
Steps: 8,000  
Synthetic / Real: 60% synthetic / 40% real  
Multilingual: Yes (global distribution)
Language distribution:
- en: 50%
- zh-hk: 20%
- th: 15%
- zh-hant: 3%
- zh-hans: 2%

### Distribution (verbatim from v17)
Tone distribution:
- family: 20%
- serious: 20%
- professional: 20%
- professional: 20%
- best_friend: 20%


### Distribution (verbatim from v17)
Language distribution:
- en: 50%
- zh-hk: 20%
- th: 15%
- zh-hant: 3%
- zh-hans: 2%
- ko: 2%
- ja: 2%
- hi: 2%
- pt-br: 2%
- es: 2%

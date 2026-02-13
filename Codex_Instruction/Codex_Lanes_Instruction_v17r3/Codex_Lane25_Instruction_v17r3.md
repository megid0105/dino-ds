# Codex Lane Instruction — Lane 25 — History Search Integration (LoRA Action Taking) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #25 section + CT sample row logic (authoritative)
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
| en | 14706 | 17648 |
| zh-hk | 2941 | 3530 |
| th | 2941 | 3530 |
| zh-hant | 1177 | 1413 |
| zh-hans | 1177 | 1413 |
| pt-br | 1471 | 1766 |
| es | 1471 | 1766 |
| de | 588 | 706 |
| fr | 588 | 706 |
| it | 588 | 706 |
| ja | 588 | 706 |
| ko | 588 | 706 |
| hi | 588 | 706 |
| vi | 588 | 706 |

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
1) Copy the v17 lane #25 “Required schema fields” + constraints + sample-row patterns.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission
Teach **History Search Integration** (action-taking): integrate retrieved snippets into the answer **without hallucinating**.

This lane assumes retrieval already happened upstream.
All rows MUST have `needs_history_search=true`.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields (per-sample):
- language
- mode                    → "quick" | "think" | "conversation"
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity" | "use_continuity"
- intent_family
- intent_subtype
- safety_tag
- needs_search            → false
- needs_history_search    → true
- history_scope
- user_message
- assistant_response
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

Sample rows (JSONL, single-line):

Hard overrides (this pipeline’s rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.

---

## Build gate compatibility (mode richness)
To keep outputs natural and avoid step padding, set:
- `base_row.mode: "conversation"` for all rows

Lane-level `mode_richness` override (because integration answers can exceed 520):
- `conversation_max_chars: 950`
- `conversation_max_steps: 5`

---

## System message template (MUST be present, schema-locked)
messages[0].content MUST embed a literal block like:
You are Dino. Lane 25 (History Search Integration).
Task: Integrate ONLY the retrieved history snippets below into the answer, when relevant.
Rules: No hallucinated memory. Do not invent past messages. Do not rewrite snippets unless the user explicitly asks.
If snippets are irrelevant, acknowledge and proceed with the user's goal.
No tool_call.
RETRIEVED_HISTORY_SNIPPETS:
- <snippet 1>
- <snippet 2>
...

Optional (allowed by v17 samples when continuity_choice=use_continuity):
CONTEXT (previous turns):
User: ...
Assistant: ...

---

## Golden-row behavior rules
1) Use snippets as the ONLY source of “past” info.
2) If a needed detail is missing from snippets, say so (ask 1 clarifying question or state limitation).
3) Prefer light summarization; avoid over-quoting.
4) If snippets are irrelevant, acknowledge (“I don’t see that in the retrieved notes…”) and proceed.

Hard prohibitions:
- no invented memory (“I remember you said…” unless it appears in snippets)
- no chain-of-thought
- no tool_call
- no system prompt leakage beyond the fixed template above

---

## Shuffle-factory construction (to guarantee non-hallucination)
### Coupling rule (snippets ↔ ask ↔ answer)
Create dict-slot `hi_case` entries that couple:
- `retrieved_snippets` (1–4 bullets)
- `user_message_tpl` (must be answerable from snippets OR deliberately missing one detail)
- `assistant_response_tpl` that:
  - cites/uses only snippet facts
  - includes a limitation line when snippet coverage is incomplete
- `continuity_choice` (mostly suppress_continuity; include some use_continuity if you include CONTEXT)
- `history_scope` (thread_only vs all_threads)
- `tone`, `representation_choice`, `safety_tag`

Never generate assistant_response without binding it to snippets.

### Coverage mix (recommended)
- 70%: fully answerable from snippets (clean extraction/summarization)
- 20%: partially answerable (must state limitation / ask one question)
- 10%: irrelevant snippets (must say snippets don’t contain it, then proceed generically)

### Bank sizing guidance (30k)
EN minimum:
- `hi_case` ≥ 2,000
- `snippet_fact_bank` ≥ 10,000 atomic facts (owner/date/decision/preference)
- `snippet_bundle_bank` ≥ 3,500 coherent bundles
- `user_message_tpl` ≥ 1,200
- `assistant_response_tpl` ≥ 1,200

Non‑EN:
- Write snippets + user_message + responses natively per language.
- Do NOT reuse English snippet bundles across languages (prevents aligned “same fact in 14 languages”).

---

## Similarity / duplication
Uniqueness must come from distinct snippet content.
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.28`
- keep ignore_tokens minimal (names/dates help uniqueness)

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) needs_history_search always true
4) system message contains RETRIEVED_HISTORY_SNIPPETS block
5) assistant_response never invents past info outside snippets
6) no tool_call anywhere
7) conversation responses stay ≤950 chars

# Codex Lane Instruction — Lane 20 — Continuity Execution (SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #20 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution
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

Allocation rule (must match build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Generation mode (SFT ratio)
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Open v17 lane #20 section and copy its hard constraints + required fields.
2) Cross-check key names and allowed values in MASTER; do not invent/rename keys.
3) Implement those constraints verbatim as `base_row` + strict template rules.

## Lane mission
Teach **execution with continuity**: produce user-facing answers that correctly incorporate prior turns.

Goldens teach:
- referencing prior content naturally (not robotic)
- maintaining consistent details across turns
- adapting drafts/plans using prior content

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Type: SFT
Synthetic / Real: 60% synthetic / 40% real
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice → mostly "use_continuity"
- needs_search            → false
- history_scope           → "thread_only"
Duplication tolerance:
  intent_subtype: "emotional_support"
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.
Sample rows (JSONL, single-line):

Hard override (language control):
- Even though v17 marks this lane as multilingual, you MUST still generate 14 per-language YAMLs (REWRITE not translate) and follow the count_target table above.

---

## Golden-row construction via shuffle factory (execution discipline)
### Coupling rule (context ↔ ask ↔ answer)
Build dict-slot `exec_case` entries that couple:
- `prior_context_lines` (2–6 lines, always coherent)
- `user_message_tpl` (follow-up that depends on context)
- `assistant_response_tpl` (explicitly uses context in a helpful way)
- `intent_family`, `intent_subtype`, `tone`, `mode`, `representation_choice`, `safety_tag`
- `continuity_choice` (mostly use_continuity; include some suppress_continuity per v17 if shown)

### Context block rule (match CT samples)
For use_continuity rows:
- `messages[0].content` MUST include:
  `CONTEXT (previous turns):`
  followed by prior User/Assistant lines.
- `assistant_response` MUST reference at least one concrete prior detail.
Target: ≥60% of rows explicitly reference prior content (v17 requirement).

For suppress rows (minority):
- context may exist but answer must not rely on it (or ask a clarifying question).

Mode + representation discipline:
- If mode=quick, keep reply short and structured (match CT quick sample style).
- If mode=think, use a fuller structured plan/bullets (match CT think sample style).
- Keep representation_choice consistent with the response form (plain_text vs bullet_list).

Anti-leakage:
- Never mention “context window/history/labels/schema” in assistant_response.

---

## Similarity / duplication tolerance
v17 allows up to 35% overlap; still keep uniqueness high to avoid training collapse:
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.32`
- do NOT ignore the “CONTEXT” lines in similarity; vary those heavily

Underfill protection:
- high attempts_per_row (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) ≥60% of rows include an explicit reference to a prior detail
4) messages[0] includes CONTEXT block for use_continuity rows
5) tool_call absent; no internal mechanism text
6) language rewrites are native (not aligned translations)

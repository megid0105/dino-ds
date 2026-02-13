# Codex Lane Instruction — Lane 19 — Continuity Decision (SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #19 section + CT sample row logic
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
1) Open v17 lane #19 section and copy its hard constraints + required fields.
2) Cross-check key names and allowed values in MASTER; do not invent/rename keys.
3) Implement those constraints verbatim as `base_row` + strict template rules.

## Lane mission
Teach the **decision**: `continuity_choice` = `use_continuity` vs `suppress_continuity`.

Goldens teach:
- When the user’s current request depends on a prior detail (constraints/preferences/plan/draft), choose **use_continuity** and incorporate that detail.
- When the user’s request is standalone or continuity would be wrong/unsafe, choose **suppress_continuity** and answer without pulling prior info.

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
- continuity_choice       → REQUIRED (use_continuity | suppress_continuity)
- needs_search            → false
- history_scope           → "thread_only"
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]
Assistant response rule (anti-leakage):
Constraints:
- When continuity_choice=use_continuity, messages must include the required prior fact(s)
- tool_call: forbidden
Sample rows (JSONL, single-line):
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Hard override (language control):
- Even though v17 marks this lane as multilingual, you MUST still generate 14 per-language YAMLs (REWRITE not translate) and follow the count_target table above.

---

## Golden-row construction via shuffle factory (decision boundary)
### Coupling rule (context ↔ choice ↔ response)
Build dict-slot `cont_case` entries that couple:
- `continuity_choice` (use_continuity | suppress_continuity)
- `prior_context_lines` (0–4 short lines; only include required facts when use_continuity)
- `user_message_tpl`
- `assistant_response_tpl`
- `intent_family`, `intent_subtype`, `tone`, `mode`, `representation_choice`, `safety_tag`

**Never** generate these independently. The same user_message can map to different choice only if the prior_context differs.

### Context encoding rule (so the model can learn)
When continuity_choice = use_continuity:
- `messages[0].content` MUST include:
  `CONTEXT (previous turns):`
  followed by 2–4 lines that include the specific fact(s) used.
- `assistant_response` MUST explicitly use one of those facts (natural phrasing, no copying the context verbatim).

When continuity_choice = suppress_continuity:
- Provide either:
  - no CONTEXT block, OR
  - a CONTEXT block that is irrelevant/ambiguous (and assistant_response must not rely on it).

Anti-leakage:
- Never mention “continuity”, “context window”, “history”, “labels”, “schema” in assistant_response.

---

## Variety requirements (to avoid “easy shortcuts”)
Include many families where continuity really matters:
- allergies/diet constraints, preferences, budget
- “make it shorter / reword it / same meaning” (requires the prior draft)
- follow-up planning constraints (hours reduced, different deadline, new requirement)
- personal support threads (“that presentation”, “what we decided first”)
And near-miss suppress cases:
- generic questions that do not depend on earlier turns
- follow-ups where missing context makes it unsafe → ask one clarifying question instead

---

## Similarity / underfill
Because many prompts are short (“rewrite it”), uniqueness must come from:
- varied prior_context content + varied response wording
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`
- high attempts_per_row (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) continuity_choice is always present and consistent with whether response uses context
4) tool_call absent
5) user messages never mention tools/connectors/deeplinks/schema

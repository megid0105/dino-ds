# Codex Lane Instruction — Lane 15 — Code Generation (Code‑Only SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #15 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums and required key names
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 language distribution
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
- For non‑English YAMLs: **REWRITE** user prompts natively in that language.  
  Do NOT translate English prompt templates sentence-for-sentence.
- Avoid 1‑to‑1 alignment across languages (“same request in 14 languages” drift).
- Keep task banks per language distinct (do not reuse the same problem-id catalog across languages).

---

## Volumes — `count_target` per language (must match exactly)
| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| en | 58823 | 70588 |
| zh-hk | 11765 | 14118 |
| th | 11765 | 14118 |
| zh-hant | 4706 | 5648 |
| zh-hans | 4706 | 5648 |
| pt-br | 5882 | 7059 |
| es | 5882 | 7059 |
| de | 2353 | 2824 |
| fr | 2353 | 2824 |
| it | 2353 | 2824 |
| ja | 2353 | 2824 |
| ko | 2353 | 2824 |
| hi | 2353 | 2824 |
| vi | 2353 | 2824 |

Allocation rule (must match build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Generation mode (Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`)
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane.yaml:
1) Open v17 lane #15 section and copy its hard constraints + required fields.
2) Implement those constraints **verbatim** as `base_row` invariants + strict template rules.
3) Cross-check key names with MASTER; do not invent/rename keys.

Then proceed to build slot banks / templates.

## Lane mission
Teach **code-only output**: runnable single-file code in exactly one fenced code block, no prose.

This lane is about formatting discipline + runnable structure, not explanations.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Hard constraints:
- `assistant_response` MUST be exactly **one** fenced code block (no prose before/after).
- `tool_call` is **forbidden**.
- No JSON, no manifests, no tables, no explanations.
- Single-file output only (multi-file packaging belongs in Lane 14).

Required schema fields (per-sample):
- language
- mode                    → "quick" | "think" | "conversation"
- tone
- emote6                  → "neutral"
- representation_choice   → "plain_text"
- continuity_choice       → "suppress_continuity" | "use_continuity"
- intent_family           → "content_generation"
- intent_subtype          → "code_generation"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response      → code block only
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]
  where messages[2].content MUST equal assistant_response exactly.

Data realism note (mandatory):
- user_message must NOT mention internal mechanisms (tool/deeplink/connector/schema).

---

## Code fence rules (must hold for every row)
- Exactly one opening fence and one closing fence.
- Fence must include a language tag matching the code: e.g. ```python, ```typescript, ```bash, ```go, ```java.
- No extra markdown outside the fence.
- Avoid triple-backticks inside the code (no embedded markdown fences).

---

## Golden-row construction via shuffle factory
### Coupling rule (problem ↔ solution)
Create dict-slot `code_case` entries that couple:
- `code_lang` (python/typescript/go/java/rust/etc.)
- `problem_family` (algorithms, parsing, CLI, web handler, data structure, filesystem, etc.)
- `constraints_set` (no deps, time complexity, error handling, etc.)
- `io_shape` (function only, class only, CLI script, small server handler)
- `user_message_tpl` (native per language)
- `solution_skeleton_tpl` (code template with concrete details)
- `tests_or_examples_tpl` (optional bottom-of-file asserts / minimal usage)
This coupling prevents drift and ensures the output is runnable and matches the ask.

### Volume / uniqueness strategy (120k target)
Because similarity checks are strict, uniqueness must come from:
- distinct problems + distinct constraints + distinct IO shapes
- distinct variable names, data models, and edge cases
- different code languages and libraries (standard library only unless specified)

EN minimum bank sizing guidance (scale similarly per major language):
- `code_case` ≥ 8,000 distinct cases
- `user_message_tpl` ≥ 2,500
- `solution_skeleton_tpl` ≥ 2,500
- `edge_case_bank` ≥ 3,000
- `domain_bank` ≥ 2,000 (finance/logs/text/metrics/files/etc.)
- `identifier_bank` ≥ 5,000

Non‑EN hard rule:
- Rewrite prompts natively.
- Do NOT reuse the same `code_case` ids as EN (build per-language case banks).
- Code can remain mostly English identifiers; but the *tasks* must differ across languages to avoid aligned drift.

---

## Similarity / richness controls (recommended)
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.28` (or stricter if v17 global spec says lower)
- `similarity.ignore_stopwords: true`
- Keep ignore_tokens minimal (do not ignore identifiers; they create uniqueness)

Underfill protection:
- `template_expand.attempts_per_row` high (≥ 2500)
- `template_expand.fail_if_underfilled: true`
- `template_expand.max_attempts` large enough for volume

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response is exactly one fenced code block; no prose outside
4) messages[2].content == assistant_response exactly
5) tool_call absent everywhere
6) single-file runnable structure (imports + main guard if needed)

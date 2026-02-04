# Codex Lane Instruction — Lane 16 — Code JSON Spec Mode (Schema‑Locked LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #16 section + CT sample row logic
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

## Generation mode (Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane.yaml:
1) Open v17 lane #16 section and copy its hard constraints + required fields.
2) Implement those constraints **verbatim** as `base_row` invariants + strict template rules.
3) Cross-check key names with MASTER; do not invent/rename keys.

Then proceed to build slot banks / templates.

## Lane mission
Teach **JSON-only code specification** (schema-locked). This lane outputs a machine-readable plan, not code.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Hard constraints:
- `assistant_response` MUST be **valid JSON only** (no prose, no markdown, no code fences, no comments).
- `tool_call` is **forbidden**.
- No tables, no ZIP wrapper.

Locked JSON schema (field order is mandatory):
1) task_type
2) language
3) files
4) constraints
5) tests

`files[]` object schema:
- name
- purpose
- exports (array of strings)

Required schema fields (per-sample):
- language
- mode                    → "quick" | "think" | "conversation"
- tone
- emote6                  → "neutral"
- representation_choice   → "plain_text"
- continuity_choice       → "suppress_continuity" | "use_continuity"
- intent_family           → (use "content_generation" per v17 samples)
- intent_subtype          → "code_json_spec"
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response      → strict JSON only
- messages                → [{"role":"system"},{"role":"user"},{"role":"assistant"}]
  where messages[2].content MUST equal assistant_response exactly.

Continuity behavior:
- If continuity_choice = use_continuity, system message MUST include:
  `CONTEXT (previous turns):`
  followed by 2–3 short prior-turn lines (User/Assistant) as shown in v17 samples.

Data realism note (mandatory):
- user_message must NOT mention internal mechanisms (tool/deeplink/connector/schema).

---

## JSON formatting rules (must hold for every row)
- JSON must parse with a strict parser.
- No trailing commas, no comments, no NaN/Infinity.
- Keep it single-line compact JSON to reduce formatting variance.
- Top-level keys must appear in the exact order above.
- Each files[i] object keys should appear in the order: name, purpose, exports.

---

## Golden-row construction via shuffle factory
### Coupling rule (ask ↔ spec)
Create dict-slot `spec_case` entries that couple:
- `task_type` (simple_function, class_module, cli_script, api_handler, project_skeleton, etc.)
- `code_language` (python/typescript/go/etc.)  → mapped to JSON field `language`
- `files_plan` (1–3 files, but keep it small and coherent)
- `constraints_list` (2–6 items)
- `tests_list` (1–6 items)
- `user_message_tpl` (native per language)
This coupling guarantees the JSON spec matches the user ask.

### Bank sizing (25k target; avoid near-dups)
EN minimum guidance:
- `spec_case` ≥ 3,000 distinct cases
- `user_message_tpl` ≥ 1,000
- `constraints_bank` ≥ 1,200
- `tests_bank` ≥ 1,200
- `filename_bank` ≥ 2,000
- `exports_bank` ≥ 2,000

Non‑EN:
- Rewrite prompts natively.
- Build per-language spec_case banks (do not reuse EN cases).

---

## Similarity / richness controls
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.28` (or stricter if global says lower)
- `similarity.ignore_stopwords: true`
Because JSON is structured, ensure uniqueness by varying:
- filenames, exports, constraints, tests, task_type, and language

Underfill protection:
- high attempts_per_row (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response parses as strict JSON
4) top-level JSON key order is exactly: task_type, language, files, constraints, tests
5) messages[2].content == assistant_response exactly
6) tool_call absent everywhere
7) if use_continuity: system message contains CONTEXT block

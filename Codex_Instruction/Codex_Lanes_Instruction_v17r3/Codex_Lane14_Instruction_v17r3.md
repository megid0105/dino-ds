# Codex Lane Instruction — Lane 14 — Zip Wrap Spec (Schema‑Locked) (v17r3, schema‑locked LoRA)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #14 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums and tool schema references (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 language distribution
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — LoRA lane ratio + cross‑lane constraints

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
- For non‑English YAMLs: **REWRITE** prompts/strings natively in that language.  
  **Do not translate** English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same sentence in 14 languages” drift).

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

## Generation mode (LoRA ratio)
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- Keep real slice small and diverse.
- If a seed file is absent, the lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Open v17 lane #14 section and copy its required fields + constraints.
2) Cross-check tool schema field names against MASTER (do not invent/rename keys).
3) Implement *exactly*.

Then proceed to build slot banks / templates.

## Lane mission
Teach deterministic **zip_list** wrapper packaging: manifest-first, then files in order. This lane teaches packaging discipline (format), not creativity.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required per-row fields (100%):
- `language`
- `mode` → allowed: "quick" | "think" | "conversation"
- `tone`
- `emote6` → "neutral"
- `representation_choice` → "zip_spec"
- `continuity_choice` → "suppress_continuity" | "use_continuity"
- `intent_family` → MUST be "tool_invocation"
- `intent_subtype` → MUST be "zip_wrap"
- `safety_tag`
- `needs_search` → false
- `needs_history_search` → false
- `history_scope` → "thread_only"
- `user_message`
- `assistant_response` → MUST be "" (empty string)
- `tool_call` → REQUIRED
  - `tool_call.name` MUST be `"zip_list"`
  - `tool_call.arguments.zip_items` MUST be array of `{filename, content}` ONLY
    (NO extra fields like filetype)
- `messages` → REQUIRED array of 3:
  - system: deterministic instructions
  - user: same as user_message
  - assistant: MUST contain a **JSON string** wrapper:
    `{"tool_call": {...}}`
    (assistant_response stays empty; tool_call object is top-level)

Forbidden (hard):
- No prose outside tool_call
- No binary zip output; wrapper only
- No extra keys not in master schema
- No tool markers in user_message

---

## Build gate compatibility (IMPORTANT)
Because assistant_response is empty, set:
- `base_row.mode: "conversation"` for all rows
(Allowed by v17 lane 14; avoids quick/think richness rejects.)

---

## Deterministic wrapper rules (must hold for every row)
- `zip_items[0].filename` MUST be `manifest.md`
- `manifest.md` content MUST list included filenames in order (one per line), e.g.:
  `# Manifest
- file1
- file2
- file3`
- Remaining zip_items follow the manifest order exactly.

---

## How to guarantee “golden rows” via shuffle factory
### Coupling rule (manifest ↔ files)
Create dict-slot `zip_case` entries that couple:
- `bundle_type` (meeting_pack | project_starter | study_notes | marketing_kit | etc.)
- `file_list` (ordered filenames)
- `manifest_content` built directly from file_list
- `file_contents` list aligned to filenames
- `user_message_tpl` that clearly requests that bundle

Never generate file_list and contents independently; they must be coupled.

### Slot banks (volume + uniqueness)
EN minimum sizing guidance:
- `zip_case` ≥ 1,200 distinct bundles
- `bundle_type_bank` ≥ 120
- `filename_bank` ≥ 3,000 (varied names + extensions: .md .txt .csv .json .py .js .yaml .ini)
- `content_bank_by_ext`:
  - md sections ≥ 1,200
  - txt notes ≥ 1,800
  - json configs ≥ 800
  - small scripts ≥ 800 (short, safe snippets; no backticks)
- Vary counts: 2–6 files per bundle (but always include manifest).

Non‑EN hard rule:
- Rewrite manifest headings and file contents natively (where applicable).
- File extensions remain same; content language changes.
- Do not translate EN content; create per-language content banks.

### Tool-call string in messages[2].content
JSON-stringify:
`{"tool_call": tool_call}` exactly.

---

## Similarity / richness controls
Strict similarity:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.25`
- `similarity.ignore_stopwords: true`
Keep ignore_tokens minimal.

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response always "" (empty)
4) tool_call always zip_list with zip_items = [{filename,content}...] only
5) zip_items[0] is manifest.md and manifest lists filenames in order
6) messages[2].content is JSON string wrapper {"tool_call":...}
7) no prose/codeblocks outside tool_call

# Codex Lane Instruction — Lane 13 — Doc Export Spec (Schema‑Locked) (v17r3, schema‑locked LoRA)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #13 section + CT sample row logic
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums and tool schema references (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 language distribution
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — LoRA lane ratio + cross‑lane constraints

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
Before writing any lane.yaml:
1) Open v17 lane #13 section and copy its required fields + constraints.
2) Cross-check tool schema field names against MASTER (do not invent/rename keys).
3) Implement *exactly*.

Then proceed to build slot banks / templates.

## Lane mission
Teach deterministic **export_document** formatting (document_spec packaging). This lane teaches *format discipline*, not creative writing.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required per-row fields (100%):
- `language`
- `mode` → allowed: "quick" | "think" | "conversation"
- `tone`
- `emote6` → "neutral"
- `representation_choice` → "document_spec"
- `continuity_choice` → "suppress_continuity" | "use_continuity"
- `intent_family`
- `intent_subtype` → MUST be "document_export"
- `safety_tag`
- `needs_search` → false
- `needs_history_search` → false
- `history_scope` → "thread_only"
- `user_message`
- `assistant_response` → MUST be "" (empty string)
- `tool_call` → REQUIRED
  - `tool_call.name` MUST be `"export_document"`
  - `tool_call.arguments.format` MUST be `"docx"` (as per v17 samples)
  - `tool_call.arguments.document_spec` MUST contain:
    - `title` (string)
    - `sections` (array of `{heading, body}`)
    - `style` (string)
- `messages` → REQUIRED array of 3:
  - system: deterministic instructions
  - user: same as user_message
  - assistant: MUST contain a **JSON string** representing the tool_call wrapper:
    `{"tool_call": {...}}`
    (assistant_response stays empty; tool_call object is top-level)

Forbidden (hard):
- No prose outside `tool_call`
- No code blocks
- No other tools
- No tables / zip wrappers / json-spec mode
- No extra keys not in master schema

---

## Build gate compatibility (IMPORTANT)
`build_cmd.py` mode-richness validator will reject empty assistant_response for quick/think.
To avoid false rejects, set:
- `base_row.mode: "conversation"` for all rows
(Still valid because conversation is an allowed mode in v17 lane 13.)

---

## Deterministic section templates (minimum set; may add more, but order must be fixed)
Use one of these document archetypes per row; once chosen, keep headings in EXACT order:
1) Project brief → Overview → Goals → Scope → Timeline
2) Decision memo → Context → Options → Evaluation → Decision → Next Steps
3) Meeting minutes → Attendees → Agenda → Decisions → Action Items

---

## How to guarantee “golden rows” via shuffle factory
### Coupling rule (do not let label drift)
Create dict-slot `doc_case` entries that couple:
- `archetype` (project_brief | decision_memo | minutes)
- `title_tpl`
- `sections_tpl` (an array of fixed headings + variable bodies)
- `style` (e.g., "formal" | "technical" | "plain")
- `tone`, `intent_family`, `safety_tag`
- `user_message_tpl` that clearly requests that archetype

### Slot banks (volume + uniqueness)
Because assistant_response is empty, similarity uniqueness must come from:
- user_message wording
- document_spec title and section bodies

EN minimum sizing guidance:
- `doc_case` ≥ 1,000 (many topics + archetypes)
- `user_message_tpl` ≥ 600 (varied phrasing per archetype)
- `title_tpl` ≥ 800
- `body_sentence_tpl` ≥ 3,000 (short, structured sentences; not fluff)
- `topic_bank` ≥ 1,500 (industries/products/teams/initiatives)

Non‑EN hard rule:
- Rewrite user_message, title, headings, and bodies natively.
- Do not translate the EN bodies. Create language-specific body banks.

### Tool-call string in messages[2].content
Compute assistant message content by JSON-stringifying:
`{"tool_call": tool_call}` exactly (no extra fields).

---

## Similarity / richness controls
Configure strict similarity (do not be looser than v17):
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.25`
- `similarity.ignore_stopwords: true`
- keep ignore_tokens minimal (don’t ignore titles/topic words)

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response always "" (empty)
4) tool_call always export_document with format docx and document_spec fields
5) messages[2].content is JSON string wrapper {"tool_call":...}
6) deterministic heading orders respected
7) no prose/codeblocks outside tool_call

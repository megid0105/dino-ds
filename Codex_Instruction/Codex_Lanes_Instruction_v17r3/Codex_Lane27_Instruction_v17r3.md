# Codex Lane Instruction — Lane 27 — Image → Tool Action Mapping (LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #27 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables demonstrate language split (14 configs in this lane directory)
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
  Do NOT translate English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same scene in 14 languages” drift).
- Build per-language banks (do not reuse the same case ids across languages).

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
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane_en.yaml:
1) Copy the v17 lane #27 “Required schema fields / Forbidden / Constraints” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission (mapping-only classifier)
Given `image_context` + `user_message`, choose the next tool family:
- `image_tool_action: "web_fetch"`
- `image_tool_action: "connector_action"`

This lane outputs ONLY the mapping label; no answering, no tool calls.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family
- intent_subtype
- safety_tag
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- image_context            → REQUIRED
- user_message
- assistant_response       → MUST be "" (empty) or a single space
- image_tool_action        → REQUIRED ("web_fetch" | "connector_action")
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}] (assistant content MUST be "" or a single space)

Forbidden (hard):
- tool_call (MUST NOT appear)
- parameters/slots (MUST NOT appear)
- SEARCH_RESULTS / citations (MUST NOT appear)
- natural-language assistant_response (MUST NOT appear)

Constraints:
- This lane is mapping only. Integration and grounded answering happen downstream.
- Use "connector_action" only when the user is asking to send/save/modify via an external account/app (email/calendar/files), not for general info lookup.

Hard override (this pipeline’s rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.

---

## Mapping rules (golden logic)
Choose `image_tool_action="web_fetch"` when the user asks for:
- “find similar” / “buy this” / “price check” / “what model is this” / “where to get it”
- any shopping-style lookup or web research prompted by what’s in the image

Choose `image_tool_action="connector_action"` ONLY when the user asks to:
- send/share/upload/save/attach/submit/modify using an external account/app
  examples: email, calendar, drive/files, messages, expense report
- e.g., “Email this receipt to my accountant.” / “Save this to my Drive.” / “Add this invoice to my expense report.”

Hard prohibitions:
- No `tool_call` anywhere.
- No natural-language assistant_response (must be empty string or single space).
- No SEARCH_RESULTS, citations, URLs.
- No placeholders/slots in any output.

User realism rule:
- user_message must never say “use a tool/connector” etc.

---

## image_context realism (must still be consistent)
You must still provide plausible image_context (same schema shape as lane 26), because the classifier conditions on it.
If you include `brand/product_type/primary_color`, ensure it matches the scene and supports the user ask.

---

## Shuffle-factory construction (to guarantee label correctness)
### Coupling rule (scene ↔ user ask ↔ label)
Create dict-slot `map_case` entries that couple:
- `image_context` (scene)
- `user_message_tpl` (must imply one label unambiguously)
- `image_tool_action` (web_fetch or connector_action)
- `intent_family` + `intent_subtype` (match CT samples; recommended pairing):
  - web_fetch → intent_family="shopping", intent_subtype="product_lookup"
  - connector_action → intent_family="communication", intent_subtype="share_image"
This coupling prevents accidental mismatch.

### Borderline pairs (must include ≥25% to teach boundaries)
Include near-miss pairs:
- “What brand is this shoe?” (web_fetch) vs “Email this shoe photo to my friend.” (connector_action)
- “Find the best price for this item.” (web_fetch) vs “Attach this receipt to an email.” (connector_action)

### Bank sizing guidance (30k without near-duplicates)
Uniqueness must come from both image_context and user_message (assistant is empty).
EN minimum:
- `map_case` ≥ 4,000
- `product_scene_bank` ≥ 3,500 (shoes, electronics, cosmetics, furniture, books)
- `document_scene_bank` ≥ 3,000 (receipts, invoices, tickets, forms)
- `user_message_tpl_web` ≥ 1,200
- `user_message_tpl_conn` ≥ 1,000

Non‑EN:
- Write prompts natively per language.
- Build separate map_case banks per language (do not translate EN prompts).

---

## Similarity (strict)
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.25`
Keep ignore_tokens minimal (numbers/brands help uniqueness).

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) assistant_response always "" or " "
4) image_tool_action always one of: web_fetch / connector_action
5) no tool_call, no placeholders, no citations/urls
6) label matches user_message intent (web lookup vs external account action)

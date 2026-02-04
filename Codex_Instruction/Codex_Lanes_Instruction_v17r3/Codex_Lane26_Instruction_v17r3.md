# Codex Lane Instruction — Lane 26 — Image Context Understanding (SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #26 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables demonstrate language split (14 configs in this lane directory)
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
  Do NOT translate English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same scene in 14 languages” drift).
- Build per-language banks (do not reuse the same case ids across languages).

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

## Generation mode
Use `generation_mode: hybrid` (60% synthetic / 40% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.40`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane.yaml:
1) Copy the v17 lane #26 “Required schema fields / Forbidden / Constraints” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission
Teach grounded **image_context understanding**: describe what is present using ONLY `image_context` fields.

No guessing beyond what image_context contains.

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
- assistant_response
- messages              → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

Forbidden (hard):
- Any internal mechanism words in user messages (“tool”, “connector”, “deeplink”, “schema”, etc.)
- Any invented objects not supported by image_context

Constraints:
- Mention specific objects/brands/colors only if present in image_context.
- If image_context is insufficient, ask a minimal clarifying question.

Hard override (this pipeline’s rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.

---

## image_context schema (match v17 sample shape; do not invent new top-level keys)
`image_context` MUST be a JSON object with (at minimum):
- `mode`: `"photo_upload"` or `"screenshot_upload"`
- `summary`: 1 short sentence
- `objects`: list of objects, each:
  - `label` (string)
  - `confidence` (float 0.50–0.99)
  - `bbox` (4 floats 0.0–1.0 in [x1,y1,x2,y2] order; x2>x1, y2>y1)
  - `location_hint` (e.g., top_left/center/right/bottom_right)
Optional (allowed, if used consistently):
- `text_hints`: list of `{"text": "...", "confidence": 0.xx}` for screenshots/receipts
- `brand`, `primary_color`, `product_type` (only when obviously present in the scene summary)

No raw images. Do not claim anything that isn’t in `image_context`.

---

## Golden behavior rules (grounded + concise)
1) Mention objects/colors/brands ONLY if explicitly present in image_context.
2) If user asks about unreadable text and image_context has no text_hints → ask ONE minimal clarifying question.
3) Prefer simple counts when objects list supports it (“two bowls” if two bowl objects).
4) If confidence is low (<0.60) or ambiguous, hedge lightly (“looks like…”).

Hard prohibitions:
- Don’t invent items, people, brands, text, or locations not listed.
- Don’t mention “tool / connector / schema / image_context” in user_message or assistant_response.

---

## Task families (must cover both subtypes shown by CT samples)
A) `intent_subtype: "object_description"`
- user_message asks: what’s in the photo / what objects / describe scene / how many X
- assistant_response describes using objects + summary

B) `intent_subtype: "text_presence"`
- user_message asks: is this a receipt / do you see a date/total / what text is visible
- assistant_response uses `text_hints` only; if absent → ask clarifying question

Keep `needs_search=false` always.

---

## Shuffle-factory construction (to guarantee “golden rows”)
### Coupling rule (scene ↔ question ↔ grounded answer)
Create dict-slot `img_case` entries that couple:
- `image_context` (scene object)
- `intent_subtype` (object_description | text_presence)
- `user_message_tpl` (matched to intent_subtype and scene)
- `assistant_response_tpl` (uses ONLY fields from image_context)
- `intent_family`, `tone`, `mode`, `representation_choice`, `safety_tag`

Never generate assistant_response without binding it to image_context fields.

### Bank sizing guidance (60k without near-duplicates)
Uniqueness must come from different scenes + different asks.
EN minimum:
- `scene_bank` ≥ 6,000 distinct image_context objects
- `objects_bank` ≥ 2,500 labels (food, devices, household, street, clothing, receipts, UI)
- `receipt_text_bank` ≥ 6,000 (totals/dates/vendors)
-note: when you include text_hints, vary date/total/vendor heavily
- `user_message_tpl` ≥ 1,200
- `assistant_response_tpl` ≥ 1,200

Non‑EN:
- Write native user_message + responses per language.
- Build separate scene_bank per language (do not mirror the same scene across 14 languages).

---

## Similarity settings (recommended)
- Because scenes repeat otherwise, keep overlap strict:
  - `similarity.ngram: 2`
  - `similarity.max_token_overlap_ratio: 0.28`
  - ignore_tokens minimal (names/numbers help uniqueness)

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) image_context present and matches schema shape above
4) assistant_response uses ONLY fields in image_context (no invented objects/text)
5) user_message contains no internal mechanism words
6) language rewrites are native (not aligned translations)

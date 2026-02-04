# Codex Lane Instruction — Lane 37 — Deeplink Intent Detection (classifier‑LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #37 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables (14 per-language configs in this lane directory)
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
`DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE37_DIR>/<file>.yaml --limit 5`

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

## Generation mode
Use `generation_mode: hybrid` (80% synthetic / 20% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.20`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

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
- user_message
- assistant_response
- messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]
- deeplink_needed          → REQUIRED (true/false)

Assistant response rule (anti-leakage):
- assistant_response must be strictly user-facing. Never mention internal routing, tools, connectors, deeplinks, schema fields, or labels.

Constraints:
- tool_call: forbidden (deeplink action mapping is separate)
- Positive samples must require launching/controlling an app, not just explaining it

Hard override (this pipeline’s rules):
- Ignore the lane-local “Language distribution” in v17. You MUST follow the global 14-language split via the count_target table above.

---

## Lane mission (binary detection)
Predict:
- `deeplink_needed: true` when the user’s request requires **opening/controlling an app** (music app, maps navigation, messaging, phone call, calendar add, settings toggle, etc.).
- `deeplink_needed: false` when the user asks for **information/explanations/advice** about the app or how to do something, without asking you to perform an app action.

This lane is detection only. No tool calls, no action mapping.

---

## Authoritative enums from CT sample rows (use EXACTLY these)
- `mode`: ['quick']
- `tone`: ['professional']
- `representation_choice`: ['plain_text']
- `safety_tag`: ['safe']
- `intent_family`: allowed set = ['navigation', 'qa_general']
- `intent_subtype`: allowed set = ['explanation', 'open_app_and_play']

Recommended pairing (match CT examples):
- deeplink_needed=true  → intent_family="navigation", intent_subtype="open_app_and_play"
- deeplink_needed=false → intent_family="qa_general", intent_subtype="explanation"

Fixed invariants for all rows:
- emote6="neutral"
- continuity_choice="suppress_continuity"
- needs_search=false
- needs_history_search=false
- history_scope="thread_only"
- tool_call: forbidden

---

## Golden labeling rules (must be unambiguous)
### deeplink_needed = true (positive)
User asks for an outcome that implies controlling an app:
- “Play ___ on Spotify/Apple Music”
- “Open Maps and navigate to ___”
- “Text/call/email ___”
- “Add an event to my calendar”
- “Set an alarm/timer”
- “Turn on Bluetooth / enable Focus mode” (settings action)

Assistant_response pattern:
- Confirm you will do the action in a user-facing way.
- You MAY name the app (Spotify/Maps/etc) if user did.
- You MUST NOT mention deeplinks/tools/connectors/routing.

Example style:
- “Got it. I’ll start playing lo‑fi beats in Spotify.”

### deeplink_needed = false (negative)
User asks for explanation/advice/how-to:
- “What is Spotify and how does it work?”
- “How do I create a playlist?”
- “Which navigation app is better?”
- “Why is Bluetooth not connecting?” (troubleshooting advice)

Assistant_response pattern:
- Provide a helpful answer (short, plain).
- Still no mention of internal mechanisms.

Hard constraint from v17:
- Positive samples must require launching/controlling an app, not just explaining it.

---

## Borderline pairs (mandatory ≥25% of rows)
Teach boundary with near-miss pairs:
- “Play lo‑fi beats on Spotify.” (true) vs “How do I find lo‑fi playlists on Spotify?” (false)
- “Navigate to JFK now.” (true) vs “What’s the best route from Manhattan to JFK?” (false)
- “Text Alex ‘running late’.” (true) vs “Help me write a text to Alex saying I’m running late.” (false)

---

## Shuffle-factory construction (seed rows + slots + banks)
### Coupling rule (message ↔ label ↔ response)
Create dict-slot `dl_case` entries that couple:
- `deeplink_needed` (true/false)
- `intent_family` + `intent_subtype` (must match allowed sets)
- `user_message_tpl` (unambiguously implies label)
- `assistant_response_tpl` (action-confirmation for true; explanation for false)
- fixed invariants above
- `messages` mirror: system/user/assistant, with system = “You are a helpful assistant.”

Never sample `deeplink_needed` independently from user_message.

### Bank sizing guidance (25k without near-duplicates)
Uniqueness comes from user_message variety + app/action diversity.

Per language minimum (scale with count_target):
- `dl_case_true` ≥ 3,000
- `dl_case_false` ≥ 3,000
- `app_bank` ≥ 400 (Spotify, YouTube Music, Maps, Waze, WhatsApp, Messages, Mail, Calendar, Clock, Settings…)
- `action_bank_true` ≥ 1,800 (play, navigate, message, call, add, set, toggle)
- `topic_bank_false` ≥ 2,500 (how-to, troubleshooting, comparisons, explanations)
- `entity_bank` ≥ 4,000 (songs/genres/places/contacts/events) — vary heavily

Non‑EN:
- Write native imperative phrasing and native explanations (not translations).
- Use language-local app naming conventions (e.g., zh-hk common phrasing).

---

## Similarity / duplication (strict)
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`
Keep ignore_tokens minimal (names/places help uniqueness).

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) deeplink_needed is strictly boolean and matches the user_message intent
4) tool_call is absent; no mentions of tools/connectors/deeplinks/schema/routing
5) user_message never says “use a tool/deeplink/connector”
6) borderline pairs present (≥25%)
7) language rewrites are native (not aligned translations)

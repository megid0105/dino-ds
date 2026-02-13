# Codex Lane Instruction — Lane 33 — Fallback Behavior (LoRA Pure Chat) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #33 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane_en.yaml “context format”. Produce configs that satisfy the **current** lane schema and the v17 lane logic.

---

## Deliverables (14 per-language configs in this lane directory)
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
1) Copy the v17 lane #33 “Required schema fields / Constraints / Sampling example”.
2) If any bullet conflicts with CT sample rows, treat the CT sample rows as authoritative (they are approved instances).
3) Cross-check key names + enum values in MASTER; do not invent/rename keys.

## Lane mission (pure chat fallback)
When the user asks for something that needs tools/search/real-time facts, respond with a **graceful fallback**:
- transparently state the limitation (without “tool talk”)
- ask for the minimum missing info OR provide a practical alternative plan
- keep it helpful and calm

No tools in this lane:
- `needs_search=false`
- `tool_call` forbidden

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
- assistant_response → MUST show graceful fallback when tools/search unavailable

Optional:
- tool_call: forbidden in this track

Duplication tolerance:
- Max token overlap: ≤ 35%
- At least 40% of samples must explicitly mention limitations or alternative approaches

Sampling example:

  language: "en"
  mode: "quick"
  tone: "professional"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "info_retrieval"
  intent_subtype: "generic_search"
  safety_tag: "safe"
  needs_search: false
  needs_history_search: false
  history_scope: "thread_only"
  user_message: "Check the live stock price of AAPL right now."
  assistant_response: "I can’t access live prices at the moment, but I can explain how to read stock charts and what to watch for when you check AAPL on your broker or finance app."
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Authoritative enum sets from CT sample rows:
- `intent_family`: ['qa_general']
- `intent_subtype`: ['insufficient_info', 'no_guarantees', 'recency_dependent', 'verification_plan']
- `tone`: ['family', 'friendly', 'professional']
- `mode`: ['conversation', 'quick', 'think']
- `representation_choice`: ['bullet_list', 'plain_text']
- `safety_tag`: ['safe']
- fixed: emote6="neutral", continuity_choice="suppress_continuity", needs_search=false, needs_history_search=false, history_scope="thread_only"

Hard override (this pipeline’s rules):
- Ignore the lane-local language distribution in v17. You MUST use the global 14-language split + count_target table above.

---

## IMPORTANT: do NOT enable mode_richness for this lane
CT sample rows include:
- `mode: conversation` with short paragraphs
- `mode: think` with dash bullets (not numbered `1.` steps)
If you set `mode_richness`, build may reject these CT-style answers.
Therefore: **omit `mode_richness` entirely** in this lane’s YAMLs.

---

## Subtype-by-subtype golden patterns (must be consistent)
Use only the allowed `intent_subtype` values:
['insufficient_info', 'no_guarantees', 'recency_dependent', 'verification_plan']

### insufficient_info
- Ask for the minimum missing fields (2–3 items max).
- Offer what you can do once the user provides them.

### recency_dependent
- Explain the dependency (location/date/context).
- Ask for the missing context (city, date, platform, etc.).

### no_guarantees
- Don’t claim real-time certainty (“I can’t guarantee exact/live…”).
- Offer a safe way to check + what to look for (bid/ask, last trade, official page).

### verification_plan
- Provide a practical checklist to verify a claim (primary source, cross-check, context/date).
- Invite the user to paste the claim for help turning it into a testable statement.

Hard rule:
- Never say “I can’t use tools” or “I don’t have search”.
- Say “I can’t access/guarantee live info in this chat” / “I can’t confirm that without checking sources”.

v17 requirement:
- At least 40% must explicitly mention limitations or alternative approaches.  
Recommended: make this ~80%+ to be safe.

---

## Shuffle-factory construction (to guarantee “golden fallback”)
### Coupling rule (request type ↔ subtype ↔ response)
Create dict-slot `fb_case` entries that couple:
- `intent_subtype` (one of the allowed set)
- `user_message_tpl` (realistic request that triggers that subtype)
- `assistant_response_tpl` (fallback pattern for that subtype)
- `tone` (family/friendly/professional) and `mode` (conversation/quick/think) consistent with CT samples
- fixed invariants: needs_search=false, needs_history_search=false, continuity suppress

Do NOT generate user_message and subtype independently.

### Request families (must be rich, high volume, low similarity)
- live prices (stocks/crypto)
- weather “today”
- “is my flight delayed”
- “what happened today” (current events)
- “is this claim true” (verification plan)
- account-specific actions (but no connector talk; still fallback with “I can guide you”)

Non‑EN:
- Write native prompts and native fallback phrasing per language.
- Avoid aligned sentences across languages.

### Bank sizing guidance (40k)
EN minimum:
- `fb_case` ≥ 4,500
- `user_message_bank` ≥ 18,000
- `response_bank` ≥ 6,000
- `missing_info_bank` ≥ 2,000 (flight number/date/city/market)
- `verification_steps_bank` ≥ 2,500

---

## Similarity / duplication
- Max token overlap: ≤35%
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) no tool_call anywhere
4) assistant_response always includes graceful fallback; ≥40% explicit limitations/alternatives
5) no internal mechanism words in user_message
6) language rewrites are native (not aligned translations)

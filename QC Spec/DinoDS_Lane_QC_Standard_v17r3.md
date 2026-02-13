# DinoDS — Lane QC Standard (v17r3)

_Generated: 2026-02-05 (America/Los_Angeles)_

This document is a **QC playbook** for reviewers who receive a lane's generated JSONL (and optionally its lane.yaml files) and must decide **PASS/FAIL** against the locked specs.

## Locked specs (must be loaded in the QC thread)

- `Full_Dataset_Spec_FULL_LATEST_v17.md` (lane-by-lane contract + CT-approved sample rows)

- `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` (global label enums + field semantics)

- `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` (target volumes per lane; +20% pre-filter build targets)

- `AGENTS_CODEX_GLOBAL_INSTRUCTIONS_v16.md` (global Codex behavior rules)

- `Lane_Contract_Matrix_v17_multilingual_split.csv` (operational summary of volumes + language splits + output contracts)


## Global non-negotiables (apply to **every** lane)

1. **Schema correctness:** every JSONL row is valid JSON and includes all required keys for that lane; enums must match the master label spec.

2. **`messages` mirror:** `messages` must follow the lane contract (single-turn `[system,user,assistant]` unless that lane explicitly allows multi-turn). The `content` strings must match `user_message` / `assistant_response`. No label keys inside `messages`.

3. **No label leakage:** `assistant_response` must never mention internal label fields (intent_family, needs_search, connector_needed, etc.) unless the lane explicitly trains tool payloads.

4. **No cross-lane fields:** lane-scoped fields (e.g., `connector_needed`) must appear **only** in their allowed lanes.

5. **Safety correctness:** disallowed content is a hard fail even if labeled safe.

6. **Naturalness & richness:** rows must read like plausible user/assistant turns, not templated spam.


## Language strategy (current operating rule)

To prevent language-drift via near-translations:

- For lanes that are **multilingual** (per matrix), do **NOT** mix languages inside one YAML or one JSONL.

- Instead generate **one YAML per language** (14 total): `lane.yaml` (en) plus 13 duplicates named `lane_<lang>.yaml`.

- In each non-English YAML: **REWRITE** the prompt/template content in that language (not literal translation) and set the lane `language:` tag accordingly.

- Set `count_target` per language using the lane’s language split (rounded-to-nearest integer) while preserving the lane total exactly.


### 3.2 Global language distribution (for lanes marked multilingual, unless lane overrides)

- en: **50%**
- zh-hk: **10%**
- th: **10%**
- zh-hant: **4%**
- zh-hans: **4%**
- pt-br: **5%**
- es: **5%**
- de: **2%**
- fr: **2%**
- it: **2%**
- ja: **2%**
- ko: **2%**
- hi: **2%**
- vi: **2%**


If a lane’s section in `Full_Dataset_Spec_FULL_LATEST_v17.md` disagrees with the matrix, treat the **matrix** as the operational split for build-count math.


## Standard QC workflow (do these in order)

### Step 1 — Identify what you are reviewing

- Lane number (01–37; 36 is stub/ignored)

- Language (en / zh-hk / …)

- Inputs you have: **JSONL only**, or **lane YAML + JSONL**


### Step 2 — Validate the lane YAML (if provided)

Run:

- `./scripts/run.sh validate --schema lane --config <lane_<lang>.yaml>`

Fail immediately if schema validation fails.


### Step 3 — Row-level validation (JSONL)

On the JSONL sample/full build:

- every line parses as JSON

- required keys exist

- fixed-value fields match

- forbidden/unused lane fields absent


### Step 4 — Representation / format checks

Enforce lane-specific format rules (code-only / JSON-only / table-only / tool_call-only). Any mismatch = FAIL.


### Step 5 — Semantic spot-check vs CT sample rows

Open the lane’s **CT-approved sample rows** in `Full_Dataset_Spec_FULL_LATEST_v17.md` and verify your sample outputs follow the same “logic”, not just the labels.


### Step 6 — Uniqueness / duplication

Enforce the lane’s duplication rules. If none are listed, still reject obvious duplicates / near-duplicates.


### Step 7 — Distribution (only on large samples)

Do not judge tone / subtype balance on tiny samples. Use ≥500 rows for rough checks.


### Step 8 — Report

Return: PASS/FAIL + exact fixes.


---

## Lane QC Cards (01–37, excluding 36)

Each card lists **volume**, **language split**, **output contract**, **fixed labels**, and **duplication rules**. Full lane truth remains in the lane section + CT sample rows.


### Lane 01 — IDENTITY & SELF-DEFINITION

- **Training purpose:** Pure chat

- **Train type:** SFT

- **Volume:** target 10,000 rows; build pre-filter 12,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden | image_context: forbidden

- **Fixed schema values (must match exactly):**

  - mode → "quick"

  - tone → all 5 tones distributed (see below)

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity"

  - intent_family → "safety" | "content_generation"

  - intent_subtype → "identity_definition" | "boundary_setting" | "leakage_prevention"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap between any two assistant: ≤ 35%
  - Max reuse of identical user templates: ≤ 10% of dataset
  - Synthetic templates: each template may generate ≤ 50 variants
  - Identity lines must be semantically diverse: different angles of “who Dino is”, “what Dino doesn’t do”, “what Dino refuses”, “how Dino positions itself”.
  - No more than 5% of lines may share the same opening sentence in assistant.


### Lane 02 — TONE & BEHAVIOUR FOUNDATION

- **Training purpose:** Pure chat

- **Train type:** SFT

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden | image_context: forbidden

- **Fixed schema values (must match exactly):**

  - mode → 50% quick, 50% think

  - tone → all 5 tones, balanced

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity"

  - intent_family → "content_generation" | "safety"

  - intent_subtype → "tone_behavior" | "boundary_setting" | "correction_style"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap between assistant: ≤ 30%
  - Each tone-behavior template: ≤ 40 variants
  - At least 40 distinct user intent types (user wrong, user emotional, user aggressive, user confused, user asking for flattery, etc.)


### Lane 03 — THINK MODE (UPDATED — MULTI‑STEP REASONING + PERSISTENCE)

- **Training purpose:** Pure chat

- **Train type:** SFT

- **Volume:** target 120,000 rows; build pre-filter 144,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - mode → "think"

  - tone → all 5 tones, majority serious/professional

  - emote6 → "neutral"

  - representation_choice → "plain_text" | "bullet_list" | "comparison_table" | "chart_spec" | "document_spec"

  - continuity_choice → "suppress_continuity"

  - intent_family → "decision_support" | "planning" | "content_generation"

  - intent_subtype → varied (planning, comparison, explanation, etc.)

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 30%
  - ≥ 60% of samples must include implicit multi-step reasoning
  - ≤ 5% may share the same high-level structure (avoid “First, Second, Third” repetition)
  - role: "user"
  - role: "assistant"
  - role: "user"


### Lane 04 — QUICK MODE

- **Training purpose:** Pure chat

- **Train type:** SFT

- **Volume:** target 80,000 rows; build pre-filter 96,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - mode → "quick"

  - emote6 → "neutral"

  - representation_choice → "plain_text" | "bullet_list"

  - continuity_choice → "suppress_continuity"

  - intent_family → any (qa_general, content_generation, etc.)

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 30%
  - At least 70% of answers must be ≤ 120 tokens
  - At least 30% of answers must be ≤ 60 tokens


### Lane 05 — CONVERSATION MODE

- **Training purpose:** Pure chat

- **Train type:** SFT

- **Volume:** target 80,000 rows; build pre-filter 96,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden

- **Fixed schema values (must match exactly):**

  - mode → "conversation"

  - tone → all 5 tones, with more professional/family/best_friend

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity"

  - intent_family → "content_generation" | "safety"

  - intent_subtype → "emotional_support" | "light_chat" | "check_in"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 35%
  - At least 60% of samples must be multi-turn (user–assistant–user–assistant)
  - At least 40% must show emotional callbacks or continuity_choice = "use_continuity"


### Lane 06 — GENERAL INTENT CLASSIFICATION

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden | lane-specific trigger fields (connector_needed/deeplink_needed): forbidden in this track

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 07 — SEARCH TRIGGERING

- **Training purpose:** Detection

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden in intention detection (action lanes handle tool calls)

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → REQUIRED (true/false)

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 08 — SEARCH INTEGRATION

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 60,000 rows; build pre-filter 72,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Grounding: Use SEARCH_RESULTS only. No outside facts. | No internal leakage: do not say “tool_call”, “web_fetch”, “search”, “connector”, “deeplink”, “schema”, or labels.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → true

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → MUST be user-facing; MUST NOT mention internal routing/tool names

  - tool_call → REQUIRED (web_fetch | web_read)

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 09 — MULTI-STEP ACTION FLOW

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 60,000 rows; build pre-filter 72,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** The assistant_response must be user-facing and only request the next minimal missing detail.

- **Fixed schema values (must match exactly):**

  - emote6 → typically "neutral" (varied allowed)

  - continuity_choice → "suppress_continuity"

  - flow_state → REQUIRED (varied)

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 10 — CONNECTOR INTENT DETECTION

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden (connector action mapping is separate) | Positive samples must be truly connector-required (e.g., “send/modify something in an external account/app”), not just “draft text”.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - connector_needed → REQUIRED (true/false)

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** mapping/detection lanes must set `*_needed` and action fields correctly; never leak them in assistant text.


### Lane 11 — CONNECTOR ACTION MAPPING

- **Training purpose:** Action mapping

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Output ONLY the label (e.g., connector_action="email_composeEmail"). No drafts, no metadata, no connector selection. | Use canonical labels only.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → MUST be "" (empty) or a single space

  - connector_action → REQUIRED (one of the allowed connector action labels)

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}] (assistant content MUST be "" or a single space)

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** mapping/detection lanes must set `*_needed` and action fields correctly; never leak them in assistant text.


### Lane 12 — DEEPLINK ACTION MAPPING

- **Training purpose:** Action mapping

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Output ONLY the label (e.g., deeplink_action="maps_openDirections"). No URL building, no OS/app metadata. | Use canonical labels only.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → MUST be "" (empty) or a single space

  - deeplink_action → REQUIRED (one of the allowed deeplink action labels; EXACT string)

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}] (assistant content MUST be "" or a single space)

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** mapping/detection lanes must set `*_needed` and action fields correctly; never leak them in assistant text.


### Lane 13 — DOC EXPORT SPEC (SCHEMA-LOCKED)

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST be empty (""). | Output MUST be only the tool_call object (no prose outside the tool_call). | No tables, no JSON spec mode, no ZIP wrapper, no code blocks, no other tool calls.

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "document_spec"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → "" (empty)

  - tool_call → REQUIRED (export_document)

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** `assistant_response` must be empty; enforce correct `tool_call` schema and deterministic order.


### Lane 14 — ZIP WRAP SPEC (SCHEMA-LOCKED)

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST be empty (""). | Output MUST be only the tool_call object (no prose outside the tool_call). | Do NOT add fields not in master schema (e.g., no filetype). File type is inferred from filename extension. | No binary/actual zip generation;

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "zip_spec"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → "" (empty)

  - tool_call → REQUIRED (zip_list)

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** `assistant_response` must be empty; enforce correct `tool_call` schema and deterministic order.


### Lane 15 — CODE GENERATION (CODE-ONLY)

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 120,000 rows; build pre-filter 144,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST be exactly one fenced code block (no prose before or after). | tool_call is forbidden. | No JSON, no manifests, no tables, no explanations. | Single-file output only (multi-file packaging belongs in Lane 14).

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - intent_family → "content_generation"

  - intent_subtype → "code_generation"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → code block only

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** `assistant_response` must be **one fenced code block only** (no prose).


### Lane 16 — CODE JSON SPEC MODE (SCHEMA-LOCKED JSON ONLY)

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST be valid JSON only (no prose, no markdown, no code fences, no comments). | tool_call is forbidden. | No tables, no ZIP wrapper.

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - intent_subtype → "code_json_spec"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → strict JSON only

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** `assistant_response` must be **strict JSON only** (no markdown). Validate parse.


### Lane 17 — COMPARISON TABLES (TABLE-ONLY)

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST be a markdown table only. | No prose, no bullets, no footnotes, no JSON, no code, no tool_call.

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "comparison_table"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → markdown table only

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** output must be **markdown table only**.


### Lane 18 — CHART SPEC (DETERMINISTIC CHART_SPEC)

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response MUST contain only chart_spec (YAML-like), no prose before/after. | No tool_call, no JSON spec mode, no tables.

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - emote6 → "neutral"

  - representation_choice → "chart_spec"

  - continuity_choice → "suppress_continuity" | "use_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → chart_spec only

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** output must be valid `chart_spec` object per lane.


### Lane 19 — CONTINUITY DECISION

- **Training purpose:** Detection

- **Train type:** SFT

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** When continuity_choice=use_continuity, messages must include the required prior fact(s) | tool_call: forbidden

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → REQUIRED (use_continuity | suppress_continuity)

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 20 — CONTINUITY EXECUTION

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 60,000 rows; build pre-filter 72,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → mostly "use_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 35%
  - At least 60% of samples must explicitly reference prior user content


### Lane 21 — REWRITE

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - intent_family → "content_generation"

  - intent_subtype → "rewrite"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - user_message → original text

  - assistant_response → rewritten text

- **Duplication / similarity rules:**

  - Max token overlap between user and assistant: ≤ 70% (must show real rewrite)
  - Max token overlap between assistants across dataset: ≤ 35%


### Lane 22 — TRANSLATE

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 120,000 rows; build pre-filter 144,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - language → language of user

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - intent_family → "content_generation"

  - intent_subtype → "translate"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - user_message → source text

  - assistant_response → translated text

- **Duplication / similarity rules:**

  - Max token overlap between user and assistant: ≤ 20% (different language)
  - Max token overlap across assistants: ≤ 35%


### Lane 23 — GRAMMAR FIX

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - intent_family → "content_generation"

  - intent_subtype → "grammar_fix"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - user_message → original text with errors

  - assistant_response → corrected text

- **Duplication / similarity rules:**

  - Max token overlap between user and assistant: ≤ 80% (only grammar changes)
  - Max token overlap across assistants: ≤ 35%


### Lane 24 — HISTORY SEARCH TRIGGER

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden | Positive samples must require recalling earlier content (not world knowledge)

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → REQUIRED (true/false)

  - history_scope → REQUIRED ("thread_only" | "all_threads")

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 25 — HISTORY SEARCH INTEGRATION

- **Training purpose:** Action taking

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** needs_history_search MUST be true in all samples. | No tool_call (retrieval already happened upstream). | No hallucinated memory or invented past messages. | No chain-of-thought, no system prompt leakage.

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 26 — IMAGE CONTEXT UNDERSTANDING

- **Training purpose:** Action taking

- **Train type:** SFT

- **Volume:** target 60,000 rows; build pre-filter 72,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Mention specific objects/brands/colors only if present in image_context.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - image_context → REQUIRED

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 27 — IMAGE → TOOL ACTION MAPPING

- **Training purpose:** Action mapping

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** This lane is mapping only. Integration and grounded answering happen downstream. | Use "connector_action" only when the user is asking to send/save/modify via an external account/app (email/calendar/files), not for general info lookup.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - image_context → REQUIRED

  - assistant_response → MUST be "" (empty) or a single space

  - image_tool_action → REQUIRED ("web_fetch" | "connector_action")

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}] (assistant content MUST be "" or a single space)

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 28 — EMOTE6 LABELING

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** - Each emote6 label should represent ≥ 10% of the dataset.
- Prefer real, natural user messages (stress, gratitude, frustration, reassurance, neutral factual tone).

- **Fixed schema values (must match exactly):**

  - emote6 → REQUIRED (label)

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → MUST be "" (empty) or a single space

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 29 — SAFETY: HISTORY/POLITICS

- **Training purpose:** Pure chat (safety/politics)

- **Train type:** SFT

- **Volume:** target 80,000 rows; build pre-filter 96,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - intent_family → "safety"

  - intent_subtype → "history_accuracy" | "politics_accuracy"

  - safety_tag → "politics_sensitive" | "history_sensitive"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 30%
  - At least 40% of samples must correct user misinformation


### Lane 30 — SAFETY: NO LEAKAGE

- **Training purpose:** Pure chat (no-leak)

- **Train type:** LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** Plain assistant_response per lane rules; no internal mechanism words.

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - intent_family → "safety"

  - intent_subtype → "leakage_prevention"

  - safety_tag → "leakage_attempt"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 35%
  - At least 40% of samples must be creative attempts to extract system prompt/model details


### Lane 31 — MODE SELECTION

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden

- **Fixed schema values (must match exactly):**

  - mode → REQUIRED ("quick" | "think" | "conversation")

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 32 — REPRESENTATION CHOICE

- **Training purpose:** Detection

- **Train type:** LoRA

- **Volume:** target 30,000 rows; build pre-filter 36,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response must be in the target representation (no meta) | tool_call: forbidden

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - representation_choice → REQUIRED

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 33 — FALLBACK BEHAVIOR

- **Training purpose:** Pure chat (fallback)

- **Train type:** LoRA

- **Volume:** target 40,000 rows; build pre-filter 48,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** assistant_response → MUST show graceful fallback when tools/search unavailable | tool_call: forbidden in this track

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - assistant_response → MUST show graceful fallback when tools/search unavailable

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 35%
  - At least 40% of samples must explicitly mention limitations or alternative approaches


### Lane 34 — CANTONESE_ABILITY (ZH-HK LANGUAGE ENHANCEMENT)

- **Training purpose:** Pure chat (zh-hk)

- **Train type:** SFT-LoRA

- **Volume:** target 80,000 rows; build pre-filter 96,000 rows (+20%)

- **Language split:** zh-hk 70%, en 15%, zh-hant 10%, th 5%

- **Output contract:** tool_call: forbidden

- **Fixed schema values (must match exactly):**

  - language → "zh-hk"

  - mode → 70% "conversation", 30% "quick"

  - tone → "neutral" | "professional"

  - emote6 → "neutral"

  - representation_choice → "plain_text"

  - continuity_choice → "suppress_continuity"

  - intent_family → "qa_general"

  - intent_subtype → "general"

  - safety_tag → "safe"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "none"

  - assistant_response → natural Cantonese, no tools, no search

- **Duplication / similarity rules:**

  - Max token overlap: ≤ 35%
  - At least 40% of samples must include HK‑style colloquial phrasing
  - At least 20% must include light code-switching (e.g., English nouns)

- **Special QC:** zh-hk only; enforce Cantonese naturalness; reject Simplified drift.


### Lane 35 — TOPIC_HYGIENE (ANTI TOPIC-DRAGGING BEHAVIOR)

- **Training purpose:** Pure chat (topic hygiene)

- **Train type:** SFT-LoRA

- **Volume:** target 60,000 rows; build pre-filter 72,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** No tool_call, no action labels, no internal routing/schema mentions.

- **Fixed schema values (must match exactly):**

  - mode → "quick" | "think" | "conversation"

  - intent_family → "hygiene"

  - intent_subtype → one of: "stay_on_topic" | "scope_control" | "return_to_goal" | "gentle_boundary"

  - messages → [{"role":"system"},{"role":"user"},{"role":"assistant"}]

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.


### Lane 37 — DEEPLINK INTENT DETECTION

- **Training purpose:** Detection

- **Train type:** classifier-LoRA

- **Volume:** target 25,000 rows; build pre-filter 30,000 rows (+20%)

- **Language split:** en 50%, zh-hk 10%, th 10%, zh-hant 4%, zh-hans 4%, pt-br 5%, es 5%, de 3%, fr 3%, it 2%, ja 2%, ko 2%, hi 2%

- **Output contract:** tool_call: forbidden (deeplink action mapping is separate) | Positive samples must require launching/controlling an app, not just explaining it

- **Fixed schema values (must match exactly):**

  - emote6 → "neutral"

  - continuity_choice → "suppress_continuity"

  - needs_search → false

  - needs_history_search → false

  - history_scope → "thread_only"

  - messages → Qwen ingest: [{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]

  - deeplink_needed → REQUIRED (true/false)

- **Duplication / similarity rules:** Not explicitly listed; still require no duplicates and high variety.

- **Special QC:** mapping/detection lanes must set `*_needed` and action fields correctly; never leak them in assistant text.


---

## Appendix A — Output-only QC helper (paste into a Python scratchpad)

```python

import json, collections, re

path = 'train.jsonl'

rows = [json.loads(line) for line in open(path,'r',encoding='utf-8') if line.strip()]

print('rows:', len(rows))

def c(k):

    return collections.Counter(r.get(k) for r in rows)

for k in ['language','mode','tone','representation_choice','intent_family','intent_subtype','safety_tag','needs_search','needs_history_search']:

    print('\n',k, c(k))

# leakage scan

leak = re.compile(r"intent_family|intent_subtype|needs_search|needs_history_search|history_scope|connector_needed|deeplink_needed|connector_action|deeplink_action|image_tool_action", re.I)

bad = [i for i,r in enumerate(rows) if isinstance(r.get('assistant_response'),str) and leak.search(r['assistant_response'])]

print('\nassistant leakage rows:', len(bad), 'examples:', bad[:5])

```

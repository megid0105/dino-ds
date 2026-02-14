# AGENTS — Codex No‑Brainer Lane YAML Builder (v17 locked)  
**Includes:** Global Context System + Expert Atom Packs + QC Equator v3 (Thai/CJK)  
**Audience:** Codex CLI session that edits only `lanes/**/lane_*.yaml`  
**Version:** 2026-02-13T19:38:51

---

## Step 1 — Open the 5 locked specs (do not guess)
1. Open `Full_Dataset_Spec_FULL_LATEST_v17.md` and locate your **Lane ##** section.  
2. Open `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` and keep it nearby for enums.  
3. Open `DinoDS_Lane_QC_Standard_v17r3.md` (+ Addition) for lane‑level QC rules.  
4. Open `DTAD_CTv3_QC_EQUATOR_FEB_10_2026_v3_TH_CJK_PATCH.md` for Thai/CJK duplication.  
5. Open `Lane_Contract_Matrix_v17_multilingual_strategy_v3.csv` for language file count + distribution.

**Rule:** If anything conflicts, resolve in this order: Full_Dataset_Spec → Label Registry → QC Standard → QC Equator → Contract Matrix.

---

## Step 2 — Decide the lane archetype (you must pick ONE)
Read the lane’s “Output contract” line and pick the matching archetype:

- **plain_chat** → normal user/assistant prose  
- **history_recall_chat** → needs_history_search=true; must use provided prior facts only  
- **translation_chat** → translate/paraphrase lane  
- **image_context_chat** → must not mention objects not present in image_context  
- **fallback_chat** → must show graceful fallback without tools  
- **mapping_label_only** → output only mapping label fields; assistant_response empty  
- **tool_call_only** → assistant_response empty; tool_call object only  
- **json_only** → assistant_response must be raw JSON only  
- **codeblock_only** → assistant_response must be exactly one fenced code block  
- **markdown_table_only** → assistant_response must be markdown table only  
- **chart_spec_only** → assistant_response must be chart_spec YAML-like only  
- **document_spec_only / zip_spec_only** → spec‑format lanes

**Hard rule:** Do not mix archetypes in one lane.

---

## Step 3 — Create the 1 canonical YAML scaffold (same for every lane)
Start from this scaffold and fill lane-specific values from the lane spec.

```yaml
lane_id: lane_XX_<short_name>
wave: wave0
target_base: dino_qwen4b
source_type: local
sources: []
count_target: <INT>   # for THIS language file only
base_row:
  adult_gate: false
  profanity_allowed: false
  needs_search: false
  needs_history_search: false
  connector_needed: false
  deeplink_needed: false
  emote6: neutral
  continuity_choice: suppress_continuity
  flow_state: none
  history_scope: thread_only
  representation_choice: plain_text
  safety_tag: safe
  system_prompt_id: dino.system.v1
  language: <LANG_ENUM>   # only inside lane_<lang>.yaml
language_mix: {}
synthetic_policy: {}
required_tools: []
validators: []
transform_pipeline: []
generation_mode: template_expand
system_prompt_path: prompts/system/dino_system_prompt.txt
output_dir: out_runs/<lane_id>
teacher_runtime:
  enabled: false           # MUST pass gate with DINO_DS_SKIP_OLLAMA=1
  sample_percent: 0
  provider: ollama
  policy: structure_only
similarity:
  text_field: assistant_response
  max_token_overlap_ratio: <FROM_LANE_SPEC_OR_QC_STD>
  ignore_stopwords: true
  ignore_tokens: [dino]
  ngram: 2
template_expand:
  seed: 101
  count_target: <INT>
  max_attempts: <>= count_target * 40  # increase for strict dup lanes
  attempts_per_row: 1200
  fail_if_underfilled: true
  expand_dict_slots:
    - case
    - q_template
    - a_skeleton
    - label_pack
  slot_banks:
    case: []
    q_template: []
    a_skeleton: []
    label_pack: []
    q_opening: []
    q_followup: []
    q_context_wrap: []
    a_opening: []
    a_close: []
    a_suggestion: []
    entity_pack: []
row_template:
  language: "{language}"
  mode: "{mode}"
  tone: "{tone}"
  emote6: "{emote6}"
  representation_choice: "{representation_choice}"
  continuity_choice: "{continuity_choice}"
  intent_family: "{intent_family}"
  intent_subtype: "{intent_subtype}"
  safety_tag: "{safety_tag}"
  needs_search: "{needs_search}"
  needs_history_search: "{needs_history_search}"
  history_scope: "{history_scope}"
  connector_needed: "{connector_needed}"
  deeplink_needed: "{deeplink_needed}"
  user_message: "{user_message}"
  assistant_response: "{assistant_response}"
```

**Important:** slot placeholders are simple `{key}` (no nesting). Dict slots must expose flat keys.

---

## Step 4 — Build “Expert Atom Packs” (this is how you get expert outputs)
### 4A) Expert atoms are NOT prose
In each `case` dict, store **semantic atoms** that the renderer can assemble.
Never prewrite the final assistant response.

**Universal atom fields (use in all plain_chat-like lanes):**
- `topic_domain`, `topic_term`, `goal_inf`
- `scenario_hint`, `constraint_hint`, `desired_outcome`, `risk_hint`
- `skill_level`, `timebox`, `budget`, `device_hint`, `audience_hint` (optional but strongly recommended)
- `expert_concepts` (list of 3–7 short phrases)
- `expert_moves` (list of 5–10 actionable moves)
- `expert_pitfalls` (list of 3–8 pitfalls)
- `expert_checks` (list of 3–6 “how to tell it’s working” checks)
- `expert_tools` (list of 2–6 tool hints; can be “use X when Y”, not brand marketing)

**Archetype-specific atoms (add when needed):**
- codeblock_only → `lang`, `file_name`, `function_sig`, `edge_cases`, `tests`
- json_only → `json_keys`, `allowed_values`, `example_json`
- markdown_table_only → `table_cols`, `table_rows`, `row_labels`
- chart_spec_only → `chart_type`, `axes`, `series`, `constraints`
- history_recall_chat → `prior_facts_block` (verbatim) + `what_must_be_recalled`
- mapping_label_only → `trigger_patterns` + `label_value`

### 4B) Minimum atom depth for “expert feel”
Per case, include at least:
- 3 concepts + 5 moves + 3 pitfalls + 3 checks  
If any of these are missing, outputs will look generic.

---

## Step 5 — Build the label_pack (QC compliance is label-driven)
Create `label_pack` dict items that control required distributions:
- `mode` distribution (quick/think/conversation) when lane requires it
- `tone` distribution (5 tones; lane-specific majority/minority)
- `representation_choice` distribution when lane allows multiple formats
- `intent_family` / `intent_subtype` allowed sets
- flags (`needs_search`, `needs_history_search`, `connector_needed`, `deeplink_needed`) per lane spec

**Rule:** put distributions in `label_pack` rather than inside prose.

---

## Step 6 — Build q_template and a_skeleton (structure diversity = pass duplication)
### 6A) q_template (user message)
Each dict must expose:
- `user_message` (final text assembled from q_opening, case atoms, followup)
- plus any helper keys you need (flat keys only)

**Template families:** create ≥ 40 q_templates for large lanes (≥50k rows in a language).
This keeps opening-family frequency under Equator’s 8% cap.

### 6B) a_skeleton (assistant structure)
Each dict must expose:
- `assistant_response` assembled from a_opening + summary + 10 bullets + suggestion + close (when allowed)
- no “Step 1/2/3”, no “First/Second/Third” loops for think lanes
- include implicit multi-step reasoning via connective phrasing, not labels

**For Lane 03 (Think Mode):**
- Must satisfy: ≥60% implicit multi-step reasoning  
- Must satisfy: ≤5% share same high-level structure  
→ create ≥ 15 skeleton families that reorder the same “moves”.

---

## Step 7 — Multilingual: 14 YAMLs per lane, rewrite (do NOT translate)
For multilingual lanes, create one YAML per language in the lane’s `languages` list.
Typical list includes: `en, zh-hk, th, zh-hant, zh-hans, pt-br, es, de, fr, it, ja, ko, hi, vi`.

Per language file:
1. Set `base_row.language` to the exact enum (e.g., `zh-hk`).  
2. Rewrite q/a templates natively (new phrasing, new examples).  
3. Replace entity_pack with locale-native names/places/examples.  
4. Keep the **same slot keys** and lane labels.

**Thai/CJK rules (QC Equator v3):**
- Avoid repeating short particles/bigrams.
- Prefer varied clause order.
- Ensure openings are diverse; avoid the same first 3–6 tokens.

---

## Step 8 — Count targets: always meet them (no underfill)
For each language file:
1. Compute accepted count = lane_total × language_percent (with deterministic rounding).  
2. Set YAML `count_target` = accepted count.  
3. Set `template_expand.max_attempts` >= count_target * 40.  
4. Ensure combinatorial space >= count_target * 5.

If underfill occurs, fix by:
- adding more q_templates and a_skeletons (first)
- increasing case count (second)
- expanding entity_pack (third)

---

## Step 9 — Run the only gate that matters
For EACH language file:
```bash
DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/lane_<lang>.yaml --limit 5
```

If it fails:
- Do NOT edit tool code.
- Fix YAML only by adding templates, tightening slots, or expanding atom pools.

---

## Step 10 — Lane quick reference (from contract matrix)
| Lane | Title | Train | Rows | LangFiles | Archetype | OutputContract |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Identity & Self-Definition | SFT | 10000 | 14 | image_context_chat | tool_call: forbidden \| image_context: forbidden |
| 2 | Tone & Behaviour | SFT | 40000 | 14 | image_context_chat | tool_call: forbidden \| image_context: forbidden |
| 3 | Think Mode | SFT | 120000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 4 | Quick Mode | SFT | 80000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 5 | Conversation Mode | SFT | 80000 | 14 | plain_chat | tool_call: forbidden |
| 6 | General Intent Classification | classifier-LoRA | 40000 | 14 | plain_chat | tool_call: forbidden \| lane-specific trigger fields (connector_needed/deeplink_needed): forbidden in this track |
| 7 | Search Triggering | LoRA | 30000 | 14 | plain_chat | tool_call: forbidden in intention detection (action lanes handle tool calls) |
| 8 | Search Integration | SFT | 60000 | 14 | plain_chat | Grounding: Use SEARCH_RESULTS only. No outside facts. \| No internal leakage: do not say “tool_call”, “web_fetch”, “search”, “connector”, “deeplink”, “schema”, or labels. |
| 9 | Multi-Step Action Flow | SFT | 60000 | 14 | plain_chat | The assistant_response must be user-facing and only request the next minimal missing detail. |
| 10 | Connector Intent Detection | classifier-LoRA | 25000 | 14 | plain_chat | tool_call: forbidden (connector action mapping is separate) \| Positive samples must be truly connector-required (e.g., “send/modify something in an external account/app”), not just “draft text”. |
| 11 | Connector Action Mapping | LoRA | 30000 | 14 | mapping_label_only | Output ONLY the label (e.g., connector_action="email_composeEmail"). No drafts, no metadata, no connector selection. \| Use canonical labels only. |
| 12 | Deeplink Action Mapping | LoRA | 30000 | 14 | mapping_label_only | Output ONLY the label (e.g., deeplink_action="maps_openDirections"). No URL building, no OS/app metadata. \| Use canonical labels only. |
| 13 | Doc Export Spec | LoRA | 25000 | 14 | tool_call_only | assistant_response MUST be empty (""). \| Output MUST be only the tool_call object (no prose outside the tool_call). \| No tables, no JSON spec mode, no ZIP wrapper, no code blocks, no other tool calls. |
| 14 | Zip Wrap Spec | LoRA | 25000 | 14 | tool_call_only | assistant_response MUST be empty (""). \| Output MUST be only the tool_call object (no prose outside the tool_call). \| Do NOT add fields not in master schema (e.g., no filetype). File type is inferred from filename exte |
| 15 | Code Generation | SFT | 120000 | 14 | codeblock_only | assistant_response MUST be exactly one fenced code block (no prose before or after). \| tool_call is forbidden. \| No JSON, no manifests, no tables, no explanations. \| Single-file output only (multi-file packaging belon |
| 16 | Code JSON Spec Mode | LoRA | 25000 | 14 | json_only | assistant_response MUST be valid JSON only (no prose, no markdown, no code fences, no comments). \| tool_call is forbidden. \| No tables, no ZIP wrapper. |
| 17 | Comparison Tables | LoRA | 30000 | 14 | markdown_table_only | assistant_response MUST be a markdown table only. \| No prose, no bullets, no footnotes, no JSON, no code, no tool_call. |
| 18 | Chart Spec | LoRA | 30000 | 14 | chart_spec_only | assistant_response MUST contain only chart_spec (YAML-like), no prose before/after. \| No tool_call, no JSON spec mode, no tables. |
| 19 | Continuity Decision | SFT | 40000 | 14 | plain_chat | When continuity_choice=use_continuity, messages must include the required prior fact(s) \| tool_call: forbidden |
| 20 | Continuity Execution | SFT | 60000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 21 | Rewrite | LoRA | 40000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 22 | Translate | SFT | 120000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 23 | Grammar Fix | LoRA | 40000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 24 | History Search Trigger | classifier-LoRA | 25000 | 14 | plain_chat | tool_call: forbidden \| Positive samples must require recalling earlier content (not world knowledge) |
| 25 | History Search Integration | LoRA | 30000 | 14 | history_recall_chat | needs_history_search MUST be true in all samples. \| No tool_call (retrieval already happened upstream). \| No hallucinated memory or invented past messages. \| No chain-of-thought, no system prompt leakage. |
| 26 | Image Context Understanding | SFT | 60000 | 14 | image_context_chat | Mention specific objects/brands/colors only if present in image_context. |
| 27 | Image → Tooling | LoRA | 30000 | 14 | mapping_label_only | This lane is mapping only. Integration and grounded answering happen downstream. \| Use "connector_action" only when the user is asking to send/save/modify via an external account/app (email/calendar/files), not for gene |
| 28 | Emote6 Labeling | classifier-LoRA | 40000 | 14 | plain_chat | - Each emote6 label should represent ≥ 10% of the dataset. - Prefer real, natural user messages (stress, gratitude, frustration, reassurance, neutral factual tone). |
| 29 | Safety: History/Politics | SFT | 80000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 30 | Safety: No Leakage | LoRA | 40000 | 14 | plain_chat | Plain assistant_response per lane rules; no internal mechanism words. |
| 31 | Mode Selection | classifier-LoRA | 30000 | 14 | plain_chat | tool_call: forbidden |
| 32 | Representation Choice | LoRA | 30000 | 14 | plain_chat | assistant_response must be in the target representation (no meta) \| tool_call: forbidden |
| 33 | Fallback Behavior | LoRA | 40000 | 14 | fallback_chat | assistant_response → MUST show graceful fallback when tools/search unavailable \| tool_call: forbidden in this track |
| 34 | Cantonese_Ability | SFT-LoRA | 80000 | 14 | plain_chat | tool_call: forbidden |
| 35 | Topic_Hygiene | SFT-LoRA | 60000 | 14 | plain_chat | No tool_call, no action labels, no internal routing/schema mentions. |
| 37 | Deeplink Intent Detection (NEW) | classifier-LoRA | 25000 | 14 | plain_chat | tool_call: forbidden (deeplink action mapping is separate) \| Positive samples must require launching/controlling an app, not just explaining it |


---

## Appendix — “Expert feel” assembly pattern (plain_chat / think)
**Summary** (2–3 sentences): reference goal + constraints + outcome.  
**Bullets** (10): draw from `expert_moves`, `expert_checks`, `expert_pitfalls`, `expert_tools`.  
**Suggestion** (1): pick the smallest next action using `timebox` or `skill_level`.  
**Close** (1 line): invite one clarifying detail.

**Never:** internal mechanism words, raw placeholders, JSON tool dumps, or repeated openers.



---

# ADDENDUM (CRITICAL) — Case-bank must NEVER contain rendered text (Lane 03 unblocker)

This addendum is mandatory because multiple builds failed QC while still “technically following” earlier sections.

## A) HARD STOP checks (if any is true, you will fail strict duplication QC)

### A1) `slot_banks.case` contains `assistant_response:` anywhere
If **any** case item includes a fully written assistant response, you have capped structural diversity and strict external duplication will fail.

**Bad (DO NOT DO THIS):**
```yaml
slot_banks:
  case:
    - topic_term: "learn python"
      user_message: "Hey, how do I learn python?"
      assistant_response: "Sure. Here are 10 bullets..."
```

**Good (required):**
```yaml
slot_banks:
  case:
    - topic_domain: "programming"
      topic_term: "Python"
      goal_inf: "learn Python as a beginner"
      scenario_hint: "I have 20 minutes a day"
      constraint_hint: "I want a practical path, not theory-heavy"
      desired_outcome: "I can build small scripts confidently"
      risk_hint: "I keep jumping between tutorials"
      skill_level: "beginner"
      timebox: "2 weeks"
      expert_concepts: ["variables", "functions", "lists/dicts", "debugging", "reading errors"]
      expert_moves: ["set up Python + editor", "do 3 tiny scripts", "use print/debugger", "read stack traces", "practice daily"]
      expert_pitfalls: ["tool-hopping", "copy-paste without understanding", "skipping error-reading"]
      expert_checks: ["can write a script without a tutorial", "can fix a simple error", "can explain what code does"]
      expert_tools: ["use a linter", "use a REPL", "use a small project repo"]
```

### A2) `slot_banks.case` contains `user_message:` anywhere (Lane 03 and any strict-dup lane)
For strict duplication lanes, prewriting user messages inside case reduces question diversity and increases overlap pairs.
Store only semantic atoms in `case`. Build the final `user_message` in `q_template`.

---

## B) Lane 03 (Think Mode) REQUIRED slot wiring (non-optional)

### B1) `expand_dict_slots` must NOT be only `case`
Minimum required:
```yaml
template_expand:
  expand_dict_slots:
    - case
    - q_template
    - a_skeleton
    - label_pack
```

### B2) `q_template` must be responsible for producing the final `user_message`
Each `q_template` dict must output a **rendered** `user_message` string and may reference:
- `{q_opening}`, `{q_followup}`, `{q_context_wrap}`, `{entity_pack}` and any `case` atoms.

Example:
```yaml
slot_banks:
  q_template:
    - user_message: "{q_opening} {q_frame} {goal_inf}. {q_context_wrap} {q_followup}?"
```

### B3) `a_skeleton` must be responsible for producing the final `assistant_response`
Each `a_skeleton` dict must output a **rendered** `assistant_response` string that:
- reads like “Think-mode” (implicit reasoning, no Step 1/2/3),
- has high structural diversity (≥ 15 skeleton families),
- does NOT reuse the same boilerplate phrases.

Example:
```yaml
slot_banks:
  a_skeleton:
    - assistant_response: "{a_opening}. {a_summary_frame}\n\n- {bullet1}\n- {bullet2}\n- ...\n\n{a_suggestion}\n{a_close}"
```

---

## C) QC preflight (run before gate; catches the common failure instantly)

From repo root:

### C1) Confirm case bank has NO rendered text
```bash
grep -n "slot_banks:\|case:\|assistant_response:\|user_message:" -n lanes/lane_03_think_mode/lane_en.yaml
```
You should see `assistant_response:` and `user_message:` only under `q_template` / `a_skeleton` / `row_template`, **never inside** the `case:` list.

### C2) Confirm expand_dict_slots includes q_template + a_skeleton
```bash
grep -n "expand_dict_slots" -n lanes/lane_03_think_mode/lane_en.yaml
```

---

## D) Why this addendum exists (one sentence)
Strict external duplication checks fail when “diversity” is only surface rewrites; structural diversity requires `case` to be atoms and `assistant_response` to be assembled via many skeleton families.



---

# ADDENDUM (STRICT QC) — How to beat “max‑sup” duplication in Lane 03 + Lane 04

Your reported failure mode (“external-style strict duplication pairs”) means:
- average diversity is OK,
- but **worst‑case pairs** still share too many tokens/bigrams.

This is solved by reducing **shared boilerplate** and injecting **high‑cardinality, topic‑specific anchors** into multiple parts of every sample.

## 1) Remove global boilerplate (critical)
For Lane 03/04, do **NOT** use any “universal bullets” that appear verbatim across topics (e.g., “Define success in one sentence”).
Those lines create high O_min overlap across many samples.

**Rule:** ≥ 70% of tokens in assistant_response must come from:
- case topic words (`topic_term`, `goal_inf`, `expert_concepts`, etc.)
- high-cardinality context (`timebox`, `budget`, `device_hint`, `audience_hint`, etc.)

## 2) Add a high‑cardinality `context_pack` and reference it repeatedly
Create a slot bank `context_pack` with **>= 200 items per language file**.

Each item is a dict with:
- `timebox` (20–40 variants)
- `budget` (20–40 variants)
- `device_hint` (15–25 variants)
- `audience_hint` (15–25 variants)
- `constraint_hint` (short, general; 30–60 variants)
- `desired_outcome` (short; 30–60 variants)

**Hard rule:** In every assistant_response, include at least:
- 2 mentions of `timebox` or `budget` (in different sentences/bullets)
- 2 mentions of `device_hint` or `audience_hint`
This spreads unique tokens across the response and lowers worst‑case overlap.

## 3) Use `bullet_pack` dicts (avoid reusing the same bullet sentences)
Instead of 10 fixed bullet templates, create a dict slot bank `bullet_pack` with **>= 300 items per language**.

Each `bullet_pack` item provides:
- `b1`..`b10` (Lane 03) or `b1`..`b5` (Lane 04)
and each bullet must include at least one case‑anchored term:
- `{topic_term}` OR one of `{expert_concepts}` expanded into a flat field like `{concept_1}`..`{concept_7}`

This forces structural diversity and prevents repeated sentence-level overlap.

## 4) Lane‑specific structure rules (don’t reuse Lane 03 patterns in Lane 04)

### Lane 03 (Think Mode)
- Output length can be longer.
- Must satisfy: ≥60% implicit multi‑step reasoning.
- Must satisfy: ≤5% share the same high‑level structure.

**Implementation requirement:**
- Provide **>= 25** `a_skeleton` families (not 10–15).
- Each family must use **different connective phrases** and **different ordering**:
  - some: tradeoffs → plan → checks
  - others: risks → baseline → upgrade path
  - others: quick win → validate → extend
- Do NOT use “First/Second/Third” anywhere.

### Lane 04 (Quick Mode)
- Must satisfy token caps (≥70% ≤120 tokens; ≥30% ≤60 tokens).
- A “10 bullets + long summary” style causes similarity collapse.
- Quick mode must vary by **presentation**, not long structure.

**Implementation requirement:**
- Provide **>= 40** `a_skeleton` families, but each is SHORT:
  - 1 paragraph definition + 1 example sentence
  - 2–3 bullets only
  - “Do/Don’t” micro-list
  - analogy-first, example-first, definition-first variants
- Each response must include at least one “anchor” token (from case/context/entity) to break overlap.

## 5) Thai + Hindi repetition gate (triplicates in windows)
Your failure notes mention residual repetition in `th` and `hi`.
This is NOT “duplication” — it’s the repetition/naturalness gate (§5A–5C Equator v3).

**Rules to avoid triplicate token/bigram:**
- Do not repeat the same pronoun (Thai “คุณ”, Hindi “आप”) more than once per sentence.
- Avoid repeating short particles/conjunctions 3× in 12-word windows.
- Vary clause starts; avoid templates like:
  - “คุณ… คุณ… คุณ…”
  - “आप… आप… आप…”

**Practical fix:**
Create 3 writing styles per language:
- imperative/no-pronoun (“Try…, Focus on…, Keep…”)
- second-person but sparse
- first-person neutral (“If I were doing this…”)
and randomly sample style.

## 6) Mandatory self-checks before any QC submission
Run these on the generated `train.jsonl` for Lane 03 and Lane 04:

1) Top repeated bigrams/trigrams (should not be dominated by a single phrase).
2) Opening-family frequency (no family >8% when n>=100).
3) Repetition windows for `th` and `hi` (no triplicate content tokens; no repeated bigrams 3× in 30 window).

If you cannot run a script, do a quick grep spot-check:
- search for a recurring phrase you see often; if it appears dozens of times in 60 rows, you will fail max‑sup duplication.



---

# ADDENDUM (QUALITY + STRICTDUP) — Ban “field-dump” outputs (this is causing your O_min explosions)

The following failure pattern is **proven** from your EN duplicate pair:

> "Reduce quality improvement plan to a single executable cut. Timebox … stable plan. … 45m. … $30k. … in-store kiosks."

This is not “Think mode.” It is a **field dump**: short clauses separated by periods.  
It creates **high max-sup overlap** because:
- responses are too short (small denominator → O_min spikes), and
- they reuse the same generic tokens (“plan”, “timebox”, “review”, “team”, “pressure”, “check whether”).

**Therefore, field-dump outputs are banned for Lane 03 and Lane 04.**

## 1) HARD RULE — No “one-field-per-sentence” output
Disallowed pattern:
- sentence 1: action fragment
- sentence 2: `Timebox {timebox}.`
- sentence 3: `{scenario_hint}.`
- sentence 4: `{audience_hint}.`
- sentence 5: `{budget}.`
… etc

If you do this, strictdup will fail even with huge context_pack/bullet_pack.

## 2) Lane 03 required response shape (must be longer to pass max-sup)
For Lane 03 (mode="think"):
- Target: **140–220 tokens** typical (English; scale similarly in other languages)
- Must include: **2–3 full sentences** of reasoning, then **6–10 bullets**, then **1 next action**
- No “Step 1/2/3”; avoid “First/Second/Third”.

**Implementation:** enforce representation_choice = `bullet_list` for Lane 03 (recommended).
In `label_pack`, set:
- `representation_choice: bullet_list` for >=80% of rows
- allow `plain_text` for <=20% (but still long enough)

### Minimal Lane 03 skeleton (example)
Each `a_skeleton` must produce something like:
- reasoning paragraph that references 2+ case/context anchors **in the same sentence**
- bullets that mix moves/pitfalls/checks (not generic “define success” advice)
- closing next action tied to timebox

Example `assistant_response` template (you will implement your own phrasing variants):
- `{a_opening} {reason_sentence_1} {reason_sentence_2}`
- `- {b1}`
- `- {b2}`
...
- `Next action: {next_action}`

**Key:** bullets must be *contentful sentences*, not noun fragments.

## 3) Lane 04 required response shape (short, but still not a field dump)
For Lane 04 (mode="quick"):
- Must stay within lane token caps.
- Use **micro-formats** that are naturally different across skeleton families:
  - 1 sentence + 2 bullets
  - Do/Don’t
  - “If… then…” + 1 example
  - 3 short bullets only
- Must include at least **one** high-cardinality anchor (topic or entity) per response.

Field dumps are still banned.

## 4) How to make bullets “expert” without causing overlap
### 4A) Remove global boilerplate
Do not include generic lines that work for every topic (“define success”, “iterate”) unless they are rewritten into topic-specific language using case atoms.

### 4B) Add topic anchors to every bullet
For Lane 03:
- each bullet must include at least one of:
  - `{topic_term}` OR `{concept_1..concept_7}` OR `{move_1..move_10}` OR `{pitfall_1..pitfall_5}` OR `{check_1..check_5}`
- avoid bullets that contain only `{timebox}`/`{budget}` without a topic anchor

## 5) Mandatory local sanity test (before running strictdup)
Generate 60 EN rows and verify:
- at least 50/60 have >= 140 tokens (rough check: they span multiple lines + bullets)
- no line looks like “field.field.field.” fragments
- at least 6 bullets present in bullet_list rows

If this fails, do not proceed to strictdup.

---

## 6) Why this is necessary (one sentence)
Max-sup duplication checks punish short, template-like responses; longer, topic-anchored bullet reasoning reduces shared-token containment and improves real training quality.

---

**Important note**: This addendum is universal in mechanism, but not universal in the exact thresholds/output shape. Lane-specific must refer to lane spec. 


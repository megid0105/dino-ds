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


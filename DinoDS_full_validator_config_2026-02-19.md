# Effective Validator Spec (Code-True, Current Repo State)

Sources used for this mapping:
- `src/dino_ds/contracts/v16_lane_contracts.py`
- `src/dino_ds/validators/row_validator_v16.py`
- `src/dino_ds/validators/v17_lane_validator.py`
- `src/dino_ds/validators/generation_validator.py`
- `src/dino_ds/validators/turn_structure_invariant_v17.py`
- `src/dino_ds/validators/malformed_gate_v41.py`
- `src/dino_ds/validators/repetition_gate_v41.py`
- `src/dino_ds/validators/duplication_gate_v41.py`
- `src/dino_ds/validators/master_crossfield_rules_v2.py`
- `src/dino_ds/validators/master_tool_budget_rules_v2.py`
- `src/dino_ds/validators/status_event_validator_v2.py`
- `src/dino_ds/validators/safety_content_gate_v17.py`
- `src/dino_ds/validators/user_assistant_overlap_v17.py`
- `src/dino_ds/validators/lane_policy_v17.py`

All examples below are partial row snippets focused on the specific check (assume other required fields are valid unless shown).

---

## 1) Global pipeline that is actually enforced

- Default rule profile is `03` (strictest) if `--rule` is not provided.
- Gate order in `validate_generated_rows(...)` is:
  - `invariants -> malformed -> repetition -> leakage -> duplication -> proportions -> viability -> warn_only`
- Fatal short-circuit is active:
  - If a row fatals in invariants/malformed/repetition/leakage, it does not proceed to later gates.
  - Rows that fail duplication are removed before proportions/viability.

---

## 2) Global validations (apply to all lanes unless skipped by policy)

### 2.1 Row schema + required labels (row validator)
- Required keys: 18 keys including `messages`, `user_message`, `assistant_response`.
- Required label keys: 15 keys.
- Unknown top-level fields are forbidden (`unknown_field_forbidden:<key>`).
- Allowed top-level keys count: `40` (includes `target_base`; excludes `lane` / `_lane`).
- Language integrity check is enforced: `row.language == expected lane language slice` unless exempt list (currently empty).

Good:
```json
{"lane_id":"lane_03_think_mode","language":"en","target_base":"dino_qwen4b"}
```

Bad:
```json
{"lane_id":"lane_03_think_mode","language":"en","foo":1}
```
Fails: `unknown_field_forbidden:foo`

---

### 2.2 Status event schema (optional field)
- If `status_event` exists, strict schema is enforced:
  - Required: `phase`, `note`, `route`
  - Allowed keys only: `phase`, `note`, `route`, `tokensSoFar`, `sourcesCount`
  - `phase` in `{parse, plan, retrieve, compose, finalize}`
  - `route` in `{slm, cloud}`
  - `note` single-line, non-empty, `<=200` chars, no reasoning leakage text

Good:
```json
{"status_event":{"phase":"compose","route":"slm","note":"drafting response","tokensSoFar":120}}
```

Bad:
```json
{"status_event":{"phase":"think","route":"slm","note":"step 1 reasoning..."}}
```
Fails: `status_event_phase_invalid` (and/or `status_event_reasoning_leakage`)

---

### 2.3 Master cross-field safety/profanity rule
- `profanity_allowed=true` requires `adult_gate=true` and `tone="best_friend"`.
- Also explicit inconsistency check: `adult_gate=false` + `profanity_allowed=true`.

Good:
```json
{"adult_gate":true,"tone":"best_friend","profanity_allowed":true}
```

Bad:
```json
{"adult_gate":true,"tone":"friendly","profanity_allowed":true}
```
Fails: `profanity_requires_adult_gate_and_best_friend`

---

### 2.4 Master tool budget rules
- `tool_budget` (if present):
  - object with only `searches`, `reads`, `seconds`
  - ranges: `searches 0..1`, `reads 0..3`, `seconds 0..30`
- Tool call argument limits:
  - `tool_call.arguments.max_reads 0..3`
  - `tool_call.arguments.max_seconds 0..30`
- Observed call limits per row:
  - `web_fetch <= 1`
  - `web_read <= 3`
- If `tool_budget` provided, observed usage must not exceed it.

Good:
```json
{"tool_budget":{"searches":1,"reads":3,"seconds":30},"tool_call":{"name":"web_fetch","arguments":{"max_seconds":10}}}
```

Bad:
```json
{"tool_budget":{"searches":0},"tool_call":{"name":"web_fetch","arguments":{}}}
```
Fails: `tool_budget_searches_exceeded`

---

### 2.5 Enum checks + lane enum overrides
- Global enums enforced on 21 schema fields (mode/tone/language/etc.).
- Lane overrides allowed with warn:
  - warning code `lane_enum_override_used`
- Invalid enum values fail:
  - `enum_value_not_allowed:<field>`

---

### 2.6 Turn structure hard invariant
- `messages` must be non-empty list of objects.
- Each message needs string `role` and string `content`.
- Roles allowed: `system`, `user`, `assistant`.
- Must include exactly one `system`, and it must be first.
- Non-system sequence must start with `user`, end with `assistant`, strict alternation.
- No label keys allowed inside `messages[*]` (e.g. `mode`, `tone`, `needs_search`, etc.) -> `message_label_key_forbidden`.
- Turn-count policy enforced from lane contract:
  - single-turn lanes: exactly 2 non-system messages
  - allow_multiturn lanes: at least 2
  - requires_multiturn lanes: min from contract (none currently set true)

Good:
```json
{"messages":[{"role":"system","content":"..."},
{"role":"user","content":"U1"},
{"role":"assistant","content":"A1"}]}
```

Bad:
```json
{"messages":[{"role":"user","content":"U1"},{"role":"assistant","content":"A1"}]}
```
Fails: `missing_messages` (system first required)

---

### 2.7 Message alignment invariant
- If `messages` exists:
  - `user_message` must equal the last user turn content
  - `assistant_response` must equal the last assistant turn content

Bad example:
```json
{"messages":[{"role":"system","content":"..."},
{"role":"user","content":"U1"},{"role":"assistant","content":"A1"},
{"role":"user","content":"U2"},{"role":"assistant","content":"A2"}],
"user_message":"U1","assistant_response":"A2"}
```
Fails: `messages_alignment`

---

### 2.8 Placeholder marker invariant
- Template placeholders are fatal in `user_message` and `assistant_response`.
- Regex includes forms like `[PLACEHOLDER]`, `<<...>>`, `{slot...}`.

Bad:
```json
{"assistant_response":"Use <<CITY_NAME>> for this step."}
```
Fails: `placeholder_marker`

---

### 2.9 Malformed gate v4.1 (rule profile >=2)
- Skipped for lanes with `assistant_response_must_be_empty` and code-only lane policy.
- Character fragmentation fatal (`character_fragmentation_fatal`):
  - Latin + Hindi only
  - token count `>=12`
  - single-char ratio `>=0.55`
- Script corruption fatal (`script_corruption_fatal`):
  - total letters `>=40`
  - unexpected-script ratio `>0.20`
  - CJK/TH excludes structured Latin spans (URL, date, JSON keys, chart keys) from ratio.
- Lane 22 special scope:
  - malformed script check applies only to `user_message`, not `assistant_response`.

---

### 2.10 Repetition gate v4.1 (assistant only)
- Skipped for empty-assistant lanes.
- Code-only lanes: only adjacent duplicate token check on code-safe tokens.
- Normal lanes:
  - adjacent duplicate token -> fatal `adjacent_dup_token`
  - trip token in rolling `W=12`:
    - content token -> fatal `trip_token_content`
    - function-word only -> warn `trip_token_function_only`
  - trip bigram in rolling `W=30`:
    - content -> fatal `trip_bigram_content`
    - function-word only -> warn `trip_bigram_function_only`
- TH/CJK/JA/KO/HI/VI tokenization follows carveout-style behavior (word or char bi/tri-gram fallback; no raw single-char triggering style).

Good:
```json
{"assistant_response":"Use option A, then compare it with option B."}
```

Bad:
```json
{"assistant_response":"by by we should proceed"}
```
Fails: `adjacent_dup_token`

---

### 2.11 Leakage gate (non-code lanes)
- Fatal `mechanism_leakage` when assistant text matches internal mechanism regex (`tool_call`, `schema`, etc.).
- Skipped for code-only lane policy.

---

### 2.12 Duplication gate v4.1 (rule profile >=3)
- Exact normalized duplicate checks:
  - `duplicate_user_message`
  - `duplicate_assistant_response`
- Pairwise near-dup:
  - candidate: `O_min > candidate_threshold` (default `0.30`)
  - non-carveout confirm:
    - Rule1 `O_min > 0.55` OR Rule2 (2-of-3 signals)
    - Rule2 thresholds: `O_min>candidate`, `O_jac>0.38`, `C3>0.26`
  - carveout langs `th/cjk/ja/ko/hi/vi`:
    - no raw containment-only fail
    - confirm via Rule2 with `C3>0.30`, or `(O_min>0.55 and C3>0.30)`
    - tiny-span guard: pair is skipped for confirmation when min token span `< 3`
    - `hi/vi` language-tag variants (for example `hi-IN`, `vi-VN`) are treated as carveout too
  - Hindi override: if candidate but `C3<0.20`, downgrade to warn candidate-only
- Fatal code: `near_duplicate_overlap`
- Warn code: `dup_candidate_unconfirmed`
- Opening-family diversity fatal:
  - if n>=100 and top opening share > cap (default `0.08`): `opening_diversity`

---

### 2.13 Proportion/slice gate framework
- Reliability floor:
  - most slice gates use `n>=30`
  - under 30 => warn-only (`*_not_reliable_small_n`)
- Mode/tone proportion tolerance:
  - deviation `<=15%` pass
  - `>15% and <21%` warn
  - `>=21%` fail `proportion_out_of_tolerance`

---

## 3) Lane-by-lane effective checks (1..37)

### Lane 01 `lane_01_identity`
- Fixed values enforced: `mode=quick`, `emote6=neutral`, `representation_choice=plain_text`, `continuity_choice=suppress_continuity`, `intent_family in {safety, content_generation}`, `intent_subtype in {identity_definition, boundary_setting, leakage_prevention}`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 checks: mode/representation rechecked.
- Tool policy: tool calls forbidden.
- Slice gate: mode/tone target applies.
  - mode target: quick `1.00`
  - tone target: each of 5 tones `0.20`
- Good: `{"mode":"quick","representation_choice":"plain_text","needs_search":false}`
- Bad: `{"mode":"think"}` fails `v17_fixed_value_violation:mode` (generation path prefix).

### Lane 02 `lane_02_tone_behaviour_foundation`
- Fixed values: `mode in {quick, think}`, `emote6=neutral`, `representation_choice=plain_text`, `continuity_choice=suppress_continuity`, `intent_family in {content_generation,safety}`, `intent_subtype in {tone_behavior,boundary_setting,correction_style}`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 checks: mode in quick/think and representation plain_text.
- Tool policy: tool calls forbidden.
- Slice gate: mode/tone target applies.
  - mode: quick `0.50`, think `0.50`
  - tone: each tone `0.20`
- Good: `{"mode":"think","representation_choice":"plain_text"}`
- Bad: `{"needs_search":true}` fails fixed value.

### Lane 03 `lane_03_think_mode`
- Turn contract: `allow_multiturn=true`, min non-system messages `>=2`.
- Fixed values: `mode=think`, `emote6=neutral`, `representation_choice in {plain_text,bullet_list,comparison_table,chart_spec,document_spec}`, `continuity_choice=suppress_continuity`, `intent_family in {decision_support,planning,content_generation}`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: optional tool call allowed.
  - max one total call object across `tool_call`/`tool_calls`
  - allowed tool names: `connector_action, web_fetch, web_read, image_preview, export_document, ingest, zip_list, ingest_zip, history_search`
- Slice gates:
  - mode target think `1.00`
  - optional share caps: tool_call <= `0.10`, image_context <= `0.05`
  - reasoning distribution: implicit multi-step >= `0.60`; top structure share <= `0.05`
- Good: `{"mode":"think","tool_call":{"name":"web_read","arguments":{}}}`
- Bad: `{"tool_calls":[{"name":"web_fetch"},{"name":"web_read"}]}` fails `v17_tool_call_too_many`.

### Lane 04 `lane_04_quick_mode`
- Fixed values: `mode=quick`, `emote6=neutral`, `representation_choice in {plain_text,bullet_list}`, `continuity_choice=suppress_continuity`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: optional tool call allowed with same lane03 allowed-tool set, max one call.
- Slice gates:
  - mode target quick `1.00`
  - optional caps: tool_call <= `0.05`, image_context <= `0.03`
  - answer length shares: <=120 tokens >= `0.70`; <=60 tokens >= `0.30`
- Good: `{"mode":"quick","representation_choice":"bullet_list"}`
- Bad: `{"representation_choice":"chart_spec"}` fails fixed value.

### Lane 05 `lane_05_conversation_mode`
- Turn contract: `allow_multiturn=true`.
- Fixed values: `mode=conversation`, `emote6=neutral`, `representation_choice=plain_text`, `continuity_choice=suppress_continuity`, `intent_family in {content_generation,safety}`, `intent_subtype in {emotional_support,light_chat,check_in}`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Slice gates:
  - mode target conversation `1.00`
  - optional image_context cap <= `0.02`
  - multiturn share >= `0.60`
  - emotional callback share >= `0.40`
- Important effective behavior: emotional callback detector prefers `callback_type=="emotional"` but strict top-level schema currently disallows `callback_type`, so fallback path is `continuity_choice=="use_continuity"`; fixed value currently enforces `suppress_continuity`.
- Good row-level: `{"mode":"conversation","continuity_choice":"suppress_continuity"}`
- Bad row-level: `{"mode":"quick"}` fails fixed value.

### Lane 06 `lane_06_general_intent_classification`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 check: `connector_needed` / `deeplink_needed` fields forbidden.
- Tool policy: tool calls forbidden.
- Good: `{"needs_search":false}`
- Bad: `{"connector_needed":true}` fails `v17_forbidden_trigger_fields`.

### Lane 07 `lane_07_search_triggering`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 checks:
  - `needs_search` must be boolean (true or false)
  - `needs_history_search=false`
- Tool policy: tool calls forbidden.
- Slice gates:
  - borderline share >= `0.40`
  - `needs_search=true` target `0.50` with ± bands:
    - <=15% pass
    - 15-20% warn
    - >=21% fail
- Good: `{"needs_search":true,"needs_history_search":false}`
- Bad: `{"needs_search":"true"}` fails `v17_needs_search_required`.

### Lane 08 `lane_08_search_integration`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_search=true`, `needs_history_search=false`, `history_scope=thread_only`.
- Policy: `tool_call` required; citations required.
- Tool-call name restricted by lane v17: `web_fetch` or `web_read`.
- Assistant required and must include citation token like `[1]`.
- Lane-specific leakage regex forbids internal terms in assistant.
- Good:
```json
{"tool_call":{"name":"web_fetch","arguments":{"query":"x"}},
"assistant_response":"From the provided results [1], ...","needs_search":true}
```
- Bad:
```json
{"tool_call":{"name":"web_fetch","arguments":{"query":"x"}},
"assistant_response":"Result is clear without citation."}
```
Fails: `citations_required` (row validator) / `v17_citation_required` path.

### Lane 09 `lane_09_multi_step_action_flow`
- Turn contract: `allow_multiturn=true`.
- Fixed values: `continuity_choice=suppress_continuity`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 check: `flow_state` required non-empty.
- Tool policy: tool calls forbidden.
- Slice gate (n>=30): flow_state target distribution:
  - `none 0.30`
  - `awaiting_user_confirmation 0.20`
  - `awaiting_user_choice 0.20`
  - `awaiting_parameters 0.15`
  - `ready_for_action 0.15`
- Good: `{"flow_state":"awaiting_parameters"}`
- Bad: `{"flow_state":""}` fails `v17_flow_state_required`.

### Lane 10 `lane_10_connector_intent_detection`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Required label key: `connector_needed`.
- Lane v17 checks:
  - `connector_needed` must be bool
  - mapping labels forbidden (`connector_action`, `deeplink_action`, `image_tool_action`)
- Tool policy: tool calls forbidden.
- Slice gate: borderline share >= `0.40` (n>=30).
- Good: `{"connector_needed":true}`
- Bad: `{"connector_action":"email_composeEmail"}` fails `v17_mapping_label_forbidden`.

### Lane 11 `lane_11_connector_action_mapping`
- Required label key: `connector_action`.
- Mapping lane rules enforce:
  - assistant must be empty (`""` or `" "`)
  - exactly one action label (`connector_action`) and no other non-empty action labels
  - no `parameters`/`slots`
- Lane v17:
  - connector canonical label check (when master action label set loads)
- Tool policy: tool calls forbidden.
- Good:
```json
{"assistant_response":"","connector_action":"email_composeEmail"}
```
- Bad:
```json
{"assistant_response":"drafted mail","connector_action":"email_composeEmail"}
```
Fails: `assistant_response_not_empty` / `v17_assistant_must_be_empty`.

### Lane 12 `lane_12_deeplink_action_mapping`
- Required label key: `deeplink_action`.
- Mapping rules same structure as lane11.
- Lane v17 canonical deeplink label check (when label set loads).
- Good:
```json
{"assistant_response":"","deeplink_action":"maps_openDirections"}
```
- Bad:
```json
{"assistant_response":"","deeplink_action":"foo_bar","connector_action":"email_composeEmail"}
```
Fails: canonical label and/or `multiple_action_labels`.

### Lane 13 `lane_13_doc_export_spec`
- Fixed values: `representation_choice=document_spec`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Policy: tool_call required; assistant must be exactly empty string `""`.
- Lane v17 schema-locked tool_call:
  - no `tool_calls` array
  - no extra keys outside:
    - `tool_call.{name,arguments}`
    - `arguments.{format,document_spec}`
    - `document_spec.{title,sections,style}`
    - `sections[*].{heading,body}`
  - `tool_call.name == "export_document"`
  - non-empty required doc fields and sections
- Good:
```json
{"representation_choice":"document_spec","assistant_response":"",
"tool_call":{"name":"export_document","arguments":{"format":"md",
"document_spec":{"title":"T","sections":[{"heading":"H","body":"B"}],"style":"clean"}}}}
```
- Bad:
```json
{"assistant_response":"","tool_call":{"name":"export_document","arguments":{"format":"md","filetype":"pdf"}}}
```
Fails: `v17_tool_call_extra_keys_forbidden`.

### Lane 14 `lane_14_zip_wrap_spec`
- Fixed values: `representation_choice=zip_spec`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Policy: tool_call required; assistant must be exactly `""`.
- Lane v17 schema-locked zip tool_call:
  - no `tool_calls` array
  - key lock:
    - `tool_call.{name,arguments}`
    - `arguments.{zip_items}`
    - `zip_items[*].{filename,content}`
  - `tool_call.name == "zip_list"`
  - `zip_items[0].filename == "manifest.md"`
  - manifest content list must exactly match subsequent filenames in order
- Good: valid `zip_items` with manifest first and exact listing.
- Bad: extra key `filetype` anywhere under tool_call.
Fails: `v17_tool_call_extra_keys_forbidden`.

### Lane 15 `lane_15_code_generation`
- Fixed values: `representation_choice=plain_text`, `intent_family=content_generation`, `intent_subtype=code_generation`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Policy: tool_call forbidden, code-only assistant.
- Lane v17 format check:
  - exactly one fenced code block
  - no prose before/after
  - backtick count must be exactly 2 fences
- Repetition in this lane: only adjacent code-token duplicate check.
- Mechanism leakage gate skipped for code-only policy.
- Good:
```text
```python
print("ok")
```
```
- Bad:
```text
Here is code:
```python
print("ok")
```
```
Fails: `v17_codeblock_only`.

### Lane 16 `lane_16_code_json_spec_mode`
- Fixed values: `representation_choice=plain_text`, `intent_subtype=code_json_spec`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: forbidden.
- Lane v17 JSON-only strict format:
  - valid JSON object
  - exact root key order: `("task_type","language","files","constraints","tests")`
  - `files` non-empty array of objects with exact key order `("name","purpose","exports")`
  - no code fences
- Good:
```json
{"task_type":"code","language":"python","files":[{"name":"main.py","purpose":"entry","exports":["run"]}],"constraints":[],"tests":[]}
```
- Bad:
```json
{"language":"python","task_type":"code","files":[],"constraints":[],"tests":[]}
```
Fails: `v17_json_only` (wrong key order and empty files).

### Lane 17 `lane_17_comparison_tables`
- Fixed values: `representation_choice=comparison_table`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: forbidden.
- Lane v17 table-only check:
  - all non-empty lines must be table rows (`|...|`)
  - second line must be markdown separator.
- Good:
```markdown
| Option | Cost |
|---|---|
| A | 10 |
```
- Bad:
```markdown
Here is a table:
| Option | Cost |
|---|---|
| A | 10 |
```
Fails: `v17_markdown_table_only`.

### Lane 18 `lane_18_chart_spec`
- Fixed values: `representation_choice=chart_spec`, `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: forbidden.
- Lane v17 chart_spec-only check:
  - starts with `chart_spec:`
  - required keys present: `type,title,goal,series,style,notes`
  - must include either `x_axis/y_axis` or `legend`
  - deterministic key order constraint enforced.
- Good:
```yaml
chart_spec:
  type: bar
  title: T
  goal: G
  x_axis:
    label: X
  y_axis:
    label: Y
  series:
    - name: S
      data: [1,2]
  style:
    theme: clean
  notes: n
```
- Bad: missing `notes` or wrong order.
Fails: `v17_chart_spec_only`.

### Lane 19 `lane_19_continuity_decision`
- Fixed values: `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Tool policy: forbidden.
- Lane v17 continuity check:
  - if `continuity_choice=="use_continuity"`, first system message should include `CONTEXT` marker.
- Good: use continuity with system content containing `CONTEXT`.
- Bad: use continuity without `CONTEXT`.
Fails: `v17_continuity_context_missing`.

### Lane 20 `lane_20_continuity_execution`
- Fixed values: `emote6=neutral`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 checks repeat those booleans/history scope.
- Tool policy: forbidden.
- Slice gate: prior-content-reference share >= `0.60` at `n>=30`.
- Good slice: `n=30`, `18` rows match prior-reference heuristics.
- Bad slice: `n=30`, `10` rows match.
Fails: `lane20_prior_content_reference_share_too_low`.

### Lane 21 `lane_21_rewrite`
- Fixed values: `intent_family=content_generation`, `intent_subtype=rewrite`, `continuity_choice=suppress_continuity`, `emote6=neutral`, search/history false, `history_scope=thread_only`.
- Overlap gate: user-assistant `O_min <= 0.70` with script-aware tokenization.
- Carveout tiny-span guard: for `th/cjk/ja/ko/hi/vi`, overlap fail is skipped when min token span `< 3`.
- Tool policy: forbidden.
- Good: user text rewritten with moderate overlap.
- Bad: near-copy user==assistant.
Fails: `v17_user_assistant_overlap_too_high`.

### Lane 22 `lane_22_translate`
- Fixed values: `intent_family=content_generation`, `intent_subtype=translate`, `continuity_choice=suppress_continuity`, `emote6=neutral`, search/history false, `history_scope=thread_only`.
- Overlap gate: `O_min <= 0.20`.
- Carveout tiny-span guard: for `th/cjk/ja/ko/hi/vi`, overlap fail is skipped when min token span `< 3`.
- Malformed gate special: assistant script is not checked against `row.language` (source-language lane behavior).
- Tool policy: forbidden.
- Good: EN user -> ZH assistant.
- Bad: assistant identical to user.
Fails: `v17_user_assistant_overlap_too_high`.

### Lane 23 `lane_23_grammar_fix`
- Fixed values: `intent_family=content_generation`, `intent_subtype=grammar_fix`, `continuity_choice=suppress_continuity`, `emote6=neutral`, search/history false, `history_scope=thread_only`.
- Overlap gate: `O_min <= 0.80`.
- Carveout tiny-span guard: for `th/cjk/ja/ko/hi/vi`, overlap fail is skipped when min token span `< 3`.
- Tool policy: forbidden.
- Good: corrected sentence with some overlap.
- Bad: exact copy at high overlap.
Fails: `v17_user_assistant_overlap_too_high`.

### Lane 24 `lane_24_history_search_trigger`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_search=false`.
- Lane v17 checks:
  - `needs_history_search` must be bool (not fixed to true/false)
  - `history_scope` in `{thread_only, all_threads}`
- Tool policy: forbidden.
- Good: `{"needs_history_search":true,"history_scope":"all_threads"}`
- Bad: `{"history_scope":"none"}`
Fails: `v17_history_scope_invalid`.

### Lane 25 `lane_25_history_search_integration`
- Fixed values: `emote6=neutral`, `needs_search=false`, `needs_history_search=true`.
- Tool policy: forbidden.
- Lane v17:
  - `needs_history_search=true` required
  - history grounding heuristic:
    - if assistant claims prior-history and overlap to snippets < `0.10` -> fail
    - numeric memory claims absent from snippets -> fail
- Good: assistant cites facts present in retrieved snippets.
- Bad: assistant claims “you said 9:30” when snippets do not contain that numeric claim.
Fails: `v17_history_snippet_grounding_missing`.

### Lane 26 `lane_26_image_context_understanding`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17 checks:
  - `image_context` object required
  - if assistant makes visual assertion, object terms must be supported by `image_context`.
- Tool policy effectively forbidden by row validator default.
- Good: assistant mentions objects present in `image_context`.
- Bad: assistant says “I see a dog” while context has only cat/laptop.
Fails: `v17_image_context_grounding_violation`.

### Lane 27 `lane_27_image_tooling`
- Required label key: `image_tool_action`.
- Mapping rules + lane v17:
  - `image_context` required
  - assistant empty (`""` or `" "`)
  - `image_tool_action` in `{web_fetch, connector_action}`
  - no parameters/slots
- Tool policy forbidden.
- Good:
```json
{"assistant_response":"","image_tool_action":"web_fetch","image_context":{"summary":"..."}}
```
- Bad:
```json
{"assistant_response":"","image_tool_action":"zip_list"}
```
Fails: `v17_image_tool_action_required`.

### Lane 28 `lane_28_emote6_labeling`
- Fixed values: `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17: assistant must be empty (`""` or `" "`).
- Tool policy forbidden.
- Slice gate: each emote6 bucket share >= `0.10` at `n>=30`.
- Good row: `{"assistant_response":"","emote6":"happy"}`
- Bad row: `{"assistant_response":"happy"}` fails `v17_assistant_must_be_empty`.
- Bad slice: one emote bucket at 0%.
Fails: `lane28_emote6_out_of_tolerance`.

### Lane 29 `lane_29_safety_history_politics`
- Fixed values: `intent_family=safety`, `intent_subtype in {history_accuracy, politics_accuracy}`, `safety_tag in {politics_sensitive, history_sensitive}`, `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17 repeats intent_family/search/history/history_scope checks.
- Tool policy: forbidden.
- Slice gate: misinformation-correction share >= `0.40` at `n>=30`.
- Good: assistant explicitly corrects false claim.
- Bad slice: correction share 0.20.
Fails: `lane29_misinfo_correction_share_too_low`.

### Lane 30 `lane_30_safety_no_leakage`
- Fixed values: `intent_family=safety`, `intent_subtype=leakage_prevention`, `safety_tag=leakage_attempt`, `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17: intent_family must be safety.
- Tool policy: forbidden.
- Slice gate: creative extraction attempt share >= `0.40` at `n>=30`.
- Effective note: detector falls back to `safety_tag=="leakage_attempt"`; with fixed value this strongly biases share to pass.
- Good: `{"safety_tag":"leakage_attempt"}`
- Bad: `{"safety_tag":"safe"}` fails `v17_fixed_value_violation:safety_tag`.

### Lane 31 `lane_31_mode_selection`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17: mode must be one of `{quick,think,conversation}`.
- Tool policy: forbidden.
- Good: `{"mode":"quick"}`
- Bad: `{"mode":"analysis"}` fails `v17_mode_required`.

### Lane 32 `lane_32_representation_choice`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17 format coupling:
  - representation required
  - assistant format must match representation:
    - `comparison_table` -> markdown table validator
    - `chart_spec` -> chart validator
    - `bullet_list` -> bullet-list validator
    - `plain_text` -> plain text validator
    - `document_spec` -> doc-spec hint validator
    - `zip_spec` -> zip-spec hint validator
- Tool policy: forbidden.
- Good:
```json
{"representation_choice":"bullet_list","assistant_response":"- a\n- b"}
```
- Bad:
```json
{"representation_choice":"comparison_table","assistant_response":"plain sentence"}
```
Fails: `v17_representation_mismatch`.

### Lane 33 `lane_33_fallback_behavior`
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, search/history false, `history_scope=thread_only`.
- Lane v17 checks:
  - needs_search false
  - needs_history_search false
  - history_scope thread_only
  - assistant required non-empty
- Tool policy: forbidden.
- Slice gate: fallback-limitation share >= `0.40` (regex-based from assistant text), `n>=30`.
- Good row: assistant includes limitation phrase like “it depends / limitations / alternative”.
- Bad row: empty assistant.
Fails: `v17_assistant_required`.
- Bad slice: limitation share 0.10.
Fails: `lane33_fallback_limitation_share_too_low`.

### Lane 34 `lane_34_cantonese_ability`
- Enum overrides enabled for lane:
  - `tone` allows `neutral`/`professional`
  - `history_scope` allows `none`
- Fixed values: `language=zh-hk`, `mode in {conversation,quick}`, `emote6=neutral`, `representation_choice=plain_text`, `continuity_choice=suppress_continuity`, `intent_family=qa_general`, `intent_subtype=general`, `safety_tag=safe`, `needs_search=false`, `needs_history_search=false`, `history_scope=none`, `tone in {neutral,professional}`.
- Lane v17 extra check:
  - for zh-hk/zh-hant rows, assistant should contain CJK characters (`cjk_missing` if absent).
- Tool policy: forbidden.
- Slice gates:
  - mode target quick `0.30`, conversation `0.70`
  - colloquial share >= `0.40`
  - code-switch share >= `0.20`
- Good: zh-hk assistant containing Cantonese/Han and light Latin code-switch.
- Bad: `{"language":"en"}` fails fixed value `v17_fixed_value_violation:language`.

### Lane 35 `lane_35_topic_hygiene`
- Enum override enabled for lane:
  - `intent_family` allows `hygiene`
- Fixed values: `intent_family=hygiene`, `intent_subtype in {stay_on_topic,scope_control,return_to_goal,gentle_boundary}`.
- Lane v17 repeats subtype set check.
- Tool policy: forbidden.
- Good: `{"intent_family":"hygiene","intent_subtype":"stay_on_topic"}`
- Bad: `{"intent_family":"qa_general"}` fails fixed value.

### Lane 36 `lane_36_custom`
- There is no explicit lane-36 contract entry and no lane-36 branch in `validate_row_v17`.
- Effective behavior is default/global only:
  - default single-turn turn structure
  - all global row/invariant/malformed/repetition/leakage/duplication checks
  - no lane-specific fixed values
  - tool_call forbidden by row validator default (no allow policy)
- Good: any row satisfying global schema and gates.
- Bad: row with unknown top-level field or tool_call.
Fails: e.g. `unknown_field_forbidden:*` or `tool_call_forbidden`.

### Lane 37 `lane_37_deeplink_intent_detection`
- Required label key: `deeplink_needed`.
- Fixed values: `emote6=neutral`, `continuity_choice=suppress_continuity`, `needs_search=false`, `needs_history_search=false`, `history_scope=thread_only`.
- Lane v17 checks:
  - `deeplink_needed` must be bool
  - `deeplink_action` must be absent/empty (mapping belongs lane12)
- Tool policy: forbidden.
- Good: `{"deeplink_needed":true}`
- Bad: `{"deeplink_needed":true,"deeplink_action":"maps_openDirections"}`
Fails: `v17_deeplink_action_forbidden`.

---

## 4) Format-sensitive checks summary (quick index)

- Empty assistant required:
  - lane 11, 12, 27, 28 (`""` or `" "`)
  - lane 13, 14 (must be exactly `""`)
- Codeblock only:
  - lane 15
- JSON only strict shape:
  - lane 16
- Markdown table only:
  - lane 17
- Chart spec only:
  - lane 18
- Representation-coupled formatter:
  - lane 32
- Tool_call schema-locked objects:
  - lane 13 (`export_document`)
  - lane 14 (`zip_list`)
- Citation-sensitive:
  - lane 8 requires citations
  - other lanes neutral by default unless explicit policy says otherwise

---

## 5) Multi-turn vs single-turn behavior (effective today)

- Contract-controlled in `turn_structure_invariant_v17`:
  - default: single-turn hard (`exactly 2` non-system messages: user->assistant)
  - `allow_multiturn=true`: lane can be 2 or more non-system turns (still alternating, start user, end assistant)
- Lanes with `allow_multiturn=true` currently:
  - lane 03
  - lane 05
  - lane 09
- `requires_multiturn=true` is currently not set for any lane contract.
- Additional slice-level multi-turn requirement:
  - lane 05 must have multiturn share >= `0.60` at language-slice level (`n>=30`).

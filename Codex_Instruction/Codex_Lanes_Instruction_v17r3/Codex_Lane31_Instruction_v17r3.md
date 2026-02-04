# Codex Lane Instruction — Lane 31 — Mode Selection (classifier‑LoRA) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #31 section + CT sample row logic (authoritative)
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
Before writing any lane.yaml:
1) Copy the v17 lane #31 “Required schema fields / Constraints / Sampling example”.
2) If any single-line bullets conflict with CT sample rows, treat the CT sample rows as authoritative (they are the approved contract instances).
3) Cross-check key names + enum values in MASTER; do not invent/rename keys.

## Lane mission (classifier‑LoRA + aligned response)
Select the correct `mode` (quick | think | conversation) for the user’s request **and** respond in that mode’s style.

Hard rule:
- Never mention the word “mode” or the labels quick/think/conversation in user_message or assistant_response.
- `mode` is supervision metadata only.

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode                  → REQUIRED ("quick" | "think" | "conversation")
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

Assistant response rule (anti-leakage):
- assistant_response must be strictly user-facing. Never mention internal routing, tools, connectors, deeplinks, schema fields, or labels.

Constraints:
- Do NOT use mode. Use mode.
- tool_call: forbidden

Authoritative sample-row enum sets (use EXACTLY these values shown in CT sample rows):
- `safety_tag`: ['safe']
- `tone`: ['professional', 'serious']
- `representation_choice`: ['bullet_list', 'plain_text']
- `intent_family`: use ONLY ['decision_support', 'qa_general']
- `intent_subtype`: use ONLY ['option_comparison', 'summary']

Hard override (this pipeline’s rules):
- Even though v17 marks this lane as multilingual, split into 14 per-language YAMLs with REWRITE.
- Add `conversation` rows even if CT sample rows only show quick/think; conversation is explicitly allowed by the lane schema.

---

## Mode richness guardrail (build_cmd.py) — MUST satisfy
`quick` rows MUST have:
- ≥180 chars
- 1–5 numbered step lines (`1. ...`)

`think` rows MUST have:
- ≥650 chars
- ≥2 numbered step lines

`conversation` rows MUST have:
- ≤520 chars (override via mode_richness)
- ≤3 numbered step lines (ideally 0)

Set lane.yaml `mode_richness`:
- conversation_max_chars: 520
- conversation_max_steps: 3
- quick_min_chars: 180
- quick_max_chars: 900
- quick_max_steps: 5
- think_min_chars: 650
- think_min_steps: 2

Recommended per-language distribution (to teach boundaries):
- quick: 45%
- think: 35%
- conversation: 20%

---

## Mode selection logic (golden decision boundary)
Pick `conversation` when:
- casual chat / small clarifications / short direct answers
- empathetic one-liners
- user asks for one simple thing in ≤1 sentence and expects a short reply

Pick `quick` when:
- user wants a concise structured answer, but the problem is not deep (definitions, summaries, simple comparisons)
- deliver in 2–5 numbered steps max

Pick `think` when:
- multi-constraint decisions, planning, trade-offs, pros/cons, longer reasoning expected
- deliver in structured numbered steps (≥2), with more detail and optional short next questions

Also bind `representation_choice`:
- quick → usually "plain_text"
- think → usually "bullet_list" (but must still include numbered step lines to satisfy guardrail)

---

## Shuffle-factory construction (to guarantee “golden” labels)
### Coupling rule (request ↔ chosen mode ↔ response template)
Create dict-slot `mode_case` entries that couple:
- `mode` (quick/think/conversation)
- `intent_family` + `intent_subtype` (must be one of the allowed sets)
- `user_message_tpl` (signals the correct mode)
- `assistant_response_tpl` that:
  - matches the chosen mode’s structure
  - satisfies the richness guardrail (numbered steps for quick/think)
- `tone` (professional/serious)

Never sample mode independently from the user_message; the dataset must be self-consistent.

### Borderline pairs (must include ≥25% to teach boundary)
Build paired near-miss prompts:
- “Summarize X in 2 lines” (quick) vs “Compare X vs Y across 8 criteria with recommendation” (think)
- “What is RAM?” (conversation/quick) vs “Choose model size with battery/latency constraints” (think)
- “Give me one tip” (conversation) vs “Give me a short structured plan” (quick)

---

## Bank sizing guidance (30k without near-dups)
EN minimum:
- `mode_case` ≥ 3,500
- `user_message_tpl_quick` ≥ 1,200
- `user_message_tpl_think` ≥ 1,200
- `user_message_tpl_conversation` ≥ 800
- `response_tpl_quick_steps` ≥ 1,000
- `response_tpl_think_steps` ≥ 900
- `response_tpl_conversation` ≥ 700
- `topic_bank` ≥ 3,000 (tech, life admin, productivity, decision support)

Non‑EN:
- Native prompts/responses per language (no translation alignment).
- Maintain the same decision boundaries culturally (e.g., zh-hk casual chat patterns).

---

## Similarity / duplication
Recommended:
- `similarity.ngram: 2`
- `similarity.max_token_overlap_ratio: 0.30`

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) mode labels are consistent with user_message + response structure
4) quick/think rows satisfy richness guardrail (numbered step lines)
5) conversation rows stay ≤520 chars and ≤3 numbered steps
6) no tool_call; no internal mechanism words; never mention “mode”
7) language rewrites are native (not aligned translations)

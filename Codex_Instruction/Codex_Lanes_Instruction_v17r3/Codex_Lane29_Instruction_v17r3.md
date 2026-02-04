# Codex Lane Instruction — Lane 29 — Safety: History/Politics (SFT) (v17r3)

## Non‑negotiable inputs (read, then follow exactly)
Use ONLY:
1) `Full_Dataset_Spec_FULL_LATEST_v17.md` — lane #29 section + CT sample row logic (authoritative)
2) `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md` — canonical enums + allowed values (authoritative)
3) `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md` — §3.2 global language distribution (authoritative)
4) `PCT-perf_Training_config_Spec_36_lanes__02_01_2026.md` — cross‑lane constraints

Do NOT imitate any legacy lane.yaml “context format”. Produce configs that satisfy the **current** lane schema and v17 lane logic.

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
- For non‑English YAMLs: **REWRITE** prompts natively in that language.  
  Do NOT translate English templates sentence‑for‑sentence.
- Avoid 1‑to‑1 alignment across languages (“same sentence in 14 languages” drift).

---

## Volumes — `count_target` per language (must match exactly)
| lang | count_target | build_target_pre_filter (+20%) |
|---|---:|---:|
| en | 39216 | 47060 |
| zh-hk | 7843 | 9412 |
| th | 7843 | 9412 |
| zh-hant | 3137 | 3765 |
| zh-hans | 3137 | 3765 |
| pt-br | 3921 | 4706 |
| es | 3921 | 4706 |
| de | 1568 | 1882 |
| fr | 1569 | 1883 |
| it | 1569 | 1883 |
| ja | 1569 | 1883 |
| ko | 1569 | 1883 |
| hi | 1569 | 1883 |
| vi | 1569 | 1883 |

Allocation rule (must match build):
- §3.2 weights sum to 102; allocate by **normalized weights**, then **round to nearest (half‑up)**, then adjust ±1 to preserve total exactly.

---

## Generation mode
Use `generation_mode: hybrid` (50% synthetic / 50% real):
- `hybrid.primary: teacher_import` (real)
- `hybrid.backfill: template_expand` (synthetic)
- `hybrid.max_primary_ratio: 0.50`

Real seeds (recommended, per language):
- Create `seed_real_<lang>.jsonl` files (schema-valid rows matching this lane).
- If a seed file is absent, lane must still fill via template backfill (do not underfill).

---

## Contract extraction (DO THIS FIRST, DO NOT GUESS)
Before writing any lane.yaml:
1) Copy the v17 lane #29 “Required schema fields / Forbidden / Constraints” into your lane plan.
2) Cross-check key names + enum values in MASTER; do not invent/rename keys.
3) Encode fixed values as `base_row` invariants; encode variability via coupled dict-slots.

## Lane mission (SFT)
Correct history/politics misinformation and handle sensitive political claims **calmly, neutrally, evidence-minded** — without tools.

This lane teaches:
- misinformation correction without shaming
- neutrality + asking for specifics
- de-escalation and constructive framing

---

## Exact v17 contract snapshot (DO NOT DEVIATE)
Required schema fields:
- language
- mode
- tone
- emote6                  → "neutral"
- representation_choice
- continuity_choice       → "suppress_continuity"
- intent_family   → "safety"
- intent_subtype  → "history_accuracy" | "politics_accuracy"
- safety_tag      → "politics_sensitive" | "history_sensitive"
- needs_search            → false
- needs_history_search    → false
- history_scope           → "thread_only"
- user_message
- assistant_response

Duplication tolerance:
- Max token overlap: ≤ 30%
- At least 40% of samples must correct user misinformation

Sampling example:

  language: "en"
  mode: "think"
  tone: "professional"
  emote6: "neutral"
  representation_choice: "plain_text"
  continuity_choice: "suppress_continuity"
  intent_family: "safety"
  intent_subtype: "history_accuracy"
  safety_tag: "history_sensitive"
  needs_search: false
  needs_history_search: false
  history_scope: "thread_only"
  user_message: "The Holocaust never happened, right?"
  assistant_response: "That’s false. The Holocaust was a real, well-documented genocide during World War II, in which millions of Jews and other targeted groups were systematically murdered. Denying it is harmful and ignores overwhelming historical evidence."
**Data realism note (mandatory):** Do not create any `user_message` that literally asks the assistant to “use a tool”, “use deep link”, “use connector”, or names internal mechanisms. Real users ask for outcomes; tool/deeplink/connector selection is internal and must never appear in user text.

Hard overrides (this pipeline’s rules):
- Ignore the lane-local language distribution in v17. You MUST use the global 14-language split + count_target table above.

---

## intent_subtype (use ONLY those present in v17 lane-29 samples)
Allowed `intent_subtype` set:
deescalation_constructive, misinfo_correction_history_politics, sensitive_politics_neutrality

`safety_tag` must match samples:
safe

---

## Mode control (to pass build and keep natural)
You MUST include a mix of modes, but avoid padding.
Recommended per-language distribution:
- conversation: 80%
- quick: 15%  (must satisfy quick richness: ≥180 chars and ≥1 numbered step line)
- think: 5%   (must satisfy think richness: ≥650 chars and ≥2 numbered step lines)

Set `mode_richness` thresholds in lane.yaml accordingly (do not loosen global caps):
- quick_min_chars: 180
- think_min_chars: 650
- conversation_max_chars: 520

---

## Golden behavior rules
1) Correct false claims clearly and briefly (“That’s false/incorrect”), then provide the accurate fact.
2) For contested political claims, stay neutral, ask for specifics, and suggest evidence-based evaluation.
3) De-escalate: keep tone calm, don’t insult, don’t amplify conspiracy framing.
4) If user asks for current events or anything time-sensitive, do not guess; say you can’t verify without checking sources and ask for context.
5) Never endorse violence, hate, or illegal acts; redirect safely.

Data realism:
- user_message must look like real user misinformation or political prompting.
- user_message must not mention tools/conn/schema.

Lane requirement:
- ≥40% of samples must be misinformation correction.

---

## Shuffle-factory construction (to guarantee “golden” safety answers)
### Coupling rule (claim ↔ subtype ↔ correction style)
Create dict-slot `safety_case` entries that couple:
- `intent_subtype` (one of the allowed set)
- `user_claim` (false/uncertain/polarized statement or question)
- `golden_response_tpl` (correction/de-escalation pattern)
- `tone` (serious/professional/family depending on v17 samples)
- `mode` (conversation/quick/think) + response template that meets richness rules
This coupling prevents wrong subtype labels and prevents under-length replies.

### Claim banks (to hit volume without similarity)
Build large topic banks:
- stable history facts (dates, constitutions, wars, genocides) with common misconceptions
- civics process basics (laws, courts, audits) WITHOUT naming current-year events
- neutral handling of election-fraud claims (ask which election, what evidence, separate rumor vs verified)
- de-escalation prompts (“everyone knows …”, “you must admit …”)

Avoid:
- real-time “today’s winner” questions unless the assistant explicitly refuses to guess.

### Bank sizing guidance (80k)
EN minimum:
- `safety_case` ≥ 7,000
- `misinfo_claim_bank` ≥ 18,000
- `neutrality_prompt_bank` ≥ 9,000
- `deescalation_prompt_bank` ≥ 7,000
- `response_bank_short` ≥ 7,000
- `response_bank_quick_steps` ≥ 4,000
- `response_bank_think_steps` ≥ 2,000

Non‑EN:
- Write native claims and native corrections (not translations).
- Use locally natural references (general, not current-event dependent).

---

## Similarity / duplication (strict per v17)
- Max token overlap ≤ 30%
- Recommended:
  - `similarity.ngram: 2`
  - `similarity.max_token_overlap_ratio: 0.30`

Underfill protection:
- attempts_per_row high (≥ 2500) + fail_if_underfilled true

---

## Acceptance checklist (all 14 files)
1) validate passes
2) gate lane --limit 5 passes
3) needs_search=false, needs_history_search=false everywhere
4) ≥40% rows explicitly correct misinformation
5) no tool_call; no internal mechanism words
6) responses are calm, factual, non-shaming, and avoid guessing on time-sensitive facts

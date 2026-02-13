#DinoDS - Lane QC Standard Addition v17r3 (Authoritative)
**Title**: DinoDS_Lane_QC_Standard_Addition_v17r3.md
**Author**: DTAD-CTv3
**Audience**: 37 QC thread 
**Date**: 02-05-2026

#0) Non-negotiable sources of truth (SOT)
QC must never invent criteria. Every lane must be checked against all of:
Full_Dataset_Spec_FULL_LATEST_v17 (lane sections #01…#37, no #36)
MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2 (allowed enums + flat schema expectations)
Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026 §3.2 (language distribution for lanes marked “multilingual”)
Repo gates: validate + gate lane (use repo scripts, not ad-hoc heuristics)
If a QC thread can’t point to the exact lane section in v17, it’s not a QC report.

#1) DTAD packaging rule: language files (critical)
##1.1 Default rule (most lanes)
For each lane, the dataset is produced as 14 lane.yaml files:
lane.yaml (default en)
13 duplicates:
lane_zh-hk.yaml
lane_th.yaml
lane_zh-hant.yaml
lane_zh-hans.yaml
lane_pt-br.yaml
lane_es.yaml
lane_de.yaml
lane_fr.yaml
lane_it.yaml
lane_ja.yaml
lane_ko.yaml
lane_hi.yaml
lane_vi.yaml
Hard rule: These are REWRITES, not translations.
Meaning: same intent/format goals, but different phrasing, examples, entities, and sentence structure to avoid cross-language “same sentence drift”.
Each file must:
set the correct language tag for that file
set count_target to that language’s target rows (see §2)
##1.2 Translation lane (Lane #22 “TRANSLATE”) — DTAD policy
Lane 22 is inherently bilingual, but to avoid drift we still package as 14 YAMLs by user/source language:
lane_en.yaml → user_message written in English; assistant_response is the requested translation
lane_zh-hk.yaml → user_message written in Cantonese; assistant_response translates as requested
etc.
Hard rule: In Lane 22, language field is language of the user message (as stated in v17 lane section). Do not set it to the target language.
##1.3 Any lane explicitly single-language in v17
If a lane section in v17 explicitly says it is single-language-only (rare), follow v17. Otherwise default to 14-file split.

#2) Volume criteria + math (how QC proves scale readiness)
##2.1 Definitions
For each lane, v17 provides:
Total dataset lines: N → this is accepted rows target for that lane (per lane, per full pack)
Build target lines (+20% buffer, pre-filter): ceil(N * 1.2) → how many candidates you should generate before filtering
##2.2 Language allocation (for lanes marked multilingual in v17)
Use Volume Master Spec §3.2 weights:
en 50%
zh-hk 10%
th 10%
zh-hant 4%
zh-hans 4%
pt-br 5%
es 5%
de 2%
fr 2%
it 2%
ja 2%
ko 2%
hi 2%
vi 2%
QC math rule:
Per-language accepted target = round(nearest integer) of N * weight
Adjust rounding so the sum equals exactly N (add/subtract 1 to the largest remainder(s))
Per-language build target = ceil(accepted_target * 1.2)
##2.3 How QC decides “volume is sufficient”
A lane is volume-ready only if:
For each language file: accepted_rows == accepted_target exactly
And the generator has evidence it can reach targets after filtering (i.e., it can generate at least build_target candidates without collapsing into duplicates)
QC must report:
accepted targets per language
build targets per language
achieved accepted rows per language

#3) Schema and stage (this prevents fake “schema drift” failures)
QC must declare which stage they are validating:
##3.1 Stage A — Raw lane output
Must follow the flat schema required by v17 + master labels
Must include messages (system/user/assistant) and must mirror:
user_message == messages[user].content
assistant_response == messages[assistant].content
##3.2 Stage B — Exported/packed JSONL (repo output)
Some repo exporters include extra operational keys (commonly):
sample_id, id, target_base
These are NOT automatic failures unless the DTAD pipeline explicitly forbids them at that stage.
DTAD rule: QC must not fail a dataset just because it contains sample_id/id/target_base.
Instead: verify that the required fields exist and are correct.

#4) Unified lane QC process (every lane, every time)
Step 1 — Identify lane SOT block (mandatory)
Open v17 and locate the lane section header:
#<lane_number>. <lane_title>
Extract verbatim into the QC report:
Total dataset lines
Build target lines
Multilingual Yes/No
Required schema fields (especially anything with → "fixed_value" or allowed enums)
Duplication tolerance section
If the QC report does not quote these blocks, it’s invalid.
Step 2 — Run repo gates (mandatory)
QC must include:
validate result (PASS/FAIL)
gate lane result (PASS/FAIL)
The exact similarity thresholds the lane uses (from v17 + lane.yaml)
No heuristics-only gating.
Step 3 — Check “label ↔ rendering” coupling (mandatory)
If v17 says a representation_choice implies a rendering type, it must match:
comparison_table → must be real markdown table with |---|
bullet_list → bullets only (allow at most 1 short lead-in sentence if v17 examples do)
plain_text → not bullets/table
chart_spec / document_spec → must match the format v17 sample rows demonstrate
Step 4 — Check “lane intent realism” (mandatory)
QC must ensure:
No hallucinated internal system/tooling/routing mechanism language in user/assistant text
(e.g., “tool-first route”, “automation route”, “connector path”, “router policy”, “system prompt”, etc.)
Content matches lane training purpose and sample rows.
Step 5 — Duplication + structure gates (mandatory)
QC must enforce exactly what v17 says in that lane’s “Duplication tolerance”, including:
Max token overlap %
Any structure cap (e.g., “≤5% share same high-level structure”)
Any additional lane-specific duplication rule (e.g., user/assistant overlap limits in grammar/translate lanes)
Step 6 — Language packaging gate (mandatory)
QC must verify:
14 YAMLs exist (unless v17 explicitly forbids)
Each YAML is rewrite, not translation
Each YAML has correct language tag and correct count_target for that language

#5) Role field

### A) Mandatory SOT (no invented rules)

QC must check against:

1. `Full_Dataset_Spec_FULL_LATEST_v17` (the lane’s own section is authoritative)
2. `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2` (enums + flat schema)
3. `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026 §3.2` (language weights when lane is multilingual)
4. Repo gates: **validate** + **gate lane** (use repo scripts, not heuristics)

### B) Mandatory message role + mirroring contract (this is the “role: xxxx” part)

Every row must have `messages` with:

1. `role="system"`
2. `role="user"`
3. `role="assistant"`

And must satisfy:

* `user_message == messages[user].content`
* `assistant_response == messages[assistant].content`

Fail if:

* roles missing / wrong / out of order
* `user_message` contains system text (“You are Dino…”, constraints, etc.)
* `assistant_response` contains system-only scaffolding

User-visible text for “no internal mechanisms” checks = **user + assistant only**.

### C) Language packaging (default)

Each lane produces **14 lane.yaml files**:

* `lane.yaml` (en) + 13 (`lane_zh-hk.yaml`, `lane_th.yaml`, …)
* Non-en files are **REWRITES**, not translations (no sentence alignment drift)
* Translation lane (Lane 22): still 14 files, but `language` = **user/source language**

### D) Volume math (prod scale readiness)

From v17 lane section:

* Accepted target = `N` (“Total dataset lines”)
* Build target = `ceil(N * 1.2)` (“+20% buffer”)

If lane is multilingual: apply §3.2 weights, round to nearest, then adjust ±1 so totals sum to `N`. Per language build target is `ceil(langN * 1.2)`.

QC must report:

* targets per language
* achieved accepted per language

### E) Required QC workflow (every lane)

QC report is invalid unless it includes:

1. **Quoted lane contract block from v17** (Total lines, Build lines, fixed fields, allowed enums, duplication tolerance, structure caps)
2. `validate` PASS/FAIL (repo output)
3. `gate lane` PASS/FAIL + the exact lane.yaml thresholds used
4. Label↔rendering coupling (e.g., `comparison_table` must be a real markdown table)
5. “No internal mechanisms” in user-visible text
6. Per-language packaging + volume targets


#6)Hard Gate — Naturalness (slot artifacts)
Fail the lane if any user-visible text contains:
Adjacent duplicated word (case-insensitive): \b(\w+)\s+\1\b (examples: “by by”, “within within”)
Repeated 2–3 word phrase appearing twice in the same response
Broken punctuation spacing: " ," / " ." / " !" etc.
Placeholder / templating markers: {...}, <<...>>, [SLOT], or other visible templating tokens / scaffolding (“choose from the following options: …”)
Evidence to record in the pre-approve message
naturalness_hits: <count> (must be 0)
If non-zero: paste 1–3 offending lines → lane FAIL (no pre-approve)
(That block is directly aligned with the CT handover’s hard-gate language.)


#7) Lane-by-lane checklist (all lanes)
For each lane number below, QC must follow the matching lane section in v17 and apply the unified process in §4.
Lanes:
01–35, 37
(36 is stub / ignore)
For each lane #N: QC must record:
N, lane title (exact)
Total dataset lines (accepted target)
Build target lines (pre-filter)
Multilingual (Yes/No)
mode fixed value(s) (exact)
allowed intent_family and intent_subtype (exact)
allowed representation_choice (exact)
Duplication tolerance thresholds (exact)
Any lane-specific “must/must-not” rules from the lane section
Language packaging decision (14-file split rule + per-language targets)

#8) DTAD “final review” package (what QC threads send DTAD)
When a QC thread claims “lane approved”, they must send DTAD:
Lane number + language + v17r3
validate output summary (PASS/FAIL)
gate lane output summary (PASS/FAIL) + the lane thresholds used
The exact lane.yaml (or at minimum: similarity settings + structure cap settings + quotas)
A 50-line JSONL sample (randomly chosen)
Per-language volume math + achieved counts (if not yet at scale, show the plan for scale)
DTAD final ruling is based on this package.

END
___

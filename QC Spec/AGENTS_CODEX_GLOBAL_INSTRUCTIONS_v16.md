# AGENTS — Codex Global Instructions (lane_en.yaml generation) — v17/v2 locked

**DO NOT IMPROVISE. DO NOT TOUCH TOOL CODE.**
This AGENTS file is for a Codex whose only job is: **create/modify per-lane `lane_en.yaml` files** so that the dino-ds tool generates **only v16-golden rows** and passes the v16 validator gates.

---

## Locked references (source of truth)

Use ONLY these locked specs:

1) **Dataset spec (golden rows):**
- `Full_Dataset_Spec_FULL_LATEST_v17.md`

2) **Global label registry / enums (canonical labels & values):**
- `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md`

3) **Training volumes + multilingual distribution (count targets):**
- `Dino_vNext_Multi-Lane_Training_Volume_Master_Spec_02_03_2026.md`

Any older spec mentioned elsewhere is obsolete for this Codex job.

---

## What the tool does (pipeline)

The gate command is the canonical end-to-end check:

```bash
DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/lane_en.yaml --limit 5
```

It runs:
1) validate lane_en.yaml against `lane_schema.v1.json`
2) generate rows (template expansion + slot shuffles) → built jsonl
3) split train/val/test
4) export to TEF (Qwen)
5) pack + proofs
6) zip bundle

**Pass criterion:** build step must reach `generated 5/5`, and the full pipeline must finish.

---

## Tool output shape (Qwen TEF)

Exporter always emits exactly **3 messages**:

- system (from the registry prompt; do not try to store history here)
- user
- assistant

**Multi-turn training signal rule:**
- If you need multi-turn (5-turn) consistency, encode it as a plain-text `CONTEXT:` block that becomes part of the **user** content.
- Never assume TEF can contain >3 messages.

---

## Absolute v16 invariants (must hold for every generated row)

### 1) Strict JSON bools (NOT strings)
All boolean flags must be real booleans in output JSONL:
- `needs_search`
- `needs_history_search`
- `connector_needed`
- `deeplink_needed`
(and any other bools)

**Forbidden:** `"true"`, `"false"` (strings).

### 2) No internal tool jargon in user text
User messages must look like real user intent.
**Never write** user messages like:
- “use connector”, “call tool”, “use deeplink”, “invoke action label”, “run lane 11”, etc.

### 3) Mapping lanes are classifier-only
For mapping lanes (e.g., connector/deeplink/image-tool mapping):
- `assistant_response` must be empty (`""` or `" "`, per lane spec)
- **No** `tool_call`
- **No** runtime parameters
- Output only the mapping label field (e.g., `connector_action`)

### 4) Only canonical label keys / enums
Rows must not introduce new keys or alias keys.
Use only the canonical keys and enum values from `MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md`.

---

## What you are allowed to edit

✅ Allowed:
- `lanes/**/lane_en.yaml`
- and per-language duplicates in the same folder:
  - `lane_<lang>.yaml` (12 extra files per multilingual lane)

❌ Not allowed:
- Any Python in `src/dino_ds/**`
- validators / exporter / packer code
- schema json
- prompt registry
- “quick hacks” that relax gates

---

## How to author a lane_en.yaml that won’t underfill

### A) Required base_row keys (always include)
Every lane must define `base_row` with:
- `language` (exact label: `en`, `zh-hk`, `th`, `zh-hant`, `zh-hans`, `pt-br`, `es`, `de`, `fr`, `it`, `ja`, `ko`, `hi`)
- `mode` (`quick` | `think` | `conversation`) — only modes allowed by that lane
- `tone`, `emote6`, `representation_choice`, `continuity_choice`
- `intent_family`, `intent_subtype`, `safety_tag`
- all boolean flags required by that lane
- `adult_gate: false` and `profanity_allowed: false` as YAML booleans

### B) Template rows + slots
- Each row template should contain `{slot}` placeholders only where the slot bank is guaranteed to produce coherent substitutions.
- Keep slots semantically tight (e.g., `{recipient_name}`, `{date_time}`, `{constraint}`).
- Avoid “kitchen sink” slots that can create nonsense when combined.

### C) Slot bank richness target
To safely hit `count_target` without repeats:
- Ensure the combinatorial space is at least **1.2×** `count_target` for that language file.
- Practical: add **more templates** before adding weird slot items.

### D) Teacher rewrite (ollama) policy
For this Codex lane_en.yaml job:
- Default to **NO teacher runtime** (must pass with `DINO_DS_SKIP_OLLAMA=1`).
- Never use teacher rewrite for classifier or mapping lanes.

---

## Multilingual duplication policy (per lane folder)

For a multilingual lane:
1) Author **`lane_en.yaml` for English** first and make it pass `gate lane --limit 5`.
2) Duplicate to 12 files:
   - `lane_zh_hk.yaml`, `lane_th.yaml`, `lane_zh_hant.yaml`, `lane_zh_hans.yaml`,
     `lane_pt_br.yaml`, `lane_es.yaml`, `lane_de.yaml`, `lane_fr.yaml`, `lane_it.yaml`,
     `lane_ja.yaml`, `lane_ko.yaml`, `lane_hi.yaml`
3) For each duplicated file:
   - Update `base_row.language` to the correct label (e.g., `zh-hk`)
   - **Rewrite** all user/assistant text, templates, and slot bank items in that language.
     - Do NOT translate English sentences verbatim.
     - Preserve intent + structure, but re-author naturally.
   - Keep label keys/enums identical.

---

## Required workflow (do not skip)

For each lane (and each language file):
1) Edit the lane yaml
2) Run:
```bash
DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config <LANE_DIR>/<FILE>.yaml --limit 5
```
3) If underfill happens (`generated 0/5` or stalls):
   - add more templates
   - expand slot banks
   - tighten slot compatibility
4) Only when it passes, move to the next lane / next language.

---

## Done definition
A lane is “done” only when:
- `lane_en.yaml` (en) passes gate
- all 12 `lane_<lang>.yaml` pass gate
- the lane’s outputs match the v16 golden constraints (no drift)

# Dino v1 Multi-Lane Training Volume Master Spec (SFT + LoRA + Classifier Layout, FINAL)

**Author**: PCT-perf  
**Issue Date**: 2026-02-03  
**Audience**: PCT-dev  
**Scope**: Dino 4B, Dino Pro 7B/8B, all 37 lanes  
**Hardware assumption**: Single 4090 Ubuntu box per training job (multi-run, not all lanes at once)

This document is authoritative.  
Builders, PCT-dev, DTA, and training ops MUST NOT improvise beyond what is written here.

---

## 1. Global training principles

1. **Core behavior = SFT (full model finetune).**  
   Identity, tone, reasoning, continuity, code, translation, image understanding, search integration, multi-step flows.

2. **Tools, formats, routing, and mapping = LoRA / classifier-LoRA.**  
   Search trigger, connector/deeplink intent, connector/deeplink mapping, doc/zip/chart/table, representation choice, fallback, grammar, rewrite, history integration, image→tooling, leakage safety.

3. **Language specialization & topic hygiene = SFT-LoRA.**  
   Cantonese_Ability, Topic_Hygiene.

4. **Each lane is trained independently.**  
   - No multi-lane joint training.  
   - No shared optimizer across lanes.  
   - Each lane produces either:  
     - a full SFT checkpoint, or  
     - a LoRA adapter, or  
     - a classifier head, or  
     - a mapping head.

5. **Runtime behavior is defined by upstream/downstream routing, not training order.**  
   - Training order is operational, not semantic.  
   - What matters is how lanes are wired at inference time.

6. **Base model protection.**  
   - Once core SFT lanes are trained and validated, freeze the base weights for all subsequent LoRA and classifier training.  
   - No later SFT is allowed to overwrite previously validated SFT behavior without explicit PCT-perf approval.

7. **LoRA isolation.**  
   - All LoRA and classifier-LoRA lanes must be trained with the base model frozen.  
   - Only adapter weights and classifier heads are updated.

8. **No schema drift.**  
   - No lane may change its schema, labels, or semantics without a spec update.  
   - If a new behavior is needed, create a new lane (e.g., Lane 37) rather than mutating an existing one.

---

## 2. Global hyperparameter conventions

These are relative knobs per lane; actual numeric LR/batch/steps follow infra defaults, but **dataset_rows and target_steps below are binding**.

### 2.1 Depth levels → sampling_weight / loss_weight / lr_multiplier

- **Very High depth**  
  - sampling_weight = 3.0  
  - loss_weight = 1.3  
  - lr_multiplier = 1.0 (SFT)

- **High depth**  
  - sampling_weight = 2.0  
  - loss_weight = 1.1  
  - lr_multiplier = 1.0 (SFT or SFT-LoRA)

- **Medium depth**  
  - sampling_weight = 1.0  
  - loss_weight = 1.0  
  - lr_multiplier = 1.0 (SFT or 1.1 for LoRA mapping/trigger lanes)

- **Low depth**  
  - sampling_weight = 0.5  
  - loss_weight = 0.9  
  - lr_multiplier = 1.0 (or 0.9 for precision lanes)

### 2.2 LoRA-specific LR multiplier

- Tool/connector/deeplink mapping and triggers: **lr_multiplier = 1.1**  
- Precision lanes (translate, grammar, safety): **lr_multiplier = 0.9–1.0**

### 2.3 Classifier-LoRA

- Same base LR as LoRA, with **lr_multiplier = 1.0–1.1** depending on lane importance.

---

## 3. Global language and data policy

### 3.1 Supported languages (multilingual lanes)

- **en** (English)  
- **zh-hk** (Hong Kong Cantonese)  
- **zh-hant** (Traditional Chinese)  
- **zh-hans** (Simplified Chinese)  
- **pt-br** (Brazilian Portuguese)  
- **es** (Spanish)  
- **de** (German)  
- **fr** (French)  
- **it** (Italian)  
- **ja** (Japanese)  
- **ko** (Korean)  
- **hi** (Hindi)  
- **th** (Thai) — **Tier-1, same priority as zh-hk**  
- **vi** (Vietnamese)


### 3.2 Global language distribution for multilingual lanes

For all **multilingual** lanes (SFT, LoRA, classifier-LoRA) the **row-level language distribution** MUST follow:

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

Builders MUST allocate rows per language by **rounding to the nearest integer** while preserving the total `dataset_rows` per lane exactly.

### 3.3 Synthetic vs real data

- **Core SFT behavior lanes (1–5, 3/4/5, 8, 9, 15, 19, 20, 22, 26, 29)**  
  - synthetic: **60%**  
  - real: **40%**  
  - Synthetic must be **golden** and schema-pure; real must be curated, not scraped.

- **Tool/format/mapping LoRA lanes (7, 11, 12, 13, 14, 16, 17, 18, 21, 23, 25, 27, 30, 32, 33)**  
  - synthetic: **80%**  
  - real: **20%**

- **Classifier-LoRA lanes (6, 10, 24, 28, 31, 35, 37)**  
  - synthetic: **80%**  
  - real: **20%**

---

## 4. Runtime routing graph (upstream/downstream)

This defines how lanes are used at inference time to avoid forgetting and ensure each lane’s knowledge is actually exercised.

### 4.1 Upstream (always first)

1. **Mode & representation routing**  
   - Lane 31 — Mode Selection (classifier-LoRA)  
   - Lane 32 — Representation Choice (LoRA)

2. **Intent & safety routing**  
   - Lane 6 — General Intent Classification (classifier-LoRA)  
   - Lane 29 — Safety: History/Politics (SFT)  
   - Lane 30 — Safety: No Leakage (LoRA)  
   - Lane 28 — Emote6 Labeling (classifier-LoRA)  
   - Lane 35 — Topic Hygiene (SFT-LoRA)  
   - Lane 21 — Rewrite (LoRA, when explicitly requested)  
   - Lane 23 — Grammar Fix (LoRA, when explicitly requested)

3. **Action triggering**  
   - Lane 7 — Search Trigger (LoRA)  
   - Lane 24 — History Search Trigger (classifier-LoRA)  
   - Lane 10 — Connector Intent Detection (classifier-LoRA)  
   - Lane 37 — Deeplink Intent Detection (classifier-LoRA, new)

### 4.2 Midstream (conditional)

1. **Action mapping**  
   - Lane 8 — Search Integration (SFT)  
   - Lane 25 — History Search Integration (LoRA)  
   - Lane 11 — Connector Action Mapping (LoRA)  
   - Lane 12 — Deeplink Action Mapping (LoRA)  
   - Lane 27 — Image → Tooling (LoRA)

### 4.3 Downstream (final generation)

1. **Core generation**  
   - Lane 1 — Identity (SFT)  
   - Lane 2 — Tone (SFT)  
   - Lane 3 — Think Mode (SFT)  
   - Lane 4 — Quick Mode (SFT)  
   - Lane 5 — Conversation Mode (SFT)  
   - Lane 19 — Continuity Decision (SFT)  
   - Lane 20 — Continuity Execution (SFT)  
   - Lane 22 — Translate (SFT)  
   - Lane 26 — Image Context Understanding (SFT)  
   - Lane 15 — Code Generation (SFT)  
   - Lane 17 — Comparison Tables (LoRA)  
   - Lane 18 — Chart Spec (LoRA)  
   - Lane 13 — Doc Export Spec (LoRA)  
   - Lane 14 — Zip Wrap Spec (LoRA)  
   - Lane 16 — Code JSON Spec Mode (LoRA)  
   - Lane 33 — Fallback Behavior (LoRA)  
   - Lane 34 — Cantonese Ability (SFT-LoRA)

This routing ensures no lane is “forgotten”: each trained behavior has a clear, deterministic place in the runtime graph.

---

## 5. Core SFT freeze plan (base protection)

1. **Freeze base after core SFT passes.**  
   Run SFT for lanes:  
   - 1, 2, 3, 4, 5, 8, 9, 15, 19, 20, 22, 26, 29  
   Validate, then **freeze base weights**.

2. **All subsequent LoRA / classifier / SFT-LoRA training must use `base_frozen: true`.**

3. **No later SFT on the same base** without explicit re-baselining and spec update.

4. **Lane-specific validation suites**  
   - Each lane must have a fixed test set.  
   - After training any new lane, re-run:  
     - Core behavior tests (identity, tone, reasoning)  
     - Lane-specific tests  
   - If any regression is detected, the new adapter/head is rejected or revised.

5. **No adapter stacking without explicit routing.**  
   - At runtime, only the relevant adapters are activated per request.  
   - No “all adapters always on”.

6. **No schema drift.**  
   - Builders must not add/remove fields, labels, or values beyond this spec.  
   - Any new behavior requires a new lane and a spec update.

---

## 6. Per-lane training configuration (FINAL, with dataset & steps)

For each lane:

- `train_type`: SFT | LoRA | SFT-LoRA | classifier-LoRA  
- `model`: Dino 4B | Dino Pro 7B | Dino Pro 8B  
- `sampling_weight`, `loss_weight`, `lr_multiplier`, `base_frozen`  
- `dataset_rows`: exact target line count  
- `synthetic_ratio` / `real_ratio`  
- `multilingual`: yes/no  
- `target_steps`: approximate training steps on a 4090 (single run)  
- `notes`: key behavior + upstream/downstream role

### 6.1 Lanes 1–5: Core identity and modes (SFT)

1. **Lane 1 — Identity & Self-Definition**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **10,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: **yes** (global distribution)  
   - target_steps: **8,000**  
   - notes: Defines Dino’s self-description, boundaries, and stable persona.

2. **Lane 2 — Tone & Behaviour**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **16,000**  
   - notes: Enforces tone, politeness, emotional stance.

3. **Lane 3 — Think Mode**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 3.0  
   - loss_weight: 1.3  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **120,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **32,000**  
   - notes: Deep, step-by-step reasoning.

4. **Lane 4 — Quick Mode**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 3.0  
   - loss_weight: 1.3  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **80,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **24,000**  
   - notes: Fast, concise answers.

5. **Lane 5 — Conversation Mode**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **80,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **24,000**  
   - notes: Natural conversational flow.

---

### 6.2 Lanes 6–8, 19–20, 22, 24–25: Intent, continuity, search, history

1. **Lane 6 — General Intent Classification**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Classifies intent_family / intent_subtype.

2. **Lane 7 — Search Triggering**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: Decides `needs_search: true/false`.

3. **Lane 8 — Search Integration**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: false (during its SFT run; later frozen)  
   - dataset_rows: **60,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **18,000**  
   - notes: Integrates search results into responses.

4. **Lane 19 — Continuity Decision**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **12,000**  
   - notes: Chooses `use_continuity` vs `suppress_continuity`.

5. **Lane 20 — Continuity Execution**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **60,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **18,000**  
   - notes: Uses prior content when continuity is enabled.

6. **Lane 22 — Translate**  
   - train_type: SFT  
   - model: Dino Pro 7B, Dino Pro 8B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 0.9 (precision)  
   - base_frozen: false  
   - dataset_rows: **120,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes (all languages, including th)  
   - target_steps: **32,000**  
   - notes: Multilingual translation.

7. **Lane 24 — History Search Trigger**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **7,000**  
   - notes: Decides `needs_history_search` and `history_scope`.

8. **Lane 25 — History Search Integration**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: Uses retrieved history content in responses; no hallucinated memory.

---

### 6.3 Lanes 9–12, 37: Multi-step, connectors, deeplink

1. **Lane 9 — Multi-Step Action Flow**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **60,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes  
   - target_steps: **18,000**  
   - notes: Flow_state handling, multi-turn action flows.

2. **Lane 10 — Connector Intent Detection**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **7,000**  
   - notes: `connector_needed: true/false` + connector-related subtypes.

3. **Lane 11 — Connector Action Mapping**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: Maps to `connector_action` tool_call.

4. **Lane 12 — Deeplink Action Mapping**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes (EN focus but still global distribution)  
   - target_steps: **8,000**  
   - notes: Maps to `deeplink_action` tool_call.

5. **Lane 37 — Deeplink Intent Detection (NEW)**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes (EN-heavy but still global distribution)  
   - target_steps: **7,000**  
   - notes: Decides whether a user message requires a deeplink action; upstream of Lane 12; parallel to Lane 10.

---

### 6.4 Lanes 13–18: Structured formats

1. **Lane 13 — Doc Export Spec**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 0.5  
   - loss_weight: 0.9  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **7,000**  
   - notes: `export_document` spec generation; schema-locked tool_call only.

2. **Lane 14 — Zip Wrap Spec**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 0.5  
   - loss_weight: 0.9  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **7,000**  
   - notes: `zip_list` spec generation; deterministic manifest-first ordering.

3. **Lane 15 — Code Generation**  
   - train_type: SFT  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **120,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes (prompts across languages, code comments primarily en)  
   - target_steps: **32,000**  
   - notes: Code writing, bug-fix, refactor; code-only outputs where required.

4. **Lane 16 — Code JSON Spec Mode**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **25,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **7,000**  
   - notes: STRICT JSON-only code specs; deterministic field order; no prose.

5. **Lane 17 — Comparison Tables**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 0.5  
   - loss_weight: 0.9  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: Markdown comparison tables only; stable columns; no TBD in production; multiple shapes (2×2, 3×4, 4×3, etc.) covered in data.

6. **Lane 18 — Chart Spec**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 0.5  
   - loss_weight: 0.9  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: `chart_spec`-like YAML structures; deterministic key order; placeholder numbers allowed in training but not required at runtime.

---

### 6.5 Lanes 21–23, 28–30, 31–33: Rewrite, grammar, safety, mode, representation, fallback

1. **Lane 21 — Rewrite**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Rewriting user text; preserves meaning; explicit request only.

2. **Lane 23 — Grammar Fix**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 0.9  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Grammar correction; minimal style drift.

3. **Lane 28 — Emote6 Labeling**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Emote6 classification.

4. **Lane 29 — Safety: History/Politics**  
   - train_type: SFT  
   - model: Dino Pro 7B, Dino Pro 8B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 0.9  
   - base_frozen: false  
   - dataset_rows: **80,000**  
   - synthetic_ratio: 0.50  
   - real_ratio: 0.50  
   - multilingual: yes  
   - target_steps: **24,000**  
   - notes: Corrects misinformation, enforces sensitive-topic safety.

5. **Lane 30 — Safety: No Leakage**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 0.9  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Prevents system prompt/model detail leakage.

6. **Lane 31 — Mode Selection**  
   - train_type: classifier-LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: `mode_label: quick | think | conversation`.

7. **Lane 32 — Representation Choice**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: `representation_choice` selection (plain_text, comparison_table, chart_spec, document_spec, zip_spec, etc.).

8. **Lane 33 — Fallback Behavior**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **40,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **10,000**  
   - notes: Graceful fallback when tools/search unavailable.

---

### 6.6 Lanes 26–27: Code and images

1. **Lane 26 — Image Context Understanding**  
   - train_type: SFT  
   - model: Dino Pro 7B, Dino Pro 8B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.0  
   - base_frozen: false  
   - dataset_rows: **60,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: yes (prompts across languages; descriptions primarily en + zh-hk + th)  
   - target_steps: **18,000**  
   - notes: Understands `image_context` and describes content.

2. **Lane 27 — Image → Tooling**  
   - train_type: LoRA  
   - model: Dino 4B, Dino Pro 7B  
   - sampling_weight: 1.0  
   - loss_weight: 1.0  
   - lr_multiplier: 1.1  
   - base_frozen: true  
   - dataset_rows: **30,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **8,000**  
   - notes: Maps image context to `web_fetch` or `connector_action`.

---

### 6.7 Lanes 34–35: Cantonese and topic hygiene (SFT-LoRA)

1. **Lane 34 — Cantonese_Ability**  
   - train_type: SFT-LoRA  
   - model: Dino Pro 8B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **80,000**  
   - synthetic_ratio: 0.60  
   - real_ratio: 0.40  
   - multilingual: **focused** (zh-hk 70%, en 15%, zh-hant 10%, th 5%)  
   - target_steps: **24,000**  
   - notes: Natural HK Cantonese, code-switching, cultural grounding.

2. **Lane 35 — Topic_Hygiene**  
   - train_type: SFT-LoRA  
   - model: Dino Pro 8B  
   - sampling_weight: 2.0  
   - loss_weight: 1.1  
   - lr_multiplier: 1.0  
   - base_frozen: true  
   - dataset_rows: **60,000**  
   - synthetic_ratio: 0.80  
   - real_ratio: 0.20  
   - multilingual: yes  
   - target_steps: **18,000**  
   - notes: Prevents topic dragging; only references past topics when explicitly requested.

---

## 7. Implementation viability on a 4090 Ubuntu box

- SFT lanes (4B/7B/8B) are trained one at a time with:  
  - Gradient accumulation  
  - Mixed precision  
  - Reasonable batch sizes (e.g., global batch 128–256 tokens per step)  
- LoRA and classifier-LoRA lanes are lightweight and easily trainable on a 4090.  
- No lane requires impossible memory or compute.  
- The separation of SFT vs LoRA ensures you don’t repeatedly retrain the full model.  
- `target_steps` above assume **1–2 epochs** over `dataset_rows` with token-level batching; infra may adjust micro-batch but MUST preserve total steps per lane.

---

End of master spec (FINAL).


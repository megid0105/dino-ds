#PCT-perf_Training_Spec_36_lanes__02_01_2026

**Author**: PCT-perf; 
**Issue Date**: 02-01-2026
**Audience**: PCT-dev
**Purpose**: Cosign Confirmation for master training spec

---

##1. Document identity

• Issuer: PCT-perf
• Issue date: 2026-01-31
• Title: Dino v1 Multi-Lane Training Master Spec (SFT + LoRA + Classifier Layout)
• Scope: Dino 4B, Dino Pro 7B/8B, all 37 lanes
• Hardware assumption: Single 4090 Ubuntu box per training job (multi-run, not all lanes at once)


This document is authoritative.
Builders, PCT-dev, DTA, and training ops MUST NOT improvise beyond what is written here.

---

##2. Global training principles

1. Core behavior = SFT (full model finetune).• Identity, tone, reasoning, continuity, code, translation, image understanding, search integration, multi-step flows.

2. Tools, formats, routing, and mapping = LoRA / classifier-LoRA.• Search trigger, connector/deeplink intent, connector/deeplink mapping, doc/zip/chart/table, representation choice, fallback, grammar, rewrite, history integration, image→tooling, leakage safety.

3. Language specialization & topic hygiene = SFT-LoRA.• Cantonese_Ability, Topic_Hygiene.

4. Each lane is trained independently.• No multi-lane joint training.
• No shared optimizer across lanes.
• Each lane produces either:• A full SFT checkpoint, or
• A LoRA adapter, or
• A classifier head, or
• A mapping head.


5. Runtime behavior is defined by upstream/downstream routing, not training order.• Training order is operational, not semantic.
• What matters is how lanes are wired at inference time.

6. Base model protection.• Once core SFT lanes are trained and validated, freeze the base weights for all subsequent LoRA and classifier training.
• No later SFT is allowed to overwrite previously validated SFT behavior without explicit PCT-perf approval.

7. LoRA isolation.• All LoRA and classifier-LoRA lanes must be trained with the base model frozen.
• Only adapter weights and classifier heads are updated.

8. No lane may change its schema, labels, or semantics without a spec update.• If a new behavior is needed, create a new lane (e.g., Lane 37) rather than mutating an existing one.



---

##3. Global hyperparameter conventions

These are relative knobs per lane; actual numeric LR/batch/steps follow your existing infra defaults.

• Depth levels → sampling_weight / loss_weight / lr_multiplier:• Very High depth:• sampling_weight = 3.0
• loss_weight = 1.3
• lr_multiplier = 1.0 (SFT)

• High depth:• sampling_weight = 2.0
• loss_weight = 1.1
• lr_multiplier = 1.0 (SFT or SFT-LoRA)

• Medium depth:• sampling_weight = 1.0
• loss_weight = 1.0
• lr_multiplier = 1.0 (SFT or 1.1 for LoRA mapping/trigger lanes)

• Low depth:• sampling_weight = 0.5
• loss_weight = 0.9
• lr_multiplier = 1.0 (or 0.9 for precision lanes)


• LoRA-specific LR multiplier:• Tool/connector/deeplink mapping and triggers: lr_multiplier = 1.1
• Precision lanes (translate, grammar, safety): lr_multiplier = 0.9–1.0

• Classifier-LoRA:• Use the same base LR as LoRA, with lr_multiplier = 1.0–1.1 depending on lane importance.



---

##4. Runtime routing graph (upstream/downstream)

This defines how lanes are used at inference time to avoid forgetting and ensure each lane’s knowledge is actually exercised.

4.1 Upstream (always first)

1. Mode & representation routing• Lane 31 — Mode Selection (classifier-LoRA)
• Lane 32 — Representation Choice (LoRA)

2. Intent & safety routing• Lane 6 — General Intent Classification (classifier-LoRA)
• Lane 29 — Safety: History/Politics (SFT)
• Lane 30 — Safety: No Leakage (LoRA)
• Lane 28 — Emote6 Labeling (classifier-LoRA)
• Lane 35 — Topic Hygiene (SFT-LoRA)
• Lane 21 — Rewrite (LoRA, when explicitly requested)
• Lane 23 — Grammar Fix (LoRA, when explicitly requested)

3. Action triggering• Lane 7 — Search Trigger (LoRA)
• Lane 24 — History Search Trigger (classifier-LoRA)
• Lane 10 — Connector Intent Detection (classifier-LoRA)
• Lane 37 — Deeplink Intent Detection (classifier-LoRA, new)



4.2 Midstream (conditional)

1. Action mapping• Lane 8 — Search Integration (SFT)
• Lane 25 — History Search Integration (LoRA)
• Lane 11 — Connector Action Mapping (LoRA)
• Lane 12 — Deeplink Action Mapping (LoRA)
• Lane 27 — Image → Tooling (LoRA)



4.3 Downstream (final generation)

1. Core generation• Lane 1 — Identity (SFT)
• Lane 2 — Tone (SFT)
• Lane 3 — Think Mode (SFT)
• Lane 4 — Quick Mode (SFT)
• Lane 5 — Conversation Mode (SFT)
• Lane 19 — Continuity Decision (SFT)
• Lane 20 — Continuity Execution (SFT)
• Lane 22 — Translate (SFT)
• Lane 26 — Image Context Understanding (SFT)
• Lane 15 — Code Generation (SFT)
• Lane 17 — Comparison Tables (LoRA)
• Lane 18 — Chart Spec (LoRA)
• Lane 13 — Doc Export Spec (LoRA)
• Lane 14 — Zip Wrap Spec (LoRA)
• Lane 16 — Code JSON Spec Mode (LoRA)
• Lane 33 — Fallback Behavior (LoRA)
• Lane 34 — Cantonese Ability (SFT-LoRA)



This routing ensures no lane is “forgotten”: each trained behavior has a clear, deterministic place in the runtime graph.

---

##5. Per-lane training configuration (authoritative)

For each lane:

• train_type: SFT | LoRA | SFT-LoRA | classifier-LoRA
• model: Dino 4B | Dino Pro 7B | Dino Pro 8B
• sampling_weight
• loss_weight
• lr_multiplier
• base_frozen: true | false
• notes: key behavior + upstream/downstream role


Phase grouping is conceptual only; training jobs are independent.

---

Lanes 1–5: Core identity and modes (SFT)

1. Lane 1 — Identity & Self-Definition• train_type: SFT
• model: Dino 4B, Dino Pro 7B
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: false (this is one of the first SFT passes)
• Role: Defines Dino’s self-description, boundaries, and stable persona.

2. Lane 2 — Tone & Behaviour• train_type: SFT
• Same config pattern as Lane 1.
• Role: Enforces tone, politeness, emotional stance.

3. Lane 3 — Think Mode• train_type: SFT
• sampling_weight: 3.0
• loss_weight: 1.3
• lr_multiplier: 1.0
• base_frozen: false (core reasoning shaping)
• Role: Deep, step-by-step reasoning.

4. Lane 4 — Quick Mode• train_type: SFT
• Same as Lane 3.
• Role: Fast, concise answers.

5. Lane 5 — Conversation Mode• train_type: SFT
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: false
• Role: Natural conversational flow.



---

Lanes 6–8, 19–20, 22, 24–25: Intent, continuity, search, history

1. Lane 6 — General Intent Classification• train_type: classifier-LoRA
• model: Dino 4B, Dino Pro 7B
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: Classifies intent_family / intent_subtype.

2. Lane 7 — Search Triggering• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true
• Role: Decides needs_search: true/false.

3. Lane 8 — Search Integration• train_type: SFT
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: false during its SFT run; later frozen.
• Role: Teaches how to integrate search results into responses.

4. Lane 19 — Continuity Decision


• train_type: SFT
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: false during its SFT run.
• Role: Chooses use_continuity vs suppress_continuity.


1. Lane 20 — Continuity Execution


• train_type: SFT
• Same config as Lane 19.
• Role: Actually uses prior content when continuity is enabled.


1. Lane 22 — Translate


• train_type: SFT
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 0.9 (precision)
• base_frozen: false during its SFT run.
• Role: Multilingual translation.


1. Lane 24 — History Search Trigger


• train_type: classifier-LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: Decides needs_history_search and history_scope.


1. Lane 25 — History Search Integration


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: Uses retrieved history content in responses.


---

Lanes 9–12, 37: Multi-step, connectors, deeplink

1. Lane 9 — Multi-Step Action Flow• train_type: SFT
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: false during its SFT run.
• Role: Flow_state handling, multi-turn action flows.

2. Lane 10 — Connector Intent Detection


• train_type: classifier-LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true
• Role: connector_needed: true/false + connector-related subtypes.


1. Lane 11 — Connector Action Mapping


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true
• Role: Maps to connector_action tool_call.


1. Lane 12 — Deeplink Action Mapping


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true
• Role: Maps to deeplink_action tool_call.


1. Lane 37 — Deeplink Intent Detection (NEW)


• Type: Classifier LoRA
• Model: Dino 4B, Dino Pro 7B
• Total dataset lines: ~25,000 (recommended)
• Synthetic / Real: 80% synthetic / 20% real
• Multilingual: EN focus (same as Lane 12)
• Language distribution:• en: 85%
• zh-hk: 10%
• zh-hant: 3%
• zh-hans: 2%

• Required schema fields:• language
• mode
• tone
• emote6 → "neutral"
• representation_choice
• continuity_choice → "suppress_continuity"
• intent_family
• intent_subtype → deeplink-related (e.g., open_app, navigate_to, play_media, open_note, open_browser, open_settings, open_contact, open_chat, open_playlist, open_map_location)
• safety_tag
• needs_search → false
• needs_history_search → false
• history_scope → "thread_only"
• user_message
• assistant_response → optional explanation
• New classifier label: deeplink_needed: true | false

• Duplication tolerance:• Max token overlap: ≤ 35%
• deeplink_needed true/false split: ~50/50
• At least 10 deeplink-related subtypes represented.

• Training config:• train_type: classifier-LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true

• Role: Decides whether a user message requires a deeplink action.• Upstream of Lane 12.
• Parallel to Lane 10 (connector intent).



---

Lanes 13–18: Structured formats

1. Lane 13 — Doc Export Spec


• train_type: LoRA
• sampling_weight: 0.5
• loss_weight: 0.9
• lr_multiplier: 1.0
• base_frozen: true
• Role: export_document spec generation.


1. Lane 14 — Zip Wrap Spec


• train_type: LoRA
• Same as Lane 13.
• Role: zip_list spec generation.


1. Lane 16 — Code JSON Spec Mode


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: JSON-like code specs.


1. Lane 17 — Comparison Tables


• train_type: LoRA
• sampling_weight: 0.5
• loss_weight: 0.9
• lr_multiplier: 1.0
• base_frozen: true
• Role: Markdown comparison tables.


1. Lane 18 — Chart Spec


• train_type: LoRA
• Same as Lane 17.
• Role: chart_spec-like structures.


---

Lanes 21–23, 28–30, 31–33: Rewrite, grammar, safety, mode, representation, fallback

1. Lane 21 — Rewrite


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: Rewriting user text.


1. Lane 23 — Grammar Fix


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 0.9
• base_frozen: true
• Role: Grammar correction.


1. Lane 28 — Emote6 Labeling


• train_type: classifier-LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: Emote6 classification.


1. Lane 29 — Safety: History/Politics


• train_type: SFT
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 0.9
• base_frozen: false during its SFT run.
• Role: Corrects misinformation, enforces sensitive-topic safety.


1. Lane 30 — Safety: No Leakage


• train_type: LoRA
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 0.9
• base_frozen: true
• Role: Prevents system prompt/model detail leakage.


1. Lane 31 — Mode Selection


• train_type: classifier-LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: mode_label: quick | think | conversation.


1. Lane 32 — Representation Choice


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: true
• Role: representation_choice selection.


1. Lane 33 — Fallback Behavior


• train_type: LoRA
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: true
• Role: Graceful fallback when tools/search unavailable.


---

Lanes 15, 26–27: Code and images

1. Lane 15 — Code Generation


• train_type: SFT
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: false during its SFT run.
• Role: Code writing, bug-fix, refactor.


1. Lane 26 — Image Context Understanding


• train_type: SFT
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.0
• base_frozen: false during its SFT run.
• Role: Understands image_context and describes content.


1. Lane 27 — Image → Tooling


• train_type: LoRA
• sampling_weight: 1.0
• loss_weight: 1.0
• lr_multiplier: 1.1
• base_frozen: true
• Role: Maps image context to web_fetch or connector_action.


---

Lanes 34–35: Cantonese and topic hygiene (SFT-LoRA)

1. Lane 34 — Cantonese_Ability


• train_type: SFT-LoRA
• model: Dino Pro 8B
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: true
• Role: Natural HK Cantonese, code-switching, cultural grounding.


1. Lane 35 — Topic_Hygiene


• train_type: SFT-LoRA
• model: Dino Pro 8B
• sampling_weight: 2.0
• loss_weight: 1.1
• lr_multiplier: 1.0
• base_frozen: true
• Role: Prevents topic dragging; only references past topics when explicitly requested.


---

##6. How to avoid unintended model “forgetting”

1. Freeze base after core SFT passes.• Run SFT for lanes 1, 2, 3, 4, 5, 8, 9, 15, 19, 20, 22, 26, 29.
• Validate.
• Freeze base weights.
• All subsequent LoRA / classifier / SFT-LoRA training must use base_frozen: true.

2. Never run later SFT on the same base without explicit re-baselining.• If a new SFT lane is needed, it must be part of a planned SFT phase, not ad-hoc.

3. Use lane-specific validation suites.• Each lane must have a fixed test set.
• After training any new lane, re-run:• Core behavior tests (identity, tone, reasoning)
• Lane-specific tests

• If any regression is detected, the new adapter/head is rejected or revised.

4. No adapter stacking without explicit routing.• At runtime, only the relevant adapters are activated per request.
• No “all adapters always on” behavior.

5. No schema drift.• Builders must not add/remove fields, labels, or values beyond this spec.
• Any new behavior requires a new lane and a spec update.



---

##7. Implementation viability on a 4090 Ubuntu box

• SFT lanes (4B/7B/8B) are trained one at a time with:• Gradient accumulation
• Mixed precision
• Reasonable batch sizes

• LoRA and classifier-LoRA lanes are lightweight and easily trainable on a 4090.
• No lane requires impossible memory or compute.
• The separation of SFT vs LoRA ensures you don’t repeatedly retrain the full model.


---

End of master spec.

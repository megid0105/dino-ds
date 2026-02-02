# SYNTHETIC DATASET LOCK SPEC (FINAL)

## 1. Purpose of Synthetic Data
Synthetic data is used ONLY for:
- structural behavior (tool_call, deeplink, connector, doc/zip, chart/table)
- safety patterns
- identity & tone shaping
- continuity logic
- image_context → reasoning
- rewrite/translate/grammar
- mode selection
- representation choice

Synthetic MUST NOT be used to teach:
- facts
- history
- politics
- geography
- science
- world knowledge
- biographies
- statistics
- current events

Synthetic = structure, not knowledge.

---

## 2. Synthetic Dataset Composition Rules

### 2.1 Diversity Requirements
Every synthetic dataset must:
- use **≥ 40 templates** per training track  
- vary:
  - sentence structure  
  - tone  
  - length  
  - user intent  
  - languages  
  - emotional framing  
  - context  
- include **negative examples** (bad answers + corrected answers)

### 2.2 No Repetition
- No two synthetic samples may share > 60% token overlap.
- No repeated Q/A pairs.
- No repeated phrasings across templates.

### 2.3 Multi-turn Required
- ≥ 70% of synthetic samples must be **multi-turn dialogues**.
- Single-turn synthetic is allowed only for:
  - tool_call specs  
  - doc/zip/chart/table specs  
  - code JSON specs  

### 2.4 No Synthetic Facts
Synthetic must NEVER:
- define a factual answer  
- define a historical event  
- define a political claim  
- define a scientific explanation  
- define a biography  

If a synthetic sample needs “content,” it must be:
- fictional  
- abstract  
- placeholder  
- or obviously non-factual  

Example:
- “The fictional city of Lumeria has 3 districts…”

---

## 3. Synthetic Dataset Ratios (Locked)

### Structural tasks  
**80% synthetic / 20% real-world**

### Reasoning tasks  
**30% synthetic / 70% real-world**

### Safety, identity, tone  
**90% synthetic / 10% real-world**

### Image understanding  
**60% synthetic / 40% real-world**

---

## 4. Synthetic Generation Pipeline

### 4.1 Inputs
- Template library (40–60 templates per track)
- Tone rules
- Behaviour rules
- Connector/deeplink schemas
- Tool_call schemas
- image_context schema
- emote6 labels
- mode labels

### 4.2 Generation Steps
1. Randomly select:
   - template  
   - tone  
   - behaviour rule  
   - language  
   - emotional intent  
   - mode  
2. Generate synthetic dialogue  
3. Validate:
   - no factual claims  
   - no repetition  
   - no hallucination  
   - correct schema  
4. Add negative sample  
5. Add multilingual variant  
6. Add style variation  

### 4.3 Validation Rules
- Reject if answer mirrors user question  
- Reject if answer repeats template phrasing  
- Reject if answer contains real-world facts  
- Reject if answer is too short (< 20 tokens)  
- Reject if answer is too long (> 250 tokens)  
- Reject if schema fields missing  

---

## 5. Synthetic Dataset Safety Locks

### 5.1 Forbidden in synthetic
- Real political figures  
- Real historical events  
- Real countries’ political claims  
- Real scientific facts  
- Real medical advice  
- Real legal advice  
- Real product specifications  
- Real companies (except as connector names)  

### 5.2 Allowed in synthetic
- Fictional entities  
- Abstract placeholders  
- Generic names (“Alex”, “Jamie”)  
- Generic tasks (“draft an email”, “create a calendar event”)  
- Generic objects (“a red box”, “a blue device”)  

---

## 6. Synthetic Dataset Output Format
All synthetic samples must include:
- `mode`
- `emote6`
- `tone` (Family / Serious / Professional / Friendly / Best Friend)
- `tool_call` (if applicable)
- `image_context` (if applicable)
- `history_search` (if applicable)
- `continuity_choice`
- `representation_choice`
- `safety_tag`
- `language`
- `assistant_response`

---

# FINAL RULE
Synthetic data **must never overwrite Dino’s knowledge**.  
It must only teach **structure, behaviour, tone, and tool usage**.



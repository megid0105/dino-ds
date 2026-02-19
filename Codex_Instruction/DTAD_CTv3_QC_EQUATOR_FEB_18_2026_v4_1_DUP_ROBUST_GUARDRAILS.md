# DTAD CT v3 — QC EQUATOR (FINAL, Stable)
## Version: FEB 18 2026 — v4.1 (Duplication Robustness + Training-Quality Guardrails)
Date: 2026-02-18
Change control: Only DTAD CT v3 may revise this equator. Revisions must increment version/date and be announced as **REPLACES PRIOR**.

> Purpose: v4.1 keeps the **duplication-robust** improvements from v4 while adding **explicit scope fences** so QC threads cannot apply masking/IDF/embeddings to the wrong sections (which could compromise training quality).

---

## What changed vs v4 (REPLACES PRIOR)
1) **Explicit “Where each rule applies” matrix** (new §0) so ops cannot drift.
2) **Hard guardrails**: boilerplate masking + IDF weighting + embeddings are **duplication-only** and **must never** influence repetition/naturalness, invariants, leakage, or viability.
3) **Short-text protection clarified**: it can suppress *duplication* false positives only; it cannot downgrade repetition or leakage failures.

---

# 0) Applicability matrix (READ FIRST — NO DRIFT)

| Gate / Metric | Applies to | MUST NOT be used for | Notes |
|---|---|---|---|
| **Hard invariants** (§1) | All lanes, all rows | Any text scoring | Schema/roles/field alignment/labels are absolute. |
| **Normalization** (§2) | All sections | Changing stored text | Stored text is never rewritten; normalization is for analysis only. |
| **Tokenization** (§3) | Repetition + Duplication | Leakage detection | Leakage is string-level; do not “mask then scan.” |
| **Malformed-text** (§4) | All lanes | Duplication confirm exceptions | Malformed is fatal regardless of duplication view. |
| **Repetition/Naturalness** (§5) | Per-row only | Duplication robustness tools | **NO masking/IDF/embeddings** in §5. |
| **Mechanism leakage** (§10) | Per-row string-level | Any masked/normalized view | Scan the raw assistant_response (trim only). |
| **Duplication/Overlap** (§6) | Pairwise within language slice | Repetition / leakage / invariants | v4 tools apply **only here**. |
| **Proportions** (§8) | Language slice with n>=30 | Any per-row fail | Do not fail small n. |
| **Viability** (§9) | Run-level | Any text quality judgement | Only underfill/attempts thresholds. |

**Hard rule:** If a row fails **§1/§4/§5/§10**, it is **FAIL** even if duplication metrics are “robust-pass”.

---

# 1) Hard invariants (FATAL)
Fail immediately if any are violated:
1. JSONL parse: every line is valid JSON object.
2. Role contract:
   - **Single-turn lanes:** exactly 3 messages `[system? , user, assistant]`
   - **Multi-turn lanes:** `[system?] + alternating user/assistant, minimum 4 messages after removing system (user→assistant→user→assistant), per lane contract
3. Field alignment:
   - user_message == messages[1].content
   - assistant_response == last assistant message content (and, for single-turn lanes, == messages[2].content)
4. Forbidden fields absent (anything outside schema contract).
5. Label consistency: labels match hard-lock enums.
6. Language integrity: row matches lane file language (except lanes explicitly marked special).

---

# 2) Normalization (FIXED)
Order:
1) Unicode NFKC
2) Whitespace collapse to single spaces; trim ends
3) Casefold: Latin only
4) Punctuation ignored for tokenization only (stored text unchanged)
5) Accents/diacritics preserved; Devanagari marks preserved

---

# 3) Tokenization (SCRIPT-AWARE)

## 3A) Latin scripts (en, es, fr, de, it, pt-br)
Regex word spans: letters/digits with internal apostrophes and hyphens allowed.

## 3B) CJK (zh-hk, zh-hant, zh-hans, ja, ko)
Two views:
- CJK char tokens (sensitive view)
- Latin/digit runs tokenized as Latin words  
**Note:** For duplication confirmation, prefer word/bigram view where defined by the lane toolchain; do not hard-fail on raw char containment alone (see §6C carve-outs).

## 3C) Thai (th)
Primary: Thai word segmentation (ICU/newmm style).  
Fallback: character bigrams/trigrams (not single chars).

## 3D) Hindi (hi)
Whitespace word tokens; keep Devanagari marks attached; strip punctuation for tokenization only.

---

# 4) Malformed-text gate (FATAL)
Fail if either triggers:
- Character fragmentation (Latin + Hindi): excessive single-char “word” tokens at sufficient length.
- Script corruption: abnormal unexpected-script ratio for that language slice.

---

# 5) Repetition / Naturalness gate (FATAL with precision) — **RAW TEXT ONLY**
Applied per assistant_response after normalization + tokenization.

## 5A) Adjacent duplicate token (always fatal)
If any t[i] == t[i+1] → FAIL

## 5B) Triplicate token in 12-window
W=12.
- Content token triplicate → FAIL
- Function-word-only triplicate → WARN

## 5C) Triplicate bigram in 30-window
W=30.
- Content bigram triplicate → FAIL
- Function-word-only triplicate → WARN

**Thai/CJK:** compute repetition on word tokens or char bigrams/trigrams; never single-character tokens.

**PROHIBITED in §5:** boilerplate masking, IDF weighting, embeddings, semantic similarity.  
(These can hide training-poison repetitions; do not use them here.)

---

# 6) Duplication / overlap gate (two-stage, language-internal) — **ROBUST VIEW ALLOWED ONLY HERE**

## 6A) Base overlap score (multiset containment)
O_min = multiset_intersection / min_len

## 6B) Candidate trigger (Stage A)
If O_min > candidate_threshold → candidate duplicate pair  
Thresholds are lane-dependent (lane.yaml / v17 spec). Defaults:
- candidate_threshold: 0.30

## 6C) Confirmation (Stage B) — robust rules
Confirm FAIL if any true:

### Rule 1 (contain-duplicate)
- If O_min > contain_threshold → FAIL  
Default contain_threshold: 0.55  
**Thai/CJK:** do not use raw char-token containment as standalone FAIL.

### Rule 2 (multi-signal confirm; 2-of-3)
FAIL if at least 2 are true:
- O_min > candidate_threshold
- O_jac > O_jac_threshold (default 0.38)
- C3 > C3_threshold (defaults: Latin/hi 0.26; CJK/th 0.30)

## 6D) v4 Robustness tools (duplication-only)
These tools exist to reduce *false duplication FAILs* caused by shared skeletons, while preserving true-dup detection.

### 6D.1 Boilerplate masking view (duplication-only)
- Create a **masked view** of assistant_response removing a centrally-maintained boilerplate pattern set (headers like “Summary:”, generic scaffolds, fixed disclaimers), **only for computing duplication metrics**.
- Stored text remains unchanged.
- **MUST NOT** be used for repetition/naturalness (§5) or leakage (§10).

### 6D.2 IDF-weighted overlap (duplication-only, optional)
- Optionally compute an IDF-weighted variant of overlap to de-emphasize very common tokens/phrases in the lane.
- Use only as a **tie-breaker** in Stage B confirmation (never to override a true hard contain-dup).

### 6D.3 Short-text protection (duplication-only)
- If both responses are very short, containment metrics can be unstable.
- Short-text protection may **downgrade duplication confirmation to WARN** when:
  - min_len is below a lane-defined minimum token count (lane.yaml), **and**
  - multi-signal confirmation is not met.
- **MUST NOT** downgrade repetition, leakage, invariants, or malformed-text failures.

### 6D.4 Embedding semantic similarity (duplication-only, optional)
- Embeddings may be used only as an **additional confirm signal** when available.
- Embeddings must never be required to PASS.
- Embeddings must never be used to downgrade a repetition/leakage failure.

## 6E) Hindi duplication override (duplication-only)
If Hindi O_min > candidate_threshold but C3 < 0.20 → downgrade duplication to WARN.  
(Does not override malformed/repetition/leakage gates.)

---

# 7) Opening diversity gate (WARN → conditional FATAL)
Warn if opening overlap > 0.60.  
Conditional FAIL only if repeated opening family exceeds lane-defined % when n>=100 (default 8%).

---

# 8) Mode/tone proportion gates (FATAL only when n>=30)
Enforced only when n>=30 per language slice.  
Targets/tolerances are lane-dependent; defaults: Mode 50/50 ±10pp; tone buckets 10–30%.

---

# 9) Generation viability gate
FATAL if underfilled rows exist.  
attempts/row thresholds are run-type dependent; defaults: WARN>80, FAIL>150.

---

# 10) Mechanism leakage / templating markers (FATAL) — **RAW TEXT ONLY**
Fail if assistant_response includes obvious internal scaffolding:
- raw JSON tool calls, placeholders ([SLOT], <<...>>, {...}), “chain-of-thought/reasoning:” dumps, router debug objects.

**NOTE:** Naturalness hard rejects (e.g., adjacent duplicate token like “by by”) are fatal even if validate/gate_lane passes. Repetition is fatal only per §5A–§5C.

**PROHIBITED in §10:** masking, normalization beyond trim, tokenization-based screening. Scan the raw assistant_response.

---

# 11) Gate order
Invariants → malformed → repetition/naturalness → leakage → duplication → proportions → viability → warn-only.

---

# 12) Decision rule
Any fatal hit = FAIL. WARNs never fail unless explicitly promoted in this document.

---

# 13) Ops “Do/Don’t” checklist (copy into QC threads)
**DO**
- Apply masking/IDF/embeddings only in **§6 duplication**.
- Always run repetition (§5) and leakage (§10) on **raw text**.
- Use lane spec thresholds when provided.

**DON’T**
- Don’t mask boilerplate before scanning for leakage.
- Don’t use semantic similarity to excuse adjacent duplicates or triplicates.
- Don’t downgrade a repetition/leakage failure because duplication looks fine.

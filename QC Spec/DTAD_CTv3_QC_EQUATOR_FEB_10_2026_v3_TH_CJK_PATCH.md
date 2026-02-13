# DTAD CT v3 — QC EQUATOR (FINAL, Stable)
## Version: FEB 10 2026 — v3 (Thai/CJK Tokenization + Gate Patch)
Date: 2026-02-10
Change control: Only DTAD CT v3 may revise this equator. Revisions must increment version/date and be announced as **REPLACES PRIOR**.

---

## What changed vs v2 (REPLACES PRIOR)
This v3 update is a controlled carve‑out for **Thai + CJK** to improve **training quality** and **effort viability** by reducing false FAILs caused by single‑character tokenization.

1) **§3C Thai tokenization**
- Switched from per‑character tokens to **Thai word segmentation** (ICU / newmm‑style).
- Added a deterministic fallback: **character bigrams** (not single chars) if word segmentation is unavailable.

2) **§5B/§5C repetition gates for th + CJK**
- Repetition checks for **th + CJK** run on **word tokens** (or **char bigrams/trigrams** fallback), **not** on single‑character tokens.

3) **§6 duplication hard‑fail rule for th + CJK**
- For **th + CJK**, **do not** use raw **char‑token containment** as a standalone hard FAIL.
- Confirm FAIL only via:
  - multi‑signal confirmation (2‑of‑3) using *(O_min, O_jac, C3)* computed on word/bigram tokens, **or**
  - `(O_min > contain_threshold) AND (C3 > C3_threshold)` together.

Everything else in v2 remains unchanged.

---

# DTAD Training‑Optimized QC Equator (Stable)

## 0) Inputs & slices
- Checks apply within each lane file and within each language slice (when multilingual).
- Repetition checks are per‑row (single assistant_response).
- Duplication checks are pairwise within a language slice.

## 1) Hard invariants (FATAL)
Fail immediately if any are violated:
1. JSONL parse: every line is valid JSON object.
2. Role order: messages = [system, user, assistant] (exactly 3).
3. Field alignment:
   - user_message == messages[1].content
   - assistant_response == messages[2].content
4. Forbidden fields absent (anything outside schema contract).
5. Label consistency: labels match hard‑lock enums.
6. Language integrity: row matches lane file language (except lanes explicitly marked special).

## 2) Normalization (FIXED)
Order:
1) Unicode NFKC
2) Whitespace collapse to single spaces; trim ends
3) Casefold: Latin only
4) Punctuation ignored for tokenization only (stored text unchanged)
5) Accents/diacritics preserved; Devanagari marks preserved

## 3) Tokenization (SCRIPT‑AWARE)

### 3A) Latin scripts (en, es, fr, de, it, pt‑br)
- Regex word spans: letters/digits with internal apostrophes and hyphens allowed.

### 3B) CJK (zh‑hk, zh‑hant, zh‑hans, ja, ko)
Compute two views:
1) **Primary for overlap**: CJK char tokens, but see §6 carve‑out (no standalone hard contain‑fail).
2) Latin/digit runs inside are tokenized as Latin word tokens.

### 3C) Thai (th) — **UPDATED in v3**
Primary tokens:
- **Thai word segmentation** (ICU word break / newmm‑style).
Fallback if segmentation unavailable:
- **Character bigrams** (sliding window over Thai codepoints; exclude whitespace/common punctuation).
Notes:
- No dictionary segmentation is required if ICU word break exists; fallback is deterministic.

### 3D) Hindi (hi)
- Split on whitespace into words; strip punctuation; keep combining marks attached.

## 4) Malformed‑text gate (FATAL)
Fail if either triggers:
- Character fragmentation (Latin + Hindi): excessive single‑char “word” tokens at sufficient length.
- Script corruption: abnormal unexpected‑script ratio for that language slice.

## 5) Repetition / Naturalness gate (FATAL with precision)

### 5A) Adjacent duplicate token (always fatal)
If any t[i] == t[i+1] → FAIL  
(For th/CJK, “token” uses §3C/§3B primary view.)

### 5B) Triplicate token in 12‑window
Window W=12.
- If any token occurs ≥3 times inside any window:
  - content token → FAIL
  - function‑word‑only → WARN

**th/CJK rule (v3):**
- Compute this on **word tokens** (Thai segmentation / CJK word view where available), else on **char bigrams/trigrams**.
- Do **not** compute triplicates on single‑character tokens.

### 5C) Triplicate bigram in 30‑window
Window W=30.
- If any bigram occurs ≥3 times inside any window:
  - both tokens content → FAIL
  - function‑word‑only → WARN

**th/CJK rule (v3):**
- Compute on **word tokens** or **char bigrams/trigrams**, not single chars.

## 6) Duplication / overlap gate (two‑stage, language‑internal)

### 6A) Overlap score (multiset containment)
O_min = multiset_intersection / min_len

### 6B) Stage A — candidate
If O_min > candidate_threshold → candidate duplicate pair  
Thresholds are lane‑dependent (lane.yaml / v17 spec). Defaults:
- candidate_threshold: 0.30

### 6C) Stage B — confirm FAIL
Confirm FAIL if any true:

**Rule 1 (contain‑duplicate):**
- If O_min > contain_threshold → FAIL  
Defaults:
- contain_threshold: 0.55

**Rule 2 (2‑of‑3 confirm):** FAIL if at least 2 are true:
- O_min > candidate_threshold
- O_jac > O_jac_threshold (default 0.38)
- C3 > C3_threshold (defaults: Latin/hi 0.26; CJK/th 0.30)

#### **th/CJK carve‑out (v3) — IMPORTANT**
For **th + CJK**:
- **Do not use Rule 1 as a standalone FAIL** when O_min is computed from raw char tokens.
- Confirm FAIL only via either:
  1) **Rule 2 (2‑of‑3)** computed on **word tokens** (preferred) or **char bigrams/trigrams** (fallback), or
  2) `(O_min > contain_threshold) AND (C3 > C3_threshold)` together, with O_min computed on **word/bigram tokens**.

### 6D) Hindi override (duplication only)
If Hindi O_min > candidate_threshold but C3 < 0.20 → downgrade duplication to WARN.
(Does not override malformed/repetition gates.)

## 7) Opening diversity gate (WARN → conditional FATAL)
- Warn if opening overlap > 0.60.
- Conditional FAIL only if repeated opening family exceeds 8% when n>=100 (lane may override).

## 8) Mode/tone proportion gates (FATAL only when n>=30)
- Enforced only when n>=30 per language slice.
- Targets/tolerances are lane‑dependent (lane.yaml / v17 spec); defaults: Mode 50/50 ±10pp; tone buckets 10–30%.

## 9) Generation viability gate
- FATAL if underfilled rows exist.
- attempts/row thresholds are run‑type dependent (smoke vs full); defaults: WARN>80, FAIL>150.

## 10) Mechanism leakage / templating markers (FATAL)
Fail if assistant_response includes obvious internal scaffolding:
- raw JSON tool calls, placeholders ([SLOT], <<...>>, {...}), “chain‑of‑thought/reasoning:” dumps, router debug objects.
**NOTE:** Naturalness hard rejects (e.g., adjacent duplicate token like “by by”) are fatal even if validate/gate_lane passes. Repetition is fatal only per §5A–§5C; function‑word‑only triplicates remain WARN.

## 11) Gate order
Invariants → malformed → repetition/naturalness → leakage → duplication → proportions → viability → warn‑only.

## 12) Decision rule
Any fatal hit = FAIL. WARNs never fail unless explicitly promoted in this document.

---

## Implementation note for ops threads (one‑liner)
- For **th/CJK**: run repetition + duplication checks on **word tokens** (or **char bigrams/trigrams** fallback); **do not** hard‑fail duplication using raw char containment alone.

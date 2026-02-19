from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import re
import subprocess
from collections import Counter, deque
from typing import Any
import uuid

from ..contracts.v16_lane_contracts import contract_for_lane
from .duplication_gate_v41 import check_pairwise as check_duplication_pairwise_v41
from .lane_policy_v17 import get_lane_policy
from .malformed_gate_v41 import evaluate_row_malformed_v41
from .qc_report_writer_v17 import write_qc_report
from .repetition_gate_v41 import evaluate_row_repetition_v41
from .row_validator_v16 import validate_row_v16
from .safety_content_gate_v17 import check_content_safety
from .turn_structure_invariant_v17 import check_turn_structure
from .v17_lane_validator import validate_row_v17

try:
    from pythainlp.tokenize import word_tokenize as _THAI_WORD_TOKENIZE
except Exception:  # pragma: no cover - optional dependency
    _THAI_WORD_TOKENIZE = None


_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_LATIN_RUN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_MECH_LEAK_RE = re.compile(
    r"(?i)\b(tool_call|connector_action|deeplink_action|image_tool_action|web_fetch|router|schema|chain[- ]of[- ]thought)\b"
)
_PLACEHOLDER_RE = re.compile(r"\[[A-Z_]{2,}\]|<<[^>\n]{1,80}>>|\{[A-Za-z_]*(slot|placeholder)[A-Za-z_]*\}", re.IGNORECASE)
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")

_CJK_LANGS = {"zh-hk", "zh_hk", "zh-hant", "zh_hant", "zh-hans", "zh_hans", "ja", "ko"}
_THAI_LANGS = {"th"}
_HI_VI_LANGS = {"hi", "vi"}
_ASIAN_CHAIN_LANGS = _CJK_LANGS | _THAI_LANGS | _HI_VI_LANGS
_LANE_ID_RE = re.compile(r"^lane_(\d+)")
_LANG_IN_DETAIL_RE = re.compile(r"\blanguage=([A-Za-z0-9_-]+)\b")
_PAIR_ROWID_RE = re.compile(r"^([^\s]+)\s+vs\s+[^\s]+")
_PAIR_BOTH_ROWIDS_RE = re.compile(r"^([^\s]+)\s+vs\s+([^\s]+)")
_LONG_QUOTED_RE = re.compile(r"'[^'\n]{60,}'|\"[^\"\n]{60,}\"")

_TONE_BALANCED_5: dict[str, float] = {
    "family": 0.20,
    "serious": 0.20,
    "professional": 0.20,
    "friendly": 0.20,
    "best_friend": 0.20,
}

# Spec-encoded mode/tone percentage constraints (v17) for slice-level proportion checks.
# Only exact percentage constraints are encoded here to avoid over-gating.
_SPEC_MODE_TONE_TARGETS: dict[int, dict[str, dict[str, float]]] = {
    1: {
        "mode": {"quick": 1.00, "think": 0.00, "conversation": 0.00},
        "tone": dict(_TONE_BALANCED_5),
    },
    2: {
        "mode": {"quick": 0.50, "think": 0.50, "conversation": 0.00},
        "tone": dict(_TONE_BALANCED_5),
    },
    3: {
        "mode": {"quick": 0.00, "think": 1.00, "conversation": 0.00},
    },
    4: {
        "mode": {"quick": 1.00, "think": 0.00, "conversation": 0.00},
    },
    5: {
        "mode": {"quick": 0.00, "think": 0.00, "conversation": 1.00},
    },
    34: {
        "mode": {"quick": 0.30, "think": 0.00, "conversation": 0.70},
    },
}
_LANE09_FLOW_STATE_TARGETS: dict[str, float] = {
    "none": 0.30,
    "awaiting_user_confirmation": 0.20,
    "awaiting_user_choice": 0.20,
    "awaiting_parameters": 0.15,
    "ready_for_action": 0.15,
}
_LANE28_EMOTE6_BUCKETS: tuple[str, ...] = (
    "happy",
    "sad",
    "angry",
    "fear",
    "encourage",
    "neutral",
)
_LANE28_EMOTE6_MIN_SHARE = 0.10
_LANE30_CREATIVE_EXTRACTION_MIN_SHARE = 0.40
_LANE33_FALLBACK_LIMITATION_MIN_SHARE = 0.40
_LANE33_FALLBACK_MIN_N = 30
_LANE20_PRIOR_REFERENCE_MIN_SHARE = 0.60
_LANE29_MISINFO_CORRECTION_MIN_SHARE = 0.40
_LANE34_COLLOQUIAL_MIN_SHARE = 0.40
_LANE34_CODESWITCH_MIN_SHARE = 0.20
_LANE03_IMPLICIT_MULTISTEP_MIN_SHARE = 0.60
_LANE03_STRUCTURE_MAX_SHARE = 0.05
_LANE04_ANSWER_LEN_LE120_MIN_SHARE = 0.70
_LANE04_ANSWER_LEN_LE60_MIN_SHARE = 0.30
_LANE07_BORDERLINE_MIN_SHARE = 0.40
_LANE07_NEEDS_SEARCH_TARGET = 0.50
_LANE10_BORDERLINE_MIN_SHARE = 0.40
_LANE03_TOOL_CALL_MAX_SHARE = 0.10
_LANE03_IMAGE_CONTEXT_MAX_SHARE = 0.05
_LANE04_TOOL_CALL_MAX_SHARE = 0.05
_LANE04_IMAGE_CONTEXT_MAX_SHARE = 0.03
_LANE05_IMAGE_CONTEXT_MAX_SHARE = 0.02
_OPTIONAL_SHARE_MIN_N = 30
_LANE03_STEP_EN_RE = re.compile(
    r"\b(because|therefore|thus|so that|however|but|if|then|while|although|since|trade-?off|"
    r"option|compare|consider|plan|next)\b",
    re.IGNORECASE,
)
_LANE03_STEP_CJK_RE = re.compile(
    r"因為|所以|因此|但是|但係|不過|如果|然後|先|再|同時|取捨|另一方面|一方面|まず|次に|"
    r"だから|一方|그러나|따라서|먼저|다음"
)
_LANE03_STEP_TH_RE = re.compile(
    r"เพราะ|ดังนั้น|แต่|อย่างไรก็ตาม|ถ้า|แล้ว|ต่อไป|อีกด้าน|ข้อดี|ข้อเสีย"
)
_LANE03_EXPLICIT_STEP_RE = re.compile(
    r"(?im)\b(first|second|third|step\s*[1-9])\b|^\s*\d+[.)]\s+|^\s*-\s+(first|second|third)\b"
)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？\n]+")
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
_LANE0710_BORDERLINE_LABEL_RE = re.compile(
    r"(borderline|ambig|clarif|disambigu|uncertain|underspec|needs_more_info)",
    re.IGNORECASE,
)
_LANE0710_BORDERLINE_ASST_EN_RE = re.compile(
    r"\b(clarify|could you clarify|can you clarify|do you mean|what exactly|which one|which .* do you mean|"
    r"can you share more|before i proceed|to proceed.*need|which account|which app|which city|which date)\b",
    re.IGNORECASE,
)
_LANE0710_BORDERLINE_ASST_CJK_RE = re.compile(
    r"請問|请问|可以講清楚|可唔可以講清楚|你係指|你是指|哪個|哪个|哪一個|邊個|再確認|再确认|先確認|先确认|補充"
)
_LANE0710_BORDERLINE_ASST_TH_RE = re.compile(
    r"ขอรายละเอียด|หมายถึง|ช่วยระบุ|ขอข้อมูลเพิ่ม|อยากยืนยัน|ช่วยบอกให้ชัดเจน|อันไหน"
)
_LANE0710_BORDERLINE_USER_HINT_RE = re.compile(
    r"\b(or|which|what should|better|best|vs|versus|should i|not sure|unsure|depends)\b",
    re.IGNORECASE,
)
_THAI_RUN_RE = re.compile(r"[\u0E00-\u0E7F]+")
_LANE33_EN_LIMITATION_RE = re.compile(
    r"\b(can(?:'|’)t|cannot|unable to|not possible|won(?:'|’)t)\b"
    r"|\b(limitations?|caveats?|trade-?offs?)\b"
    r"|\b(depends on|it depends)\b"
    r"|\b(alternatives?|another option|instead)\b"
    r"|\b(i may be wrong|i might be wrong|not certain|uncertain)\b"
    r"|\b(verify|double-check|confirm)\b",
    re.IGNORECASE,
)
_LANE33_CJK_LIMITATION_RE = re.compile(
    r"限制|局限|未必|可能|視乎|取決於|建議.*確認|最好.*確認|替代|另一個方法"
)
_LANE33_TH_LIMITATION_RE = re.compile(
    r"ข้อจำกัด|อาจจะ|ขึ้นอยู่กับ|ทางเลือก|แนะนำให้ตรวจสอบ|ควรตรวจสอบ"
)
_LANE20_PRIOR_REF_EN_RE = re.compile(
    r"\b(earlier|before|previous|last time|as discussed|as we discussed|we discussed|you said|you mentioned|"
    r"from before|from earlier|following up|based on what you said)\b",
    re.IGNORECASE,
)
_LANE20_PRIOR_REF_CJK_RE = re.compile(
    r"之前|先前|剛才|头先|頭先|上次|你話過|你提過|我哋.*(之前|頭先)|延續|跟進|承接"
)
_LANE20_PRIOR_REF_TH_RE = re.compile(
    r"ก่อนหน้านี้|เมื่อกี้|ที่คุยไว้|ที่บอกไว้|ที่พูดไว้|ต่อจาก"
)
_LANE29_CORRECTION_EN_RE = re.compile(
    r"\b(that'?s false|that is false|that'?s not true|not true|incorrect|inaccurate|not quite|"
    r"that's wrong|that is wrong|i can(?:'|’)t assume that as a fact|cannot assume that as a fact|"
    r"denial.*false|is false)\b",
    re.IGNORECASE,
)
_LANE29_CORRECTION_CJK_RE = re.compile(
    r"唔係|不正確|不准确|不準確|錯誤|不是事實|不是真的|有誤|未必正確|並不正確|并不正确|並非事實"
)
_LANE29_CORRECTION_TH_RE = re.compile(
    r"ไม่จริง|ไม่ถูกต้อง|คลาดเคลื่อน|ไม่ใช่ข้อเท็จจริง|ไม่แม่นยำ"
)
_LANE29_CLAIM_EN_RE = re.compile(
    r"\b(always|never|100%|everyone knows|obviously|definitely|hoax|fake|made up|didn'?t happen|"
    r"never happened|rigged|myth)\b",
    re.IGNORECASE,
)
_LANE29_CLAIM_CJK_RE = re.compile(
    r"一定|完全|根本|從來|从来|造假|假|冇發生|没发生|不存在|舞弊|陰謀|阴谋"
)
_LANE29_CLAIM_TH_RE = re.compile(
    r"แน่นอน|ไม่มีทาง|ปลอม|ไม่เคยเกิดขึ้น|โกง|สมคบคิด"
)
_LANE34_COLLOQUIAL_RE = re.compile(
    r"我哋|你哋|佢哋|而家|頭先|咁樣|點算|搞掂|唔使|唔該|返工|收工|睇下|試下|幫手|有冇|"
    r"可唔可以|唔好|唔會|唔係|冇|咗|喺|啲|啦|呀|囉|喎"
)
_LANE34_COLLOQUIAL_STRONG = {
    "有冇",
    "可唔可以",
    "點算",
    "搞掂",
    "返工",
    "收工",
}
_LANE34_LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+-]{1,}")

# Deviation bands requested for Equator §8 proportion check.
_PROPORTION_PASS_MAX_DEV = 0.15
_PROPORTION_FAIL_MIN_DEV = 0.21
_SPEC_VERSION = "Full_Dataset_Spec_FULL_LATEST_v17"
_EQUATOR_VERSION = "DTAD_CTv3_QC_EQUATOR_FEB_18_2026_v4_1"
_GATE_ORDER = (
    "invariants",
    "malformed",
    "repetition",
    "leakage",
    "duplication",
    "proportions",
    "viability",
    "warn_only",
)

_RULE_ALIASES: dict[str, int] = {
    "01": 1,
    "1": 1,
    "rule01": 1,
    "rule_01": 1,
    "baseline": 1,
    "compat": 1,
    "02": 2,
    "2": 2,
    "rule02": 2,
    "rule_02": 2,
    "strict": 2,
    "standard": 2,
    "03": 3,
    "3": 3,
    "rule03": 3,
    "rule_03": 3,
    "strict_plus": 3,
    "strictplus": 3,
    "max": 3,
}


def _safe_preview(text: str, max_chars: int = 180) -> str:
    t = _WS_RE.sub(" ", (text or "").strip())
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def _row_id(rr: dict[str, Any], idx1: int) -> str:
    sid = rr.get("sample_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    rid = rr.get("id")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return f"row#{idx1}"


def _norm_text(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    return _WS_RE.sub(" ", text.strip().lower())


def _norm_lang(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _is_hi_or_vi_lang(lang: str) -> bool:
    if lang in _HI_VI_LANGS:
        return True
    return lang.startswith("hi-") or lang.startswith("hi_") or lang.startswith("vi-") or lang.startswith("vi_")


def _is_asian_chain_lang(lang: str) -> bool:
    if lang in _CJK_LANGS or lang in _THAI_LANGS:
        return True
    return _is_hi_or_vi_lang(lang)


def _expected_lane_language(lane: dict[str, Any]) -> str | None:
    # Lane files are language-scoped; derive one canonical expected language label.
    if not isinstance(lane, dict):
        return None
    for key in ("language",):
        val = lane.get(key)
        norm = _norm_lang(val)
        if norm:
            return norm
    base_row = lane.get("base_row")
    if isinstance(base_row, dict):
        norm = _norm_lang(base_row.get("language"))
        if norm:
            return norm
    te = lane.get("template_expand")
    if isinstance(te, dict):
        slots = te.get("slot_banks")
        if isinstance(slots, dict):
            lang_slot = slots.get("language")
            if isinstance(lang_slot, str):
                norm = _norm_lang(lang_slot)
                if norm:
                    return norm
            if (
                isinstance(lang_slot, list)
                and len(lang_slot) == 1
                and isinstance(lang_slot[0], str)
            ):
                norm = _norm_lang(lang_slot[0])
                if norm:
                    return norm
    return None


def _lane_num_from_id(lane_id: str) -> int | None:
    m = _LANE_ID_RE.match(str(lane_id or "").strip().lower())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _char_ngrams(chars: list[str], n: int) -> list[str]:
    if n <= 1:
        return chars
    if len(chars) < n:
        return []
    out: list[str] = []
    for i in range(0, len(chars) - n + 1):
        out.append("".join(chars[i : i + n]))
    return out


def _token_ngrams(tokens: list[str], n: int, joiner: str = "__") -> list[str]:
    if n <= 1:
        return tokens
    if len(tokens) < n:
        return []
    out: list[str] = []
    for i in range(0, len(tokens) - n + 1):
        out.append(joiner.join(tokens[i : i + n]))
    return out


def _thai_word_tokens(text: str, ignore: set[str] | None = None) -> list[str]:
    if _THAI_WORD_TOKENIZE is None:
        return []
    try:
        words = _THAI_WORD_TOKENIZE(text or "", keep_whitespace=False, engine="newmm")
    except TypeError:
        words = _THAI_WORD_TOKENIZE(text or "")
    except Exception:
        return []
    out: list[str] = []
    for w in words:
        if not isinstance(w, str):
            continue
        tok = w.strip().lower()
        if not tok:
            continue
        if not _THAI_CHAR_RE.search(tok):
            continue
        if ignore and tok in ignore:
            continue
        out.append(tok)
    return out


def _jaccard_from_tokens(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    sa = set(tokens_a)
    sb = set(tokens_b)
    if not sa or not sb:
        return 0.0
    inter = len(sa.intersection(sb))
    union = len(sa.union(sb))
    if union <= 0:
        return 0.0
    return inter / float(union)


def _multiset_overlap_min(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    min_len = min(len(tokens_a), len(tokens_b))
    if min_len <= 0:
        return 0.0
    ca = Counter(tokens_a)
    cb = Counter(tokens_b)
    inter = 0
    for tok, n in ca.items():
        if tok in cb:
            inter += min(n, cb[tok])
    return inter / float(min_len)


def _longest_common_chain_ratio(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    min_len = min(len(tokens_a), len(tokens_b))
    if min_len <= 0:
        return 0.0

    # Longest common contiguous chain (LCSubstring), normalized by min length.
    prev = [0] * (len(tokens_b) + 1)
    best = 0
    for i in range(1, len(tokens_a) + 1):
        cur = [0] * (len(tokens_b) + 1)
        ta = tokens_a[i - 1]
        for j in range(1, len(tokens_b) + 1):
            if ta == tokens_b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best / float(min_len)


def _common_prefix_len(tokens_a: list[str], tokens_b: list[str]) -> int:
    n = min(len(tokens_a), len(tokens_b))
    i = 0
    while i < n and tokens_a[i] == tokens_b[i]:
        i += 1
    return i


def _common_suffix_len(tokens_a: list[str], tokens_b: list[str], prefix_len: int = 0) -> int:
    ia = len(tokens_a) - 1
    ib = len(tokens_b) - 1
    stop_a = max(0, prefix_len)
    stop_b = max(0, prefix_len)
    n = 0
    while ia >= stop_a and ib >= stop_b and tokens_a[ia] == tokens_b[ib]:
        ia -= 1
        ib -= 1
        n += 1
    return n


def _cfg_float(cfg: dict[str, Any], key: str, default: float) -> float:
    v = cfg.get(key)
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    return default


def _cfg_int(cfg: dict[str, Any], key: str, default: int) -> int:
    v = cfg.get(key)
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return int(v)
    return default


def _safe_ratio(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _asian_prefix_divergence_guard(tokens_a: list[str], tokens_b: list[str], cfg: dict[str, Any]) -> tuple[bool, int, int, float]:
    if len(tokens_a) < 4 or len(tokens_b) < 4:
        return False, 0, 0, 0.0

    prefix_min = _cfg_int(cfg, "asian_chain_prefix_min", 2)
    if prefix_min < 1:
        prefix_min = 1
    tail_min = _cfg_int(cfg, "asian_chain_tail_min", 2)
    if tail_min < 1:
        tail_min = 1
    tail_jac_max = _cfg_float(cfg, "asian_chain_tail_jaccard_max", 0.20)
    if tail_jac_max < 0.0:
        tail_jac_max = 0.0
    if tail_jac_max > 1.0:
        tail_jac_max = 1.0

    prefix_len = _common_prefix_len(tokens_a, tokens_b)
    if prefix_len < prefix_min:
        return False, prefix_len, 0, 0.0

    suffix_len = _common_suffix_len(tokens_a, tokens_b, prefix_len=prefix_len)
    end_a = len(tokens_a) - suffix_len if suffix_len > 0 else len(tokens_a)
    end_b = len(tokens_b) - suffix_len if suffix_len > 0 else len(tokens_b)
    tail_a = tokens_a[prefix_len:end_a]
    tail_b = tokens_b[prefix_len:end_b]
    if len(tail_a) < tail_min or len(tail_b) < tail_min:
        return False, prefix_len, suffix_len, 0.0

    tail_jac = _jaccard_from_tokens(tail_a, tail_b)
    if tail_jac <= tail_jac_max:
        return True, prefix_len, suffix_len, tail_jac
    return False, prefix_len, suffix_len, tail_jac


def _tokenize(text: str, ignore: set[str] | None = None, ngram: int = 1, lang: str | None = None) -> list[str]:
    ltag = _norm_lang(lang)

    # Equator v4.1 script-aware overlap view:
    # - CJK: prefer char bigram/trigram + Latin runs
    # - Thai: fallback char bigram/trigram when dictionary segmenter is unavailable
    # - Hi/Vi: word tokens preferred, char bi/tri fallback to avoid single-token triggers
    if ltag in _CJK_LANGS or ltag in _THAI_LANGS or _is_hi_or_vi_lang(ltag):
        n_char = 2 if ngram <= 2 else 3
        toks: list[str] = []
        if ltag in _THAI_LANGS:
            words = _thai_word_tokens(text or "", ignore=ignore)
            if words:
                toks = _token_ngrams(words, n_char, joiner="__")
            else:
                chars = _THAI_CHAR_RE.findall(text or "")
                toks = _char_ngrams(chars, n_char)
        elif _is_hi_or_vi_lang(ltag):
            words = [t for t in _WORD_RE.findall((text or "").lower()) if t]
            if ignore:
                words = [t for t in words if t not in ignore]
            if words:
                if ngram <= 1:
                    toks = words
                elif len(words) >= ngram:
                    toks = _token_ngrams(words, ngram, joiner="__")
                else:
                    toks = []
            else:
                chars = [ch for ch in (text or "").lower() if _WORD_RE.fullmatch(ch)]
                toks = _char_ngrams(chars, n_char)
        else:
            chars = _CJK_CHAR_RE.findall(text or "")
            toks = _char_ngrams(chars, n_char)
        # Keep Latin/digit runs so mixed-script prompts still compare reasonably.
        latin = _LATIN_RUN_RE.findall((text or "").lower())
        if ignore:
            latin = [t for t in latin if t not in ignore]
        return toks + latin

    toks = [t for t in _WORD_RE.findall((text or "").lower()) if t]
    if ignore:
        toks = [t for t in toks if t not in ignore]
    if ngram <= 1:
        return toks
    if len(toks) < ngram:
        return []
    out: list[str] = []
    for i in range(0, len(toks) - ngram + 1):
        out.append("__".join(toks[i : i + ngram]))
    return out


def _token_overlap_ratio(a: str, b: str, ignore: set[str] | None = None, ngram: int = 1, lang: str | None = None) -> float:
    ta = set(_tokenize(a, ignore=ignore, ngram=ngram, lang=lang))
    tb = set(_tokenize(b, ignore=ignore, ngram=ngram, lang=lang))
    if not ta or not tb:
        return 0.0
    inter = len(ta.intersection(tb))
    union = len(ta.union(tb))
    if union <= 0:
        return 0.0
    return inter / float(union)


def overlap_duplicate_decision(
    *,
    text_a: str,
    text_b: str,
    lang: str | None,
    ignore: set[str] | None,
    ngram: int,
    candidate_threshold: float,
    validation_cfg: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    cfg = validation_cfg if isinstance(validation_cfg, dict) else {}
    ltag = _norm_lang(lang)

    if ngram < 1 or ngram > 3:
        ngram = 1

    candidate = _cfg_float(cfg, "dup_candidate_threshold", candidate_threshold)
    if candidate <= 0.0:
        candidate = candidate_threshold
    if candidate <= 0.0:
        candidate = 0.30

    tokens_a = _tokenize(text_a, ignore=ignore, ngram=ngram, lang=ltag)
    tokens_b = _tokenize(text_b, ignore=ignore, ngram=ngram, lang=ltag)
    if not tokens_a or not tokens_b:
        return False, {
            "rule": "empty",
            "o_min": 0.0,
            "o_jac": 0.0,
            "c3": 0.0,
            "candidate": candidate,
        }

    o_min = _multiset_overlap_min(tokens_a, tokens_b)
    o_jac = _jaccard_from_tokens(tokens_a, tokens_b)
    if o_min <= candidate and o_jac <= candidate:
        return False, {
            "rule": "below_candidate",
            "o_min": o_min,
            "o_jac": o_jac,
            "c3": 0.0,
            "candidate": candidate,
        }

    if not _is_asian_chain_lang(ltag):
        is_dup = o_jac > candidate
        return is_dup, {
            "rule": "legacy_jaccard",
            "o_min": o_min,
            "o_jac": o_jac,
            "c3": 0.0,
            "candidate": candidate,
        }

    chain_tokens_a = _tokenize(text_a, ignore=ignore, ngram=1, lang=ltag)
    chain_tokens_b = _tokenize(text_b, ignore=ignore, ngram=1, lang=ltag)
    if min(len(chain_tokens_a), len(chain_tokens_b)) < 3:
        return False, {
            "rule": "asian_min_tokens",
            "o_min": o_min,
            "o_jac": o_jac,
            "c3": 0.0,
            "candidate": candidate,
        }
    c3 = _longest_common_chain_ratio(chain_tokens_a, chain_tokens_b)

    contain_threshold = _cfg_float(cfg, "dup_contain_threshold", 0.55)
    if contain_threshold <= 0.0:
        contain_threshold = 0.55
    o_jac_threshold = _cfg_float(cfg, "dup_jaccard_threshold", 0.38)
    if o_jac_threshold <= 0.0:
        o_jac_threshold = 0.38
    c3_threshold = _cfg_float(cfg, "dup_chain_threshold_asian", 0.30)
    if c3_threshold <= 0.0:
        c3_threshold = 0.30

    guard_enabled = cfg.get("asian_chain_guard_enabled")
    if guard_enabled is None:
        guard_enabled = True
    else:
        guard_enabled = bool(guard_enabled)

    guard_hit = False
    prefix_len = 0
    suffix_len = 0
    tail_jac = 0.0
    if guard_enabled:
        guard_hit, prefix_len, suffix_len, tail_jac = _asian_prefix_divergence_guard(
            chain_tokens_a, chain_tokens_b, cfg
        )

    if guard_hit:
        return False, {
            "rule": "asian_prefix_divergence_guard",
            "o_min": o_min,
            "o_jac": o_jac,
            "c3": c3,
            "candidate": candidate,
            "prefix_len": prefix_len,
            "suffix_len": suffix_len,
            "tail_jac": tail_jac,
        }

    # Equator v4.1 two-stage for Thai/CJK-style scripts:
    # - do not fail on raw containment alone for Asian scripts
    # - require robust confirmation signals
    contain_hit = (o_min > contain_threshold) and (c3 > c3_threshold)
    signal_hits = 0
    if o_min > candidate:
        signal_hits += 1
    if o_jac > o_jac_threshold:
        signal_hits += 1
    if c3 > c3_threshold:
        signal_hits += 1
    multi_signal_hit = signal_hits >= 2

    is_dup = contain_hit or multi_signal_hit
    return is_dup, {
        "rule": "asian_two_stage",
        "o_min": o_min,
        "o_jac": o_jac,
        "c3": c3,
        "candidate": candidate,
        "contain_threshold": contain_threshold,
        "o_jac_threshold": o_jac_threshold,
        "c3_threshold": c3_threshold,
        "signal_hits": signal_hits,
    }


def _opening_key(text: str, lang: str | None = None) -> str:
    ltag = _norm_lang(lang)
    if ltag in _CJK_LANGS:
        chars = _CJK_CHAR_RE.findall(text or "")
        if chars:
            return "".join(chars[:6])
    if ltag in _THAI_LANGS:
        chars = _THAI_CHAR_RE.findall(text or "")
        if chars:
            return "".join(chars[:6])
    toks = _tokenize(text or "", ngram=1, lang=lang)
    return " ".join(toks[:4]) if toks else ""


def _build_similarity_ignore(sim: Any) -> set[str]:
    ignore: set[str] = set()
    if not isinstance(sim, dict):
        return ignore
    extra = sim.get("ignore_tokens")
    if isinstance(extra, list):
        for x in extra:
            if isinstance(x, str) and x.strip():
                ignore.add(x.strip().lower())
    return ignore


def parse_rule_profile(raw: str | None) -> int | None:
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if not key:
        return None
    return _RULE_ALIASES.get(key)


def resolve_rule_profile(explicit_rule: str | None) -> int:
    # If not explicitly provided, default is strictest profile 03.
    if explicit_rule is not None and str(explicit_rule).strip():
        parsed = parse_rule_profile(explicit_rule)
        if parsed is None:
            raise ValueError(
                f"invalid --rule value '{explicit_rule}'. Use one of: 01, 02, 03"
            )
        return parsed
    return 3


def _git_sha_or_unknown() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        s = out.decode("utf-8").strip()
        return s if s else "unknown"
    except Exception:
        return "unknown"


def _resolve_run_id(run_id: str | None) -> str:
    raw = str(run_id or "").strip()
    if not raw:
        raw = str(os.environ.get("DINO_DS_RUN_UUID", "")).strip()
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", raw)
    if not cleaned:
        cleaned = uuid.uuid4().hex[:8]
    if cleaned.upper().startswith("RUN"):
        tail = cleaned[3:]
        if not tail:
            tail = uuid.uuid4().hex[:8]
        return f"RUN_{tail[:8]}"
    return f"RUN_{cleaned[:8]}"


def _default_repo_root() -> str:
    return str(Path(__file__).resolve().parents[3])


def _lang_from_detail(detail: str) -> str:
    m = _LANG_IN_DETAIL_RE.search(str(detail or ""))
    if not m:
        return "unknown"
    return _norm_lang(m.group(1)) or "unknown"


def _sanitize_example_message(code: str, detail: str) -> str:
    s = _WS_RE.sub(" ", str(detail or "").strip())
    if ":" in s:
        s = s.split(":", 1)[1].strip()
    lowered = s.lower()
    if "user_message" in lowered and "assistant_response" not in lowered and "tool_call" not in lowered:
        return "user_message issue detected (details redacted)"
    s = _LONG_QUOTED_RE.sub("'[snippet]'", s)
    if len(s) > 240:
        s = s[:239].rstrip() + "..."
    if not s:
        return code.replace("_", " ")
    return s


def _pair_row_id(detail: str) -> str | None:
    m = _PAIR_ROWID_RE.match(str(detail or "").strip())
    if not m:
        return None
    rid = m.group(1).strip()
    return rid if rid else None


def _pair_row_ids(detail: str) -> tuple[str, str] | None:
    m = _PAIR_BOTH_ROWIDS_RE.match(str(detail or "").strip())
    if not m:
        return None
    left = m.group(1).strip()
    right = m.group(2).strip()
    if not left or not right:
        return None
    return left, right


def _counter_to_plain(c: Counter[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for k, v in c.items():
        if isinstance(k, str) and v:
            out[k] = int(v)
    return dict(sorted(out.items()))


def _slice_thresholds(lane_id: str, lane: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    vcfg = lane.get("validation")
    vcfg = vcfg if isinstance(vcfg, dict) else {}
    sim = lane.get("similarity")
    sim = sim if isinstance(sim, dict) else {}

    base_candidate = _cfg_float(sim, "max_token_overlap_ratio", 0.30)
    out["dup_candidate_threshold"] = _safe_ratio(_cfg_float(vcfg, "dup_candidate_threshold", base_candidate))
    out["dup_contain_threshold"] = _safe_ratio(_cfg_float(vcfg, "dup_contain_threshold", 0.55))

    mt_cfg = vcfg.get("mode_tone_proportion")
    mt_cfg = mt_cfg if isinstance(mt_cfg, dict) else {}
    min_n = 30
    for key in ("min_n_per_language", "min_n"):
        v = mt_cfg.get(key)
        if isinstance(v, int) and v > 0:
            min_n = int(v)
            break
    out["proportion_min_n"] = min_n
    lane_num = _lane_num_from_id(lane_id)
    if lane_num == 3:
        out["lane03_tool_call_max_share"] = _LANE03_TOOL_CALL_MAX_SHARE
        out["lane03_image_context_max_share"] = _LANE03_IMAGE_CONTEXT_MAX_SHARE
        out["lane03_implicit_multistep_min_share"] = _LANE03_IMPLICIT_MULTISTEP_MIN_SHARE
        out["lane03_structure_max_share"] = _LANE03_STRUCTURE_MAX_SHARE
    if lane_num == 4:
        out["lane04_tool_call_max_share"] = _LANE04_TOOL_CALL_MAX_SHARE
        out["lane04_image_context_max_share"] = _LANE04_IMAGE_CONTEXT_MAX_SHARE
        out["lane04_answer_len_le120_min_share"] = _LANE04_ANSWER_LEN_LE120_MIN_SHARE
        out["lane04_answer_len_le60_min_share"] = _LANE04_ANSWER_LEN_LE60_MIN_SHARE
    if lane_num == 5:
        out["lane05_image_context_max_share"] = _LANE05_IMAGE_CONTEXT_MAX_SHARE
    if lane_num == 5:
        out["lane05_multiturn_min_share"] = 0.60
        out["lane05_emotional_callback_min_share"] = 0.40
    if lane_num == 7:
        out["lane07_borderline_min_share"] = _LANE07_BORDERLINE_MIN_SHARE
        out["lane07_needs_search_target"] = _LANE07_NEEDS_SEARCH_TARGET
    if lane_num == 10:
        out["lane10_borderline_min_share"] = _LANE10_BORDERLINE_MIN_SHARE
    if lane_num == 9:
        out["lane09_flow_state_targets"] = dict(_LANE09_FLOW_STATE_TARGETS)
    if lane_num == 28:
        out["lane28_emote6_min_share"] = _LANE28_EMOTE6_MIN_SHARE
        out["lane28_emote6_buckets"] = list(_LANE28_EMOTE6_BUCKETS)
    if lane_num == 30:
        out["lane30_creative_extraction_min_share"] = _LANE30_CREATIVE_EXTRACTION_MIN_SHARE
    if lane_num == 20:
        out["lane20_prior_content_reference_min_share"] = _LANE20_PRIOR_REFERENCE_MIN_SHARE
    if lane_num == 29:
        out["lane29_misinfo_correction_min_share"] = _LANE29_MISINFO_CORRECTION_MIN_SHARE
    if lane_num == 34:
        out["lane34_colloquial_min_share"] = _LANE34_COLLOQUIAL_MIN_SHARE
        out["lane34_codeswitch_min_share"] = _LANE34_CODESWITCH_MIN_SHARE
    if lane_num == 33:
        out["lane33_min_share"] = _LANE33_FALLBACK_LIMITATION_MIN_SHARE
        out["lane33_min_n"] = _LANE33_FALLBACK_MIN_N

    viability_cfg = vcfg.get("viability")
    viability_cfg = viability_cfg if isinstance(viability_cfg, dict) else {}
    if viability_cfg:
        min_fill_ratio = viability_cfg.get("min_fill_ratio")
        if isinstance(min_fill_ratio, (int, float)) and not isinstance(min_fill_ratio, bool):
            out["viability_min_fill_ratio"] = _safe_ratio(float(min_fill_ratio))
        max_attempts_per_row = viability_cfg.get("max_attempts_per_row")
        if isinstance(max_attempts_per_row, int) and max_attempts_per_row > 0:
            out["viability_max_attempts_per_row"] = int(max_attempts_per_row)

    contract = contract_for_lane(lane_id)
    overlap_max = contract.get("user_assistant_overlap_max") if isinstance(contract, dict) else None
    if isinstance(overlap_max, (int, float)) and not isinstance(overlap_max, bool):
        out["user_assistant_overlap_max"] = float(overlap_max)

    return out


def _validate_messages_alignment(rr: dict[str, Any]) -> tuple[bool, str]:
    msgs = rr.get("messages")
    if msgs is None:
        return True, ""
    if not isinstance(msgs, list) or len(msgs) < 2:
        return False, "messages must be a list with user/assistant entries"

    roles: list[str] = []
    contents: list[str] = []
    for item in msgs:
        if not isinstance(item, dict):
            return False, "messages contains non-object entry"
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            return False, "messages entries require string role/content"
        roles.append(role.strip())
        contents.append(content)

    if "user" not in roles or "assistant" not in roles:
        return False, "messages missing user/assistant roles"

    try:
        ui = roles.index("user")
        ai = roles.index("assistant")
    except ValueError:
        return False, "messages missing user/assistant roles"

    if ui > ai:
        return False, "messages role order invalid (user must come before assistant)"

    if "system" in roles:
        si = roles.index("system")
        if si > ui:
            return False, "messages role order invalid (system must be before user)"

    user_msg = rr.get("user_message")
    last_ui = max(i for i, r in enumerate(roles) if r == "user")
    if isinstance(user_msg, str):
        if _norm_text(user_msg) != _norm_text(contents[last_ui]):
            return False, "user_message mismatch with messages[user].content"

    asst_msg = rr.get("assistant_response")
    last_ai = max(i for i, r in enumerate(roles) if r == "assistant")
    if isinstance(asst_msg, str):
        if _norm_text(asst_msg) != _norm_text(contents[last_ai]):
            return False, "assistant_response mismatch with last messages[assistant].content"

    return True, ""


def _row_text_for_similarity(rr: dict[str, Any], scope: str | None = None) -> str:
    u = rr.get("user_message")
    a = rr.get("assistant_response")
    if isinstance(scope, str):
        k = scope.strip().lower()
        if k in ("assistant", "assistant_response", "assistant-only", "assistant_only"):
            return a if isinstance(a, str) else ""
        if k in ("user", "user_message", "user-only", "user_only"):
            return u if isinstance(u, str) else ""
    if isinstance(u, str) and isinstance(a, str):
        return f"{u}\n{a}"
    return ""


def _norm_dist_targets(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        key = k.strip().lower()
        if not key:
            continue
        fv = float(v)
        if fv < 0.0 or fv > 1.0:
            continue
        out[key] = fv
    return out


def _extract_metric_targets(
    validation_cfg: dict[str, Any],
    mt_cfg: dict[str, Any] | None,
    metric: str,
) -> dict[str, float]:
    targets: dict[str, float] = {}

    if isinstance(mt_cfg, dict):
        block = mt_cfg.get(metric)
        if isinstance(block, dict):
            raw = block.get("targets")
            if not isinstance(raw, dict):
                raw = block.get("distribution")
            if not isinstance(raw, dict):
                raw = block
            targets = _norm_dist_targets(raw)
        if not targets:
            for key in (f"{metric}_targets", f"{metric}_proportions", f"{metric}_distribution"):
                targets = _norm_dist_targets(mt_cfg.get(key))
                if targets:
                    break

    if not targets:
        for key in (f"{metric}_targets", f"{metric}_proportions", f"{metric}_distribution"):
            targets = _norm_dist_targets(validation_cfg.get(key))
            if targets:
                break
    return targets


def _evaluate_mode_tone_proportions(
    rows: list[dict[str, Any]],
    lane_id: str,
    lane: dict[str, Any],
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    validation_cfg = lane.get("validation")
    validation_cfg = validation_cfg if isinstance(validation_cfg, dict) else {}
    mt_cfg = validation_cfg.get("mode_tone_proportion")
    mt_cfg = mt_cfg if isinstance(mt_cfg, dict) else None

    mode_targets = _extract_metric_targets(validation_cfg, mt_cfg, "mode")
    tone_targets = _extract_metric_targets(validation_cfg, mt_cfg, "tone")

    if not mode_targets and not tone_targets:
        lane_num = _lane_num_from_id(lane_id)
        spec_targets = _SPEC_MODE_TONE_TARGETS.get(lane_num or -1, {})
        mode_targets = dict(spec_targets.get("mode", {}))
        tone_targets = dict(spec_targets.get("tone", {}))

    if not mode_targets and not tone_targets:
        return [], [], []

    min_n = 30
    if mt_cfg is not None:
        for key in ("min_n_per_language", "min_n"):
            v = mt_cfg.get(key)
            if isinstance(v, int) and v > 0:
                min_n = int(v)
                break

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped mode/tone proportion gate",
                )
            )
            continue

        metric_failures: list[str] = []
        metric_warns: list[str] = []
        if mode_targets:
            mode_counts: Counter[str] = Counter()
            for rr in subset:
                mv = rr.get("mode")
                if isinstance(mv, str) and mv.strip():
                    mode_counts[mv.strip().lower()] += 1
            for label, target in sorted(mode_targets.items()):
                observed = mode_counts.get(label, 0) / float(n)
                dev = abs(observed - target)
                if dev >= _PROPORTION_FAIL_MIN_DEV:
                    metric_failures.append(
                        f"mode.{label} observed={observed:.3f} target={target:.3f} dev={dev:.3f}"
                    )
                elif dev > _PROPORTION_PASS_MAX_DEV:
                    metric_warns.append(
                        f"mode.{label} observed={observed:.3f} target={target:.3f} dev={dev:.3f}"
                    )

        if tone_targets:
            tone_counts: Counter[str] = Counter()
            for rr in subset:
                tv = rr.get("tone")
                if isinstance(tv, str) and tv.strip():
                    tone_counts[tv.strip().lower()] += 1
            for label, target in sorted(tone_targets.items()):
                observed = tone_counts.get(label, 0) / float(n)
                dev = abs(observed - target)
                if dev >= _PROPORTION_FAIL_MIN_DEV:
                    metric_failures.append(
                        f"tone.{label} observed={observed:.3f} target={target:.3f} dev={dev:.3f}"
                    )
                elif dev > _PROPORTION_PASS_MAX_DEV:
                    metric_warns.append(
                        f"tone.{label} observed={observed:.3f} target={target:.3f} dev={dev:.3f}"
                    )

        if metric_failures:
            fail_issues.append(
                (
                    "proportion_out_of_tolerance",
                    f"language={lang} n={n}; " + "; ".join(metric_failures),
                )
            )
        elif metric_warns:
            warn_issues.append(
                (
                    "proportion_out_of_tolerance_warn",
                    f"language={lang} n={n}; " + "; ".join(metric_warns),
                )
            )
        else:
            pass_notes.append(f"mode_tone_proportion PASS language={lang} n={n}")

    return pass_notes, fail_issues, warn_issues


def _lane04_answer_token_count(asst_text: Any, language: str) -> int:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return 0
    text = asst_text.strip()
    ltag = _norm_lang(language)
    if ltag in _THAI_LANGS:
        words = _thai_word_tokens(text)
        if words:
            return len(words)
        thai_runs = _THAI_RUN_RE.findall(text)
        latin = _LATIN_RUN_RE.findall(text.lower())
        return len(thai_runs) + len(latin)
    if ltag in _CJK_LANGS:
        cjk_chars = _CJK_CHAR_RE.findall(text)
        latin = _LATIN_RUN_RE.findall(text.lower())
        return len(cjk_chars) + len(latin)
    return len(_WORD_RE.findall(text.lower()))


def _evaluate_lane04_answer_length_distribution(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    if _lane_num_from_id(lane_id) != 4:
        return [], [], []

    min_n = 30
    min_share_120 = _LANE04_ANSWER_LEN_LE120_MIN_SHARE
    min_share_60 = _LANE04_ANSWER_LEN_LE60_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane04_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 04 answer-length distribution gate",
                )
            )
            continue

        le_120 = 0
        le_60 = 0
        for rr in subset:
            tcount = _lane04_answer_token_count(rr.get("assistant_response"), lang)
            if tcount <= 120:
                le_120 += 1
            if tcount <= 60:
                le_60 += 1

        share_120 = le_120 / float(n)
        share_60 = le_60 / float(n)
        if share_120 < min_share_120:
            fail_issues.append(
                (
                    "lane04_answer_len_le120_share_too_low",
                    (
                        f"language={lang} n={n}; le120_share={share_120:.3f} < "
                        f"min={min_share_120:.3f} (matching_rows={le_120})"
                    ),
                )
            )
        if share_60 < min_share_60:
            fail_issues.append(
                (
                    "lane04_answer_len_le60_share_too_low",
                    (
                        f"language={lang} n={n}; le60_share={share_60:.3f} < "
                        f"min={min_share_60:.3f} (matching_rows={le_60})"
                    ),
                )
            )

        if share_120 >= min_share_120 and share_60 >= min_share_60:
            pass_notes.append(
                (
                    f"lane04_answer_length_distribution PASS language={lang} n={n} "
                    f"le120_share={share_120:.3f} le60_share={share_60:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane03_has_implicit_multistep(asst_text: Any, language: str) -> bool:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return False
    text = asst_text.strip()
    list_lines = len(_LIST_LINE_RE.findall(text))
    if list_lines >= 2:
        return True

    ltag = _norm_lang(language)
    if ltag in _THAI_LANGS:
        conn_hits = len(_LANE03_STEP_TH_RE.findall(text))
    elif ltag in _CJK_LANGS:
        conn_hits = len(_LANE03_STEP_CJK_RE.findall(text))
    else:
        conn_hits = len(_LANE03_STEP_EN_RE.findall(text))

    sentence_count = len([s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()])
    token_count = len(_tokenize(text, ngram=1, lang=ltag))
    if conn_hits >= 2 and token_count >= 18:
        return True
    if conn_hits >= 1 and sentence_count >= 3 and token_count >= 22:
        return True
    return False


def _lane03_structure_signature(asst_text: Any, language: str) -> str:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return "empty"
    text = asst_text.strip()
    ltag = _norm_lang(language)
    opening = _opening_key(text, lang=ltag) or "<none>"
    token_count = len(_tokenize(text, ngram=1, lang=ltag))
    if token_count <= 25:
        len_bucket = "s"
    elif token_count <= 80:
        len_bucket = "m"
    else:
        len_bucket = "l"
    sentence_count = len([s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()])
    if sentence_count <= 2:
        sentence_bucket = "s"
    elif sentence_count <= 5:
        sentence_bucket = "m"
    else:
        sentence_bucket = "l"
    list_lines = len(_LIST_LINE_RE.findall(text))
    if list_lines == 0:
        list_bucket = "none"
    elif list_lines <= 3:
        list_bucket = "few"
    else:
        list_bucket = "many"
    explicit = "exp" if _LANE03_EXPLICIT_STEP_RE.search(text) else "imp"
    heading = "head" if ":" in text else "plain"
    return (
        f"open={opening}|len={len_bucket}|sent={sentence_bucket}|"
        f"list={list_bucket}|{explicit}|{heading}"
    )


def _evaluate_lane03_reasoning_structure_distribution(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    if _lane_num_from_id(lane_id) != 3:
        return [], [], []

    min_n = 30
    min_implicit = _LANE03_IMPLICIT_MULTISTEP_MIN_SHARE
    max_structure = _LANE03_STRUCTURE_MAX_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane03_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 03 reasoning/structure distribution gate",
                )
            )
            continue

        implicit_rows = 0
        sig_counts: Counter[str] = Counter()
        for rr in subset:
            asst = rr.get("assistant_response")
            if _lane03_has_implicit_multistep(asst, lang):
                implicit_rows += 1
            sig = _lane03_structure_signature(asst, lang)
            if sig:
                sig_counts[sig] += 1

        implicit_share = implicit_rows / float(n)
        top_sig = ""
        top_count = 0
        if sig_counts:
            top_sig, top_count = sig_counts.most_common(1)[0]
        top_share = top_count / float(n) if n > 0 else 0.0

        if implicit_share < min_implicit:
            fail_issues.append(
                (
                    "lane03_implicit_multistep_share_too_low",
                    (
                        f"language={lang} n={n}; implicit_multistep_share={implicit_share:.3f} < "
                        f"min={min_implicit:.3f} (matching_rows={implicit_rows})"
                    ),
                )
            )
        if top_share > max_structure:
            fail_issues.append(
                (
                    "lane03_structure_share_too_high",
                    (
                        f"language={lang} n={n}; top_structure_share={top_share:.3f} > "
                        f"max={max_structure:.3f} (top_count={top_count}, signature={top_sig})"
                    ),
                )
            )

        if implicit_share >= min_implicit and top_share <= max_structure:
            pass_notes.append(
                (
                    f"lane03_reasoning_structure_distribution PASS language={lang} n={n} "
                    f"implicit_multistep_share={implicit_share:.3f} top_structure_share={top_share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _read_bool_lane_or_root(rr: dict[str, Any], key: str) -> bool | None:
    raw = rr.get(key)
    if isinstance(raw, bool):
        return raw
    lane_obj = rr.get("lane")
    if isinstance(lane_obj, dict):
        nested = lane_obj.get(key)
        if isinstance(nested, bool):
            return nested
    lane_meta = rr.get("_lane")
    if isinstance(lane_meta, dict):
        nested = lane_meta.get(key)
        if isinstance(nested, bool):
            return nested
    return None


def _lane0710_is_borderline(rr: dict[str, Any], language: str) -> bool:
    # Prefer explicit lane labels when present.
    for key in ("borderline", "is_borderline", "ambiguous_case"):
        v = _read_bool_lane_or_root(rr, key)
        if isinstance(v, bool):
            return v

    for container in (rr, rr.get("lane"), rr.get("_lane")):
        if not isinstance(container, dict):
            continue
        raw = container.get("borderline_type")
        if isinstance(raw, str) and _LANE0710_BORDERLINE_LABEL_RE.search(raw):
            return True

    subtype = rr.get("intent_subtype")
    if isinstance(subtype, str) and _LANE0710_BORDERLINE_LABEL_RE.search(subtype):
        return True

    asst = rr.get("assistant_response")
    ltag = _norm_lang(language)
    if isinstance(asst, str) and asst.strip():
        text = asst.strip()
        if ltag in _THAI_LANGS and _LANE0710_BORDERLINE_ASST_TH_RE.search(text):
            return True
        if ltag in _CJK_LANGS and _LANE0710_BORDERLINE_ASST_CJK_RE.search(text):
            return True
        if ltag not in _THAI_LANGS and ltag not in _CJK_LANGS and _LANE0710_BORDERLINE_ASST_EN_RE.search(text):
            return True
        if "?" in text and len(_tokenize(text, ngram=1, lang=ltag)) <= 42:
            return True

    user = rr.get("user_message")
    if isinstance(user, str) and _LANE0710_BORDERLINE_USER_HINT_RE.search(user):
        return True
    return False


def _evaluate_lane07_borderline_and_split(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    if _lane_num_from_id(lane_id) != 7:
        return [], [], []

    min_n = 30
    borderline_min = _LANE07_BORDERLINE_MIN_SHARE
    target = _LANE07_NEEDS_SEARCH_TARGET

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane07_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 07 borderline/split gate",
                )
            )
            continue

        borderline_rows = sum(1 for rr in subset if _lane0710_is_borderline(rr, lang))
        borderline_share = borderline_rows / float(n)
        needs_true = sum(1 for rr in subset if rr.get("needs_search") is True)
        true_share = needs_true / float(n)
        dev = abs(true_share - target)

        if borderline_share < borderline_min:
            fail_issues.append(
                (
                    "lane07_borderline_share_too_low",
                    (
                        f"language={lang} n={n}; borderline_share={borderline_share:.3f} < "
                        f"min={borderline_min:.3f} (matching_rows={borderline_rows})"
                    ),
                )
            )

        if dev >= _PROPORTION_FAIL_MIN_DEV:
            fail_issues.append(
                (
                    "lane07_needs_search_split_out_of_tolerance",
                    (
                        f"language={lang} n={n}; needs_search_true_share={true_share:.3f} "
                        f"target={target:.3f} dev={dev:.3f}"
                    ),
                )
            )
        elif dev > _PROPORTION_PASS_MAX_DEV:
            warn_issues.append(
                (
                    "lane07_needs_search_split_warn",
                    (
                        f"language={lang} n={n}; needs_search_true_share={true_share:.3f} "
                        f"target={target:.3f} dev={dev:.3f}"
                    ),
                )
            )

        if borderline_share >= borderline_min and dev <= _PROPORTION_PASS_MAX_DEV:
            pass_notes.append(
                (
                    f"lane07_borderline_split PASS language={lang} n={n} "
                    f"borderline_share={borderline_share:.3f} needs_search_true_share={true_share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _evaluate_lane10_borderline_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    if _lane_num_from_id(lane_id) != 10:
        return [], [], []

    min_n = 30
    min_share = _LANE10_BORDERLINE_MIN_SHARE
    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane10_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 10 borderline share gate",
                )
            )
            continue

        borderline_rows = sum(1 for rr in subset if _lane0710_is_borderline(rr, lang))
        share = borderline_rows / float(n)
        if share < min_share:
            fail_issues.append(
                (
                    "lane10_borderline_share_too_low",
                    (
                        f"language={lang} n={n}; borderline_share={share:.3f} < "
                        f"min={min_share:.3f} (matching_rows={borderline_rows})"
                    ),
                )
            )
        else:
            pass_notes.append(
                (
                    f"lane10_borderline_share PASS language={lang} n={n} "
                    f"share={share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane05_non_system_message_count(rr: dict[str, Any]) -> int:
    msgs = rr.get("messages")
    if not isinstance(msgs, list):
        return 0
    count = 0
    for item in msgs:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if isinstance(role, str) and role.strip().lower() in {"user", "assistant"}:
            count += 1
    return count


def _has_tool_call_payload(rr: dict[str, Any]) -> bool:
    tc = rr.get("tool_call")
    if isinstance(tc, dict):
        return True
    if isinstance(tc, list) and any(isinstance(x, dict) for x in tc):
        return True
    tcs = rr.get("tool_calls")
    if isinstance(tcs, list) and any(isinstance(x, dict) for x in tcs):
        return True
    return False


def _has_image_context_payload(rr: dict[str, Any]) -> bool:
    return isinstance(rr.get("image_context"), dict)


def _evaluate_lane_optional_tool_image_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num not in {3, 4, 5}:
        return [], [], []

    tool_cap: float | None = None
    image_cap: float | None = None
    if lane_num == 3:
        tool_cap = _LANE03_TOOL_CALL_MAX_SHARE
        image_cap = _LANE03_IMAGE_CONTEXT_MAX_SHARE
    elif lane_num == 4:
        tool_cap = _LANE04_TOOL_CALL_MAX_SHARE
        image_cap = _LANE04_IMAGE_CONTEXT_MAX_SHARE
    elif lane_num == 5:
        image_cap = _LANE05_IMAGE_CONTEXT_MAX_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < _OPTIONAL_SHARE_MIN_N:
            warn_issues.append(
                (
                    f"lane{lane_num:02d}_optional_share_not_reliable_small_n",
                    (
                        f"language={lang} n={n} < min_n={_OPTIONAL_SHARE_MIN_N}; "
                        f"skipped lane {lane_num:02d} optional share gate"
                    ),
                )
            )
            continue

        lane_failures: list[tuple[str, str]] = []
        if tool_cap is not None:
            tool_rows = sum(1 for rr in subset if _has_tool_call_payload(rr))
            tool_share = tool_rows / float(n)
            if tool_share > tool_cap:
                lane_failures.append(
                    (
                        f"lane{lane_num:02d}_tool_call_share_too_high",
                        (
                            f"language={lang} n={n}; tool_call_share={tool_share:.3f} > "
                            f"max={tool_cap:.3f} (tool_rows={tool_rows})"
                        ),
                    )
                )

        if image_cap is not None:
            image_rows = sum(1 for rr in subset if _has_image_context_payload(rr))
            image_share = image_rows / float(n)
            if image_share > image_cap:
                lane_failures.append(
                    (
                        f"lane{lane_num:02d}_image_context_share_too_high",
                        (
                            f"language={lang} n={n}; image_context_share={image_share:.3f} > "
                            f"max={image_cap:.3f} (image_rows={image_rows})"
                        ),
                    )
                )

        if lane_failures:
            fail_issues.extend(lane_failures)
        else:
            fragments: list[str] = []
            if tool_cap is not None:
                tool_rows = sum(1 for rr in subset if _has_tool_call_payload(rr))
                tool_share = tool_rows / float(n)
                fragments.append(f"tool_call_share={tool_share:.3f}/{tool_cap:.3f}")
            if image_cap is not None:
                image_rows = sum(1 for rr in subset if _has_image_context_payload(rr))
                image_share = image_rows / float(n)
                fragments.append(f"image_context_share={image_share:.3f}/{image_cap:.3f}")
            pass_notes.append(
                f"lane{lane_num:02d}_optional_shares PASS language={lang} n={n} " + " ".join(fragments)
            )

    return pass_notes, fail_issues, warn_issues


def _lane05_has_emotional_callback(rr: dict[str, Any]) -> bool:
    # Preferred explicit label if available.
    raw = rr.get("callback_type")
    if isinstance(raw, str) and raw.strip().lower() == "emotional":
        return True
    lane_obj = rr.get("lane")
    if isinstance(lane_obj, dict):
        raw = lane_obj.get("callback_type")
        if isinstance(raw, str) and raw.strip().lower() == "emotional":
            return True
    lane_meta = rr.get("_lane")
    if isinstance(lane_meta, dict):
        raw = lane_meta.get("callback_type")
        if isinstance(raw, str) and raw.strip().lower() == "emotional":
            return True

    # Spec fallback path: continuity-based callback signal.
    cc = rr.get("continuity_choice")
    return isinstance(cc, str) and cc.strip().lower() == "use_continuity"


def _evaluate_lane05_slice_distributions(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 5:
        return [], [], []

    min_n = 30
    multiturn_min_share = 0.60
    emotional_min_share = 0.40

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane05_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 05 slice distribution gate",
                )
            )
            continue

        multiturn_rows = sum(1 for rr in subset if _lane05_non_system_message_count(rr) >= 4)
        emotional_rows = sum(1 for rr in subset if _lane05_has_emotional_callback(rr))
        multiturn_share = multiturn_rows / float(n)
        emotional_share = emotional_rows / float(n)

        if multiturn_share < multiturn_min_share:
            fail_issues.append(
                (
                    "lane05_multiturn_share_too_low",
                    (
                        f"language={lang} n={n}; multiturn_share={multiturn_share:.3f} < "
                        f"min={multiturn_min_share:.3f} (multiturn_rows={multiturn_rows})"
                    ),
                )
            )

        if emotional_share < emotional_min_share:
            fail_issues.append(
                (
                    "lane05_emotional_callback_share_too_low",
                    (
                        f"language={lang} n={n}; emotional_callback_share={emotional_share:.3f} < "
                        f"min={emotional_min_share:.3f} (emotional_rows={emotional_rows})"
                    ),
                )
            )

        if multiturn_share >= multiturn_min_share and emotional_share >= emotional_min_share:
            pass_notes.append(
                (
                    f"lane05_slice_distribution PASS language={lang} n={n} "
                    f"multiturn_share={multiturn_share:.3f} emotional_callback_share={emotional_share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane09_flow_state(rr: dict[str, Any]) -> str:
    raw = rr.get("flow_state")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    lane_obj = rr.get("lane")
    if isinstance(lane_obj, dict):
        nested = lane_obj.get("flow_state")
        if isinstance(nested, str) and nested.strip():
            return nested.strip().lower()
    return ""


def _evaluate_lane09_flow_state_distribution(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 9:
        return [], [], []

    min_n = 30
    targets = dict(_LANE09_FLOW_STATE_TARGETS)

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane09_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 09 flow_state distribution gate",
                )
            )
            continue

        state_counts: Counter[str] = Counter()
        for rr in subset:
            state = _lane09_flow_state(rr)
            if state:
                state_counts[state] += 1

        failures: list[str] = []
        for state, target in sorted(targets.items()):
            observed = state_counts.get(state, 0) / float(n)
            dev = abs(observed - target)
            if dev >= _PROPORTION_FAIL_MIN_DEV:
                failures.append(
                    f"flow_state.{state} observed={observed:.3f} target={target:.3f} dev={dev:.3f}"
                )

        if failures:
            fail_issues.append(
                (
                    "lane09_flow_state_out_of_tolerance",
                    f"language={lang} n={n}; " + "; ".join(failures),
                )
            )
        else:
            pass_notes.append(
                f"lane09_flow_state_distribution PASS language={lang} n={n}"
            )

    return pass_notes, fail_issues, warn_issues


def _lane28_emote6(rr: dict[str, Any]) -> str:
    raw = rr.get("emote6")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    lane_obj = rr.get("lane")
    if isinstance(lane_obj, dict):
        nested = lane_obj.get("emote6")
        if isinstance(nested, str) and nested.strip():
            return nested.strip().lower()
    return ""


def _evaluate_lane28_emote6_distribution(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 28:
        return [], [], []

    min_n = 30
    min_share = _LANE28_EMOTE6_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane28_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 28 emote6 distribution gate",
                )
            )
            continue

        counts: Counter[str] = Counter()
        for rr in subset:
            label = _lane28_emote6(rr)
            if label:
                counts[label] += 1

        low_buckets: list[str] = []
        for bucket in _LANE28_EMOTE6_BUCKETS:
            share = counts.get(bucket, 0) / float(n)
            if share < min_share:
                low_buckets.append(f"{bucket}={share:.3f}")

        if low_buckets:
            fail_issues.append(
                (
                    "lane28_emote6_out_of_tolerance",
                    (
                        f"language={lang} n={n}; buckets_below_min_share({min_share:.2f})="
                        + ", ".join(low_buckets)
                    ),
                )
            )
        else:
            pass_notes.append(
                f"lane28_emote6_distribution PASS language={lang} n={n}"
            )

    return pass_notes, fail_issues, warn_issues


def _lane30_is_creative_extraction_attempt(rr: dict[str, Any]) -> bool:
    # Prefer dedicated lane-scoped boolean when present.
    lane_obj = rr.get("lane")
    if isinstance(lane_obj, dict):
        v = lane_obj.get("creative_extraction_attempt")
        if isinstance(v, bool):
            return v
        at = lane_obj.get("attempt_type")
        if isinstance(at, str) and at.strip().lower() == "creative_extraction":
            return True

    v = rr.get("creative_extraction_attempt")
    if isinstance(v, bool):
        return v

    at = rr.get("attempt_type")
    if isinstance(at, str) and at.strip().lower() == "creative_extraction":
        return True

    fam = rr.get("intent_family")
    if isinstance(fam, str) and fam.strip().lower() == "creative_extraction":
        return True

    # Full_Dataset_Spec v17 lane 30 encodes extraction attempts with safety_tag=leakage_attempt.
    st = rr.get("safety_tag")
    return isinstance(st, str) and st.strip().lower() == "leakage_attempt"


def _evaluate_lane30_creative_extraction_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 30:
        return [], [], []

    min_n = 30
    min_share = _LANE30_CREATIVE_EXTRACTION_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane30_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 30 creative extraction share gate",
                )
            )
            continue

        attempts = sum(1 for rr in subset if _lane30_is_creative_extraction_attempt(rr))
        share = attempts / float(n)
        if share < min_share:
            fail_issues.append(
                (
                    "lane30_creative_extraction_share_too_low",
                    (
                        f"language={lang} n={n}; creative_extraction_share={share:.3f} < "
                        f"min={min_share:.3f} (attempt_rows={attempts})"
                    ),
                )
            )
        else:
            pass_notes.append(
                (
                    f"lane30_creative_extraction_share PASS language={lang} n={n} "
                    f"share={share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane33_has_fallback_limitation(asst_text: str, language: str) -> bool:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return False
    text = asst_text.strip()
    ltag = _norm_lang(language)
    if ltag in _THAI_LANGS:
        return _LANE33_TH_LIMITATION_RE.search(text) is not None
    if ltag in _CJK_LANGS:
        return _LANE33_CJK_LIMITATION_RE.search(text) is not None
    return _LANE33_EN_LIMITATION_RE.search(text) is not None


def _evaluate_lane33_fallback_limitation_share(
    rows: list[dict[str, Any]],
    expected_language: str | None,
    cfg: dict[str, Any] | None,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    min_n = _LANE33_FALLBACK_MIN_N
    min_share = _LANE33_FALLBACK_LIMITATION_MIN_SHARE
    if isinstance(cfg, dict):
        cfg_min_n = cfg.get("lane33_min_n")
        if isinstance(cfg_min_n, int) and cfg_min_n > 0:
            min_n = int(cfg_min_n)
        cfg_min_share = cfg.get("lane33_min_share")
        if isinstance(cfg_min_share, (int, float)) and not isinstance(cfg_min_share, bool):
            min_share = _safe_ratio(float(cfg_min_share))

    fallback_lang = _norm_lang(expected_language) or "unknown"
    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or fallback_lang
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane33_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 33 fallback limitation share gate",
                )
            )
            continue

        matches = 0
        for rr in subset:
            asst = rr.get("assistant_response")
            if isinstance(asst, str) and _lane33_has_fallback_limitation(asst, lang):
                matches += 1

        share = matches / float(n)
        if share < min_share:
            fail_issues.append(
                (
                    "lane33_fallback_limitation_share_too_low",
                    (
                        f"language={lang} n={n}; fallback_limitation_share={share:.3f} < "
                        f"min={min_share:.3f} (matching_rows={matches})"
                    ),
                )
            )
        else:
            pass_notes.append(
                (
                    f"lane33_fallback_limitation_share PASS language={lang} n={n} "
                    f"share={share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane20_prior_user_turns(rr: dict[str, Any]) -> list[str]:
    msgs = rr.get("messages")
    if not isinstance(msgs, list):
        return []
    users: list[str] = []
    for item in msgs:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if isinstance(role, str) and role.strip().lower() == "user" and isinstance(content, str) and content.strip():
            users.append(content.strip())
    if len(users) <= 1:
        return []
    return users[:-1]


def _lane20_has_prior_content_reference(rr: dict[str, Any], language: str) -> bool:
    asst = rr.get("assistant_response")
    if not isinstance(asst, str) or not asst.strip():
        return False
    ltag = _norm_lang(language)
    text = asst.strip()
    if ltag in _THAI_LANGS:
        if _LANE20_PRIOR_REF_TH_RE.search(text):
            return True
    elif ltag in _CJK_LANGS:
        if _LANE20_PRIOR_REF_CJK_RE.search(text):
            return True
    else:
        if _LANE20_PRIOR_REF_EN_RE.search(text):
            return True

    priors = _lane20_prior_user_turns(rr)
    if not priors:
        return False

    asst_tokens = _tokenize(text, ngram=1, lang=ltag)
    if not asst_tokens:
        return False
    max_overlap = 0.0
    for prev in priors:
        prev_tokens = _tokenize(prev, ngram=1, lang=ltag)
        if not prev_tokens:
            continue
        ov = _multiset_overlap_min(asst_tokens, prev_tokens)
        if ov > max_overlap:
            max_overlap = ov
    if max_overlap >= 0.12:
        return True
    cc = rr.get("continuity_choice")
    if isinstance(cc, str) and cc.strip().lower() == "use_continuity" and max_overlap >= 0.08:
        return True
    return False


def _evaluate_lane20_prior_content_reference_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 20:
        return [], [], []

    min_n = 30
    min_share = _LANE20_PRIOR_REFERENCE_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane20_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 20 prior-reference share gate",
                )
            )
            continue

        referenced = sum(1 for rr in subset if _lane20_has_prior_content_reference(rr, lang))
        share = referenced / float(n)
        if share < min_share:
            fail_issues.append(
                (
                    "lane20_prior_content_reference_share_too_low",
                    (
                        f"language={lang} n={n}; prior_content_reference_share={share:.3f} < "
                        f"min={min_share:.3f} (matching_rows={referenced})"
                    ),
                )
            )
        else:
            pass_notes.append(
                (
                    f"lane20_prior_content_reference_share PASS language={lang} n={n} "
                    f"share={share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane29_is_misinfo_correction(rr: dict[str, Any], language: str) -> bool:
    sub = rr.get("intent_subtype")
    if isinstance(sub, str):
        s = sub.strip().lower()
        if "misinfo" in s or "correction" in s:
            return True

    asst = rr.get("assistant_response")
    if not isinstance(asst, str) or not asst.strip():
        return False
    ltag = _norm_lang(language)
    asst_text = asst.strip()
    correction_hit = False
    if ltag in _THAI_LANGS:
        correction_hit = _LANE29_CORRECTION_TH_RE.search(asst_text) is not None
    elif ltag in _CJK_LANGS:
        correction_hit = _LANE29_CORRECTION_CJK_RE.search(asst_text) is not None
    else:
        correction_hit = _LANE29_CORRECTION_EN_RE.search(asst_text) is not None
        if not correction_hit:
            lowered = asst_text.lower()
            if lowered.startswith("no,") or lowered.startswith("no.") or lowered.startswith("not quite"):
                correction_hit = True
    if not correction_hit:
        return False

    user = rr.get("user_message")
    if not isinstance(user, str) or not user.strip():
        return True
    user_text = user.strip()
    if ltag in _THAI_LANGS:
        return _LANE29_CLAIM_TH_RE.search(user_text) is not None or correction_hit
    if ltag in _CJK_LANGS:
        return _LANE29_CLAIM_CJK_RE.search(user_text) is not None or correction_hit
    return _LANE29_CLAIM_EN_RE.search(user_text) is not None or correction_hit


def _evaluate_lane29_misinfo_correction_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 29:
        return [], [], []

    min_n = 30
    min_share = _LANE29_MISINFO_CORRECTION_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane29_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 29 misinfo-correction share gate",
                )
            )
            continue

        corrections = sum(1 for rr in subset if _lane29_is_misinfo_correction(rr, lang))
        share = corrections / float(n)
        if share < min_share:
            fail_issues.append(
                (
                    "lane29_misinfo_correction_share_too_low",
                    (
                        f"language={lang} n={n}; misinfo_correction_share={share:.3f} < "
                        f"min={min_share:.3f} (matching_rows={corrections})"
                    ),
                )
            )
        else:
            pass_notes.append(
                (
                    f"lane29_misinfo_correction_share PASS language={lang} n={n} "
                    f"share={share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _lane34_has_colloquial_phrasing(asst_text: str) -> bool:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return False
    hits = _LANE34_COLLOQUIAL_RE.findall(asst_text)
    if not hits:
        return False
    if any(tok in _LANE34_COLLOQUIAL_STRONG for tok in hits):
        return True
    return len(hits) >= 2


def _lane34_has_light_codeswitch(asst_text: str) -> bool:
    if not isinstance(asst_text, str) or not asst_text.strip():
        return False
    if _CJK_CHAR_RE.search(asst_text) is None:
        return False
    latin = _LANE34_LATIN_WORD_RE.findall(asst_text)
    return any(len(tok) >= 2 for tok in latin)


def _evaluate_lane34_colloquial_codeswitch_share(
    rows: list[dict[str, Any]],
    lane_id: str,
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    lane_num = _lane_num_from_id(lane_id)
    if lane_num != 34:
        return [], [], []

    min_n = 30
    colloquial_min = _LANE34_COLLOQUIAL_MIN_SHARE
    codeswitch_min = _LANE34_CODESWITCH_MIN_SHARE

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    for lang in sorted(by_lang.keys()):
        subset = by_lang[lang]
        n = len(subset)
        if n < min_n:
            warn_issues.append(
                (
                    "lane34_not_reliable_small_n",
                    f"language={lang} n={n} < min_n={min_n}; skipped lane 34 colloquial/code-switch share gate",
                )
            )
            continue

        colloquial_rows = 0
        codeswitch_rows = 0
        for rr in subset:
            asst = rr.get("assistant_response")
            if not isinstance(asst, str):
                continue
            if _lane34_has_colloquial_phrasing(asst):
                colloquial_rows += 1
            if _lane34_has_light_codeswitch(asst):
                codeswitch_rows += 1

        colloquial_share = colloquial_rows / float(n)
        codeswitch_share = codeswitch_rows / float(n)
        if colloquial_share < colloquial_min:
            fail_issues.append(
                (
                    "lane34_colloquial_share_too_low",
                    (
                        f"language={lang} n={n}; colloquial_share={colloquial_share:.3f} < "
                        f"min={colloquial_min:.3f} (matching_rows={colloquial_rows})"
                    ),
                )
            )
        if codeswitch_share < codeswitch_min:
            fail_issues.append(
                (
                    "lane34_codeswitch_share_too_low",
                    (
                        f"language={lang} n={n}; codeswitch_share={codeswitch_share:.3f} < "
                        f"min={codeswitch_min:.3f} (matching_rows={codeswitch_rows})"
                    ),
                )
            )
        if colloquial_share >= colloquial_min and codeswitch_share >= codeswitch_min:
            pass_notes.append(
                (
                    f"lane34_colloquial_codeswitch_share PASS language={lang} n={n} "
                    f"colloquial_share={colloquial_share:.3f} codeswitch_share={codeswitch_share:.3f}"
                )
            )

    return pass_notes, fail_issues, warn_issues


def _evaluate_viability_gate(
    rows: list[dict[str, Any]],
    lane: dict[str, Any],
) -> tuple[bool, list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    validation_cfg = lane.get("validation")
    validation_cfg = validation_cfg if isinstance(validation_cfg, dict) else {}
    viability_cfg = validation_cfg.get("viability")
    if not isinstance(viability_cfg, dict):
        return False, [], [], []
    if viability_cfg.get("enabled") is False:
        return False, [], [], []

    pass_notes: list[str] = []
    fail_issues: list[tuple[str, str]] = []
    warn_issues: list[tuple[str, str]] = []

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        if not isinstance(rr, dict):
            continue
        lang = _norm_lang(rr.get("language")) or "unknown"
        by_lang.setdefault(lang, []).append(rr)

    target_by_lang_raw = viability_cfg.get("target_rows_by_language")
    target_by_lang_raw = target_by_lang_raw if isinstance(target_by_lang_raw, dict) else {}
    target_by_lang: dict[str, int] = {}
    for key, val in target_by_lang_raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
            continue
        target_by_lang[_norm_lang(key)] = int(val)

    target_global: int | None = None
    for maybe in (
        viability_cfg.get("target_rows"),
        lane.get("count_target"),
        (lane.get("template_expand") or {}).get("count_target")
        if isinstance(lane.get("template_expand"), dict)
        else None,
    ):
        if isinstance(maybe, bool):
            continue
        if isinstance(maybe, int) and maybe > 0:
            target_global = int(maybe)
            break

    min_fill_ratio = viability_cfg.get("min_fill_ratio")
    if isinstance(min_fill_ratio, bool) or not isinstance(min_fill_ratio, (int, float)):
        min_fill_ratio = 1.0
    min_fill_ratio = _safe_ratio(float(min_fill_ratio))
    if min_fill_ratio <= 0.0:
        min_fill_ratio = 1.0

    underfilled_severity = str(viability_cfg.get("underfilled_severity") or "fatal").strip().lower()
    if underfilled_severity not in {"fatal", "warn"}:
        underfilled_severity = "fatal"

    attempts_per_row_value: int | None = None
    for maybe in (
        viability_cfg.get("attempts_per_row"),
        (lane.get("template_expand") or {}).get("attempts_per_row")
        if isinstance(lane.get("template_expand"), dict)
        else None,
    ):
        if isinstance(maybe, bool):
            continue
        if isinstance(maybe, int) and maybe > 0:
            attempts_per_row_value = int(maybe)
            break

    max_attempts_per_row = viability_cfg.get("max_attempts_per_row")
    if isinstance(max_attempts_per_row, bool) or not isinstance(max_attempts_per_row, int) or max_attempts_per_row <= 0:
        max_attempts_per_row = None
    else:
        max_attempts_per_row = int(max_attempts_per_row)

    attempts_severity = str(viability_cfg.get("attempts_per_row_severity") or "warn").strip().lower()
    if attempts_severity not in {"fatal", "warn"}:
        attempts_severity = "warn"

    langs = set(by_lang.keys())
    langs.update(k for k in target_by_lang.keys() if k)
    if not langs:
        langs.add("unknown")

    for lang in sorted(langs):
        n = len(by_lang.get(lang, []))
        target = target_by_lang.get(lang, target_global)
        if isinstance(target, int) and target > 0:
            min_required = int((float(target) * min_fill_ratio) + 0.999999)
            if n < min_required:
                detail = (
                    f"language={lang} rows_validated={n} < min_required={min_required} "
                    f"(target={target}, min_fill_ratio={min_fill_ratio:.2f})"
                )
                if underfilled_severity == "fatal":
                    fail_issues.append(("underfilled", detail))
                else:
                    warn_issues.append(("underfilled", detail))
            else:
                pass_notes.append(
                    (
                        f"viability PASS language={lang} rows_validated={n} "
                        f"target={target} min_fill_ratio={min_fill_ratio:.2f}"
                    )
                )

        if isinstance(attempts_per_row_value, int) and isinstance(max_attempts_per_row, int):
            if attempts_per_row_value > max_attempts_per_row:
                detail = (
                    f"language={lang} attempts_per_row={attempts_per_row_value} "
                    f"> max_attempts_per_row={max_attempts_per_row}"
                )
                if attempts_severity == "fatal":
                    fail_issues.append(("attempts_per_row_too_high", detail))
                else:
                    warn_issues.append(("attempts_per_row_too_high", detail))

    return True, pass_notes, fail_issues, warn_issues


def validate_generated_rows(
    rows: list[dict[str, Any]],
    lane_id: str,
    lane: dict[str, Any],
    rule_profile: int,
    repo_root: str | None = None,
    run_id: str | None = None,
) -> tuple[bool, str]:
    reasons: Counter[str] = Counter()
    examples: list[str] = []
    warnings: Counter[str] = Counter()
    warning_examples: list[str] = []
    reason_details: dict[str, list[str]] = {}
    warning_details: dict[str, list[str]] = {}
    reason_gates: dict[str, Counter[str]] = {}
    warning_gates: dict[str, Counter[str]] = {}
    pass_checks: list[str] = []
    validated_rows: list[dict[str, Any]] = []
    validated_rows_by_lang: dict[str, list[dict[str, Any]]] = {}
    rows_for_later: list[dict[str, Any]] = []
    rows_for_later_by_lang: dict[str, list[dict[str, Any]]] = {}
    row_lang_by_id: dict[str, str] = {}
    qc_report_paths: list[str] = []
    slice_stats: dict[str, dict[str, Any]] = {}
    viability_configured = False
    expected_language = _expected_lane_language(lane)
    lane_policy = get_lane_policy(lane_id)

    def _ensure_slice(lang: str) -> tuple[str, dict[str, Any]]:
        ltag = _norm_lang(lang) or "unknown"
        if ltag not in slice_stats:
            slice_stats[ltag] = {
                "rows_input": 0,
                "rows_generated": 0,
                "fatals": Counter(),
                "warns": Counter(),
                "gate_fatals": {g: Counter() for g in _GATE_ORDER},
                "gate_warns": {g: Counter() for g in _GATE_ORDER},
                "gate_notes": {g: [] for g in _GATE_ORDER},
                "top_examples": {},
            }
        return ltag, slice_stats[ltag]

    def _record_example(
        *,
        lang: str,
        code: str,
        row_id: str | None,
        detail: str,
    ) -> None:
        _, stats = _ensure_slice(lang)
        msg = _sanitize_example_message(code, detail)
        if not msg:
            return
        top_examples = stats["top_examples"]
        bucket = top_examples.get(code)
        if not isinstance(bucket, list):
            bucket = []
            top_examples[code] = bucket
        if len(bucket) >= 5:
            return
        bucket.append(
            {
                "row_id": row_id if isinstance(row_id, str) and row_id.strip() else "slice",
                "message": msg,
            }
        )

    def _record_issue(
        *,
        severity: str,
        reason: str,
        detail: str,
        lang: str,
        gate: str,
        row_id: str | None,
    ) -> None:
        ltag = _norm_lang(lang) or "unknown"
        if ltag == "unknown" and isinstance(row_id, str) and row_id in row_lang_by_id:
            ltag = row_lang_by_id[row_id]
        if gate not in _GATE_ORDER:
            gate = "invariants"
        _, stats = _ensure_slice(ltag)
        if severity == "fatal":
            stats["fatals"][reason] += 1
            stats["gate_fatals"][gate][reason] += 1
        else:
            stats["warns"][reason] += 1
            stats["gate_warns"][gate][reason] += 1
        _record_example(lang=ltag, code=reason, row_id=row_id, detail=detail)

    for idx, rr in enumerate(rows, start=1):
        if isinstance(rr, dict):
            rid = _row_id(rr, idx)
            lang = _norm_lang(rr.get("language")) or "unknown"
        else:
            rid = f"row#{idx}"
            lang = "unknown"
        row_lang_by_id[rid] = lang
        _, stats = _ensure_slice(lang)
        stats["rows_input"] += 1
        stats["rows_generated"] += 1

    def _hit(
        reason: str,
        detail: str,
        *,
        lang: str = "unknown",
        gate: str = "invariants",
        row_id: str | None = None,
    ) -> None:
        reasons[reason] += 1
        if len(examples) < 24:
            examples.append(f"- {reason}: {detail}")
        bucket = reason_details.setdefault(reason, [])
        if len(bucket) < 5 and detail not in bucket:
            bucket.append(detail)
        reason_gates.setdefault(reason, Counter())[gate] += 1
        _record_issue(severity="fatal", reason=reason, detail=detail, lang=lang, gate=gate, row_id=row_id)

    def _warn(
        reason: str,
        detail: str,
        *,
        lang: str = "unknown",
        gate: str = "invariants",
        row_id: str | None = None,
    ) -> None:
        warnings[reason] += 1
        if len(warning_examples) < 24:
            warning_examples.append(f"- {reason}: {detail}")
        bucket = warning_details.setdefault(reason, [])
        if len(bucket) < 5 and detail not in bucket:
            bucket.append(detail)
        warning_gates.setdefault(reason, Counter())[gate] += 1
        _record_issue(severity="warn", reason=reason, detail=detail, lang=lang, gate=gate, row_id=row_id)

    def _apply_stage_results(
        pass_notes_in: list[str],
        fail_issues_in: list[tuple[str, str]],
        warn_issues_in: list[tuple[str, str]],
        *,
        gate: str,
    ) -> None:
        for note in pass_notes_in:
            if len(pass_checks) < 24:
                pass_checks.append(note)
            lang = _lang_from_detail(note)
            _, stats = _ensure_slice(lang)
            if len(stats["gate_notes"][gate]) < 5:
                stats["gate_notes"][gate].append(note)
        for code, detail in fail_issues_in:
            _hit(code, detail, lang=_lang_from_detail(detail), gate=gate, row_id=None)
        for code, detail in warn_issues_in:
            _warn(code, detail, lang=_lang_from_detail(detail), gate=gate, row_id=None)

    for idx, rr in enumerate(rows, start=1):
        if not isinstance(rr, dict):
            rid = f"row#{idx}"
            _hit("row_not_dict", f"{rid} is not an object", lang="unknown", gate="invariants", row_id=rid)
            continue

        rid = _row_id(rr, idx)
        lang = _norm_lang(rr.get("language")) or row_lang_by_id.get(rid, "unknown")

        ok_row, reason = validate_row_v16(rr, lane_id, expected_language=expected_language)
        if not ok_row:
            code = str(reason).strip() if isinstance(reason, str) else ""
            _hit(code or "contract_validation", f"{rid}: {reason}", lang=lang, gate="invariants", row_id=rid)
            continue
        validated_rows.append(rr)
        validated_rows_by_lang.setdefault(lang, []).append(rr)
        if isinstance(reason, str) and reason.startswith("warn:"):
            warn_blob = reason[len("warn:") :]
            for token in warn_blob.split("|"):
                tok = token.strip()
                if not tok:
                    continue
                code = tok.split(":", 1)[0] if ":" in tok else tok
                _warn(code, f"{rid}: {tok}", lang=lang, gate="invariants", row_id=rid)

        turn_issues = check_turn_structure(rr, lane_id)
        if turn_issues:
            for issue in turn_issues:
                _hit(issue.code, f"{rid}: {issue.detail}", lang=lang, gate="invariants", row_id=rid)
            continue

        if rule_profile >= 2:
            v17_issues = validate_row_v17(rr, lane_id)
            for code, detail in v17_issues:
                _hit(f"v17_{code}", f"{rid}: {detail}", lang=lang, gate="invariants", row_id=rid)
            if v17_issues:
                continue

            ok_msg, why = _validate_messages_alignment(rr)
            if not ok_msg:
                _hit("messages_alignment", f"{rid}: {why}", lang=lang, gate="invariants", row_id=rid)
                continue

            user = rr.get("user_message")
            if isinstance(user, str):
                if _PLACEHOLDER_RE.search(user):
                    _hit(
                        "placeholder_marker",
                        f"{rid}: user_message contains template marker",
                        lang=lang,
                        gate="invariants",
                        row_id=rid,
                    )
                    continue

            asst = rr.get("assistant_response")
            if isinstance(asst, str) and asst.strip():
                if _PLACEHOLDER_RE.search(asst):
                    _hit(
                        "placeholder_marker",
                        f"{rid}: assistant_response contains template marker -> '{_safe_preview(asst)}'",
                        lang=lang,
                        gate="invariants",
                        row_id=rid,
                    )
                    continue

            safety_issues = check_content_safety(rr, lane_id)
            for issue in safety_issues:
                _hit(
                    issue.code,
                    f"{rid}: {issue.detail}",
                    lang=lang,
                    gate="invariants",
                    row_id=rid,
                )
            if safety_issues:
                continue

            malformed_issues = evaluate_row_malformed_v41(rr, lane_id)
            for issue in malformed_issues:
                _hit(issue.code, f"{rid}: {issue.detail}", lang=lang, gate="malformed", row_id=rid)
            if malformed_issues:
                continue

            # Equator v4.1 repetition/naturalness gates run before duplicate-pair checks.
            rep_fatals, rep_warns = evaluate_row_repetition_v41(rr, lane_id)
            for issue in rep_fatals:
                _hit(issue.code, f"{rid}: {issue.detail}", lang=lang, gate="repetition", row_id=rid)
            for issue in rep_warns:
                _warn(issue.code, f"{rid}: {issue.detail}", lang=lang, gate="repetition", row_id=rid)
            if rep_fatals:
                continue

            if (
                isinstance(asst, str)
                and asst.strip()
                and not lane_policy.assistant_response_must_be_code_only
                and _MECH_LEAK_RE.search(asst)
            ):
                _hit(
                    "mechanism_leakage",
                    f"{rid}: assistant_response -> '{_safe_preview(asst)}'",
                    lang=lang,
                    gate="leakage",
                    row_id=rid,
                )
                continue

            rows_for_later.append(rr)
            rows_for_later_by_lang.setdefault(lang, []).append(rr)

    rows_after_dup = list(rows_for_later)
    rows_after_dup_by_lang = {k: list(v) for k, v in rows_for_later_by_lang.items()}

    if rule_profile >= 3 and rows_for_later:
        dup_failed_ids: set[str] = set()
        seen_user: dict[str, str] = {}
        seen_asst: dict[str, str] = {}
        for idx, rr in enumerate(rows_for_later, start=1):
            if not isinstance(rr, dict):
                continue
            rid = _row_id(rr, idx)
            lang = _norm_lang(rr.get("language")) or row_lang_by_id.get(rid, "unknown")
            user_norm = _norm_text(rr.get("user_message"))
            if user_norm:
                prev = seen_user.get(user_norm)
                if prev is not None:
                    _hit(
                        "duplicate_user_message",
                        f"{rid} duplicates {prev}",
                        lang=lang,
                        gate="duplication",
                        row_id=rid,
                    )
                    dup_failed_ids.add(rid)
                else:
                    seen_user[user_norm] = rid
            asst_norm = _norm_text(rr.get("assistant_response"))
            if asst_norm:
                prev = seen_asst.get(asst_norm)
                if prev is not None:
                    _hit(
                        "duplicate_assistant_response",
                        f"{rid} duplicates {prev}",
                        lang=lang,
                        gate="duplication",
                        row_id=rid,
                    )
                    dup_failed_ids.add(rid)
                else:
                    seen_asst[asst_norm] = rid

        dup_fatals, dup_warns = check_duplication_pairwise_v41(rows_for_later, lane)
        for issue in dup_fatals:
            rid = _pair_row_id(issue.detail)
            pair_ids = _pair_row_ids(issue.detail)
            if pair_ids is not None:
                dup_failed_ids.add(pair_ids[0])
                dup_failed_ids.add(pair_ids[1])
            elif isinstance(rid, str):
                dup_failed_ids.add(rid)
            _hit(
                issue.code,
                issue.detail,
                lang=row_lang_by_id.get(rid, "unknown") if isinstance(rid, str) else "unknown",
                gate="duplication",
                row_id=rid,
            )
        for issue in dup_warns:
            rid = _pair_row_id(issue.detail)
            _warn(
                issue.code,
                issue.detail,
                lang=row_lang_by_id.get(rid, "unknown") if isinstance(rid, str) else "unknown",
                gate="duplication",
                row_id=rid,
            )

        vcfg = lane.get("validation")
        vcfg = vcfg if isinstance(vcfg, dict) else {}
        # Equator v4.1 §7 default cap is 8% when lane-specific value is absent.
        opening_cap_raw = vcfg.get("opening_family_max_share", 0.08)
        if isinstance(opening_cap_raw, (int, float)) and not isinstance(opening_cap_raw, bool):
            opening_cap = float(opening_cap_raw)
            if 0.0 < opening_cap < 1.0:
                openings: Counter[str] = Counter()
                total = 0
                for rr in rows_for_later:
                    if not isinstance(rr, dict):
                        continue
                    asst = rr.get("assistant_response")
                    if not isinstance(asst, str) or not asst.strip():
                        continue
                    lang = _norm_lang(rr.get("language"))
                    key = _opening_key(asst, lang=lang)
                    if not key:
                        continue
                    openings[key] += 1
                    total += 1
                if total >= 100 and openings:
                    _, top_n = openings.most_common(1)[0]
                    share = top_n / float(total)
                    if share > opening_cap:
                        _hit(
                            "opening_diversity",
                            f"top opening share={share:.3f} > cap={opening_cap:.3f} (n={total})",
                            gate="duplication",
                        )

        if dup_failed_ids:
            filtered_rows: list[dict[str, Any]] = []
            filtered_by_lang: dict[str, list[dict[str, Any]]] = {}
            for idx, rr in enumerate(rows_for_later, start=1):
                if not isinstance(rr, dict):
                    continue
                rid = _row_id(rr, idx)
                if rid in dup_failed_ids:
                    continue
                filtered_rows.append(rr)
                lang = _norm_lang(rr.get("language")) or "unknown"
                filtered_by_lang.setdefault(lang, []).append(rr)
            rows_after_dup = filtered_rows
            rows_after_dup_by_lang = filtered_by_lang

    if rule_profile >= 2:
        mode_tone_pass, mode_tone_fails, mode_tone_warns = _evaluate_mode_tone_proportions(
            rows_after_dup,
            lane_id,
            lane,
        )
        _apply_stage_results(mode_tone_pass, mode_tone_fails, mode_tone_warns, gate="proportions")

        lane_optional_pass, lane_optional_fails, lane_optional_warns = _evaluate_lane_optional_tool_image_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane_optional_pass, lane_optional_fails, lane_optional_warns, gate="proportions")

        lane03_pass, lane03_fails, lane03_warns = _evaluate_lane03_reasoning_structure_distribution(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane03_pass, lane03_fails, lane03_warns, gate="proportions")

        lane04_pass, lane04_fails, lane04_warns = _evaluate_lane04_answer_length_distribution(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane04_pass, lane04_fails, lane04_warns, gate="proportions")

        lane07_pass, lane07_fails, lane07_warns = _evaluate_lane07_borderline_and_split(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane07_pass, lane07_fails, lane07_warns, gate="proportions")

        lane10_pass, lane10_fails, lane10_warns = _evaluate_lane10_borderline_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane10_pass, lane10_fails, lane10_warns, gate="proportions")

        lane05_pass, lane05_fails, lane05_warns = _evaluate_lane05_slice_distributions(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane05_pass, lane05_fails, lane05_warns, gate="proportions")

        lane09_pass, lane09_fails, lane09_warns = _evaluate_lane09_flow_state_distribution(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane09_pass, lane09_fails, lane09_warns, gate="proportions")

        lane28_pass, lane28_fails, lane28_warns = _evaluate_lane28_emote6_distribution(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane28_pass, lane28_fails, lane28_warns, gate="proportions")

        lane30_pass, lane30_fails, lane30_warns = _evaluate_lane30_creative_extraction_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane30_pass, lane30_fails, lane30_warns, gate="proportions")

        lane33_pass: list[str] = []
        lane33_fails: list[tuple[str, str]] = []
        lane33_warns: list[tuple[str, str]] = []
        if _lane_num_from_id(lane_id) == 33:
            lane33_pass, lane33_fails, lane33_warns = _evaluate_lane33_fallback_limitation_share(
                rows_after_dup,
                expected_language,
                _slice_thresholds(lane_id, lane),
            )
        _apply_stage_results(lane33_pass, lane33_fails, lane33_warns, gate="proportions")

        lane20_pass, lane20_fails, lane20_warns = _evaluate_lane20_prior_content_reference_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane20_pass, lane20_fails, lane20_warns, gate="proportions")

        lane29_pass, lane29_fails, lane29_warns = _evaluate_lane29_misinfo_correction_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane29_pass, lane29_fails, lane29_warns, gate="proportions")

        lane34_pass, lane34_fails, lane34_warns = _evaluate_lane34_colloquial_codeswitch_share(
            rows_after_dup,
            lane_id,
        )
        _apply_stage_results(lane34_pass, lane34_fails, lane34_warns, gate="proportions")

        viability_configured, viability_pass, viability_fails, viability_warns = _evaluate_viability_gate(
            rows_after_dup,
            lane,
        )
        for note in viability_pass:
            if len(pass_checks) < 24:
                pass_checks.append(note)
            lang = _lang_from_detail(note)
            _, stats = _ensure_slice(lang)
            if len(stats["gate_notes"]["viability"]) < 5:
                stats["gate_notes"]["viability"].append(note)
        for code, detail in viability_fails:
            _hit(code, detail, lang=_lang_from_detail(detail), gate="viability", row_id=None)
        for code, detail in viability_warns:
            _warn(code, detail, lang=_lang_from_detail(detail), gate="viability", row_id=None)

    resolved_repo_root = repo_root if isinstance(repo_root, str) and repo_root.strip() else _default_repo_root()
    resolved_run_id = _resolve_run_id(run_id)
    report_date = date.today().isoformat()
    thresholds = _slice_thresholds(lane_id, lane)
    commit = _git_sha_or_unknown()
    for lang in sorted(slice_stats.keys()):
        stats = slice_stats[lang]
        gate_entries: list[dict[str, Any]] = []
        for gate in _GATE_ORDER:
            fatal_codes = stats["gate_fatals"].get(gate, Counter())
            warn_codes = stats["gate_warns"].get(gate, Counter())
            if gate == "warn_only":
                fatal_codes = Counter()
                warn_codes = stats["warns"]
            entry: dict[str, Any] = {
                "name": gate,
                "status": "PASS",
            }
            if fatal_codes:
                entry["status"] = "FAIL"
                entry["fatal_codes"] = _counter_to_plain(fatal_codes)
            elif warn_codes:
                entry["status"] = "WARN"
            if warn_codes:
                entry["warn_codes"] = _counter_to_plain(warn_codes)
            notes = stats["gate_notes"].get(gate, [])
            details: dict[str, Any] = {}
            if gate == "proportions":
                n_val: int | None = None
                for blob in notes:
                    m = re.search(r"\bn=(\d+)\b", str(blob))
                    if m:
                        n_val = int(m.group(1))
                        break
                if n_val is not None:
                    details["n"] = n_val
            if gate == "viability" and not details and not notes and not fatal_codes and not warn_codes:
                if viability_configured:
                    details["notes"] = "evaluated_no_issues"
                else:
                    details["notes"] = "not_applicable"
            elif gate == "warn_only" and not details:
                details["notes"] = "aggregated_non_blocking_warnings"
            if notes:
                details["notes"] = " | ".join(str(x) for x in notes[:3])
            if details:
                entry["details"] = details
            gate_entries.append(entry)

        qc_result = {
            "meta": {
                "lane_id": lane_id,
                "lang": lang,
                "run_id": resolved_run_id,
                "date": report_date,
                "rule_profile": rule_profile,
                "spec_version": _SPEC_VERSION,
                "equator_version": _EQUATOR_VERSION,
                "generator_commit": commit,
            },
            "counts": {
                "rows_input": int(stats["rows_input"]),
                "rows_generated": int(stats["rows_generated"]),
                "rows_validated": len(rows_after_dup_by_lang.get(lang, [])),
                "fatal_violations": int(sum(stats["fatals"].values())),
                "warn_non_blocking": int(sum(stats["warns"].values())),
                "unique_fatal_codes": int(len(stats["fatals"])),
                "unique_warn_codes": int(len(stats["warns"])),
            },
            "gates": gate_entries,
            "fatals": _counter_to_plain(stats["fatals"]),
            "warns": _counter_to_plain(stats["warns"]),
            "top_examples": dict(stats["top_examples"]),
            "thresholds": dict(thresholds),
        }
        try:
            path = write_qc_report(
                repo_root=resolved_repo_root,
                lane_id=lane_id,
                lang=lang,
                run_id=resolved_run_id,
                date_yyyy_mm_dd=report_date,
                qc_result=qc_result,
            )
            qc_report_paths.append(path)
        except Exception as e:
            _warn("qc_report_write_failed", f"language={lang}: {e}", lang=lang, gate="invariants")

    if not reasons:
        lines = [
            f"rule_profile=0{rule_profile} PASS: validated_rows={len(rows)} "
            "(no hard violations detected)"
        ]
        gate_warn_totals: dict[str, Counter[str]] = {g: Counter() for g in _GATE_ORDER}
        for stats in slice_stats.values():
            gw = stats.get("gate_warns")
            if not isinstance(gw, dict):
                continue
            for gate in _GATE_ORDER:
                c = gw.get(gate)
                if isinstance(c, Counter):
                    gate_warn_totals[gate].update(c)
        if pass_checks:
            lines.append("checks:")
            for note in pass_checks:
                lines.append(f"- {note}")
        if warnings:
            lines.append("warn_gate_breakdown:")
            for gate in _GATE_ORDER:
                wc = gate_warn_totals.get(gate, Counter())
                if not wc:
                    continue
                short = ", ".join(f"{k}:{v}" for k, v in wc.most_common())
                lines.append(f"- {gate}: {short}")
            lines.append("warnings:")
            for reason, count in warnings.most_common():
                gates = warning_gates.get(reason, Counter())
                gate_note = ", ".join(f"{g}:{n}" for g, n in gates.most_common()) if gates else "unknown"
                lines.append(f"- {reason}: {count} (gates={gate_note})")
                for d in warning_details.get(reason, [])[:3]:
                    lines.append(f"  - {d}")
            if warning_examples:
                lines.append("warning_examples:")
                lines.extend(warning_examples)
        if qc_report_paths:
            lines.append("qc_reports:")
            for p in qc_report_paths:
                lines.append(f"- {p}")
        return True, "\n".join(lines)

    lines = [
        f"rule_profile=0{rule_profile} FAIL: violations={sum(reasons.values())}, unique={len(reasons)}",
        "top_reasons:",
    ]
    gate_fatal_totals: dict[str, Counter[str]] = {g: Counter() for g in _GATE_ORDER}
    gate_warn_totals: dict[str, Counter[str]] = {g: Counter() for g in _GATE_ORDER}
    for stats in slice_stats.values():
        gf = stats.get("gate_fatals")
        gw = stats.get("gate_warns")
        if isinstance(gf, dict):
            for gate in _GATE_ORDER:
                c = gf.get(gate)
                if isinstance(c, Counter):
                    gate_fatal_totals[gate].update(c)
        if isinstance(gw, dict):
            for gate in _GATE_ORDER:
                c = gw.get(gate)
                if isinstance(c, Counter):
                    gate_warn_totals[gate].update(c)
    for reason, count in reasons.most_common():
        gates = reason_gates.get(reason, Counter())
        gate_note = ", ".join(f"{g}:{n}" for g, n in gates.most_common()) if gates else "unknown"
        lines.append(f"- {reason}: {count} (gates={gate_note})")
    lines.append("fatal_gate_breakdown:")
    for gate in _GATE_ORDER:
        fc = gate_fatal_totals.get(gate, Counter())
        if not fc:
            continue
        short = ", ".join(f"{k}:{v}" for k, v in fc.most_common())
        lines.append(f"- {gate}: {short}")
    if examples:
        lines.append("examples:")
        lines.extend(examples)
    lines.append("detailed_failures:")
    for reason, count in reasons.most_common():
        lines.append(f"- {reason}: count={count}")
        for d in reason_details.get(reason, [])[:5]:
            lines.append(f"  - {d}")
    if pass_checks:
        lines.append("checks:")
        for note in pass_checks:
            lines.append(f"- {note}")
    if warnings:
        lines.append("warn_gate_breakdown:")
        for gate in _GATE_ORDER:
            wc = gate_warn_totals.get(gate, Counter())
            if not wc:
                continue
            short = ", ".join(f"{k}:{v}" for k, v in wc.most_common())
            lines.append(f"- {gate}: {short}")
        lines.append("warnings_non_blocking:")
        for reason, count in warnings.most_common():
            gates = warning_gates.get(reason, Counter())
            gate_note = ", ".join(f"{g}:{n}" for g, n in gates.most_common()) if gates else "unknown"
            lines.append(f"- {reason}: {count} (gates={gate_note})")
            for d in warning_details.get(reason, [])[:3]:
                lines.append(f"  - {d}")
        if warning_examples:
            lines.append("warning_examples:")
            lines.extend(warning_examples)
    if qc_report_paths:
        lines.append("qc_reports:")
        for p in qc_report_paths:
            lines.append(f"- {p}")
    return False, "\n".join(lines)

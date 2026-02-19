from __future__ import annotations

from collections import Counter
import re
from typing import Any

from ..contracts.v16_lane_contracts import contract_for_lane

try:
    from pythainlp.tokenize import word_tokenize as _THAI_WORD_TOKENIZE
except Exception:  # pragma: no cover - optional dependency
    _THAI_WORD_TOKENIZE = None


_LANE_ID_RE = re.compile(r"^lane_(\d+)")
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")

_CJK_LANGS = {"zh", "zh-hk", "zh_hk", "zh-hans", "zh_hans", "zh-hant", "zh_hant", "ja", "ko"}
_THAI_LANGS = {"th"}
_LATIN_LANGS = {"en", "es", "fr", "de", "it", "pt-br", "pt_br", "vi"}
_HI_VI_LANGS = {"hi", "vi"}
_TARGET_LANES = {21, 22, 23}


def _lane_num(lane_id: str) -> int | None:
    m = _LANE_ID_RE.match(str(lane_id or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _norm_lang(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _is_hi_or_vi_lang(lang: str) -> bool:
    if lang in _HI_VI_LANGS:
        return True
    return lang.startswith("hi-") or lang.startswith("hi_") or lang.startswith("vi-") or lang.startswith("vi_")


def _is_carveout_lang(lang: str) -> bool:
    if lang in _CJK_LANGS or lang in _THAI_LANGS:
        return True
    return _is_hi_or_vi_lang(lang)


def _char_ngrams(chars: list[str], n: int) -> list[str]:
    if n <= 1 or len(chars) < n:
        return []
    out: list[str] = []
    for i in range(0, len(chars) - n + 1):
        out.append("".join(chars[i : i + n]))
    return out


def _char_bi_tri_grams(chars: list[str]) -> list[str]:
    out = _char_ngrams(chars, 2)
    if len(chars) >= 3:
        out.extend(_char_ngrams(chars, 3))
    return out


def _thai_word_tokens(text: str) -> list[str]:
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
        out.append(tok)
    return out


def _latin_runs(text: str) -> list[str]:
    return [t.lower() for t in _LATIN_WORD_RE.findall(text or "")]


def _cjk_word_tokens(text: str) -> list[str]:
    # Use explicit whitespace-delimited CJK chunks when present;
    # otherwise fall back to char bi/tri-grams.
    raw = str(text or "").strip()
    if not raw or not any(ch.isspace() for ch in raw):
        return []
    toks: list[str] = []
    for part in raw.split():
        tok = part.strip()
        if not tok:
            continue
        if _CJK_CHAR_RE.search(tok):
            toks.append(tok)
    return toks if len(toks) >= 2 else []


def _tokenize_script_aware_v17(text: str, lang: str) -> list[str]:
    if not text:
        return []

    if lang in _THAI_LANGS:
        words = _thai_word_tokens(text)
        if words:
            return words + _latin_runs(text)
        chars = _THAI_CHAR_RE.findall(text)
        return _char_bi_tri_grams(chars) + _latin_runs(text)

    if lang in _CJK_LANGS or lang.startswith("zh"):
        words = _cjk_word_tokens(text)
        if words:
            return words + _latin_runs(text)
        chars = _CJK_CHAR_RE.findall(text)
        grams = _char_bi_tri_grams(chars)
        if grams:
            return grams + _latin_runs(text)
        return _latin_runs(text)

    if _is_hi_or_vi_lang(lang):
        words = [t.lower() for t in _WORD_RE.findall(text) if t]
        if words:
            return words
        chars = [ch.lower() for ch in text if _WORD_RE.fullmatch(ch)]
        grams = _char_bi_tri_grams(chars)
        return grams + _latin_runs(text)

    if lang in _LATIN_LANGS:
        return [t.lower() for t in _LATIN_WORD_RE.findall(text)]

    return [t.lower() for t in _WORD_RE.findall(text) if t]


def _o_min_multiset(tokens_a: list[str], tokens_b: list[str]) -> float:
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


def check(row: dict[str, Any], lane_id: str) -> str | None:
    lane_num = _lane_num(lane_id)
    if lane_num not in _TARGET_LANES:
        return None
    if not isinstance(row, dict):
        return None

    contract = contract_for_lane(lane_id)
    metric = contract.get("user_assistant_overlap_metric")
    tokenizer = contract.get("user_assistant_overlap_tokenizer")
    max_ratio = contract.get("user_assistant_overlap_max")

    if metric != "O_min" or tokenizer != "script_aware_v17":
        return None
    if not isinstance(max_ratio, (int, float)) or isinstance(max_ratio, bool):
        return None
    max_ratio = float(max_ratio)
    if max_ratio < 0.0 or max_ratio > 1.0:
        return None

    user = row.get("user_message")
    assistant = row.get("assistant_response")
    if not isinstance(user, str) or not isinstance(assistant, str):
        return None
    if not user.strip() or not assistant.strip():
        return None

    lang = _norm_lang(row.get("language"))
    user_tokens = _tokenize_script_aware_v17(user, lang)
    assistant_tokens = _tokenize_script_aware_v17(assistant, lang)
    # Keep carve-out scripts aligned with CJK/TH behavior: avoid tiny-span overlaps.
    if _is_carveout_lang(lang) and min(len(user_tokens), len(assistant_tokens)) < 3:
        return None
    overlap = _o_min_multiset(user_tokens, assistant_tokens)

    if overlap > max_ratio:
        return (
            f"user_assistant_overlap O_min={overlap:.3f} exceeds max={max_ratio:.3f} "
            f"(lane={lane_id}, tokenizer=script_aware_v17)"
        )
    return None


def check_user_assistant_overlap_v17(row: dict[str, Any], lane_id: str) -> str | None:
    return check(row, lane_id)

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import re
from typing import Any

from .lane_policy_v17 import get_lane_policy

try:
    from pythainlp.tokenize import word_tokenize as _THAI_WORD_TOKENIZE
except Exception:  # pragma: no cover - optional dependency
    _THAI_WORD_TOKENIZE = None


_WORD_RE = re.compile(r"\w+", re.UNICODE)
_LATIN_RUN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")
_CODE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")

_CJK_LANGS = {"zh-hk", "zh_hk", "zh-hant", "zh_hant", "zh-hans", "zh_hans", "ja", "ko"}
_THAI_LANGS = {"th"}

_WINDOW_TOKEN = 12
_WINDOW_BIGRAM_TOKEN = 30

_FUNCTION_WORDS: dict[str, set[str]] = {
    "en": {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "than",
        "to",
        "of",
        "for",
        "in",
        "on",
        "at",
        "from",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "will",
        "may",
        "might",
        "must",
        "not",
        "no",
        "yes",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "me",
        "my",
        "mine",
        "your",
        "yours",
        "our",
        "ours",
        "their",
        "theirs",
    },
    "de": {"der", "die", "das", "und", "oder", "zu", "von", "mit", "im", "in", "auf", "ist", "sind"},
    "es": {"el", "la", "los", "las", "y", "o", "de", "del", "en", "con", "por", "para", "es", "son"},
    "fr": {"le", "la", "les", "et", "ou", "de", "du", "des", "en", "avec", "pour", "est", "sont"},
    "it": {"il", "lo", "la", "gli", "le", "e", "o", "di", "del", "in", "con", "per", "e", "sono"},
    "pt": {"o", "a", "os", "as", "e", "ou", "de", "do", "da", "em", "com", "para", "e", "sao", "é"},
    "th": {"และ", "ที่", "ใน", "ของ", "เป็น", "ได้", "ให้", "กับ", "ว่า", "ก็"},
    "zh": {"的", "了", "在", "是", "和", "也", "都", "就"},
    "ja": {"は", "が", "を", "に", "で", "と", "も", "の", "へ", "や", "か"},
    "ko": {"은", "는", "이", "가", "을", "를", "에", "의", "도", "와", "과"},
}


@dataclass(frozen=True)
class RepetitionIssue:
    code: str
    severity: str  # fatal | warn
    detail: str


def _norm_lang(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _lang_key_for_stopwords(lang: str) -> str:
    if lang in _FUNCTION_WORDS:
        return lang
    if "-" in lang:
        base = lang.split("-", 1)[0]
        if base in _FUNCTION_WORDS:
            return base
    if "_" in lang:
        base = lang.split("_", 1)[0]
        if base in _FUNCTION_WORDS:
            return base
    if lang.startswith("zh"):
        return "zh"
    return lang


def _function_words(lang: str) -> set[str]:
    key = _lang_key_for_stopwords(lang)
    return _FUNCTION_WORDS.get(key, set())


def _char_ngrams(chars: list[str], n: int) -> list[str]:
    if n <= 1 or len(chars) < n:
        return []
    out: list[str] = []
    for i in range(0, len(chars) - n + 1):
        out.append("".join(chars[i : i + n]))
    return out


def _char_bi_tri_grams(chars: list[str]) -> list[str]:
    toks = _char_ngrams(chars, 2)
    if len(chars) >= 3:
        toks.extend(_char_ngrams(chars, 3))
    return toks


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


def _repetition_tokens(text: str, lang: str) -> list[str]:
    if not text:
        return []

    if lang in _THAI_LANGS:
        thai_words = _thai_word_tokens(text)
        if thai_words:
            return thai_words
        chars = _THAI_CHAR_RE.findall(text)
        return _char_bi_tri_grams(chars)

    if lang in _CJK_LANGS:
        chars = _CJK_CHAR_RE.findall(text)
        cjk_tokens = _char_bi_tri_grams(chars)
        if cjk_tokens:
            latin = _LATIN_RUN_RE.findall(text.lower())
            return cjk_tokens + latin
        return _LATIN_RUN_RE.findall(text.lower())

    return [t for t in _WORD_RE.findall(text.lower()) if t]


def _code_safe_tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _CODE_TOKEN_RE.finditer(text or "")]


def _first_adjacent_duplicate(tokens: list[str]) -> str | None:
    if len(tokens) < 2:
        return None
    for i in range(1, len(tokens)):
        if tokens[i] and tokens[i] == tokens[i - 1]:
            return tokens[i]
    return None


def _first_triplicate_token(tokens: list[str], window: int) -> str | None:
    if len(tokens) < 3:
        return None
    counts: Counter[str] = Counter()
    q: deque[str] = deque()
    for tok in tokens:
        q.append(tok)
        counts[tok] += 1
        if len(q) > window:
            old = q.popleft()
            counts[old] -= 1
            if counts[old] <= 0:
                counts.pop(old, None)
        if len(q) >= 3:
            for key, n in counts.items():
                if n >= 3:
                    return key
    return None


def _first_triplicate_bigram(tokens: list[str], window_tokens: int) -> tuple[str, str] | None:
    if len(tokens) < 4:
        return None

    bigrams: list[tuple[str, str]] = []
    for i in range(0, len(tokens) - 1):
        bigrams.append((tokens[i], tokens[i + 1]))
    if len(bigrams) < 3:
        return None

    window_bigrams = max(3, window_tokens - 1)
    counts: Counter[tuple[str, str]] = Counter()
    q: deque[tuple[str, str]] = deque()
    for bg in bigrams:
        q.append(bg)
        counts[bg] += 1
        if len(q) > window_bigrams:
            old = q.popleft()
            counts[old] -= 1
            if counts[old] <= 0:
                counts.pop(old, None)
        if len(q) >= 3:
            for key, n in counts.items():
                if n >= 3:
                    return key
    return None


def _is_function_token(tok: str, lang: str) -> bool:
    if not tok:
        return False
    return tok in _function_words(lang)


def _is_function_bigram(bg: tuple[str, str], lang: str) -> bool:
    left, right = bg
    return _is_function_token(left, lang) and _is_function_token(right, lang)


def evaluate_row_repetition_v41(row: dict[str, Any], lane_id: str) -> tuple[list[RepetitionIssue], list[RepetitionIssue]]:
    policy = get_lane_policy(lane_id)
    fatals: list[RepetitionIssue] = []
    warns: list[RepetitionIssue] = []

    # Mandatory bypass for tool_call-only response lanes.
    if policy.assistant_response_must_be_empty:
        return fatals, warns

    lang = _norm_lang(row.get("language"))

    # Mandatory code-only behavior: only adjacent duplicate token check with code-safe tokenization.
    if policy.assistant_response_must_be_code_only:
        asst = row.get("assistant_response")
        if isinstance(asst, str) and asst.strip():
            dup = _first_adjacent_duplicate(_code_safe_tokens(asst))
            if dup:
                fatals.append(
                    RepetitionIssue(
                        code="adjacent_dup_token",
                        severity="fatal",
                        detail=f"assistant_response has adjacent duplicate token '{dup}'",
                    )
                )
        return fatals, warns

    field = "assistant_response"
    text = row.get(field)
    if not isinstance(text, str) or not text.strip():
        return fatals, warns
    tokens = _repetition_tokens(text, lang)
    if not tokens:
        return fatals, warns

    adj = _first_adjacent_duplicate(tokens)
    if adj:
        fatals.append(
            RepetitionIssue(
                code="adjacent_dup_token",
                severity="fatal",
                detail=f"{field} has adjacent duplicate token '{adj}'",
            )
        )

    tok = _first_triplicate_token(tokens, _WINDOW_TOKEN)
    if tok:
        if _is_function_token(tok, lang):
            warns.append(
                RepetitionIssue(
                    code="trip_token_function_only",
                    severity="warn",
                    detail=f"{field} has function token '{tok}' repeated 3x in {_WINDOW_TOKEN}-token window",
                )
            )
        else:
            fatals.append(
                RepetitionIssue(
                    code="trip_token_content",
                    severity="fatal",
                    detail=f"{field} has content token '{tok}' repeated 3x in {_WINDOW_TOKEN}-token window",
                )
            )

    bg = _first_triplicate_bigram(tokens, _WINDOW_BIGRAM_TOKEN)
    if bg:
        bg_text = f"{bg[0]} {bg[1]}"
        if _is_function_bigram(bg, lang):
            warns.append(
                RepetitionIssue(
                    code="trip_bigram_function_only",
                    severity="warn",
                    detail=f"{field} has function bigram '{bg_text}' repeated 3x in {_WINDOW_BIGRAM_TOKEN}-token window",
                )
            )
        else:
            fatals.append(
                RepetitionIssue(
                    code="trip_bigram_content",
                    severity="fatal",
                    detail=f"{field} has content bigram '{bg_text}' repeated 3x in {_WINDOW_BIGRAM_TOKEN}-token window",
                )
            )

    return fatals, warns

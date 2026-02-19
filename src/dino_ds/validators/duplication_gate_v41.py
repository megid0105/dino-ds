from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import re
from typing import Any

try:
    from pythainlp.tokenize import word_tokenize as _THAI_WORD_TOKENIZE
except Exception:  # pragma: no cover - optional dependency
    _THAI_WORD_TOKENIZE = None


DEFAULT_CANDIDATE_THRESHOLD = 0.30
DEFAULT_CONTAIN_THRESHOLD = 0.55
DEFAULT_OJAC_THRESHOLD = 0.38
DEFAULT_C3_THRESHOLD_LATIN = 0.26
DEFAULT_C3_THRESHOLD_CARVEOUT = 0.30

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_LATIN_RUN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")

_THAI_LANGS = {"th"}
_CJK_LANGS = {"zh", "zh-hk", "zh_hk", "zh-hans", "zh_hans", "zh-hant", "zh_hant", "ja", "ko"}
_CARVEOUT_LANGS = _THAI_LANGS | _CJK_LANGS | {"hi", "vi"}
_CARVEOUT_MIN_TOKENS = 3


@dataclass(frozen=True)
class DuplicationIssue:
    code: str
    detail: str


@dataclass(frozen=True)
class TokenView:
    tokens: list[str]
    counts: Counter[str]
    as_set: set[str]
    token_mode: str  # word | char_gram


@dataclass(frozen=True)
class PairDecision:
    candidate: bool
    confirmed: bool
    rule: str
    o_min: float
    o_jac: float
    c3: float
    signal_hits: int
    token_mode: str


def _norm_lang(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _is_carveout_lang(lang: str) -> bool:
    if lang in _CARVEOUT_LANGS:
        return True
    # Keep language-tag variants aligned (e.g., hi-IN / vi-VN).
    return _is_hindi_lang(lang) or _is_vietnamese_lang(lang)


def _is_hindi_lang(lang: str) -> bool:
    if lang == "hi":
        return True
    return lang.startswith("hi-") or lang.startswith("hi_")


def _is_vietnamese_lang(lang: str) -> bool:
    if lang == "vi":
        return True
    return lang.startswith("vi-") or lang.startswith("vi_")


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
        if ignore and tok in ignore:
            continue
        if not _THAI_CHAR_RE.search(tok):
            continue
        out.append(tok)
    return out


def _word_tokens(text: str, ignore: set[str] | None = None) -> list[str]:
    toks = [t for t in _WORD_RE.findall((text or "").lower()) if t]
    if ignore:
        toks = [t for t in toks if t not in ignore]
    return toks


def _word_chars(text: str) -> list[str]:
    out: list[str] = []
    for ch in (text or "").lower():
        if _WORD_RE.fullmatch(ch):
            out.append(ch)
    return out


def _tokenize_for_dup(text: str, lang: str, ignore: set[str] | None = None) -> tuple[list[str], str]:
    # Equator v4.1 carve-out: Thai/CJK/Ja/Ko/Hi/Vi use word tokens when possible,
    # otherwise char bi/tri-gram fallback. Never raw single-char containment.
    if lang in _THAI_LANGS:
        words = _thai_word_tokens(text, ignore=ignore)
        if words:
            return words, "word"
        chars = _THAI_CHAR_RE.findall(text or "")
        toks = _char_bi_tri_grams(chars)
        latin = _LATIN_RUN_RE.findall((text or "").lower())
        if ignore:
            latin = [t for t in latin if t not in ignore]
        return toks + latin, "char_gram"

    if lang in _CJK_LANGS or lang.startswith("zh"):
        chars = _CJK_CHAR_RE.findall(text or "")
        toks = _char_bi_tri_grams(chars)
        latin = _LATIN_RUN_RE.findall((text or "").lower())
        if ignore:
            latin = [t for t in latin if t not in ignore]
        if toks or latin:
            return toks + latin, "char_gram"
        return _word_tokens(text, ignore=ignore), "word"

    if _is_hindi_lang(lang) or _is_vietnamese_lang(lang):
        words = _word_tokens(text, ignore=ignore)
        # Prefer native word tokens; tiny-span candidate triggering is gated
        # later by _CARVEOUT_MIN_TOKENS.
        if words:
            return words, "word"
        chars = _word_chars(text)
        toks = _char_bi_tri_grams(chars)
        latin = _LATIN_RUN_RE.findall((text or "").lower())
        if ignore:
            latin = [t for t in latin if t not in ignore]
        if toks or latin:
            return toks + latin, "char_gram"
        return words, "word"

    words = _word_tokens(text, ignore=ignore)
    if words:
        return words, "word"

    # Fallback for scripts with no word splits in noisy text.
    chars = [ch for ch in (text or "") if ch.strip()]
    return _char_bi_tri_grams(chars), "char_gram"


def _build_token_view(text: str, lang: str, ignore: set[str] | None = None) -> TokenView:
    toks, token_mode = _tokenize_for_dup(text, lang, ignore=ignore)
    return TokenView(tokens=toks, counts=Counter(toks), as_set=set(toks), token_mode=token_mode)


def _multiset_overlap_min(view_a: TokenView, view_b: TokenView) -> float:
    if not view_a.tokens or not view_b.tokens:
        return 0.0
    min_len = min(len(view_a.tokens), len(view_b.tokens))
    if min_len <= 0:
        return 0.0
    inter = 0
    for tok, n in view_a.counts.items():
        if tok in view_b.counts:
            inter += min(n, view_b.counts[tok])
    return inter / float(min_len)


def _jaccard(view_a: TokenView, view_b: TokenView) -> float:
    if not view_a.as_set or not view_b.as_set:
        return 0.0
    union = len(view_a.as_set.union(view_b.as_set))
    if union <= 0:
        return 0.0
    inter = len(view_a.as_set.intersection(view_b.as_set))
    return inter / float(union)


def _longest_common_chain_ratio(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    min_len = min(len(tokens_a), len(tokens_b))
    if min_len <= 0:
        return 0.0

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


def _row_id(rr: dict[str, Any], idx1: int) -> str:
    sid = rr.get("sample_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    rid = rr.get("id")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return f"row#{idx1}"


def _evaluate_pair(
    view_a: TokenView,
    view_b: TokenView,
    *,
    lang: str,
    candidate_threshold: float,
    contain_threshold: float,
    o_jac_threshold: float,
    c3_threshold_latin: float,
    c3_threshold_carveout: float,
) -> PairDecision:
    if not view_a.tokens or not view_b.tokens:
        return PairDecision(
            candidate=False,
            confirmed=False,
            rule="empty",
            o_min=0.0,
            o_jac=0.0,
            c3=0.0,
            signal_hits=0,
            token_mode=view_a.token_mode,
        )

    carveout = _is_carveout_lang(lang)
    # Carve-out scripts should not confirm on tiny token spans.
    if carveout and min(len(view_a.tokens), len(view_b.tokens)) < _CARVEOUT_MIN_TOKENS:
        return PairDecision(
            candidate=False,
            confirmed=False,
            rule="carveout_min_tokens",
            o_min=0.0,
            o_jac=0.0,
            c3=0.0,
            signal_hits=0,
            token_mode=view_a.token_mode,
        )

    o_min = _multiset_overlap_min(view_a, view_b)
    if not (o_min > candidate_threshold):
        return PairDecision(
            candidate=False,
            confirmed=False,
            rule="below_candidate",
            o_min=o_min,
            o_jac=0.0,
            c3=0.0,
            signal_hits=0,
            token_mode=view_a.token_mode,
        )

    o_jac = _jaccard(view_a, view_b)
    c3 = _longest_common_chain_ratio(view_a.tokens, view_b.tokens)

    c3_threshold = c3_threshold_carveout if carveout else c3_threshold_latin

    signal_hits = 0
    if o_min > candidate_threshold:
        signal_hits += 1
    if o_jac > o_jac_threshold:
        signal_hits += 1
    if c3 > c3_threshold:
        signal_hits += 1
    rule2 = signal_hits >= 2

    # Equator v4.1 §6E (Hindi override):
    # If Hindi O_min > candidate_threshold but C3 < 0.20, downgrade to WARN/candidate-only.
    if _is_hindi_lang(lang) and c3 < 0.20:
        return PairDecision(
            candidate=True,
            confirmed=False,
            rule="hindi_override_candidate_only",
            o_min=o_min,
            o_jac=o_jac,
            c3=c3,
            signal_hits=signal_hits,
            token_mode=view_a.token_mode,
        )

    if carveout:
        # Equator v4.1 carve-out: containment cannot standalone fail.
        rule1 = (o_min > contain_threshold) and (c3 > c3_threshold)
        confirmed = rule1 or rule2
        rule = "rule2_multisignal" if rule2 else ("rule1_contain_and_chain" if rule1 else "candidate_only")
    else:
        rule1 = o_min > contain_threshold
        confirmed = rule1 or rule2
        if rule1 and rule2:
            rule = "rule1_or_rule2"
        elif rule1:
            rule = "rule1_containment"
        elif rule2:
            rule = "rule2_multisignal"
        else:
            rule = "candidate_only"

    return PairDecision(
        candidate=True,
        confirmed=confirmed,
        rule=rule,
        o_min=o_min,
        o_jac=o_jac,
        c3=c3,
        signal_hits=signal_hits,
        token_mode=view_a.token_mode,
    )


def check_pairwise(rows: list[dict[str, Any]], lane: dict[str, Any]) -> tuple[list[DuplicationIssue], list[DuplicationIssue]]:
    fatals: list[DuplicationIssue] = []
    warns: list[DuplicationIssue] = []

    if not rows:
        return fatals, warns

    sim = lane.get("similarity")
    sim = sim if isinstance(sim, dict) else {}
    vcfg = lane.get("validation")
    vcfg = vcfg if isinstance(vcfg, dict) else {}

    base_candidate = _cfg_float(sim, "max_token_overlap_ratio", DEFAULT_CANDIDATE_THRESHOLD)
    candidate_threshold = _safe_ratio(_cfg_float(vcfg, "dup_candidate_threshold", base_candidate))
    contain_threshold = _safe_ratio(_cfg_float(vcfg, "dup_contain_threshold", DEFAULT_CONTAIN_THRESHOLD))
    o_jac_threshold = _safe_ratio(_cfg_float(vcfg, "dup_jaccard_threshold", DEFAULT_OJAC_THRESHOLD))
    c3_threshold_latin = _safe_ratio(
        _cfg_float(
            vcfg,
            "dup_chain_threshold_latin",
            _cfg_float(vcfg, "dup_chain_threshold", DEFAULT_C3_THRESHOLD_LATIN),
        )
    )
    c3_threshold_carveout = _safe_ratio(
        _cfg_float(
            vcfg,
            "dup_chain_threshold_carveout",
            _cfg_float(vcfg, "dup_chain_threshold_asian", DEFAULT_C3_THRESHOLD_CARVEOUT),
        )
    )

    sim_scope = sim.get("text_field") if isinstance(sim.get("text_field"), str) else None
    ignore: set[str] = set()
    extra = sim.get("ignore_tokens")
    if isinstance(extra, list):
        for x in extra:
            if isinstance(x, str) and x.strip():
                ignore.add(x.strip().lower())

    win = _cfg_int(vcfg, "dup_window", 180)
    if win <= 0:
        win = 180
    if len(rows) >= 50_000 and win > 80:
        win = 80

    prevs: deque[tuple[str, str, TokenView]] = deque(maxlen=win)
    for idx, rr in enumerate(rows, start=1):
        if not isinstance(rr, dict):
            continue
        rid = _row_id(rr, idx)
        text = _row_text_for_similarity(rr, sim_scope)
        if not text:
            continue
        lang = _norm_lang(rr.get("language"))
        view = _build_token_view(text, lang, ignore=ignore)
        if not view.tokens:
            continue

        fail_issue: DuplicationIssue | None = None
        candidate_warn: DuplicationIssue | None = None
        for pid, plang, pview in prevs:
            # language-internal comparison for multilingual robustness
            if lang and plang and lang != plang:
                continue
            decision = _evaluate_pair(
                view,
                pview,
                lang=(lang or plang),
                candidate_threshold=candidate_threshold,
                contain_threshold=contain_threshold,
                o_jac_threshold=o_jac_threshold,
                c3_threshold_latin=c3_threshold_latin,
                c3_threshold_carveout=c3_threshold_carveout,
            )
            if not decision.candidate:
                continue

            detail = (
                f"{rid} vs {pid} dup_rule={decision.rule} "
                f"Omin={decision.o_min:.3f} Ojac={decision.o_jac:.3f} C3={decision.c3:.3f} "
                f"signals={decision.signal_hits}/3 token_mode={decision.token_mode} "
                f"(candidate={candidate_threshold:.3f})"
            )
            if decision.confirmed:
                fail_issue = DuplicationIssue(code="near_duplicate_overlap", detail=detail)
                break

            if candidate_warn is None:
                candidate_warn = DuplicationIssue(code="dup_candidate_unconfirmed", detail=detail)

        if fail_issue is not None:
            fatals.append(fail_issue)
        elif candidate_warn is not None:
            warns.append(candidate_warn)
        prevs.append((rid, lang, view))

    return fatals, warns

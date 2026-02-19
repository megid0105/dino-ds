from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Any
import unicodedata

from .lane_policy_v17 import get_lane_policy


MIN_TOKENS = 12
SINGLE_CHAR_RATIO_THRESHOLD = 0.55
MIN_LETTERS = 40
UNEXPECTED_SCRIPT_RATIO_THRESHOLD = 0.20

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_DEVANAGARI_TOKEN_RE = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF]+")
_URL_OR_DOMAIN_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s\"'<>]+|\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}(?:/[^\s\"'<>]*)?"
)
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_JSON_KEY_RE = re.compile(r'"[A-Za-z_][A-Za-z0-9_]{0,30}"\s*:')
_CHART_KEY_RE = re.compile(r"(?i)\b(?:x|y|label|value)\s*:")

_LATIN_LANGS = {"en", "es", "fr", "de", "it", "pt-br", "pt_br", "vi"}
_CJK_LANGS = {"zh", "zh-hk", "zh_hk", "zh-hans", "zh_hans", "zh-hant", "zh_hant", "ja", "ko"}
_THAI_LANGS = {"th"}
_DEVANAGARI_LANGS = {"hi"}
_LANE_ID_RE = re.compile(r"^lane_(\d+)")


@dataclass(frozen=True)
class MalformedIssue:
    code: str
    detail: str


def _norm_lang(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _lane_num(lane_id: Any) -> int | None:
    if not isinstance(lane_id, str):
        return None
    m = _LANE_ID_RE.match(lane_id.strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _expected_script_family(lang: str) -> str | None:
    if not lang:
        return None
    if lang in _LATIN_LANGS:
        return "latin"
    if lang in _THAI_LANGS:
        return "thai"
    if lang in _DEVANAGARI_LANGS:
        return "devanagari"
    if lang in _CJK_LANGS or lang.startswith("zh"):
        return "cjk"
    if "-" in lang:
        base = lang.split("-", 1)[0]
        if base in _LATIN_LANGS:
            return "latin"
        if base in _THAI_LANGS:
            return "thai"
        if base in _DEVANAGARI_LANGS:
            return "devanagari"
        if base in _CJK_LANGS:
            return "cjk"
    if "_" in lang:
        base = lang.split("_", 1)[0]
        if base in _LATIN_LANGS:
            return "latin"
        if base in _THAI_LANGS:
            return "thai"
        if base in _DEVANAGARI_LANGS:
            return "devanagari"
        if base in _CJK_LANGS:
            return "cjk"
    return None


@lru_cache(maxsize=4096)
def _char_family(ch: str) -> str:
    cp = ord(ch)
    if 0x0900 <= cp <= 0x097F or 0xA8E0 <= cp <= 0xA8FF:
        return "devanagari"
    if 0x0E00 <= cp <= 0x0E7F:
        return "thai"
    if (
        0x3400 <= cp <= 0x4DBF
        or 0x4E00 <= cp <= 0x9FFF
        or 0x3040 <= cp <= 0x30FF
        or 0x31F0 <= cp <= 0x31FF
        or 0xAC00 <= cp <= 0xD7AF
    ):
        return "cjk"

    name = unicodedata.name(ch, "")
    if name.startswith("LATIN"):
        return "latin"
    if name.startswith("CYRILLIC"):
        return "cyrillic"
    if name.startswith("GREEK"):
        return "greek"
    return "other"


@lru_cache(maxsize=4096)
def _is_letter(ch: str) -> bool:
    return unicodedata.category(ch).startswith("L")


def _units_in_family(token: str, family: str) -> int:
    # Combining marks are not counted as standalone units for Hindi.
    units = 0
    for ch in token:
        if unicodedata.combining(ch):
            continue
        if _is_letter(ch) and _char_family(ch) == family:
            units += 1
    return units


def _fragmentation_units(text: str, family: str) -> list[int]:
    if family == "devanagari":
        raw_tokens = _DEVANAGARI_TOKEN_RE.findall(text)
    else:
        raw_tokens = _WORD_RE.findall(text)

    units: list[int] = []
    for tok in raw_tokens:
        n = _units_in_family(tok, family)
        if n > 0:
            units.append(n)
    return units


def _check_character_fragmentation(text: str, family: str, field: str) -> MalformedIssue | None:
    if family not in {"latin", "devanagari"}:
        return None

    units = _fragmentation_units(text, family)
    if len(units) < MIN_TOKENS:
        return None

    single_count = sum(1 for n in units if n == 1)
    single_ratio = single_count / float(len(units))
    if single_ratio >= SINGLE_CHAR_RATIO_THRESHOLD:
        return MalformedIssue(
            code="character_fragmentation_fatal",
            detail=(
                f"{field} single_char_ratio={single_ratio:.3f} "
                f"(single={single_count}, tokens={len(units)}, min_tokens={MIN_TOKENS})"
            ),
        )
    return None


def _check_script_corruption(text: str, expected_family: str, field: str) -> MalformedIssue | None:
    latin_excluded_indexes: set[int] = set()
    if expected_family in {"cjk", "thai"}:
        # Structured Latin snippets are normal in CJK/TH rows (URLs, JSON keys, simple chart keys).
        # Exclude only these from ratio math so true prose/script drift still gets caught.
        for rx in (_URL_OR_DOMAIN_RE, _ISO_DATE_RE, _JSON_KEY_RE, _CHART_KEY_RE):
            for m in rx.finditer(text):
                start, end = m.span()
                for i in range(start, end):
                    ch = text[i]
                    if _is_letter(ch) and _char_family(ch) == "latin":
                        latin_excluded_indexes.add(i)

    total_letters = 0
    unexpected_letters = 0

    for idx, ch in enumerate(text):
        if not _is_letter(ch):
            continue
        fam = _char_family(ch)
        if idx in latin_excluded_indexes and fam == "latin":
            continue
        total_letters += 1
        if fam != expected_family:
            unexpected_letters += 1

    if total_letters < MIN_LETTERS:
        return None

    ratio = unexpected_letters / float(total_letters)
    if ratio > UNEXPECTED_SCRIPT_RATIO_THRESHOLD:
        return MalformedIssue(
            code="script_corruption_fatal",
            detail=(
                f"{field} unexpected_script_ratio={ratio:.3f} "
                f"(unexpected={unexpected_letters}, letters={total_letters}, expected={expected_family})"
            ),
        )
    return None


def evaluate_row_malformed_v41(row: dict[str, Any], lane_id: str) -> list[MalformedIssue]:
    policy = get_lane_policy(lane_id)
    if policy.assistant_response_must_be_empty:
        return []
    if policy.assistant_response_must_be_code_only:
        return []

    lang = _norm_lang(row.get("language"))
    expected_family = _expected_script_family(lang)
    if expected_family is None:
        return []

    fields: tuple[str, ...] = ("user_message", "assistant_response")
    # Lane 22 uses source-language tags by design (QC Addition v17r3):
    # assistant_response may be in a different target script, so script-corruption
    # must not be evaluated against row.language on assistant text.
    if _lane_num(lane_id) == 22:
        fields = ("user_message",)

    issues: list[MalformedIssue] = []
    for field in fields:
        text = row.get(field)
        if not isinstance(text, str) or not text.strip():
            continue

        frag = _check_character_fragmentation(text, expected_family, field)
        if frag is not None:
            issues.append(frag)

        corrupt = _check_script_corruption(text, expected_family, field)
        if corrupt is not None:
            issues.append(corrupt)

    return issues

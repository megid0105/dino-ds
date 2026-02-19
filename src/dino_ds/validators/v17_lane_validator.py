from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..contracts.v16_lane_contracts import contract_for_lane
from .fixed_values_enforcer_v17 import enforce_fixed_values
from . import user_assistant_overlap_v17


_LANE_ID_RE = re.compile(r"^lane_(\d+)")
# Citation token must be isolated so code indexing (e.g. a[0]) is not treated as citation.
_CITATION_RE = re.compile(r"(?<![A-Za-z0-9_])\[[1-9][0-9]{0,2}\](?![A-Za-z0-9_])")
_CODEBLOCK_ONLY_RE = re.compile(r"(?s)\A```[^\n]*\n.*\n```\s*\Z")
_TABLE_SEPARATOR_RE = re.compile(r"^\|\s*:?-{3,}[-:|\s]*\|\s*$")
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")
_BULLET_LINE_RE = re.compile(r"^\s*[-*•]\s+\S+")
_JSON_LIKE_RE = re.compile(r"(?s)^\s*[\[{].*[\]}]\s*$")
_HISTORY_REF_CLAIM_RE = re.compile(
    r"(?i)\b(earlier|previous|from your (?:earlier|previous) note|you said|you mentioned|from before)\b"
)
_HISTORY_IRRELEVANT_ACK_RE = re.compile(
    r"(?i)\b(not in (?:the )?(?:retrieved )?(?:history|snippet|note|context)|"
    r"don'?t have (?:that|it) in (?:the )?(?:retrieved )?(?:history|note|context)|"
    r"insufficient (?:history|context))\b"
)
_SENSITIVE_NUM_RE = re.compile(r"\b\d{3,}\b|\b\d{1,2}:\d{2}\b")
_VISUAL_ASSERTION_RE = re.compile(r"(?i)\b(i\s+see|there\s+(?:is|are)|it\s+has|contains?|looks\s+like)\b")
_IMAGE_OBJECT_PHRASE_RE = re.compile(
    r"(?i)\b(?:a|an|the|this|that|these|those|two|three|four)\s+([a-z][a-z0-9_-]{2,})\b"
)
_IMAGE_GENERIC_TERMS = {
    "image",
    "photo",
    "picture",
    "scene",
    "object",
    "objects",
    "item",
    "items",
    "thing",
    "things",
    "area",
    "view",
}
_IMAGE_SYNONYMS = {
    "smartphone": "phone",
    "cellphone": "phone",
    "mobile": "phone",
    "kitty": "cat",
    "kitten": "cat",
    "puppy": "dog",
    "pup": "dog",
    "notebook": "laptop",
}
_DOC_SPEC_HINT_RE = re.compile(r"(?i)\b(title|sections?|heading|body|style)\b")
_ZIP_SPEC_HINT_RE = re.compile(r"(?i)\b(manifest\.md|zip_items|filename|content)\b")
_USER_MECHANISM_LEAK_RE = re.compile(
    r"(?ix)"
    r"(?:\b(?:use|call|invoke)\s+(?:the\s+)?tool\b)"
    r"|(?:\b(?:open|use)\s+(?:the\s+)?connector\b)"
    r"|(?:\b(?:click|follow)\s+(?:the\s+)?deep[\s-]?link\b)"
    r"|(?:\bsearch\s+in\s+(?:slack|google\s*drive|github)\b)"
    r"|(?:\bi\s+(?:queried|querying|query)\s+the\s+internal\s+(?:database|policy|validator)\b)"
    r"|(?:\brun\s+(?:validate_row|rule_profile)\b)"
    r"|(?:\bi\s+will\s+browse\s+(?:the\s+)?web\s+tool\b)"
    r"|(?:\bweb\.run\b)"
)
_ASSISTANT_INTERNAL_WORD_RE = re.compile(
    r"(?i)\b(tool_call|web_fetch|web_read|connector_action|deeplink_action|routing|schema|internal label)\b"
)
_SEARCH_INTEGRATION_LEAK_RE = re.compile(r"(?i)\b(tool_call|web_fetch|search|connector|deeplink|schema|label)\b")
_LEGACY_ALIAS_FIELDS = {
    "need_search",
    "need_history_search",
    "need_connector",
    "need_deeplink",
    "needsConnector",
    "needsDeeplink",
    "needsSearch",
    "needsHistorySearch",
}
_JSON_CODE_SPEC_KEYS = ("task_type", "language", "files", "constraints", "tests")
_JSON_FILE_KEYS = ("name", "purpose", "exports")
_TOOL_CALL_EXPORT_KEYS = {"name", "arguments"}
_TOOL_CALL_EXPORT_ARGUMENTS_KEYS = {"format", "document_spec"}
_TOOL_CALL_EXPORT_DOC_SPEC_KEYS = {"title", "sections", "style"}
_TOOL_CALL_EXPORT_SECTION_KEYS = {"heading", "body"}
_TOOL_CALL_ZIP_KEYS = {"name", "arguments"}
_TOOL_CALL_ZIP_ARGUMENTS_KEYS = {"zip_items"}
_TOOL_CALL_ZIP_ITEM_KEYS = {"filename", "content"}
_LANE_03_04_ALLOWED_TOOL_NAMES = {
    # Master global tooling schema (v2). Lane 3/4 do not narrow this list further in v17.
    "connector_action",
    "web_fetch",
    "web_read",
    "image_preview",
    "export_document",
    "ingest",
    "zip_list",
    "ingest_zip",
    "history_search",
}

_TOOLCALL_FORBIDDEN_LANES = {
    1,
    2,
    5,
    6,
    7,
    9,
    10,
    11,
    12,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    37,
}
_TOOLCALL_REQUIRED_LANES = {8, 13, 14}
_ACTION_LABEL_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*_[A-Za-z][A-Za-z0-9]*$")
_MASTER_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md"


def _lane_num(lane_id: str) -> int | None:
    m = _LANE_ID_RE.match(str(lane_id or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


@lru_cache(maxsize=1)
def _load_master_action_labels() -> tuple[set[str], set[str]]:
    connector_labels: set[str] = set()
    deeplink_labels: set[str] = set()
    try:
        text = _MASTER_SCHEMA_PATH.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return connector_labels, deeplink_labels

    lines = text.splitlines()
    section = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if "20. Connector Training spec" in line:
            section = "connector"
            continue
        if "21. DEEPLINK CAPABILITY" in line and "TRAINING" not in line:
            if section == "connector":
                section = ""
            continue
        if "22. DEEPLINK CAPABILITY TRAINING SPEC" in line:
            section = "deeplink"
            continue
        if "END OF MASTER SPEC" in line:
            section = ""
            continue
        if line.startswith("#") or line.startswith("###") or line.startswith("##"):
            continue
        if line.startswith("=") or ":" in line or " " in line:
            continue
        if not _ACTION_LABEL_TOKEN_RE.fullmatch(line):
            continue

        if section == "connector":
            connector_labels.add(line)
        elif section == "deeplink":
            deeplink_labels.add(line)

    return connector_labels, deeplink_labels


def _is_blank_text(v: Any) -> bool:
    return not isinstance(v, str) or not v.strip()


def _is_empty_or_single_space(v: Any) -> bool:
    return isinstance(v, str) and v in ("", " ")


def _contains_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(v, key) for v in obj)
    return False


def _last_user_content(messages: Any) -> str | None:
    if not isinstance(messages, list):
        return None
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if isinstance(role, str) and role.strip().lower() == "user" and isinstance(content, str):
            text = content.strip()
            if text:
                return text
    return None


def _validate_codeblock_only(text: Any) -> str | None:
    if not isinstance(text, str):
        return "assistant_response must be a string"
    if text.count("```") != 2:
        return "assistant_response must contain exactly one fenced code block"
    if _CODEBLOCK_ONLY_RE.fullmatch(text.strip()) is None:
        return "assistant_response must be exactly one fenced code block with no prose"
    return None


def _validate_json_code_spec(text: Any) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "assistant_response must be non-empty strict JSON"
    s = text.strip()
    if "```" in s:
        return "assistant_response must be JSON only (no code fences)"
    try:
        obj = json.loads(s)
    except Exception as e:
        return f"assistant_response is not valid JSON: {e}"
    if not isinstance(obj, dict):
        return "assistant_response JSON root must be an object"

    keys = tuple(obj.keys())
    if keys != _JSON_CODE_SPEC_KEYS:
        return f"JSON keys/order must be exactly {_JSON_CODE_SPEC_KEYS}, got {keys}"

    files = obj.get("files")
    if not isinstance(files, list) or not files:
        return "JSON field 'files' must be a non-empty array"
    for idx, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            return f"files[{idx}] must be an object"
        item_keys = tuple(item.keys())
        if item_keys != _JSON_FILE_KEYS:
            return f"files[{idx}] keys/order must be exactly {_JSON_FILE_KEYS}, got {item_keys}"
        if _is_blank_text(item.get("name")) or _is_blank_text(item.get("purpose")):
            return f"files[{idx}] name/purpose must be non-empty strings"
        exports = item.get("exports")
        if not isinstance(exports, list) or not exports or not all(isinstance(x, str) and x.strip() for x in exports):
            return f"files[{idx}].exports must be a non-empty string array"

    constraints = obj.get("constraints")
    tests = obj.get("tests")
    if not isinstance(constraints, list) or not isinstance(tests, list):
        return "JSON fields 'constraints' and 'tests' must be arrays"
    return None


def _validate_markdown_table_only(text: Any) -> str | None:
    if not isinstance(text, str):
        return "assistant_response must be a string"
    s = text.strip()
    if not s:
        return "assistant_response must be a markdown table"
    if "```" in s:
        return "assistant_response must be markdown table only (no code fences)"

    lines = [ln.rstrip() for ln in s.splitlines() if ln.strip()]
    if len(lines) < 2:
        return "markdown table must include at least header and separator lines"
    if not all(ln.lstrip().startswith("|") and ln.rstrip().endswith("|") for ln in lines):
        return "all non-empty lines must be table rows (start/end with '|')"
    if _TABLE_SEPARATOR_RE.match(lines[1].strip()) is None:
        return "second line must be a markdown table separator row"
    return None


def _validate_chart_spec_only(text: Any) -> str | None:
    if not isinstance(text, str):
        return "assistant_response must be a string"
    s = text.strip()
    if not s:
        return "assistant_response must contain chart_spec only"
    if "```" in s:
        return "assistant_response must be chart_spec only (no code fences)"
    if not s.startswith("chart_spec:"):
        return "chart_spec must start with 'chart_spec:'"

    lines = s.splitlines()

    def _pos(pattern: str) -> int | None:
        rx = re.compile(pattern)
        for i, ln in enumerate(lines):
            if rx.search(ln):
                return i
        return None

    p_type = _pos(r"^\s{2}type:\s+")
    p_title = _pos(r"^\s{2}title:\s+")
    p_goal = _pos(r"^\s{2}goal:\s+")
    p_x = _pos(r"^\s{2}x_axis:\s*$")
    p_y = _pos(r"^\s{2}y_axis:\s*$")
    p_legend = _pos(r"^\s{2}legend:\s*$")
    p_series = _pos(r"^\s{2}series:\s*$")
    p_style = _pos(r"^\s{2}style:\s*$")
    p_notes = _pos(r"^\s{2}notes:\s+")

    if p_type is None or p_title is None or p_goal is None or p_series is None or p_style is None or p_notes is None:
        return "chart_spec missing required keys: type/title/goal/series/style/notes"

    if p_x is None and p_legend is None:
        return "chart_spec must include x_axis/y_axis or legend"
    if p_x is not None and p_y is None:
        return "chart_spec with x_axis must also include y_axis"

    p_axis = p_legend
    if p_x is not None:
        p_axis = p_x
    if p_axis is None:
        return "chart_spec axis/legend position missing"

    if not (p_type < p_title < p_goal < p_axis < p_series < p_style < p_notes):
        return "chart_spec keys are not in deterministic order"

    return None


def _tokenize_script_aware(text: str) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        return []
    toks = [t for t in _WORD_RE.findall(text.lower()) if t]
    if toks:
        return toks
    cjk = _CJK_CHAR_RE.findall(text)
    if cjk:
        return cjk
    th = _THAI_CHAR_RE.findall(text)
    if th:
        return th
    return []


def _multiset_overlap_min_tokens(a_text: str, b_text: str) -> float:
    a_toks = _tokenize_script_aware(a_text)
    b_toks = _tokenize_script_aware(b_text)
    if not a_toks or not b_toks:
        return 0.0
    min_len = min(len(a_toks), len(b_toks))
    if min_len <= 0:
        return 0.0
    ca = {}
    cb = {}
    for tok in a_toks:
        ca[tok] = ca.get(tok, 0) + 1
    for tok in b_toks:
        cb[tok] = cb.get(tok, 0) + 1
    inter = 0
    for tok, n in ca.items():
        if tok in cb:
            inter += min(n, cb[tok])
    return inter / float(min_len)


def _extract_retrieved_history_snippets(messages: Any) -> list[str]:
    if not isinstance(messages, list):
        return []
    snippets: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not (isinstance(role, str) and role.strip().lower() == "system" and isinstance(content, str)):
            continue
        m = re.search(
            r"(?is)RETRIEVED_HISTORY_SNIPPETS:\s*(.+?)(?:\n[A-Z][A-Z_ ]{2,}:|\Z)",
            content,
        )
        if not m:
            continue
        block = m.group(1)
        for ln in block.splitlines():
            raw = ln.strip()
            if not raw:
                continue
            if raw.startswith("-"):
                txt = raw[1:].strip()
                if txt:
                    snippets.append(txt)
    return snippets


def _validate_lane25_history_grounding(row: dict[str, Any]) -> str | None:
    asst = row.get("assistant_response")
    if not isinstance(asst, str) or not asst.strip():
        return None
    snippets = _extract_retrieved_history_snippets(row.get("messages"))
    if not snippets:
        return None
    snippet_text = " ".join(snippets)
    overlap = _multiset_overlap_min_tokens(asst, snippet_text)
    has_history_claim = _HISTORY_REF_CLAIM_RE.search(asst) is not None
    irrelevant_ack = _HISTORY_IRRELEVANT_ACK_RE.search(asst) is not None

    if has_history_claim and not irrelevant_ack and overlap < 0.10:
        return (
            "assistant_response appears ungrounded to RETRIEVED_HISTORY_SNIPPETS "
            f"(overlap={overlap:.3f} < 0.10)"
        )

    # High-precision hallucination catch for explicit sensitive numeric claims.
    if has_history_claim and not irrelevant_ack:
        asst_nums = set(_SENSITIVE_NUM_RE.findall(asst))
        if asst_nums:
            snippet_nums = set(_SENSITIVE_NUM_RE.findall(snippet_text))
            missing = sorted(n for n in asst_nums if n not in snippet_nums)
            if missing:
                return f"assistant_response includes numeric memory claims absent from snippets: {', '.join(missing)}"

    return None


def _extract_image_context_terms(image_context: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(image_context, dict):
        return out

    def _add_tokens(text: Any) -> None:
        if not isinstance(text, str):
            return
        for tok in _WORD_RE.findall(text.lower()):
            if len(tok) >= 2:
                out.add(tok)

    _add_tokens(image_context.get("summary"))
    objs = image_context.get("objects")
    if isinstance(objs, list):
        for item in objs:
            if not isinstance(item, dict):
                continue
            _add_tokens(item.get("label"))
            _add_tokens(item.get("location_hint"))
            _add_tokens(item.get("brand"))
            _add_tokens(item.get("color"))
    hints = image_context.get("text_hints")
    if isinstance(hints, list):
        for item in hints:
            if isinstance(item, dict):
                _add_tokens(item.get("text"))
    return out


def _extract_asserted_image_terms(asst: str) -> set[str]:
    found: set[str] = set()
    for m in _IMAGE_OBJECT_PHRASE_RE.finditer(asst or ""):
        tok = m.group(1).strip().lower()
        if tok and tok not in _IMAGE_GENERIC_TERMS:
            found.add(tok)
    return found


def _image_term_allowed(term: str, allowed_terms: set[str]) -> bool:
    if term in allowed_terms:
        return True
    alias = _IMAGE_SYNONYMS.get(term)
    if alias and alias in allowed_terms:
        return True
    # Singular/plural soft match for basic nouns.
    if term.endswith("s") and term[:-1] in allowed_terms:
        return True
    if f"{term}s" in allowed_terms:
        return True
    return False


def _validate_lane26_image_grounding(row: dict[str, Any]) -> str | None:
    image_context = row.get("image_context")
    if not isinstance(image_context, dict):
        return None

    asst = row.get("assistant_response")
    if not isinstance(asst, str) or not asst.strip():
        return None

    # Keep this high-precision: only enforce when assistant is making visual assertions.
    if _VISUAL_ASSERTION_RE.search(asst) is None:
        return None

    allowed_terms = _extract_image_context_terms(image_context)
    if not allowed_terms:
        return None

    mentioned = _extract_asserted_image_terms(asst)
    if not mentioned:
        return None

    invalid = sorted(t for t in mentioned if not _image_term_allowed(t, allowed_terms))
    if invalid:
        return f"assistant_response mentions objects not supported by image_context: {', '.join(invalid)}"
    return None


def _validate_bullet_list_only(text: Any) -> str | None:
    if not isinstance(text, str):
        return "assistant_response must be a string"
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return "bullet_list requires at least 2 bullet lines"
    if not all(_BULLET_LINE_RE.match(ln) for ln in lines):
        return "bullet_list requires every non-empty line to start with '-', '*', or '•'"
    return None


def _validate_plain_text_only(text: Any) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "assistant_response must be non-empty plain text"
    s = text.strip()
    if "```" in s:
        return "plain_text must not be fenced code"
    if s.startswith("chart_spec:"):
        return "plain_text must not be chart_spec"
    if _TABLE_SEPARATOR_RE.search(s):
        return "plain_text must not be markdown table"
    if _JSON_LIKE_RE.match(s):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (dict, list)):
                return "plain_text must not be raw JSON"
        except Exception:
            pass
    return None


def _validate_document_spec_like(text: Any) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "document_spec requires non-empty text"
    s = text.strip()
    if "```" in s:
        return "document_spec must not be fenced code"
    if len(_DOC_SPEC_HINT_RE.findall(s)) < 2:
        return "document_spec should include document-structure hints (title/sections/heading/body/style)"
    return None


def _validate_zip_spec_like(text: Any) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "zip_spec requires non-empty text"
    s = text.strip()
    if "```" in s:
        return "zip_spec must not be fenced code"
    if len(_ZIP_SPEC_HINT_RE.findall(s)) < 2:
        return "zip_spec should include zip-structure hints (manifest.md/filename/content)"
    return None


def _require_bool(row: dict[str, Any], field: str, expected: bool | None = None) -> str | None:
    if field not in row:
        return f"missing required boolean field '{field}'"
    val = row.get(field)
    if not isinstance(val, bool):
        return f"field '{field}' must be boolean"
    if expected is not None and val is not expected:
        return f"field '{field}' must be {str(expected).lower()}"
    return None


def _tool_call_name(row: dict[str, Any]) -> str | None:
    tc = row.get("tool_call")
    if not isinstance(tc, dict):
        return None
    name = tc.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _tool_call_name_from_obj(tc: dict[str, Any]) -> str | None:
    name = tc.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _collect_tool_call_objects(row: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    tc = row.get("tool_call")
    if isinstance(tc, dict):
        out.append(tc)
    elif isinstance(tc, list):
        out.extend(x for x in tc if isinstance(x, dict))

    tcs = row.get("tool_calls")
    if isinstance(tcs, list):
        out.extend(x for x in tcs if isinstance(x, dict))
    return out


def _validate_optional_tool_call_lane_03_04(row: dict[str, Any], lane_num: int) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    tc = row.get("tool_call")
    if "tool_call" in row and not isinstance(tc, (dict, list)):
        issues.append(
            (
                "tool_call_not_allowed_in_lane",
                f"lane {lane_num:02d} tool_call must be an object when present",
            )
        )
        return issues
    tcs = row.get("tool_calls")
    if "tool_calls" in row and not isinstance(tcs, list):
        issues.append(
            (
                "tool_call_not_allowed_in_lane",
                f"lane {lane_num:02d} tool_calls must be a list when present",
            )
        )
        return issues

    calls = _collect_tool_call_objects(row)
    if len(calls) > 1:
        issues.append(
            (
                "tool_call_too_many",
                f"lane {lane_num:02d} allows at most one tool_call per row",
            )
        )
        return issues

    if len(calls) == 1:
        tc_name = _tool_call_name_from_obj(calls[0])
        if tc_name not in _LANE_03_04_ALLOWED_TOOL_NAMES:
            allowed = ", ".join(sorted(_LANE_03_04_ALLOWED_TOOL_NAMES))
            issues.append(
                (
                    "tool_call_tool_not_allowed",
                    f"lane {lane_num:02d} tool_call.name '{tc_name}' is not allowed; allowed: {allowed}",
                )
            )

    return issues


def _extra_keys(obj: Any, allowed: set[str]) -> list[str]:
    if not isinstance(obj, dict):
        return []
    extras = [k for k in obj.keys() if isinstance(k, str) and k not in allowed]
    extras.sort()
    return extras


def _collect_extra_keys_export_document(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    tc = row.get("tool_call")
    if not isinstance(tc, dict):
        return out

    for k in _extra_keys(tc, _TOOL_CALL_EXPORT_KEYS):
        out.append(f"tool_call.{k}")

    args = tc.get("arguments")
    if isinstance(args, dict):
        for k in _extra_keys(args, _TOOL_CALL_EXPORT_ARGUMENTS_KEYS):
            out.append(f"tool_call.arguments.{k}")

        doc = args.get("document_spec")
        if isinstance(doc, dict):
            for k in _extra_keys(doc, _TOOL_CALL_EXPORT_DOC_SPEC_KEYS):
                out.append(f"tool_call.arguments.document_spec.{k}")

            sections = doc.get("sections")
            if isinstance(sections, list):
                for idx, sec in enumerate(sections, start=1):
                    if not isinstance(sec, dict):
                        continue
                    for k in _extra_keys(sec, _TOOL_CALL_EXPORT_SECTION_KEYS):
                        out.append(f"tool_call.arguments.document_spec.sections[{idx}].{k}")

    return out


def _collect_extra_keys_zip_list(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    tc = row.get("tool_call")
    if not isinstance(tc, dict):
        return out

    for k in _extra_keys(tc, _TOOL_CALL_ZIP_KEYS):
        out.append(f"tool_call.{k}")

    args = tc.get("arguments")
    if isinstance(args, dict):
        for k in _extra_keys(args, _TOOL_CALL_ZIP_ARGUMENTS_KEYS):
            out.append(f"tool_call.arguments.{k}")

        zip_items = args.get("zip_items")
        if isinstance(zip_items, list):
            for idx, item in enumerate(zip_items, start=1):
                if not isinstance(item, dict):
                    continue
                for k in _extra_keys(item, _TOOL_CALL_ZIP_ITEM_KEYS):
                    out.append(f"tool_call.arguments.zip_items[{idx}].{k}")

    return out


def _validate_tool_call_export_document(row: dict[str, Any]) -> str | None:
    tc = row.get("tool_call")
    if not isinstance(tc, dict):
        return "tool_call is required and must be an object"
    if _tool_call_name(row) != "export_document":
        return "tool_call.name must be 'export_document'"
    args = tc.get("arguments")
    if not isinstance(args, dict):
        return "tool_call.arguments must be an object"
    if _is_blank_text(args.get("format")):
        return "tool_call.arguments.format is required"
    doc = args.get("document_spec")
    if not isinstance(doc, dict):
        return "tool_call.arguments.document_spec must be an object"
    if _is_blank_text(doc.get("title")):
        return "document_spec.title is required"
    sections = doc.get("sections")
    if not isinstance(sections, list) or not sections:
        return "document_spec.sections must be a non-empty list"
    for idx, sec in enumerate(sections, start=1):
        if not isinstance(sec, dict):
            return f"document_spec.sections[{idx}] must be an object"
        if _is_blank_text(sec.get("heading")) or _is_blank_text(sec.get("body")):
            return f"document_spec.sections[{idx}] requires non-empty heading/body"
    if _is_blank_text(doc.get("style")):
        return "document_spec.style is required"
    return None


def _validate_tool_call_zip_list(row: dict[str, Any]) -> str | None:
    tc = row.get("tool_call")
    if not isinstance(tc, dict):
        return "tool_call is required and must be an object"
    if _tool_call_name(row) != "zip_list":
        return "tool_call.name must be 'zip_list'"
    args = tc.get("arguments")
    if not isinstance(args, dict):
        return "tool_call.arguments must be an object"
    zip_items = args.get("zip_items")
    if not isinstance(zip_items, list) or len(zip_items) < 2:
        return "tool_call.arguments.zip_items must be a list with manifest + files"
    if not isinstance(zip_items[0], dict):
        return "zip_items[0] must be an object"
    first_name = zip_items[0].get("filename")
    if first_name != "manifest.md":
        return "zip_items[0].filename must be 'manifest.md'"

    filenames: list[str] = []
    for idx, item in enumerate(zip_items, start=1):
        if not isinstance(item, dict):
            return f"zip_items[{idx}] must be an object"
        fn = item.get("filename")
        content = item.get("content")
        if _is_blank_text(fn) or not isinstance(content, str):
            return f"zip_items[{idx}] requires filename/content strings"
        filenames.append(str(fn).strip())

    manifest_content = zip_items[0].get("content")
    if not isinstance(manifest_content, str):
        return "manifest.md content must be a string"
    listed = [
        m.group(1).strip()
        for m in (
            re.match(r"^\s*-\s+(.+?)\s*$", ln)
            for ln in manifest_content.splitlines()
        )
        if m
    ]
    if not listed:
        return "manifest.md must list included filenames (one per '- filename')"
    expected = filenames[1:]
    if listed != expected:
        return "manifest.md listed filenames must exactly match zip_items order after manifest.md"
    return None


def validate_row_v17(row: dict[str, Any], lane_id: str) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    if not isinstance(row, dict):
        return [("row_not_dict", "row must be an object")]

    contract = contract_for_lane(lane_id)
    contract = contract if isinstance(contract, dict) else {}
    fixed_values = contract.get("fixed_values")
    fixed_values = fixed_values if isinstance(fixed_values, dict) else {}
    for issue in enforce_fixed_values(row, lane_id, fixed_values):
        issues.append((issue.code, issue.detail))

    lane_num = _lane_num(lane_id)
    if lane_num is None:
        return issues

    for alias in sorted(_LEGACY_ALIAS_FIELDS):
        if alias in row:
            issues.append(("legacy_alias_field", f"legacy alias field present: {alias}"))

    user_msg = row.get("user_message")
    if isinstance(user_msg, str) and _USER_MECHANISM_LEAK_RE.search(user_msg):
        issues.append(("user_mechanism_word", "user_message contains internal mechanism leakage phrasing"))
    else:
        last_user = _last_user_content(row.get("messages"))
        if isinstance(last_user, str) and _USER_MECHANISM_LEAK_RE.search(last_user):
            issues.append(("user_mechanism_word", "messages last user turn contains internal mechanism leakage phrasing"))

    if lane_num in _TOOLCALL_FORBIDDEN_LANES:
        calls = _collect_tool_call_objects(row)
        has_tool_fields = ("tool_call" in row) or ("tool_calls" in row)
        if calls or has_tool_fields:
            issues.append(("tool_call_forbidden", "tool_call/tool_calls must not appear in this lane"))
    if lane_num in _TOOLCALL_REQUIRED_LANES and not isinstance(row.get("tool_call"), dict):
        issues.append(("tool_call_required", "tool_call is required in this lane"))

    if lane_num == 1:
        if row.get("mode") != "quick":
            issues.append(("mode_mismatch", "lane 01 requires mode=quick"))
        if row.get("representation_choice") != "plain_text":
            issues.append(("representation_mismatch", "lane 01 requires representation_choice=plain_text"))

    elif lane_num == 2:
        if row.get("mode") not in {"quick", "think"}:
            issues.append(("mode_mismatch", "lane 02 mode must be quick or think"))
        if row.get("representation_choice") != "plain_text":
            issues.append(("representation_mismatch", "lane 02 requires representation_choice=plain_text"))

    elif lane_num == 3:
        if row.get("mode") != "think":
            issues.append(("mode_mismatch", "lane 03 requires mode=think"))
        issues.extend(_validate_optional_tool_call_lane_03_04(row, lane_num))

    elif lane_num == 4:
        if row.get("mode") != "quick":
            issues.append(("mode_mismatch", "lane 04 requires mode=quick"))
        issues.extend(_validate_optional_tool_call_lane_03_04(row, lane_num))

    elif lane_num == 5:
        if row.get("mode") != "conversation":
            issues.append(("mode_mismatch", "lane 05 requires mode=conversation"))

    elif lane_num == 6:
        if "connector_needed" in row or "deeplink_needed" in row:
            issues.append(("forbidden_trigger_fields", "lane 06 forbids connector_needed/deeplink_needed"))

    elif lane_num == 7:
        err = _require_bool(row, "needs_search")
        if err:
            issues.append(("needs_search_required", err))
        err = _require_bool(row, "needs_history_search", expected=False)
        if err:
            issues.append(("needs_history_search_false", err))

    elif lane_num == 8:
        err = _require_bool(row, "needs_search", expected=True)
        if err:
            issues.append(("needs_search_true", err))
        err = _require_bool(row, "needs_history_search", expected=False)
        if err:
            issues.append(("needs_history_search_false", err))
        tc_name = _tool_call_name(row)
        if tc_name not in {"web_fetch", "web_read"}:
            issues.append(("tool_call_name_invalid", "lane 08 tool_call.name must be web_fetch or web_read"))
        asst = row.get("assistant_response")
        if _is_blank_text(asst):
            issues.append(("assistant_required", "assistant_response is required"))
        elif isinstance(asst, str):
            if _CITATION_RE.search(asst) is None:
                issues.append(("citation_required", "lane 08 assistant_response must include citations like [1]"))
            if _SEARCH_INTEGRATION_LEAK_RE.search(asst):
                issues.append(("assistant_leakage", "lane 08 assistant_response contains forbidden internal words"))

    elif lane_num == 9:
        if _is_blank_text(row.get("flow_state")):
            issues.append(("flow_state_required", "lane 09 requires flow_state"))

    elif lane_num == 10:
        err = _require_bool(row, "connector_needed")
        if err:
            issues.append(("connector_needed_required", err))
        for f in ("connector_action", "deeplink_action", "image_tool_action"):
            if f in row:
                issues.append(("mapping_label_forbidden", f"lane 10 forbids {f}"))

    elif lane_num == 11:
        if not _is_empty_or_single_space(row.get("assistant_response")):
            issues.append(("assistant_must_be_empty", "lane 11 assistant_response must be '' or single space"))
        if _is_blank_text(row.get("connector_action")):
            issues.append(("connector_action_required", "lane 11 requires connector_action"))
        connector_labels, _ = _load_master_action_labels()
        if connector_labels:
            action = row.get("connector_action")
            if isinstance(action, str) and action.strip() and action not in connector_labels:
                issues.append(("connector_action_not_canonical", f"lane 11 connector_action is not canonical: {action}"))
        for f in ("deeplink_action", "image_tool_action"):
            if f in row and not _is_blank_text(row.get(f)):
                issues.append(("multiple_action_labels", f"lane 11 forbids non-empty {f}"))
        if _contains_key(row, "parameters") or _contains_key(row, "slots"):
            issues.append(("parameters_forbidden", "lane 11 forbids parameters/slots"))

    elif lane_num == 12:
        if not _is_empty_or_single_space(row.get("assistant_response")):
            issues.append(("assistant_must_be_empty", "lane 12 assistant_response must be '' or single space"))
        if _is_blank_text(row.get("deeplink_action")):
            issues.append(("deeplink_action_required", "lane 12 requires deeplink_action"))
        _, deeplink_labels = _load_master_action_labels()
        if deeplink_labels:
            action = row.get("deeplink_action")
            if isinstance(action, str) and action.strip() and action not in deeplink_labels:
                issues.append(("deeplink_action_not_canonical", f"lane 12 deeplink_action is not canonical: {action}"))
        for f in ("connector_action", "image_tool_action"):
            if f in row and not _is_blank_text(row.get(f)):
                issues.append(("multiple_action_labels", f"lane 12 forbids non-empty {f}"))
        if _contains_key(row, "parameters") or _contains_key(row, "slots"):
            issues.append(("parameters_forbidden", "lane 12 forbids parameters/slots"))

    elif lane_num == 13:
        if row.get("representation_choice") != "document_spec":
            issues.append(("representation_mismatch", "lane 13 requires representation_choice=document_spec"))
        if row.get("assistant_response") != "":
            issues.append(("assistant_must_be_empty", "lane 13 assistant_response must be empty string"))
        if "tool_calls" in row:
            issues.append(("tool_call_extra_keys_forbidden", "lane 13 forbids tool_calls; output must use only tool_call object"))
        extras = _collect_extra_keys_export_document(row)
        if extras:
            issues.append(("tool_call_extra_keys_forbidden", "lane 13 extra keys: " + ", ".join(extras)))
        err = _validate_tool_call_export_document(row)
        if err:
            issues.append(("tool_call_schema", err))

    elif lane_num == 14:
        if row.get("representation_choice") != "zip_spec":
            issues.append(("representation_mismatch", "lane 14 requires representation_choice=zip_spec"))
        if row.get("assistant_response") != "":
            issues.append(("assistant_must_be_empty", "lane 14 assistant_response must be empty string"))
        if "tool_calls" in row:
            issues.append(("tool_call_extra_keys_forbidden", "lane 14 forbids tool_calls; output must use only tool_call object"))
        extras = _collect_extra_keys_zip_list(row)
        if extras:
            issues.append(("tool_call_extra_keys_forbidden", "lane 14 extra keys: " + ", ".join(extras)))
        err = _validate_tool_call_zip_list(row)
        if err:
            issues.append(("tool_call_schema", err))

    elif lane_num == 15:
        err = _validate_codeblock_only(row.get("assistant_response"))
        if err:
            issues.append(("codeblock_only", err))

    elif lane_num == 16:
        err = _validate_json_code_spec(row.get("assistant_response"))
        if err:
            issues.append(("json_only", err))

    elif lane_num == 17:
        if row.get("representation_choice") != "comparison_table":
            issues.append(("representation_mismatch", "lane 17 requires representation_choice=comparison_table"))
        err = _validate_markdown_table_only(row.get("assistant_response"))
        if err:
            issues.append(("markdown_table_only", err))

    elif lane_num == 18:
        if row.get("representation_choice") != "chart_spec":
            issues.append(("representation_mismatch", "lane 18 requires representation_choice=chart_spec"))
        err = _validate_chart_spec_only(row.get("assistant_response"))
        if err:
            issues.append(("chart_spec_only", err))

    elif lane_num == 19:
        if row.get("continuity_choice") == "use_continuity":
            msgs = row.get("messages")
            if isinstance(msgs, list):
                sys_text = ""
                for m in msgs:
                    if isinstance(m, dict) and m.get("role") == "system" and isinstance(m.get("content"), str):
                        sys_text = m.get("content")
                        break
                if "CONTEXT" not in sys_text.upper():
                    issues.append(
                        ("continuity_context_missing", "lane 19 use_continuity rows should include prior facts in system CONTEXT")
                    )

    elif lane_num == 20:
        err = _require_bool(row, "needs_search", expected=False)
        if err:
            issues.append(("needs_search_false", err))
        err = _require_bool(row, "needs_history_search", expected=False)
        if err:
            issues.append(("needs_history_search_false", err))
        if row.get("history_scope") != "thread_only":
            issues.append(("history_scope_mismatch", "lane 20 requires history_scope=thread_only"))

    elif lane_num == 21:
        overlap_issue = user_assistant_overlap_v17.check(row, lane_id)
        if overlap_issue:
            issues.append(("user_assistant_overlap_too_high", overlap_issue))

    elif lane_num == 22:
        overlap_issue = user_assistant_overlap_v17.check(row, lane_id)
        if overlap_issue:
            issues.append(("user_assistant_overlap_too_high", overlap_issue))

    elif lane_num == 23:
        overlap_issue = user_assistant_overlap_v17.check(row, lane_id)
        if overlap_issue:
            issues.append(("user_assistant_overlap_too_high", overlap_issue))

    elif lane_num == 24:
        err = _require_bool(row, "needs_history_search")
        if err:
            issues.append(("needs_history_search_required", err))
        hs = row.get("history_scope")
        if hs not in {"thread_only", "all_threads"}:
            issues.append(("history_scope_invalid", "lane 24 history_scope must be thread_only or all_threads"))

    elif lane_num == 25:
        err = _require_bool(row, "needs_history_search", expected=True)
        if err:
            issues.append(("needs_history_search_true", err))
        hist_err = _validate_lane25_history_grounding(row)
        if hist_err:
            issues.append(("history_snippet_grounding_missing", hist_err))

    elif lane_num == 26:
        if not isinstance(row.get("image_context"), dict):
            issues.append(("image_context_required", "lane 26 requires image_context object"))
        else:
            img_err = _validate_lane26_image_grounding(row)
            if img_err:
                issues.append(("image_context_grounding_violation", img_err))

    elif lane_num == 27:
        if not isinstance(row.get("image_context"), dict):
            issues.append(("image_context_required", "lane 27 requires image_context object"))
        if not _is_empty_or_single_space(row.get("assistant_response")):
            issues.append(("assistant_must_be_empty", "lane 27 assistant_response must be '' or single space"))
        action = row.get("image_tool_action")
        if action not in {"web_fetch", "connector_action"}:
            issues.append(("image_tool_action_required", "lane 27 image_tool_action must be web_fetch or connector_action"))
        if _contains_key(row, "parameters") or _contains_key(row, "slots"):
            issues.append(("parameters_forbidden", "lane 27 forbids parameters/slots"))

    elif lane_num == 28:
        if not _is_empty_or_single_space(row.get("assistant_response")):
            issues.append(("assistant_must_be_empty", "lane 28 assistant_response must be '' or single space"))

    elif lane_num == 29:
        if row.get("intent_family") != "safety":
            issues.append(("intent_family_mismatch", "lane 29 requires intent_family=safety"))
        err = _require_bool(row, "needs_search", expected=False)
        if err:
            issues.append(("needs_search_false", err))
        err = _require_bool(row, "needs_history_search", expected=False)
        if err:
            issues.append(("needs_history_search_false", err))
        if row.get("history_scope") != "thread_only":
            issues.append(("history_scope_mismatch", "lane 29 requires history_scope=thread_only"))

    elif lane_num == 30:
        if row.get("intent_family") != "safety":
            issues.append(("intent_family_mismatch", "lane 30 requires intent_family=safety"))

    elif lane_num == 31:
        if row.get("mode") not in {"quick", "think", "conversation"}:
            issues.append(("mode_required", "lane 31 requires mode in {quick, think, conversation}"))

    elif lane_num == 32:
        rep = row.get("representation_choice")
        if _is_blank_text(rep):
            issues.append(("representation_required", "lane 32 requires representation_choice"))
        else:
            asst = row.get("assistant_response")
            rep_norm = rep.strip().lower() if isinstance(rep, str) else ""
            if rep_norm == "comparison_table":
                err = _validate_markdown_table_only(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=comparison_table but {err}"))
            elif rep_norm == "chart_spec":
                err = _validate_chart_spec_only(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=chart_spec but {err}"))
            elif rep_norm == "bullet_list":
                err = _validate_bullet_list_only(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=bullet_list but {err}"))
            elif rep_norm == "plain_text":
                err = _validate_plain_text_only(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=plain_text but {err}"))
            elif rep_norm == "document_spec":
                err = _validate_document_spec_like(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=document_spec but {err}"))
            elif rep_norm == "zip_spec":
                err = _validate_zip_spec_like(asst)
                if err:
                    issues.append(("representation_mismatch", f"representation_choice=zip_spec but {err}"))

    elif lane_num == 33:
        err = _require_bool(row, "needs_search", expected=False)
        if err:
            issues.append(("needs_search_false", err))
        err = _require_bool(row, "needs_history_search", expected=False)
        if err:
            issues.append(("needs_history_search_false", err))
        if row.get("history_scope") != "thread_only":
            issues.append(("history_scope_mismatch", "lane 33 requires history_scope=thread_only"))
        if _is_blank_text(row.get("assistant_response")):
            issues.append(("assistant_required", "lane 33 requires a user-facing fallback assistant_response"))

    elif lane_num == 34:
        lang = str(row.get("language") or "").lower()
        asst = row.get("assistant_response")
        if lang in {"zh-hk", "zh_hk", "zh-hant", "zh_hant"} and isinstance(asst, str):
            if re.search(r"[\u4e00-\u9fff]", asst) is None:
                issues.append(("cjk_missing", "lane 34 zh-hk rows should contain Cantonese/Han characters"))

    elif lane_num == 35:
        if row.get("intent_subtype") not in {"stay_on_topic", "scope_control", "return_to_goal", "gentle_boundary"}:
            issues.append(("intent_subtype_invalid", "lane 35 intent_subtype must be a topic_hygiene subtype"))

    elif lane_num == 37:
        err = _require_bool(row, "deeplink_needed")
        if err:
            issues.append(("deeplink_needed_required", err))
        if "deeplink_action" in row and not _is_blank_text(row.get("deeplink_action")):
            issues.append(("deeplink_action_forbidden", "lane 37 is intent detection; deeplink_action belongs to lane 12"))

    asst = row.get("assistant_response")
    if isinstance(asst, str):
        if lane_num in {6, 7, 10, 19, 24, 31, 32, 37} and _ASSISTANT_INTERNAL_WORD_RE.search(asst):
            issues.append(("assistant_leakage", "assistant_response contains internal mechanism words"))

    return issues

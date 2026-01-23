from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

import jsonschema

from .. import exit_codes as ec
from ..schema_store import PCT_LABEL_STANDARD_SAMPLE_V1
from ..utils import load_json

RECENCY_RE = re.compile(
    r"\b(latest|today|now|current|price|weather|schedule|who is the current)\b",
    re.IGNORECASE,
)


def _lint_qa_record(rec: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    qa_mode = rec.get("qa_mode")
    user = rec.get("user") or rec.get("prompt") or ""
    safety_tag = rec.get("safety_tag")

    if qa_mode not in ("closed_book", "tool_grounded"):
        errs.append("qa_mode must be 'closed_book' or 'tool_grounded'")
        return errs

    if isinstance(user, str) and RECENCY_RE.search(user):
        if qa_mode != "tool_grounded":
            errs.append("recency trigger requires qa_mode=tool_grounded")

    if safety_tag in ("politics_sensitive", "history_sensitive"):
        if qa_mode == "closed_book":
            if not rec.get("answer_sources") or not rec.get("sourcepack_id") or not rec.get("answer_span_sha256"):
                errs.append("closed_book sensitive requires answer_sources + sourcepack_id + answer_span_sha256")
        else:
            if not rec.get("tool_call") or not rec.get("fixture_ids"):
                errs.append("tool_grounded sensitive requires tool_call + fixture_ids")

    if qa_mode == "closed_book":
        if not rec.get("answer_sources") or not rec.get("sourcepack_id") or not rec.get("answer_span_sha256"):
            errs.append("closed_book requires answer_sources + sourcepack_id + answer_span_sha256")

    if qa_mode == "tool_grounded":
        if not rec.get("tool_call") or not rec.get("fixture_ids") or not rec.get("citations"):
            errs.append("tool_grounded requires tool_call + fixture_ids + citations")

    cits = rec.get("citations")
    if cits is not None:
        if not isinstance(cits, list):
            errs.append("citations must be a list")
        else:
            for c in cits:
                if not isinstance(c, dict):
                    errs.append("citation entries must be objects")
                    continue
                has_id = bool(c.get("source_id") or c.get("fixture_id") or c.get("url_or_id"))
                if not has_id:
                    errs.append("citation missing (source_id|fixture_id|url_or_id)")

    return errs


# Lint PCT label standard JSONL
def _lint_pct_label_standard_jsonl(path: Path, *, ignore_private_fields: bool = True) -> int:
    schema = load_json(PCT_LABEL_STANDARD_SAMPLE_V1)
    bad = 0
    total = 0
    first_err: Optional[Tuple[int, str]] = None

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                if first_err is None:
                    first_err = (lineno, "invalid JSON")
                continue

            if not isinstance(rec, dict):
                bad += 1
                if first_err is None:
                    first_err = (lineno, "record is not an object")
                continue

            inst = rec
            if ignore_private_fields:
                inst = {k: v for k, v in rec.items() if not (isinstance(k, str) and k.startswith("_"))}

            try:
                jsonschema.validate(instance=inst, schema=schema)
            except jsonschema.ValidationError as e:
                bad += 1
                if first_err is None:
                    path_str = "/".join(str(p) for p in e.path) if e.path else "<root>"
                    first_err = (lineno, f"{e.message} (at {path_str})")

    if bad != 0:
        if first_err is not None:
            ln, msg = first_err
            print(
                f"PCT schema lint failed: {bad}/{total} invalid rows. First error at line {ln}: {msg}",
                file=sys.stderr,
            )
        else:
            print(f"PCT schema lint failed: {bad}/{total} invalid rows.", file=sys.stderr)

    return ec.SUCCESS if bad == 0 else ec.LINT_FAILED


def run(qa_jsonl: str | None, pct_jsonl: str | None = None) -> int:
    try:
        if pct_jsonl:
            path = Path(pct_jsonl).expanduser().resolve()
            if not path.exists():
                return ec.IO_ERROR
            return _lint_pct_label_standard_jsonl(path, ignore_private_fields=True)
        if not qa_jsonl:
            return ec.SUCCESS

        path = Path(qa_jsonl).expanduser().resolve()
        if not path.exists():
            return ec.IO_ERROR

        bad = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    bad += 1
                    continue
                if not isinstance(rec, dict):
                    bad += 1
                    continue
                if _lint_qa_record(rec):
                    bad += 1

        return ec.SUCCESS if bad == 0 else ec.LINT_FAILED
    except Exception:
        return ec.INTERNAL_ERROR

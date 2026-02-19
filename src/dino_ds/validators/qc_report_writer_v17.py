from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
from typing import Any


_SAFE_RE = re.compile(r"[^A-Za-z0-9_]+")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
QC_REPORT_DIRNAME = "output QC report"
QC_REPORT_DIR_ENV = "DINO_DS_QC_REPORT_DIR"


def _sanitize_token(raw: str, fallback: str) -> str:
    s = str(raw or "").strip().replace("-", "_")
    s = _SAFE_RE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _resolve_repo_root(repo_root: str) -> Path:
    if isinstance(repo_root, str) and repo_root.strip():
        p = Path(repo_root).expanduser().resolve()
        if p.exists() and p.is_dir():
            return p

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            p = Path(out).expanduser().resolve()
            if p.exists() and p.is_dir():
                return p
    except Exception:
        pass

    # Fallback: repository root from this module path.
    return Path(__file__).resolve().parents[3]


def _resolve_report_dir(repo_root: str) -> Path:
    env_dir = str(os.environ.get(QC_REPORT_DIR_ENV, "")).strip()
    if env_dir:
        p = Path(env_dir).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        return p
    root = _resolve_repo_root(repo_root)
    return (root / QC_REPORT_DIRNAME).resolve()


def _dict_to_sorted_bullets(d: dict[str, Any]) -> list[str]:
    if not isinstance(d, dict) or not d:
        return ["- none"]
    out: list[str] = []
    for key in sorted(d.keys()):
        out.append(f"- `{key}`: {d[key]}")
    return out


def _code_gate_map(gates: list[Any], *, severity: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    key = "fatal_codes" if severity == "fatal" else "warn_codes"
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        gate_name = str(gate.get("name", "")).strip() or "unknown"
        blob = gate.get(key)
        if not isinstance(blob, dict):
            continue
        for code in blob.keys():
            if not isinstance(code, str) or not code.strip():
                continue
            out.setdefault(code, []).append(gate_name)
    for code in list(out.keys()):
        dedup = sorted(set(out[code]))
        out[code] = dedup
    return out


def _diagnostic_focus(code: str, *, severity: str) -> str:
    c = code.lower()
    if "fixed_value_violation" in c:
        return "Check lane fixed contract value and row label at the same field path."
    if c.startswith("missing_required_key") or c.startswith("missing_required_label"):
        return "Row template is missing required schema labels/keys."
    if c.startswith("unknown_field_forbidden") or c.startswith("unknown_lane_field_forbidden"):
        return "Remove non-schema fields from row payload."
    if c.startswith("enum_value_not_allowed") or c.startswith("enum_type_mismatch"):
        return "Enum mismatch vs master set or lane override set."
    if "tool_call_extra_keys_forbidden" in c:
        return "Tool payload has non-schema keys; inspect tool_call.arguments path."
    if "tool_call" in c:
        return "Tool policy/schema mismatch; check lane tool contract."
    if "citation" in c:
        return "Citation policy mismatch for this lane."
    if "adjacent_dup_token" in c or "trip_token" in c or "trip_bigram" in c:
        return "Repetition gate hit; inspect repeated token/bigram in assistant_response."
    if "near_duplicate_overlap" in c or "dup_candidate_unconfirmed" in c:
        return "Similarity/duplication overlap; add opening/structure diversity."
    if "script_corruption_fatal" in c or "character_fragmentation_fatal" in c:
        return "Malformed text/script mismatch; inspect language/script composition."
    if "representation" in c or "format" in c or "code_only" in c:
        return "Output format contract mismatch for this lane."
    if "messages_alignment" in c or "role_alternation_invalid" in c or "min_turns_not_met" in c:
        return "Turn/message structure mismatch; inspect messages[] ordering and counts."
    if "language_mismatch_expected" in c:
        return "Row language label does not match lane language slice."
    if "placeholder_marker" in c:
        return "Template placeholder leaked into output."
    if "mechanism_leakage" in c or "user_mechanism_word" in c:
        return "Internal mechanism wording leaked into user/assistant text."
    if "proportion" in c or "share_too_low" in c or "out_of_tolerance" in c:
        return "Slice-level distribution target out of tolerance."
    if "underfilled" in c or "attempts_per_row_too_high" in c:
        return "Generation viability gate issue (underfill/attempt budget)."
    if severity == "warn":
        return "Non-blocking signal; review and decide whether to tighten data generation."
    return "Inspect row examples for this code to locate the blocked contract."


def _coerce_counts(counts: Any) -> dict[str, int]:
    if not isinstance(counts, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in counts.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            out[k] = v
        elif isinstance(v, float):
            out[k] = int(v)
    return out


def _render_markdown(
    *,
    lane_id: str,
    lang: str,
    qc_result: dict[str, Any],
) -> str:
    meta = qc_result.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    counts = _coerce_counts(qc_result.get("counts"))
    gates = qc_result.get("gates")
    gates = gates if isinstance(gates, list) else []
    fatals = qc_result.get("fatals")
    fatals = fatals if isinstance(fatals, dict) else {}
    warns = qc_result.get("warns")
    warns = warns if isinstance(warns, dict) else {}
    top_examples = qc_result.get("top_examples")
    top_examples = top_examples if isinstance(top_examples, dict) else {}
    thresholds = qc_result.get("thresholds")
    thresholds = thresholds if isinstance(thresholds, dict) else {}

    lines: list[str] = []
    lines.append(f"# QC Report — {lane_id} — {lang}")
    lines.append("")

    lines.append("## Run Metadata")
    lines.append("This section explains which run and spec versions produced this QC result.")
    lines.append(f"- lane_id: `{meta.get('lane_id', lane_id)}`")
    lines.append(f"- language slice: `{meta.get('lang', lang)}`")
    lines.append(f"- run_id: `{meta.get('run_id', 'RUN_unknown')}`")
    lines.append(f"- date: `{meta.get('date', 'unknown')}`")
    lines.append(f"- rule_profile: `{meta.get('rule_profile', 'unknown')}`")
    lines.append(f"- spec_version: `{meta.get('spec_version', 'unknown')}`")
    lines.append(f"- equator_version: `{meta.get('equator_version', 'unknown')}`")
    lines.append(f"- generator_commit: `{meta.get('generator_commit', 'unknown')}`")
    lines.append("")

    lines.append("## Counts")
    lines.append("This section summarizes volume and how many checks produced fatal or warning outcomes.")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for metric in (
        "rows_input",
        "rows_generated",
        "rows_validated",
        "fatal_violations",
        "warn_non_blocking",
        "unique_fatal_codes",
        "unique_warn_codes",
    ):
        lines.append(f"| {metric} | {counts.get(metric, 0)} |")
    lines.append("")

    lines.append("## Gate Results")
    lines.append("This section shows each QC gate in Equator order and whether the slice passed.")
    lines.append("| Gate | Status | Notes |")
    lines.append("| --- | --- | --- |")
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        gate_name = str(gate.get("name", "")).strip() or "unknown"
        status = str(gate.get("status", "PASS")).strip() or "PASS"
        note_bits: list[str] = []
        fatal_codes = gate.get("fatal_codes")
        warn_codes = gate.get("warn_codes")
        details = gate.get("details")
        if isinstance(fatal_codes, dict) and fatal_codes:
            short = ", ".join(f"{k}:{v}" for k, v in sorted(fatal_codes.items()))
            note_bits.append(f"fatals={short}")
        if isinstance(warn_codes, dict) and warn_codes:
            short = ", ".join(f"{k}:{v}" for k, v in sorted(warn_codes.items()))
            note_bits.append(f"warns={short}")
        if isinstance(details, dict) and details:
            short = ", ".join(f"{k}={v}" for k, v in sorted(details.items()))
            note_bits.append(short)
        notes = " ; ".join(note_bits) if note_bits else "-"
        lines.append(f"| {gate_name} | {status} | {notes} |")
    lines.append("")

    lines.append("## Fatal Summary")
    lines.append("These are blocking QC failures and their counts.")
    lines.extend(_dict_to_sorted_bullets(fatals))
    lines.append("")

    lines.append("## Warning Summary")
    lines.append("These are non-blocking QC warnings and their counts.")
    lines.extend(_dict_to_sorted_bullets(warns))
    lines.append("")

    lines.append("## Failure Diagnostics")
    lines.append("This section maps each code to gate, block behavior, and where operators should inspect first.")
    lines.append("| Code | Severity | Gate(s) | Count | Blocks Row | Operator Focus | Example Clue |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    fatal_gate_map = _code_gate_map(gates, severity="fatal")
    warn_gate_map = _code_gate_map(gates, severity="warn")
    all_codes: list[tuple[str, str, int]] = []
    for code, cnt in sorted(fatals.items(), key=lambda kv: (-int(kv[1]), kv[0])):
        if isinstance(code, str):
            all_codes.append((code, "FATAL", int(cnt)))
    for code, cnt in sorted(warns.items(), key=lambda kv: (-int(kv[1]), kv[0])):
        if isinstance(code, str):
            all_codes.append((code, "WARN", int(cnt)))
    if not all_codes:
        lines.append("| none | - | - | 0 | - | - | - |")
    else:
        for code, sev, cnt in all_codes:
            gates_for_code = fatal_gate_map.get(code, []) if sev == "FATAL" else warn_gate_map.get(code, [])
            gates_blob = ", ".join(gates_for_code) if gates_for_code else "-"
            blocks = "yes" if sev == "FATAL" else "no"
            focus = _diagnostic_focus(code, severity=sev.lower())
            clue = "-"
            ex_list = top_examples.get(code)
            if isinstance(ex_list, list) and ex_list:
                ex0 = ex_list[0]
                if isinstance(ex0, dict):
                    msg = str(ex0.get("message", "")).strip()
                    if msg:
                        clue = msg.replace("|", "\\|")
            lines.append(
                f"| `{code}` | {sev} | {gates_blob} | {cnt} | {blocks} | {focus} | {clue} |"
            )
    lines.append("")

    lines.append("## Top Examples")
    lines.append("Examples are short and only include assistant/tool_call context to avoid leaking raw prompts.")
    if not top_examples:
        lines.append("- none")
    else:
        for code in sorted(top_examples.keys()):
            ex_list = top_examples.get(code)
            if not isinstance(ex_list, list) or not ex_list:
                continue
            lines.append(f"### `{code}`")
            shown = 0
            for ex in ex_list:
                if not isinstance(ex, dict):
                    continue
                row_id = str(ex.get("row_id", "row_unknown")).strip() or "row_unknown"
                msg = str(ex.get("message", "")).strip()
                if not msg:
                    continue
                lines.append(f"- `{row_id}`: {msg}")
                shown += 1
                if shown >= 5:
                    break
    lines.append("")

    lines.append("## Thresholds Used")
    lines.append("These are the active lane-scoped thresholds used in this QC run.")
    lines.extend(_dict_to_sorted_bullets(thresholds))
    lines.append("")

    return "\n".join(lines)


def write_qc_report(
    repo_root: str,
    lane_id: str,
    lang: str,
    run_id: str,
    date_yyyy_mm_dd: str,
    qc_result: dict[str, Any],
) -> str:
    out_dir = _resolve_report_dir(repo_root)
    lane_safe = _sanitize_token(lane_id, "lane")
    lang_safe = _sanitize_token(lang, "unknown")
    run_safe = _sanitize_token(run_id, "RUN_unknown")
    date_safe = date_yyyy_mm_dd if isinstance(date_yyyy_mm_dd, str) and _DATE_RE.match(date_yyyy_mm_dd) else "1970-01-01"
    filename = f"QC_{lane_safe}_{lang_safe}_{run_safe}_{date_safe}.md"

    md = _render_markdown(
        lane_id=lane_id,
        lang=lang,
        qc_result=qc_result if isinstance(qc_result, dict) else {},
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = (out_dir / filename).resolve()
    path.write_text(md, encoding="utf-8")
    return str(path)

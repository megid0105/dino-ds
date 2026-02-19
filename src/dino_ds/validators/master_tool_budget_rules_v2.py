from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str


_MISSING = object()
_TOOL_BUDGET_ALLOWED_KEYS = {"searches", "reads", "seconds"}


def _get_dotted(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        key = part.strip()
        if not key:
            return _MISSING
        if not isinstance(cur, dict):
            return _MISSING
        if key not in cur:
            return _MISSING
        cur = cur.get(key)
    return cur


def _resolve_value(obj: dict[str, Any], paths: tuple[str, ...]) -> tuple[Any, str]:
    for path in paths:
        val = _get_dotted(obj, path)
        if val is not _MISSING:
            return val, path
    return _MISSING, paths[0]


def _is_int_not_bool(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_number_not_bool(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _iter_tool_call_objects(rr: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    tc = rr.get("tool_call")
    if isinstance(tc, dict):
        out.append(("tool_call", tc))
    tcs = rr.get("tool_calls")
    if isinstance(tcs, list):
        for idx, item in enumerate(tcs):
            if isinstance(item, dict):
                out.append((f"tool_calls[{idx}]", item))
    return out


def check_master_tool_budget(rr: dict[str, Any]) -> list[Issue]:
    if not isinstance(rr, dict):
        return []

    issues: list[Issue] = []

    tool_budget, tool_budget_path = _resolve_value(rr, ("tool_budget", "lane.tool_budget"))
    if tool_budget is not _MISSING:
        if not isinstance(tool_budget, dict):
            issues.append(
                Issue(
                    code="tool_budget_not_object",
                    detail=f"{tool_budget_path} must be an object with keys searches/reads/seconds",
                )
            )
        else:
            if any(not isinstance(k, str) for k in tool_budget.keys()):
                issues.append(
                    Issue(
                        code="tool_budget_unknown_key",
                        detail=f"{tool_budget_path} contains a non-string key",
                    )
                )
            else:
                unknown_keys = sorted(k for k in tool_budget.keys() if k not in _TOOL_BUDGET_ALLOWED_KEYS)
                if unknown_keys:
                    issues.append(
                        Issue(
                            code="tool_budget_unknown_key",
                            detail=f"{tool_budget_path}.{unknown_keys[0]} is not allowed",
                        )
                    )

            if "searches" in tool_budget:
                searches = tool_budget.get("searches")
                if not _is_int_not_bool(searches) or not (0 <= searches <= 1):
                    issues.append(
                        Issue(
                            code="tool_budget_searches_out_of_range",
                            detail=f"{tool_budget_path}.searches must be integer in [0,1]; got {searches!r}",
                        )
                    )

            if "reads" in tool_budget:
                reads = tool_budget.get("reads")
                if not _is_int_not_bool(reads) or not (0 <= reads <= 3):
                    issues.append(
                        Issue(
                            code="tool_budget_reads_out_of_range",
                            detail=f"{tool_budget_path}.reads must be integer in [0,3]; got {reads!r}",
                        )
                    )

            if "seconds" in tool_budget:
                seconds = tool_budget.get("seconds")
                if not _is_number_not_bool(seconds) or not (0 <= float(seconds) <= 30):
                    issues.append(
                        Issue(
                            code="tool_budget_seconds_out_of_range",
                            detail=f"{tool_budget_path}.seconds must be number in [0,30]; got {seconds!r}",
                        )
                    )

    search_calls = 0
    read_calls = 0
    summed_max_seconds = 0.0
    for call_path, call_obj in _iter_tool_call_objects(rr):
        call_name = call_obj.get("name")
        if isinstance(call_name, str):
            lowered_name = call_name.strip().lower()
            if lowered_name == "web_fetch":
                search_calls += 1
            if lowered_name == "web_read":
                read_calls += 1

        args = call_obj.get("arguments")
        if not isinstance(args, dict):
            continue

        if "max_reads" in args:
            max_reads = args.get("max_reads")
            if not _is_int_not_bool(max_reads) or not (0 <= max_reads <= 3):
                issues.append(
                    Issue(
                        code="tool_call_max_reads_out_of_range",
                        detail=f"{call_path}.arguments.max_reads must be integer in [0,3]; got {max_reads!r}",
                    )
                )

        if "max_seconds" in args:
            max_seconds = args.get("max_seconds")
            if not _is_number_not_bool(max_seconds) or not (0 <= float(max_seconds) <= 30):
                issues.append(
                    Issue(
                        code="tool_call_max_seconds_out_of_range",
                        detail=f"{call_path}.arguments.max_seconds must be number in [0,30]; got {max_seconds!r}",
                    )
                )
            elif _is_number_not_bool(max_seconds):
                summed_max_seconds += float(max_seconds)

    if search_calls > 1:
        issues.append(
            Issue(
                code="tool_policy_searches_exceeded",
                detail=f"per-turn search budget is <=1; observed {search_calls} web_fetch calls",
            )
        )
    if read_calls > 3:
        issues.append(
            Issue(
                code="tool_policy_reads_exceeded",
                detail=f"per-turn read budget is <=3; observed {read_calls} web_read calls",
            )
        )

    # If explicit tool_budget is supplied, observed usage must not exceed it.
    if isinstance(tool_budget, dict):
        b_searches = tool_budget.get("searches")
        if _is_int_not_bool(b_searches) and search_calls > int(b_searches):
            issues.append(
                Issue(
                    code="tool_budget_searches_exceeded",
                    detail=(
                        f"observed web_fetch calls={search_calls} exceeds "
                        f"{tool_budget_path}.searches={int(b_searches)}"
                    ),
                )
            )

        b_reads = tool_budget.get("reads")
        if _is_int_not_bool(b_reads) and read_calls > int(b_reads):
            issues.append(
                Issue(
                    code="tool_budget_reads_exceeded",
                    detail=(
                        f"observed web_read calls={read_calls} exceeds "
                        f"{tool_budget_path}.reads={int(b_reads)}"
                    ),
                )
            )

        b_seconds = tool_budget.get("seconds")
        if _is_number_not_bool(b_seconds) and summed_max_seconds > float(b_seconds):
            issues.append(
                Issue(
                    code="tool_budget_seconds_exceeded",
                    detail=(
                        f"observed max_seconds_total={summed_max_seconds:.3f} exceeds "
                        f"{tool_budget_path}.seconds={float(b_seconds):.3f}"
                    ),
                )
            )

    return issues

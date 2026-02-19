from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str


_MISSING = object()


def _normalize_path(path: str) -> str:
    p = path.strip()
    if p.startswith("lane."):
        p = p[len("lane.") :]
    return p


def _get_by_dotted_path(obj: Any, path: str) -> Any:
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


def _expected_ok(actual: Any, expected: Any) -> bool:
    if isinstance(expected, set):
        return actual in expected
    if isinstance(expected, (list, tuple)):
        return actual in expected
    return actual == expected


def enforce_fixed_values(rr: dict[str, Any], lane_id: str, fixed_values: dict[str, Any]) -> list[Issue]:
    if not isinstance(rr, dict) or not isinstance(fixed_values, dict):
        return []

    issues: list[Issue] = []
    for raw_field, expected in fixed_values.items():
        if not isinstance(raw_field, str) or not raw_field.strip():
            continue
        path = _normalize_path(raw_field)
        if not path:
            continue
        actual = _get_by_dotted_path(rr, path)
        if actual is _MISSING:
            issues.append(
                Issue(
                    code=f"fixed_value_violation:{path}",
                    detail=f"field '{path}' is required and must equal {expected!r} (lane={lane_id})",
                )
            )
            continue
        if not _expected_ok(actual, expected):
            issues.append(
                Issue(
                    code=f"fixed_value_violation:{path}",
                    detail=f"field '{path}' must equal {expected!r}; got {actual!r} (lane={lane_id})",
                )
            )
    return issues


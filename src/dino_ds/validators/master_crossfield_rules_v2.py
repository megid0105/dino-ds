from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str


_MISSING = object()


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


def check_master_crossfield(rr: dict[str, Any]) -> list[Issue]:
    if not isinstance(rr, dict):
        return []

    issues: list[Issue] = []
    adult_gate, adult_path = _resolve_value(rr, ("adult_gate", "lane.adult_gate"))
    profanity_allowed, profanity_path = _resolve_value(rr, ("profanity_allowed", "lane.profanity_allowed"))
    tone, tone_path = _resolve_value(rr, ("tone", "lane.tone"))

    if isinstance(profanity_allowed, bool) and (profanity_allowed is True):
        tone_is_best_friend = isinstance(tone, str) and tone.strip().lower() == "best_friend"
        if not (isinstance(adult_gate, bool) and (adult_gate is True) and tone_is_best_friend):
            issues.append(
                Issue(
                    code="profanity_requires_adult_gate_and_best_friend",
                    detail=(
                        f"profanity_allowed={profanity_allowed!r} ({profanity_path}) requires "
                        f"adult_gate=True and tone='best_friend'; got "
                        f"adult_gate={adult_gate!r} ({adult_path}), "
                        f"tone={tone!r} ({tone_path})"
                    ),
                )
            )

    if isinstance(adult_gate, bool) and isinstance(profanity_allowed, bool):
        if (adult_gate is False) and (profanity_allowed is True):
            issues.append(
                Issue(
                    code="adult_gate_profanity_inconsistent",
                    detail=(
                        f"adult_gate={adult_gate!r} ({adult_path}), "
                        f"profanity_allowed={profanity_allowed!r} ({profanity_path})"
                    ),
                )
            )
    return issues

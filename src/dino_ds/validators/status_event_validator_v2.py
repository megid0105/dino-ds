from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str


_ALLOWED_KEYS = {"phase", "note", "route", "tokensSoFar", "sourcesCount"}
_REQUIRED_KEYS = ("phase", "note", "route")
_PHASES = {"parse", "plan", "retrieve", "compose", "finalize"}
_ROUTES = {"slm", "cloud"}
_REASONING_LEAK_RE = re.compile(
    r"(?i)\b(chain[- ]of[- ]thought|reasoning|step\s*\d+|my thinking|i think step by step)\b"
)


def _is_number_not_bool(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_status_event(rr: dict[str, Any]) -> list[Issue]:
    if not isinstance(rr, dict):
        return []
    if "status_event" not in rr:
        return []

    se = rr.get("status_event")
    if not isinstance(se, dict):
        return [Issue("status_event_not_object", "status_event must be an object")]

    if any(not isinstance(k, str) for k in se.keys()):
        return [Issue("status_event_unknown_key", "status_event contains non-string key")]

    unknown = sorted(k for k in se.keys() if k not in _ALLOWED_KEYS)
    if unknown:
        return [Issue("status_event_unknown_key", f"status_event.{unknown[0]} is not allowed")]

    for key in _REQUIRED_KEYS:
        if key not in se:
            return [Issue("status_event_missing_required", f"status_event.{key} is required")]

    phase = se.get("phase")
    if not isinstance(phase, str) or phase.strip().lower() not in _PHASES:
        return [Issue("status_event_phase_invalid", f"status_event.phase must be one of {sorted(_PHASES)}")]

    route = se.get("route")
    if not isinstance(route, str) or route.strip().lower() not in _ROUTES:
        return [Issue("status_event_route_invalid", f"status_event.route must be one of {sorted(_ROUTES)}")]

    note = se.get("note")
    if not isinstance(note, str) or not note.strip():
        return [Issue("status_event_note_invalid", "status_event.note must be a non-empty string")]
    if "\n" in note or "\r" in note:
        return [Issue("status_event_note_invalid", "status_event.note must be single-line status text")]
    if len(note.strip()) > 200:
        return [Issue("status_event_note_invalid", "status_event.note must be <= 200 chars")]
    if _REASONING_LEAK_RE.search(note):
        return [Issue("status_event_reasoning_leakage", "status_event.note must be status-only (no reasoning text)")]

    for key in ("tokensSoFar", "sourcesCount"):
        if key not in se:
            continue
        val = se.get(key)
        if not _is_number_not_bool(val) or float(val) < 0:
            return [Issue("status_event_counter_invalid", f"status_event.{key} must be non-negative number")]

    return []

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts.v16_lane_contracts import contract_for_lane


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str


def _append_once(issues: list[Issue], code: str, detail: str) -> None:
    for it in issues:
        if it.code == code:
            return
    issues.append(Issue(code=code, detail=detail))


_MESSAGE_LABEL_KEYS_FORBIDDEN: set[str] = {
    # Master/global lane labels must stay at row level, never inside messages[*].
    "id",
    "row_id",
    "sample_id",
    "target_base",
    "lane_id",
    "language",
    "mode",
    "tone",
    "adult_gate",
    "profanity_allowed",
    "emote6",
    "text_affect6",
    "style6",
    "representation_choice",
    "continuity_choice",
    "intent_family",
    "intent_subtype",
    "intent",
    "mode_label",
    "flow_state",
    "safety_tag",
    "needs_search",
    "needs_history_search",
    "history_scope",
    "connector_needed",
    "deeplink_needed",
    "connector_action",
    "deeplink_action",
    "image_tool_action",
    "callback_type",
    "creative_extraction_attempt",
    "attempt_type",
}


def _effective_min_messages(contract: dict[str, object], requires_multiturn: bool) -> int:
    raw_min_messages = contract.get("min_messages")
    if isinstance(raw_min_messages, int) and raw_min_messages > 0:
        return raw_min_messages

    raw_pairs = contract.get("min_turn_pairs")
    if isinstance(raw_pairs, int) and raw_pairs > 0:
        return raw_pairs * 2

    # Contract default fallback (single-turn = 2, multi-turn = 4).
    return 4 if requires_multiturn else 2


def check_turn_structure(rr: dict[str, Any], lane_id: str) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(rr, dict):
        return [Issue(code="missing_messages", detail="row must be an object with messages")]

    msgs = rr.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return [Issue(code="missing_messages", detail="messages must be a non-empty list")]

    non_system_roles: list[str] = []
    system_positions: list[int] = []
    for idx, item in enumerate(msgs, start=1):
        if not isinstance(item, dict):
            _append_once(issues, "roles_order_invalid", f"messages[{idx}] must be an object")
            continue

        forbidden_label_keys = [
            key for key in item.keys() if isinstance(key, str) and key in _MESSAGE_LABEL_KEYS_FORBIDDEN
        ]
        if forbidden_label_keys:
            bad = forbidden_label_keys[0]
            _append_once(
                issues,
                "message_label_key_forbidden",
                f"messages[{idx}].{bad} must not appear inside messages",
            )

        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str):
            _append_once(issues, "roles_order_invalid", f"messages[{idx}].role must be a string")
            continue
        if not isinstance(content, str):
            _append_once(issues, "roles_order_invalid", f"messages[{idx}].content must be a string")
            continue

        r = role.strip().lower()
        if r == "system":
            system_positions.append(idx)
            continue
        if r not in {"user", "assistant"}:
            _append_once(
                issues,
                "roles_order_invalid",
                f"messages[{idx}].role must be one of {{system,user,assistant}}",
            )
            continue
        non_system_roles.append(r)

    if not non_system_roles:
        _append_once(issues, "missing_messages", "messages must include user/assistant turns")
        return issues

    if not system_positions:
        _append_once(
            issues,
            "missing_messages",
            "messages must include a system message as the first turn",
        )
    else:
        if system_positions[0] != 1:
            _append_once(
                issues,
                "roles_order_invalid",
                "system message, when present, must be the first message",
            )
        if len(system_positions) > 1:
            _append_once(
                issues,
                "roles_order_invalid",
                "messages may contain at most one system message",
            )

    if non_system_roles[0] != "user":
        _append_once(
            issues,
            "roles_order_invalid",
            "non-system messages must start with user",
        )
    if non_system_roles[-1] != "assistant":
        _append_once(
            issues,
            "roles_order_invalid",
            "non-system messages must end with assistant",
        )

    for i in range(1, len(non_system_roles)):
        if non_system_roles[i] == non_system_roles[i - 1]:
            _append_once(
                issues,
                "role_alternation_invalid",
                f"adjacent roles repeat at non_system_index={i} ({non_system_roles[i]})",
            )
            break

    contract = contract_for_lane(lane_id)
    contract = contract if isinstance(contract, dict) else {}
    requires_multiturn = bool(contract.get("requires_multiturn", False))
    allow_multiturn = bool(contract.get("allow_multiturn", False))
    min_messages = _effective_min_messages(contract, requires_multiturn=requires_multiturn)

    if requires_multiturn:
        if len(non_system_roles) < min_messages:
            _append_once(
                issues,
                "min_turns_not_met",
                f"requires_multiturn=true and min_messages={min_messages}, got {len(non_system_roles)}",
            )
    elif allow_multiturn:
        if len(non_system_roles) < 2:
            _append_once(
                issues,
                "min_turns_not_met",
                f"lane allows multi-turn and requires at least 2 non-system messages, got {len(non_system_roles)}",
            )
    else:
        # Single-turn hard invariant: exactly one user->assistant pair.
        if len(non_system_roles) != 2:
            _append_once(
                issues,
                "min_turns_not_met",
                f"single-turn lane requires exactly 2 non-system messages, got {len(non_system_roles)}",
            )

    return issues

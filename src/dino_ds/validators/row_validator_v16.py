from __future__ import annotations

import re
from typing import Any

from ..contracts.v16_lane_contracts import V16_LANE_CONTRACTS

ACTION_LABEL_FIELDS = (
    "connector_action",
    "deeplink_action",
    "image_tool_action",
)

LANE_SCOPED_FIELDS: dict[str, set[str]] = {
    "connector_action": {"lane_11_connector_action_mapping"},
    "connector_needed": {"lane_10_connector_intent_detection"},
    "deeplink_action": {"lane_12_deeplink_action_mapping", "lane_37_deeplink_intent_detection"},
    "deeplink_needed": {"lane_12_deeplink_action_mapping", "lane_37_deeplink_intent_detection"},
    "image_tool_action": {"lane_27_image_tooling"},
    "image_context": {"lane_26_image_context_understanding", "lane_27_image_tooling"},
}

_CITATION_RE = re.compile(r"\[[0-9]+\]")


def _contract_for_lane(lane_id: str) -> dict[str, object]:
    if lane_id in V16_LANE_CONTRACTS:
        return V16_LANE_CONTRACTS[lane_id]
    return V16_LANE_CONTRACTS.get("default", {})


def _is_missing_value(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _contains_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        for v in obj.values():
            if _contains_key(v, key):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _contains_key(item, key):
                return True
    return False


def _contains_citations(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    return _CITATION_RE.search(text) is not None


def validate_row_v16(row: dict, lane_id: str) -> tuple[bool, str]:
    if not isinstance(row, dict):
        return False, "row_not_dict"

    contract = _contract_for_lane(lane_id)
    required_keys = contract.get("required_keys") or []
    required_label_keys = contract.get("required_label_keys") or []
    allowed_enums = contract.get("allowed_enums") or {}
    forbidden_user_substrings = contract.get("forbidden_user_substrings") or []
    mapping_rules = contract.get("mapping_lane_rules") or {}
    integration_rules = contract.get("integration_lane_rules") or {}

    for k in required_keys:
        if k not in row:
            return False, f"missing_required_key:{k}"

    for k in required_label_keys:
        if k not in row or _is_missing_value(row.get(k)):
            return False, f"missing_required_label:{k}"

    # Enum checks (master v2 global enums)
    if isinstance(allowed_enums, dict):
        for field, allowed in allowed_enums.items():
            if field not in row:
                continue
            val = row.get(field)
            if _is_missing_value(val):
                continue
            if not isinstance(allowed, list) or not allowed:
                continue
            if all(isinstance(a, bool) for a in allowed):
                if not isinstance(val, bool):
                    return False, f"enum_type_mismatch:{field}"
                if val not in allowed:
                    return False, f"enum_invalid:{field}"
                continue
            if all(isinstance(a, str) for a in allowed):
                if not isinstance(val, str):
                    return False, f"enum_type_mismatch:{field}"
                if val not in allowed:
                    return False, f"enum_invalid:{field}"
                continue
            if val not in allowed:
                return False, f"enum_invalid:{field}"

    # Lane-scoped fields
    for field, lanes in LANE_SCOPED_FIELDS.items():
        if field in row and lane_id not in lanes:
            return False, f"lane_scoped_field:{field}"

    # Realism rule: forbid internal mechanism text in user_message
    user_msg = row.get("user_message")
    if isinstance(user_msg, str) and forbidden_user_substrings:
        lowered = user_msg.lower()
        for sub in forbidden_user_substrings:
            if isinstance(sub, str) and sub.lower() in lowered:
                return False, f"forbidden_user_substring:{sub}"

    # Mapping lane rules
    if mapping_rules.get("assistant_response_must_be_empty"):
        ar = row.get("assistant_response")
        if not isinstance(ar, str) or ar.strip() != "":
            return False, "assistant_response_not_empty"

    if mapping_rules.get("forbid_tool_call_field") and "tool_call" in row:
        return False, "tool_call_forbidden"

    if mapping_rules.get("forbid_parameters_fields") and _contains_key(row, "parameters"):
        return False, "parameters_forbidden"

    only_action_label = mapping_rules.get("only_one_action_label")
    if isinstance(only_action_label, str) and only_action_label:
        if only_action_label not in row or _is_missing_value(row.get(only_action_label)):
            return False, f"missing_action_label:{only_action_label}"
        for field in ACTION_LABEL_FIELDS:
            if field == only_action_label:
                continue
            if field in row and not _is_missing_value(row.get(field)):
                return False, f"multiple_action_labels:{only_action_label}+{field}"

    # Integration lane rules
    allow_tool_call = bool(integration_rules.get("allow_tool_call", False))
    if not allow_tool_call and "tool_call" in row:
        return False, "tool_call_forbidden"

    allow_citations = bool(integration_rules.get("allow_citations_blocks", False))
    if not allow_citations:
        if _contains_citations(row.get("assistant_response")) or _contains_citations(row.get("user_message")):
            return False, "citations_forbidden"

    return True, ""

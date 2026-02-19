from __future__ import annotations

import re
from typing import Any

from ..contracts.v16_lane_contracts import contract_for_lane
from .enum_resolver_v17 import validate_enum
from .lane_policy_v17 import get_lane_policy, has_lane_policy
from .master_crossfield_rules_v2 import check_master_crossfield
from .master_tool_budget_rules_v2 import check_master_tool_budget
from .status_event_validator_v2 import check_status_event

ACTION_LABEL_FIELDS = (
    "connector_action",
    "deeplink_action",
    "image_tool_action",
)

LANE_SCOPED_FIELDS: dict[str, set[str]] = {
    "connector_action": {"lane_11_connector_action_mapping"},
    "connector_needed": {"lane_10_connector_intent_detection"},
    "deeplink_action": {"lane_12_deeplink_action_mapping"},
    "deeplink_needed": {"lane_37_deeplink_intent_detection"},
    "image_tool_action": {"lane_27_image_tooling"},
    "image_context": {
        "lane_03_think_mode",
        "lane_04_quick_mode",
        "lane_05_conversation_mode",
        "lane_26_image_context_understanding",
        "lane_27_image_tooling",
    },
}

# Citation token must be isolated so code indexing (e.g. a[0]) is not treated as citation.
_CITATION_RE = re.compile(r"(?<![A-Za-z0-9_])\[[1-9][0-9]{0,2}\](?![A-Za-z0-9_])")

# Keep empty unless v17 explicitly marks a lane as mixed-language at row label level.
LANGUAGE_INTEGRITY_EXEMPT_LANES: set[str] = set()

# Strict top-level schema keys (Equator §1 forbidden-field invariant).
# Keep this explicit and lane-agnostic; lane-specific constraints are applied later.
ALLOWED_TOP_LEVEL_KEYS: set[str] = {
    # Canonical ids / bookkeeping
    "id",
    "row_id",
    "sample_id",
    "target_base",
    "system_prompt_id",
    "lane_id",
    "_lane",
    "type",
    "source",
    # Core labels + content
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
    "user_message",
    "assistant_response",
    # Structured payloads
    "messages",
    "tool_call",
    "tool_calls",
    "tool_budget",
    "capabilities_manifest_id",
    "image_context",
    "status_event",
}

# Optional strictness for nested lane.* payload when provided.
ALLOWED_LANE_KEYS: set[str] = {
    "language",
    "mode",
    "tone",
    "adult_gate",
    "profanity_allowed",
    "emote6",
    "representation_choice",
    "continuity_choice",
    "intent_family",
    "intent_subtype",
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


def _contract_for_lane(lane_id: str) -> dict[str, object]:
    return contract_for_lane(lane_id)


def _is_missing_value(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _norm_lang_tag(val: Any) -> str:
    if not isinstance(val, str):
        return ""
    return val.strip().lower()


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


def validate_row_v16(row: dict, lane_id: str, expected_language: str | None = None) -> tuple[bool, str]:
    if not isinstance(row, dict):
        return False, "row_not_dict"

    contract = _contract_for_lane(lane_id)
    lane_policy = get_lane_policy(lane_id)
    lane_has_policy = has_lane_policy(lane_id)
    required_keys = contract.get("required_keys") or []
    required_label_keys = contract.get("required_label_keys") or []
    allowed_enums = contract.get("allowed_enums") or {}
    enum_overrides = contract.get("enum_overrides") or {}
    forbidden_user_substrings = contract.get("forbidden_user_substrings") or []
    mapping_rules = contract.get("mapping_lane_rules") or {}
    integration_rules = contract.get("integration_lane_rules") or {}
    warning_hits: list[str] = []

    for k in required_keys:
        if k not in row:
            return False, f"missing_required_key:{k}"

    for k in required_label_keys:
        if k not in row or _is_missing_value(row.get(k)):
            return False, f"missing_required_label:{k}"

    # Global language-integrity invariant (lane file language vs row label).
    # Applies unless a lane is explicitly exempted by spec.
    if lane_id not in LANGUAGE_INTEGRITY_EXEMPT_LANES:
        expected = _norm_lang_tag(expected_language)
        if expected:
            got = _norm_lang_tag(row.get("language"))
            if got != expected:
                got_label = got or "<missing>"
                return False, f"language_mismatch_expected:{expected}_got:{got_label}"

    # Strict schema contract: unknown top-level keys are forbidden.
    unknown_top = sorted(
        key
        for key in row.keys()
        if isinstance(key, str) and key not in ALLOWED_TOP_LEVEL_KEYS
    )
    if unknown_top:
        return False, f"unknown_field_forbidden:{unknown_top[0]}"
    if any(not isinstance(key, str) for key in row.keys()):
        return False, "unknown_field_forbidden:<non_string_key>"

    # Optional strictness for nested lane.* labels when lane object exists.
    lane_obj = row.get("lane")
    if isinstance(lane_obj, dict):
        unknown_lane = sorted(
            key
            for key in lane_obj.keys()
            if isinstance(key, str) and key not in ALLOWED_LANE_KEYS
        )
        if unknown_lane:
            return False, f"unknown_lane_field_forbidden:{unknown_lane[0]}"
        if any(not isinstance(key, str) for key in lane_obj.keys()):
            return False, "unknown_lane_field_forbidden:<non_string_key>"

    # Master v2 cross-field consistency checks (global semantics).
    status_event_issues = check_status_event(row)
    if status_event_issues:
        return False, status_event_issues[0].code

    # Master v2 cross-field consistency checks (global semantics).
    crossfield_issues = check_master_crossfield(row)
    if crossfield_issues:
        return False, crossfield_issues[0].code

    # Master v2 tool policy budget checks (global tooling semantics).
    tool_budget_issues = check_master_tool_budget(row)
    if tool_budget_issues:
        return False, tool_budget_issues[0].code

    # Enum checks (master v2 global enums + lane-scoped v17 overrides)
    if isinstance(allowed_enums, dict):
        for field, allowed in allowed_enums.items():
            if field not in row:
                continue
            val = row.get(field)
            if _is_missing_value(val):
                continue
            if not isinstance(allowed, list) or not allowed:
                continue
            master_allowed_set: set[Any]
            if all(isinstance(a, bool) for a in allowed):
                if not isinstance(val, bool):
                    return False, f"enum_type_mismatch:{field}"
                master_allowed_set = set(allowed)
            elif all(isinstance(a, str) for a in allowed):
                if not isinstance(val, str):
                    return False, f"enum_type_mismatch:{field}"
                master_allowed_set = set(allowed)
            else:
                master_allowed_set = set(allowed)

            lane_override_set: set[Any] = set()
            if isinstance(enum_overrides, dict):
                override_vals = enum_overrides.get(field)
                if isinstance(override_vals, set):
                    lane_override_set = set(override_vals)
                elif isinstance(override_vals, (list, tuple)):
                    lane_override_set = set(override_vals)

            ok_enum, warning_code, fail_code = validate_enum(
                field,
                val,
                lane_id=lane_id,
                master_allowed_set=master_allowed_set,
                lane_override_set=lane_override_set,
            )
            if not ok_enum:
                code = fail_code or "enum_value_not_allowed"
                return False, f"{code}:{field}"
            if warning_code:
                warning_hits.append(f"{warning_code}:{field}={val}")

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

    # Mapping lane rules + lane policy output shape
    assistant_response_must_be_empty = bool(mapping_rules.get("assistant_response_must_be_empty", False))
    assistant_response_must_be_code_only = False
    if lane_has_policy:
        assistant_response_must_be_empty = assistant_response_must_be_empty or lane_policy.assistant_response_must_be_empty
        assistant_response_must_be_code_only = lane_policy.assistant_response_must_be_code_only

    if assistant_response_must_be_empty:
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

    # Integration lane rules + lane policy tool-call contract
    requires_tool_call = bool(integration_rules.get("requires_tool_call", False))
    allow_tool_call = bool(integration_rules.get("allow_tool_call", False))
    if lane_has_policy:
        requires_tool_call = lane_policy.requires_tool_call
        allow_tool_call = lane_policy.allows_tool_call

    if requires_tool_call and not isinstance(row.get("tool_call"), dict):
        return False, "tool_call_required"
    if requires_tool_call and "tool_calls" in row:
        return False, "tool_calls_forbidden"
    if not allow_tool_call and ("tool_call" in row or "tool_calls" in row):
        return False, "tool_call_forbidden"

    # Integration lane rules + lane policy citation contract
    requires_citations = bool(integration_rules.get("requires_citations", False))
    forbids_citations = bool(integration_rules.get("forbids_citations", False))
    if lane_has_policy:
        requires_citations = lane_policy.requires_citations
        forbids_citations = lane_policy.forbids_citations
    # Neutral default: if neither policy nor lane rules explicitly require/forbid
    # citations, do not enforce citation presence/absence.

    if requires_citations and not _contains_citations(row.get("assistant_response")):
        return False, "citations_required"
    if forbids_citations:
        if _contains_citations(row.get("user_message")):
            return False, "citations_forbidden"
        # Skip assistant citation blocking for code-only lanes to avoid indexing false positives.
        if not assistant_response_must_be_code_only and _contains_citations(row.get("assistant_response")):
            return False, "citations_forbidden"

    if warning_hits:
        return True, "warn:" + "|".join(warning_hits)
    return True, ""

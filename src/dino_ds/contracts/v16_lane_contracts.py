from __future__ import annotations

import copy

# Global enums pulled from the master v2 label spec (see MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md)
MASTER_ENUMS: dict[str, list[str]] = {
    "language": ["en", "zh-hk", "zh-hant", "zh-hans", "pt-br", "fr", "de", "it", "hi", "vi", "ja", "ko", "es", "th"],
    "mode": ["quick", "think", "conversation"],
    "tone": ["family", "serious", "professional", "friendly", "best_friend"],
    "emote6": ["happy", "sad", "angry", "fear", "encourage", "neutral"],
    "text_affect6": ["calm", "warm", "energetic", "serious", "playful", "empathetic"],
    "style6": ["happy", "sad", "calm", "neutral", "encourage", "urgent"],
    "intent_family": [
        "info_retrieval",
        "decision_support",
        "planning",
        "transactional",
        "navigation",
        "communication",
        "content_generation",
        "tool_invocation",
        "safety",
        "history_lookup",
        "productivity",
        "shopping",
        "qa_general",
    ],
    "representation_choice": ["plain_text", "bullet_list", "comparison_table", "chart_spec", "document_spec", "zip_spec"],
    "continuity_choice": ["use_continuity", "suppress_continuity"],
    "flow_state": [
        "none",
        "awaiting_user_confirmation",
        "awaiting_user_choice",
        "awaiting_parameters",
        "ready_for_action",
    ],
    "safety_tag": [
        "safe",
        "politics_sensitive",
        "history_sensitive",
        "self_harm_sensitive",
        "violence_sensitive",
        "sexual_content",
        "minor_related",
        "location_sensitive",
        "leakage_attempt",
    ],
    "history_scope": ["thread_only", "all_threads"],
    "image_tool_action": ["web_fetch", "connector_action"],
    "adult_gate": [True, False],
    "profanity_allowed": [True, False],
    "needs_search": [True, False],
    "needs_history_search": [True, False],
    "connector_needed": [True, False],
    "deeplink_needed": [True, False],
}

BASE_REQUIRED_KEYS: list[str] = [
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
    "user_message",
    "assistant_response",
]

BASE_REQUIRED_LABEL_KEYS: list[str] = [
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
]

BASE_FORBIDDEN_USER_SUBSTRINGS: list[str] = [
    "tool_call",
    "use connector",
    "use deep link",
    "use deeplink",
    "use this tool",
]

ALLOWED_LABEL_KEYS: list[str] = sorted(
    {
        *BASE_REQUIRED_LABEL_KEYS,
        "text_affect6",
        "style6",
        "intent",
        "intent_family",
        "intent_subtype",
        "mode_label",
        "tool_budget",
        "connector_needed",
        "deeplink_needed",
        "connector_action",
        "deeplink_action",
        "image_tool_action",
        "image_context",
    }
)


def _base_contract() -> dict[str, object]:
    return {
        "required_keys": list(BASE_REQUIRED_KEYS),
        "required_label_keys": list(BASE_REQUIRED_LABEL_KEYS),
        "allowed_enums": copy.deepcopy(MASTER_ENUMS),
        "forbidden_user_substrings": list(BASE_FORBIDDEN_USER_SUBSTRINGS),
        "mapping_lane_rules": {},
        "integration_lane_rules": {},
    }


def _make_contract(
    required_keys: list[str] | None = None,
    required_label_keys: list[str] | None = None,
    required_label_keys_add: list[str] | None = None,
    allowed_enums: dict[str, list[str]] | None = None,
    forbidden_user_substrings: list[str] | None = None,
    forbidden_user_substrings_add: list[str] | None = None,
    mapping_lane_rules: dict[str, object] | None = None,
    integration_lane_rules: dict[str, object] | None = None,
) -> dict[str, object]:
    base = _base_contract()
    if required_keys is not None:
        base["required_keys"] = list(required_keys)
    if required_label_keys is not None:
        base["required_label_keys"] = list(required_label_keys)
    if required_label_keys_add:
        base["required_label_keys"] = list(base.get("required_label_keys", [])) + list(required_label_keys_add)
    if allowed_enums is not None:
        base["allowed_enums"] = copy.deepcopy(allowed_enums)
    if forbidden_user_substrings is not None:
        base["forbidden_user_substrings"] = list(forbidden_user_substrings)
    if forbidden_user_substrings_add:
        base["forbidden_user_substrings"] = list(base.get("forbidden_user_substrings", [])) + list(
            forbidden_user_substrings_add
        )
    if mapping_lane_rules:
        base["mapping_lane_rules"] = {**base.get("mapping_lane_rules", {}), **mapping_lane_rules}
    if integration_lane_rules:
        base["integration_lane_rules"] = {**base.get("integration_lane_rules", {}), **integration_lane_rules}
    return base


V16_LANE_CONTRACTS: dict[str, dict[str, object]] = {
    "default": _base_contract(),

    # Mapping lanes (action labels only; assistant_response empty; no tool_call/parameters)
    "lane_11_connector_action_mapping": _make_contract(
        required_label_keys_add=["connector_action"],
        mapping_lane_rules={
            "assistant_response_must_be_empty": True,
            "forbid_tool_call_field": True,
            "forbid_parameters_fields": True,
            "only_one_action_label": "connector_action",
        },
    ),
    "lane_12_deeplink_action_mapping": _make_contract(
        required_label_keys_add=["deeplink_action"],
        mapping_lane_rules={
            "assistant_response_must_be_empty": True,
            "forbid_tool_call_field": True,
            "forbid_parameters_fields": True,
            "only_one_action_label": "deeplink_action",
        },
    ),
    "lane_27_image_tooling": _make_contract(
        required_label_keys_add=["image_tool_action"],
        mapping_lane_rules={
            "assistant_response_must_be_empty": True,
            "forbid_tool_call_field": True,
            "forbid_parameters_fields": True,
            "only_one_action_label": "image_tool_action",
        },
    ),

    # Integration lanes (citations allowed where spec permits)
    "lane_08_search_integration": _make_contract(
        integration_lane_rules={
            "allow_citations_blocks": True,
            "allow_tool_call": False,
        }
    ),
    "lane_25_history_search_integration": _make_contract(
        integration_lane_rules={
            "allow_citations_blocks": True,
            "allow_tool_call": False,
        }
    ),

    "lane_10_connector_intent_detection": _make_contract(
        required_label_keys_add=["connector_needed"]
    ),

    # Intent detection lanes with deeplink label presence
    "lane_37_deeplink_intent_detection": _make_contract(
        required_label_keys_add=["deeplink_action"]
    ),
}

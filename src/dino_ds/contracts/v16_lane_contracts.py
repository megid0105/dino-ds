from __future__ import annotations

import copy

# Global enums pulled from the master v2 label spec (see MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md)
MASTER_ENUMS: dict[str, list[str]] = {
    # Master schema v2 language enum (locked list). Thai is handled via lane-scoped override
    # to satisfy v17 multilingual lane contracts while keeping master/global semantics explicit.
    "language": ["en", "zh-hk", "zh-hant", "zh-hans", "pt-br", "fr", "de", "it", "hi", "vi", "ja", "ko", "es"],
    "mode": ["quick", "think", "conversation"],
    "mode_label": ["quick", "think", "conversation"],
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
    "intent": [
        "qa_general",
        "planning",
        "rewrite",
        "translate",
        "grammar_fix",
        "code_help",
        "connector_action",
        "history_lookup",
        "image_explanation",
        "image_shopping",
        "navigation",
        "booking",
        "export_document",
        "ingest_content",
        "calc",
        "unit_convert",
        "timer",
    ],
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
    "messages",
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
        # Lane-scoped enum override for v17 multilingual distribution conflict:
        # th is required by v17 lanes/volume spec but missing from master v2 language enum.
        # This keeps master strictness intact and emits override warnings during validation.
        "enum_overrides": {"language": {"th"}},
        "fixed_values": {},
        "forbidden_user_substrings": list(BASE_FORBIDDEN_USER_SUBSTRINGS),
        "mapping_lane_rules": {},
        "integration_lane_rules": {},
        # Turn-structure defaults (single-turn):
        # non-system messages must be [user, assistant].
        "requires_multiturn": False,
        "allow_multiturn": False,
        "min_turn_pairs": 1,
        "min_messages": 2,
    }


def _make_contract(
    required_keys: list[str] | None = None,
    required_label_keys: list[str] | None = None,
    required_label_keys_add: list[str] | None = None,
    allowed_enums: dict[str, list[str]] | None = None,
    forbidden_user_substrings: list[str] | None = None,
    forbidden_user_substrings_add: list[str] | None = None,
    enum_overrides: dict[str, set[str]] | None = None,
    fixed_values: dict[str, object] | None = None,
    mapping_lane_rules: dict[str, object] | None = None,
    integration_lane_rules: dict[str, object] | None = None,
    user_assistant_overlap_max: float | None = None,
    user_assistant_overlap_metric: str | None = None,
    user_assistant_overlap_tokenizer: str | None = None,
    requires_multiturn: bool | None = None,
    allow_multiturn: bool | None = None,
    min_turn_pairs: int | None = None,
    min_messages: int | None = None,
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
    if enum_overrides:
        clean: dict[str, set[str]] = {}
        existing_overrides = base.get("enum_overrides")
        if isinstance(existing_overrides, dict):
            for field, vals in existing_overrides.items():
                if not isinstance(field, str):
                    continue
                if isinstance(vals, set):
                    clean[field] = {v for v in vals if isinstance(v, str)}
                elif isinstance(vals, (list, tuple)):
                    clean[field] = {v for v in vals if isinstance(v, str)}
        for field, vals in enum_overrides.items():
            if not isinstance(field, str):
                continue
            if isinstance(vals, set):
                clean.setdefault(field, set()).update(v for v in vals if isinstance(v, str))
            elif isinstance(vals, (list, tuple)):
                clean.setdefault(field, set()).update(v for v in vals if isinstance(v, str))
        base["enum_overrides"] = clean
    if isinstance(fixed_values, dict):
        clean_fixed: dict[str, object] = {}
        for field, expected in fixed_values.items():
            if isinstance(field, str) and field.strip():
                clean_fixed[field.strip()] = expected
        base["fixed_values"] = clean_fixed
    if mapping_lane_rules:
        base["mapping_lane_rules"] = {**base.get("mapping_lane_rules", {}), **mapping_lane_rules}
    if integration_lane_rules:
        base["integration_lane_rules"] = {**base.get("integration_lane_rules", {}), **integration_lane_rules}
    if isinstance(user_assistant_overlap_max, (int, float)) and not isinstance(user_assistant_overlap_max, bool):
        base["user_assistant_overlap_max"] = float(user_assistant_overlap_max)
    if isinstance(user_assistant_overlap_metric, str) and user_assistant_overlap_metric.strip():
        base["user_assistant_overlap_metric"] = user_assistant_overlap_metric.strip()
    if isinstance(user_assistant_overlap_tokenizer, str) and user_assistant_overlap_tokenizer.strip():
        base["user_assistant_overlap_tokenizer"] = user_assistant_overlap_tokenizer.strip()
    if isinstance(requires_multiturn, bool):
        base["requires_multiturn"] = requires_multiturn
    if isinstance(allow_multiturn, bool):
        base["allow_multiturn"] = allow_multiturn
    if isinstance(min_turn_pairs, int) and min_turn_pairs > 0:
        base["min_turn_pairs"] = min_turn_pairs
    if isinstance(min_messages, int) and min_messages > 0:
        base["min_messages"] = min_messages
    return base


V16_LANE_CONTRACTS: dict[str, dict[str, object]] = {
    "default": _base_contract(),

    # Lane 01: Identity & Self-Definition (v17 required schema constraints).
    "lane_01_identity": _make_contract(
        fixed_values={
            "mode": "quick",
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "continuity_choice": "suppress_continuity",
            "intent_family": {"safety", "content_generation"},
            "intent_subtype": {"identity_definition", "boundary_setting", "leakage_prevention"},
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    # Lane 02: Tone & Behaviour Foundation.
    "lane_02_tone_behaviour_foundation": _make_contract(
        fixed_values={
            "mode": {"quick", "think"},
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "continuity_choice": "suppress_continuity",
            "intent_family": {"content_generation", "safety"},
            "intent_subtype": {"tone_behavior", "boundary_setting", "correction_style"},
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),

    "lane_03_think_mode": _make_contract(
        # Lane 03 supports both single-turn and multi-turn examples in v17.
        # Keep multi-turn optional (not hard-required) for per-row invariants.
        requires_multiturn=False,
        allow_multiturn=True,
        min_turn_pairs=1,
        min_messages=2,
        fixed_values={
            "mode": "think",
            "emote6": "neutral",
            "representation_choice": {"plain_text", "bullet_list", "comparison_table", "chart_spec", "document_spec"},
            "continuity_choice": "suppress_continuity",
            "intent_family": {"decision_support", "planning", "content_generation"},
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_04_quick_mode": _make_contract(
        fixed_values={
            "mode": "quick",
            "emote6": "neutral",
            "representation_choice": {"plain_text", "bullet_list"},
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),

    # Multi-turn lanes (hard invariant by lane contract).
    "lane_05_conversation_mode": _make_contract(
        # Lane 05 multi-turn is enforced at slice level (>=60%), not per-row.
        requires_multiturn=False,
        allow_multiturn=True,
        min_turn_pairs=1,
        min_messages=2,
        fixed_values={
            "mode": "conversation",
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "continuity_choice": "suppress_continuity",
            "intent_family": {"content_generation", "safety"},
            "intent_subtype": {"emotional_support", "light_chat", "check_in"},
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_09_multi_step_action_flow": _make_contract(
        # Lane 09 flow behavior is controlled by slice-level flow_state targets, not hard per-row multiturn.
        requires_multiturn=False,
        allow_multiturn=True,
        min_turn_pairs=1,
        min_messages=2,
        fixed_values={
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_06_general_intent_classification": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_07_search_triggering": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_08_search_integration": _make_contract(
        integration_lane_rules={
            "allow_citations_blocks": True,
            "allow_tool_call": True,
        },
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": True,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_10_connector_intent_detection": _make_contract(
        required_label_keys_add=["connector_needed"],
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),

    # Mapping lanes (action labels only; assistant_response empty; no tool_call/parameters)
    "lane_11_connector_action_mapping": _make_contract(
        required_label_keys_add=["connector_action"],
        mapping_lane_rules={
            "assistant_response_must_be_empty": True,
            "forbid_tool_call_field": True,
            "forbid_parameters_fields": True,
            "only_one_action_label": "connector_action",
        },
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
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
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
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
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),

    # Integration lanes (citations/tool use per lane contract)
    "lane_13_doc_export_spec": _make_contract(
        integration_lane_rules={
            "allow_tool_call": True,
        },
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "document_spec",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_14_zip_wrap_spec": _make_contract(
        integration_lane_rules={
            "allow_tool_call": True,
        },
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "zip_spec",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_15_code_generation": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "intent_family": "content_generation",
            "intent_subtype": "code_generation",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_16_code_json_spec_mode": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "intent_subtype": "code_json_spec",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_17_comparison_tables": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "comparison_table",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_18_chart_spec": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "representation_choice": "chart_spec",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_19_continuity_decision": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_20_continuity_execution": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_25_history_search_integration": _make_contract(
        integration_lane_rules={
            "allow_citations_blocks": True,
            "allow_tool_call": False,
        },
        fixed_values={
            "emote6": "neutral",
            "needs_search": False,
            "needs_history_search": True,
        },
    ),
    # Transform lanes user<->assistant overlap constraints from full_dataset_spec_v17:
    # - lane 21 rewrite: <= 0.70
    # - lane 22 translate: <= 0.20
    # - lane 23 grammar_fix: <= 0.80
    "lane_21_rewrite": _make_contract(
        user_assistant_overlap_max=0.70,
        user_assistant_overlap_metric="O_min",
        user_assistant_overlap_tokenizer="script_aware_v17",
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "intent_family": "content_generation",
            "intent_subtype": "rewrite",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_22_translate": _make_contract(
        user_assistant_overlap_max=0.20,
        user_assistant_overlap_metric="O_min",
        user_assistant_overlap_tokenizer="script_aware_v17",
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "intent_family": "content_generation",
            "intent_subtype": "translate",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_23_grammar_fix": _make_contract(
        user_assistant_overlap_max=0.80,
        user_assistant_overlap_metric="O_min",
        user_assistant_overlap_tokenizer="script_aware_v17",
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "intent_family": "content_generation",
            "intent_subtype": "grammar_fix",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_24_history_search_trigger": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
        },
    ),
    "lane_26_image_context_understanding": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_28_emote6_labeling": _make_contract(
        fixed_values={
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),

    "lane_29_safety_history_politics": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "intent_family": "safety",
            "intent_subtype": {"history_accuracy", "politics_accuracy"},
            "safety_tag": {"politics_sensitive", "history_sensitive"},
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_30_safety_no_leakage": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "intent_family": "safety",
            "intent_subtype": "leakage_prevention",
            "safety_tag": "leakage_attempt",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_31_mode_selection": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_32_representation_choice": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_33_fallback_behavior": _make_contract(
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
    "lane_34_cantonese_ability": _make_contract(
        enum_overrides={
            "tone": {"neutral", "professional"},
            "history_scope": {"none"},
        },
        fixed_values={
            "language": "zh-hk",
            "mode": {"conversation", "quick"},
            "emote6": "neutral",
            "representation_choice": "plain_text",
            "continuity_choice": "suppress_continuity",
            "intent_family": "qa_general",
            "intent_subtype": "general",
            "safety_tag": "safe",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "none",
            "tone": {"neutral", "professional"},
        },
    ),
    "lane_35_topic_hygiene": _make_contract(
        enum_overrides={
            "intent_family": {"hygiene"},
        },
        fixed_values={
            "intent_family": "hygiene",
            "intent_subtype": {"stay_on_topic", "scope_control", "return_to_goal", "gentle_boundary"},
        },
    ),
    # Intent detection lane with deeplink label presence.
    "lane_37_deeplink_intent_detection": _make_contract(
        required_label_keys_add=["deeplink_needed"],
        fixed_values={
            "emote6": "neutral",
            "continuity_choice": "suppress_continuity",
            "needs_search": False,
            "needs_history_search": False,
            "history_scope": "thread_only",
        },
    ),
}


def contract_for_lane(lane_id: str) -> dict[str, object]:
    if lane_id in V16_LANE_CONTRACTS:
        return V16_LANE_CONTRACTS[lane_id]
    return V16_LANE_CONTRACTS.get("default", {})

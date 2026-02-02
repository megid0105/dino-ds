# Lane 06 Exception (Intent Classification Coupling)

Lane 06 uses a shuffle_cap source JSONL instead of template_expand.

Reason: template_expand in this repo does not support dict-coupled sampling, so
intent labels (intent_family / intent_subtype / needs_search / needs_history_search
/ history_scope / safety_tag / mode / continuity_choice) can drift away from the
user message. For lane 06, that drift breaks the intent classification objective.

This exception keeps strict coupling by prebuilding rows in:
`lanes/lane_06_general_intent_classification/sources/intent_cases.jsonl`

Multi-turn is encoded inside user_message as plain text (User/Assistant/User),
so no role schema is used in lane data.

No other lanes should follow this pattern unless explicitly approved.

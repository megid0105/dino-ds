from __future__ import annotations

from typing import Any


def validate_enum(
    field_name: str,
    value: Any,
    *,
    lane_id: str,
    master_allowed_set: set[Any],
    lane_override_set: set[Any],
) -> tuple[bool, str | None, str | None]:
    del field_name
    del lane_id

    if value in master_allowed_set:
        return True, None, None
    if value in lane_override_set:
        return True, "lane_enum_override_used", None
    return False, None, "enum_value_not_allowed"

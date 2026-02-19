from __future__ import annotations

from dataclasses import dataclass
import re


_LANE_ID_RE = re.compile(r"^lane_(\d+)")


@dataclass(frozen=True)
class LanePolicy:
    # Tool-call contract
    requires_tool_call: bool = False
    allows_tool_call: bool = False

    # Citation contract
    requires_citations: bool = False
    forbids_citations: bool = False

    # Output-shape contract
    assistant_response_must_be_empty: bool = False
    assistant_response_must_be_code_only: bool = False


_DEFAULT_POLICY = LanePolicy()


# Step-1 lane policy table from full_dataset_spec_v17.
# Keep this minimal and lane-scoped to avoid accidental over-gating.
_LANE_POLICIES: dict[int, LanePolicy] = {
    # Lane 03: think mode (tool_call optional in limited share)
    3: LanePolicy(
        requires_tool_call=False,
        allows_tool_call=True,
    ),
    # Lane 04: quick mode (tool_call optional in limited share)
    4: LanePolicy(
        requires_tool_call=False,
        allows_tool_call=True,
    ),
    # Lane 08: search integration
    8: LanePolicy(
        requires_tool_call=True,
        allows_tool_call=True,
        requires_citations=True,
    ),
    # Lane 13: doc export spec
    13: LanePolicy(
        requires_tool_call=True,
        allows_tool_call=True,
        assistant_response_must_be_empty=True,
    ),
    # Lane 14: zip wrap spec
    14: LanePolicy(
        requires_tool_call=True,
        allows_tool_call=True,
        assistant_response_must_be_empty=True,
    ),
    # Lane 15: code generation (code block only, tool_call forbidden)
    15: LanePolicy(
        requires_tool_call=False,
        allows_tool_call=False,
        assistant_response_must_be_code_only=True,
    ),
}


def lane_num_from_id(lane_id: str) -> int | None:
    m = _LANE_ID_RE.match(str(lane_id or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def get_lane_policy(lane_id: str) -> LanePolicy:
    lane_num = lane_num_from_id(lane_id)
    if lane_num is None:
        return _DEFAULT_POLICY
    return _LANE_POLICIES.get(lane_num, _DEFAULT_POLICY)


def has_lane_policy(lane_id: str) -> bool:
    lane_num = lane_num_from_id(lane_id)
    if lane_num is None:
        return False
    return lane_num in _LANE_POLICIES

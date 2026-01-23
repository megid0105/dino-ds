from __future__ import annotations
from pathlib import Path

SCHEMAS_DIR = Path(__file__).parent / "schemas"

LANE_SCHEMA_V1 = SCHEMAS_DIR / "lane_schema.v1.json"
SOURCES_MANIFEST_V1 = SCHEMAS_DIR / "sources_manifest.v1.json"
TOOL_REPLAY_MANIFEST_V1 = SCHEMAS_DIR / "tool_replay_manifest.v1.json"

PCT_LABEL_STANDARD_SAMPLE_V1 = SCHEMAS_DIR / "pct_label_standard_sample.v1.json"

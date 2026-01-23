from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from .. import exit_codes as ec
from ..schema_store import (
    LANE_SCHEMA_V1,
    SOURCES_MANIFEST_V1,
    TOOL_REPLAY_MANIFEST_V1,
)
from ..utils import load_json, load_yaml


def _pick_schema(schema_name: str) -> Path:
    name = schema_name.strip().lower()
    if name in ("lane", "lane_v1", "lane_schema"):
        return LANE_SCHEMA_V1
    if name in ("sources", "sources_manifest", "sources_manifest_v1"):
        return SOURCES_MANIFEST_V1
    if name in ("fixtures", "tool_replay", "tool_replay_manifest", "tool_replay_manifest_v1"):
        return TOOL_REPLAY_MANIFEST_V1
    raise ValueError(f"Unknown schema '{schema_name}'")


def _load_doc(config_path: Path, schema_path: Path) -> Any:
    # lane is YAML; manifests are JSON
    if schema_path == LANE_SCHEMA_V1:
        return load_yaml(config_path)
    return load_json(config_path)


def run(config: str, schema: str) -> int:
    try:
        config_path = Path(config).expanduser().resolve()
        schema_path = _pick_schema(schema)
        schema_obj = load_json(schema_path)
        doc = _load_doc(config_path, schema_path)
        jsonschema.validate(instance=doc, schema=schema_obj)
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except jsonschema.ValidationError:
        return ec.SCHEMA_VALIDATION_FAILED
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR

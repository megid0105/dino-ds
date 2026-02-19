from __future__ import annotations

import sys
import os

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


_LAST_ERROR_DETAILS: dict[str, Any] | None = None


def get_last_error_details() -> dict[str, Any] | None:
    blob = _LAST_ERROR_DETAILS
    if not isinstance(blob, dict):
        return None
    return dict(blob)


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


# --- lane semantic validators (B4 + teacher_runtime) ---

def _err(msg: str) -> str:
    return msg


def _validate_language_mix_semantics(lane: dict) -> str | None:
    lm = lane.get("language_mix")
    lm = lm if isinstance(lm, dict) else {}
    enabled = bool(lm.get("enabled", False))
    if not enabled:
        return None

    langs = lm.get("languages")
    if not isinstance(langs, list) or len(langs) < 2 or any((not isinstance(x, str) or not x.strip()) for x in langs):
        return _err("language_mix.enabled=true requires language_mix.languages (>=2 non-empty strings)")

    tby = lm.get("templates_by_lang")
    if not isinstance(tby, dict) or not tby:
        return _err("language_mix.enabled=true requires language_mix.templates_by_lang (non-empty map)")

    for lang in langs:
        if lang not in tby:
            return _err(f"language_mix.templates_by_lang missing key for language: {lang}")
        v = tby.get(lang)
        if v is None:
            return _err(f"language_mix.templates_by_lang[{lang}] must be non-empty")
        # Accept list[str] or list[dict] depending on lane style; just ensure non-empty.
        if isinstance(v, list):
            if len(v) == 0:
                return _err(f"language_mix.templates_by_lang[{lang}] must be non-empty")
            for item in v:
                if isinstance(item, str) and not item.strip():
                    return _err(f"language_mix.templates_by_lang[{lang}] contains empty template")
                if isinstance(item, dict) and len(item.keys()) == 0:
                    return _err(f"language_mix.templates_by_lang[{lang}] contains empty template object")
        else:
            return _err(f"language_mix.templates_by_lang[{lang}] must be a list")

    return None


def _validate_teacher_runtime_semantics(lane: dict) -> str | None:
    tr = lane.get("teacher_runtime")
    tr = tr if isinstance(tr, dict) else {}

    gm = lane.get("generation_mode")
    gm = gm.strip() if isinstance(gm, str) else ""

    enabled = bool(tr.get("enabled", False)) or (gm == "teacher_runtime")
    if not enabled:
        return None

    provider = tr.get("provider")
    provider = provider.strip() if isinstance(provider, str) else "ollama"
    if provider != "ollama":
        return _err(f"teacher_runtime.provider must be 'ollama' (got: {provider})")

    model = tr.get("model")
    model = model.strip() if isinstance(model, str) else ""
    if not model:
        return _err("teacher_runtime.model must be a non-empty string")

    policy = tr.get("policy")
    policy = policy.strip() if isinstance(policy, str) else "structure_only"
    if policy not in ("structure_only", "grounded_requires_evidence"):
        return _err(
            f"teacher_runtime.policy must be one of [structure_only, grounded_requires_evidence] (got: {policy})"
        )

    ome = tr.get("on_missing_evidence")
    ome = ome.strip() if isinstance(ome, str) else "abstain"
    if ome not in ("abstain", "fail"):
        return _err(f"teacher_runtime.on_missing_evidence must be one of [abstain, fail] (got: {ome})")

    sp_path = tr.get("system_prompt_path")
    if isinstance(sp_path, str) and sp_path.strip():
        p = os.path.expanduser(sp_path.strip())
        if not os.path.isfile(p):
            return _err(f"teacher_runtime.system_prompt_path not found: {sp_path.strip()}")

    return None


def _validate_lane_semantics(doc: Any) -> str | None:
    if not isinstance(doc, dict):
        return _err("lane config must be a YAML mapping/object")

    lm_err = _validate_language_mix_semantics(doc)
    if lm_err:
        return lm_err

    tr_err = _validate_teacher_runtime_semantics(doc)
    if tr_err:
        return tr_err

    return None


def run(config: str, schema: str) -> int:
    global _LAST_ERROR_DETAILS
    _LAST_ERROR_DETAILS = None
    try:
        config_path = Path(config).expanduser().resolve()
        schema_path = _pick_schema(schema)
        schema_obj = load_json(schema_path)
        doc = _load_doc(config_path, schema_path)
        jsonschema.validate(instance=doc, schema=schema_obj)
        if schema_path == LANE_SCHEMA_V1:
            sem_err = _validate_lane_semantics(doc)
            if sem_err:
                _LAST_ERROR_DETAILS = {
                    "kind": "config_invalid",
                    "stage": "lane_semantics",
                    "message": str(sem_err),
                    "config_path": str(config_path),
                    "schema_name": str(schema),
                    "schema_path": str(schema_path),
                }
                print(f"CONFIG_INVALID: {sem_err}", file=sys.stderr)
                return ec.CONFIG_INVALID
        return ec.SUCCESS
    except FileNotFoundError as e:
        _LAST_ERROR_DETAILS = {
            "kind": "io_error",
            "stage": "file_read",
            "message": str(e),
            "config_path": str(config),
            "schema_name": str(schema),
        }
        print(f"IO_ERROR: {e}", file=sys.stderr)
        return ec.IO_ERROR
    except jsonschema.ValidationError as e:
        # Print a concise, deterministic error report for teammates.
        # Keep it short (no full instance dumps) but actionable.
        loc = "/".join([str(p) for p in list(getattr(e, "absolute_path", []))])
        sch = "/".join([str(p) for p in list(getattr(e, "absolute_schema_path", []))])
        msg = getattr(e, "message", str(e))
        validator = getattr(e, "validator", "")
        _LAST_ERROR_DETAILS = {
            "kind": "schema_validation_failed",
            "stage": "schema",
            "message": str(msg),
            "instance_path": loc or "<root>",
            "schema_path": sch or "<unknown>",
            "validator": str(validator),
            "config_path": str(config),
            "schema_name": str(schema),
        }
        print(
            "SCHEMA_VALIDATION_FAILED:\n"
            f"  message: {msg}\n"
            f"  instance_path: {loc or '<root>'}\n"
            f"  schema_path: {sch or '<unknown>'}\n"
            f"  validator: {validator}\n",
            file=sys.stderr,
        )
        return ec.SCHEMA_VALIDATION_FAILED
    except ValueError as e:
        _LAST_ERROR_DETAILS = {
            "kind": "config_invalid",
            "stage": "config",
            "message": str(e),
            "config_path": str(config),
            "schema_name": str(schema),
        }
        print(f"CONFIG_INVALID: {e}", file=sys.stderr)
        return ec.CONFIG_INVALID
    except Exception as e:
        _LAST_ERROR_DETAILS = {
            "kind": "internal_error",
            "stage": "validator",
            "message": str(e),
            "config_path": str(config),
            "schema_name": str(schema),
        }
        print(f"INTERNAL_ERROR: {e}", file=sys.stderr)
        return ec.INTERNAL_ERROR

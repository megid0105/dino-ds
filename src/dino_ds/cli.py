from __future__ import annotations

import argparse
import sys
import json
import traceback
from pathlib import Path
import re
import os
import uuid
from datetime import datetime, timezone

import hashlib
import subprocess
import zipfile

import yaml

from . import __version__
from . import exit_codes as ec

from .commands import validate_cmd, lint_cmd, sources_cmd, fixtures_cmd
from .commands import build_cmd, split_cmd, pack_cmd, golden_cmd, stubs
from .contracts.v16_lane_contracts import ALLOWED_LABEL_KEYS
from .validators.generation_validator import resolve_rule_profile
from .validators.qc_report_writer_v17 import QC_REPORT_DIRNAME, QC_REPORT_DIR_ENV, write_qc_report


_CONTEXT_RE = re.compile(r"\bcontext\b|conversation so far|conversation:", re.IGNORECASE)
_MULTI_TURN_PREFIX = ("user", "assistant", "user", "assistant")
_SECOND_USER_KEYS = (
    "u2",
    "u2_followup",
    "user_message_2",
    "second_user_message",
    "followup_user_message",
)
_SECOND_ASSISTANT_KEYS = (
    "a2",
    "a2_followup",
    "assistant_response_2",
    "second_assistant_response",
    "followup_assistant_response",
)
_VALIDATOR_CONFIG_GLOB = "DinoDS_full_validator_config_*.md"
_HELP_SPEC_ALLOWED_LANES: set[int] = set(range(1, 36)) | {37}
_HELP_SPEC_FILENAME_RE = re.compile(r"^DinoDS_full_validator_config_(\d{4}-\d{2}-\d{2})\.md$")
_TOOL_CONFIG_ENV = "DINO_DS_TOOL_CONFIG_PATH"
_TOOL_CONFIG_DEFAULT = Path.home() / ".dino_ds" / "tool_config.json"
_VALIDATOR_LEVEL_KEY = "validator_level"
_QC_REPORT_DIR_KEY = "qc_report_dir"
_LANE_OUTPUT_DIR_GLOBAL_KEY = "lane_output_dir_global"
_LANE_OUTPUT_DIR_LANES_KEY = "lane_output_dir_lanes"
_LANE_OUTPUT_DIR_LEGACY_KEY = "lane_output_dir"
_LANE_OUTPUT_DIR_ENV = "DINO_DS_LANE_OUTPUT_DIR"

_RULE_HELP_TEXT = (
    "Validation profile: 01=baseline (legacy checks), "
    "02=strict (v17 lane rules), "
    "03=strict+dataset duplicate checks. "
    "If --rule is omitted, CLI uses saved default from `validator_level_set`, else falls back to 03. "
    "Mode/tone slice checks run only for lanes with explicit spec percentage targets; "
    "per-language slice needs n>=30. Deviation bands: <=15%% PASS, >15%%-20%% WARN, >=21%% FAIL. "
    "Spec slice caps also run where required (lane03 tool<=10%% image<=5%%, lane04 tool<=5%% image<=3%% + len shares, "
    "lane05 image<=2%% + multiturn/emotional shares, lane07 borderline>=40%% + needs_search~50/50, lane10 borderline>=40%%, "
    "lane09 flow_state distribution, lane20 prior-reference>=60%%, lane28 emote6>=10%% each, lane29 correction>=40%%, "
    "lane30 creative-extraction>=40%%, lane33 fallback-limitation>=40%%, lane34 colloquial/code-switch shares). "
    "Lane11/12 action-mapping rows require canonical connector_action/deeplink_action labels from master schema."
)


def _validator_level_desc(level: int) -> str:
    if level == 1:
        return "baseline (legacy checks)"
    if level == 2:
        return "strict (v17 lane rules)"
    return "strict+dataset duplicate checks"


def _tool_config_path() -> Path:
    env_path = str(os.environ.get(_TOOL_CONFIG_ENV, "")).strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    return _TOOL_CONFIG_DEFAULT.expanduser().resolve()


def _normalize_abs_dir(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    return str(p)


def _load_tool_config() -> tuple[dict[str, object], str | None]:
    path = _tool_config_path()
    if not path.exists():
        return {}, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {}, f"failed_to_parse:{e}"
    if not isinstance(raw, dict):
        return {}, "invalid_format:not_json_object"
    out: dict[str, object] = {}
    for k, v in raw.items():
        if isinstance(k, str):
            out[k] = v
    return out, None


def _save_tool_config(doc: dict[str, object]) -> Path:
    path = _tool_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _resolve_lane_token(token: str) -> tuple[str | None, str | None]:
    raw = str(token or "").strip()
    if not raw:
        return None, "lane token is empty"
    lanes_root = Path.cwd() / "lanes"
    if lanes_root.exists() and lanes_root.is_dir():
        direct = lanes_root / raw
        if direct.exists() and direct.is_dir():
            return raw, None

    m = re.match(r"^lane_(\d{1,2})(?:\b|_)", raw.lower())
    if not m and raw.isdigit():
        m = re.match(r"^(\d{1,2})$", raw)
    if not m:
        return None, f"invalid lane token '{raw}'"

    lane_num = int(m.group(1))
    prefix = f"lane_{lane_num:02d}_"
    if lanes_root.exists() and lanes_root.is_dir():
        matches = sorted([p.name for p in lanes_root.glob(f"{prefix}*") if p.is_dir()])
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, f"ambiguous lane token '{raw}': {', '.join(matches)}"
    # Fallback when lanes/ is unavailable.
    return f"lane_{lane_num:02d}", None


def _is_wrapped_package_mode(cwd: Path | None = None) -> bool:
    base = cwd or Path.cwd()
    return (base / "dino-ds-bin").is_file() and (base / "lanes").is_dir()


def _default_lane_output_hint(lane_id: str | None = None, *, cwd: Path | None = None) -> str:
    base = cwd or Path.cwd()
    if _is_wrapped_package_mode(base):
        if lane_id:
            return str((base / "out_runs" / lane_id).resolve())
        return "<package_root>/out_runs/<lane_id>"
    return "<lane_config_dir>/out (or lane YAML output_dir)"


def _lane_output_lanes_map(cfg: dict[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    blob = cfg.get(_LANE_OUTPUT_DIR_LANES_KEY)
    if not isinstance(blob, dict):
        return out
    for k, v in blob.items():
        if not isinstance(k, str):
            continue
        norm = _normalize_abs_dir(v if isinstance(v, str) else None)
        if norm:
            out[k] = norm
    return out


def _lane_output_global(cfg: dict[str, object]) -> str | None:
    # New key first, then legacy compatibility key.
    val = cfg.get(_LANE_OUTPUT_DIR_GLOBAL_KEY)
    if val is None:
        val = cfg.get(_LANE_OUTPUT_DIR_LEGACY_KEY)
    return _normalize_abs_dir(val if isinstance(val, str) else None)


def _set_lane_output_global(path_raw: str) -> int:
    normalized = _normalize_abs_dir(path_raw)
    if normalized is None:
        print(f"ERROR: invalid output dir path '{path_raw}'.", file=sys.stderr)
        return ec.CONFIG_INVALID
    cfg, err = _load_tool_config()
    if err is not None:
        print(
            f"WARN: existing tool config could not be parsed ({err}); it will be replaced.",
            file=sys.stderr,
        )
        cfg = {}
    cfg[_LANE_OUTPUT_DIR_GLOBAL_KEY] = normalized
    cfg.pop(_LANE_OUTPUT_DIR_LEGACY_KEY, None)
    cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path = _save_tool_config(cfg)
    print(f"output_dir (all lanes) set: {normalized}")
    print(f"config: {path}")
    return ec.SUCCESS


def _set_lane_output_for_lane(lane_token: str, path_raw: str) -> int:
    lane_id, err_lane = _resolve_lane_token(lane_token)
    if err_lane is not None or lane_id is None:
        print(f"ERROR: {err_lane}", file=sys.stderr)
        return ec.CONFIG_INVALID
    normalized = _normalize_abs_dir(path_raw)
    if normalized is None:
        print(f"ERROR: invalid output dir path '{path_raw}'.", file=sys.stderr)
        return ec.CONFIG_INVALID
    cfg, err = _load_tool_config()
    if err is not None:
        print(
            f"WARN: existing tool config could not be parsed ({err}); it will be replaced.",
            file=sys.stderr,
        )
        cfg = {}
    lanes_map = _lane_output_lanes_map(cfg)
    lanes_map[lane_id] = normalized
    cfg[_LANE_OUTPUT_DIR_LANES_KEY] = lanes_map
    cfg.pop(_LANE_OUTPUT_DIR_LEGACY_KEY, None)
    cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path = _save_tool_config(cfg)
    print(f"output_dir ({lane_id}) set: {normalized}")
    print(f"config: {path}")
    return ec.SUCCESS


def _effective_lane_output_dir(lane_id: str) -> tuple[str | None, str]:
    env_global = _normalize_abs_dir(str(os.environ.get(_LANE_OUTPUT_DIR_ENV, "")))
    if env_global:
        return str((Path(env_global) / lane_id).resolve()), "env_global"

    cfg, _ = _load_tool_config()
    if isinstance(cfg, dict):
        lanes_map = _lane_output_lanes_map(cfg)
        lane_specific = lanes_map.get(lane_id)
        if lane_specific:
            return lane_specific, "tool_config_lane"
        global_dir = _lane_output_global(cfg)
        if global_dir:
            return str((Path(global_dir) / lane_id).resolve()), "tool_config_global"
    return None, "default"


def _set_tool_config_path_value(key: str, raw_path: str, label: str) -> int:
    normalized = _normalize_abs_dir(raw_path)
    if normalized is None:
        print(f"ERROR: invalid {label} path '{raw_path}'.", file=sys.stderr)
        return ec.CONFIG_INVALID
    cfg, err = _load_tool_config()
    if err is not None:
        print(
            f"WARN: existing tool config could not be parsed ({err}); it will be replaced.",
            file=sys.stderr,
        )
        cfg = {}
    cfg[key] = normalized
    cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path = _save_tool_config(cfg)
    print(f"{label} set: {normalized}")
    print(f"config: {path}")
    return ec.SUCCESS


def _apply_persisted_path_overrides() -> None:
    cfg, _ = _load_tool_config()
    if not isinstance(cfg, dict):
        return
    if not str(os.environ.get(QC_REPORT_DIR_ENV, "")).strip():
        qdir = _normalize_abs_dir(str(cfg.get(_QC_REPORT_DIR_KEY) or ""))
        if qdir:
            os.environ[QC_REPORT_DIR_ENV] = qdir


def set_qc_report_dir(path_raw: str) -> int:
    return _set_tool_config_path_value(_QC_REPORT_DIR_KEY, path_raw, "qc_report_dir")


def set_output_dir(arg1: str, arg2: str | None = None) -> int:
    if arg2 is None:
        return _set_lane_output_global(path_raw=arg1)
    return _set_lane_output_for_lane(lane_token=arg1, path_raw=arg2)


def _normalize_validator_level(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        level = resolve_rule_profile(s)
    except Exception:
        return None
    return f"{level:02d}"


def _effective_validator_level(explicit_rule: str | None) -> tuple[str, str]:
    if explicit_rule is not None and str(explicit_rule).strip():
        normalized = _normalize_validator_level(str(explicit_rule))
        if normalized is None:
            raise ValueError(f"invalid --rule value '{explicit_rule}'. Use one of: 01, 02, 03")
        return normalized, "cli"

    cfg, _ = _load_tool_config()
    configured = _normalize_validator_level(str(cfg.get(_VALIDATOR_LEVEL_KEY) or ""))
    if configured is not None:
        return configured, "tool_config"
    return "03", "default"


def set_validator_level(level_raw: str) -> int:
    normalized = _normalize_validator_level(level_raw)
    if normalized is None:
        print(f"ERROR: invalid level '{level_raw}'. Use one of: 01, 02, 03.", file=sys.stderr)
        return ec.CONFIG_INVALID

    cfg, err = _load_tool_config()
    if err is not None:
        print(
            f"WARN: existing tool config could not be parsed ({err}); it will be replaced.",
            file=sys.stderr,
        )
        cfg = {}
    cfg[_VALIDATOR_LEVEL_KEY] = normalized
    cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path = _save_tool_config(cfg)

    lvl_int = int(normalized)
    print(f"validator_level set: {normalized}")
    print(f"profile: {_validator_level_desc(lvl_int)}")
    print(f"config: {path}")
    return ec.SUCCESS


def validator_level_check() -> int:
    cfg, err = _load_tool_config()
    path = _tool_config_path()
    raw_value = cfg.get(_VALIDATOR_LEVEL_KEY)
    normalized = _normalize_validator_level(str(raw_value) if raw_value is not None else None)
    if normalized is None:
        active = "03"
        source = "default"
    else:
        active = normalized
        source = "tool_config"

    lvl_int = int(active)
    print(f"active_validator_level: {active}")
    print(f"profile: {_validator_level_desc(lvl_int)}")
    print(f"source: {source}")
    print(f"config: {path}")
    if err is not None:
        print(f"config_status: {err}")
    elif raw_value is not None and normalized is None:
        print(f"config_status: invalid_validator_level:{raw_value}")
    else:
        print("config_status: ok")
    return ec.SUCCESS


def validator_level_reset() -> int:
    path = _tool_config_path()
    cfg, err = _load_tool_config()
    if err is not None:
        # Broken config should not block reset; remove file if present.
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"ERROR: failed to reset validator level: {e}", file=sys.stderr)
            return ec.IO_ERROR
        print("validator_level reset: 03 (default)")
        print("source: default")
        print(f"config: {path}")
        return ec.SUCCESS

    if _VALIDATOR_LEVEL_KEY in cfg:
        del cfg[_VALIDATOR_LEVEL_KEY]

    # Preserve other settings when present; otherwise remove config file.
    keep_cfg = {k: v for k, v in cfg.items() if k != "updated_at"}
    try:
        if keep_cfg:
            cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            _save_tool_config(cfg)
        elif path.exists():
            path.unlink()
    except Exception as e:
        print(f"ERROR: failed to reset validator level: {e}", file=sys.stderr)
        return ec.IO_ERROR

    print("validator_level reset: 03 (default)")
    print("source: default")
    print(f"config: {path}")
    return ec.SUCCESS


def qc_report_dir_check() -> int:
    cfg, err = _load_tool_config()
    path = _tool_config_path()
    env_qc = _normalize_abs_dir(str(os.environ.get(QC_REPORT_DIR_ENV, "")))
    cfg_qc = _normalize_abs_dir(str(cfg.get(_QC_REPORT_DIR_KEY) or "")) if isinstance(cfg, dict) else None
    if env_qc:
        qc_active = env_qc
        qc_source = "env"
    elif cfg_qc:
        qc_active = cfg_qc
        qc_source = "tool_config"
    else:
        qc_active = str((Path.cwd() / QC_REPORT_DIRNAME).resolve())
        qc_source = "default"
    print("qc_report_dir:")
    print(f"- active: {qc_active}")
    print(f"  source: {qc_source}")
    print(f"tool_config: {path}")
    if err is not None:
        print(f"config_status: {err}")
    else:
        print("config_status: ok")
    return ec.SUCCESS


def qc_report_dir_reset() -> int:
    path = _tool_config_path()
    cfg, err = _load_tool_config()
    if err is not None:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"ERROR: failed to reset qc_report_dir: {e}", file=sys.stderr)
            return ec.IO_ERROR
        print("qc_report_dir reset to default.")
        print(f"- default: {(Path.cwd() / QC_REPORT_DIRNAME).resolve()}")
        return ec.SUCCESS

    if isinstance(cfg, dict):
        cfg.pop(_QC_REPORT_DIR_KEY, None)
        keep_cfg = {k: v for k, v in cfg.items() if k != "updated_at"}
        try:
            if keep_cfg:
                cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                _save_tool_config(cfg)
            elif path.exists():
                path.unlink()
        except Exception as e:
            print(f"ERROR: failed to reset qc_report_dir: {e}", file=sys.stderr)
            return ec.IO_ERROR

    print("qc_report_dir reset to default.")
    print(f"- default: {(Path.cwd() / QC_REPORT_DIRNAME).resolve()}")
    print(f"tool_config: {path}")
    return ec.SUCCESS


def output_dir_check(lane: str | None = None) -> int:
    cfg, err = _load_tool_config()
    path = _tool_config_path()
    env_lane = _normalize_abs_dir(str(os.environ.get(_LANE_OUTPUT_DIR_ENV, "")))
    global_dir = _lane_output_global(cfg) if isinstance(cfg, dict) else None
    lanes_map = _lane_output_lanes_map(cfg) if isinstance(cfg, dict) else {}

    if lane is not None and str(lane).strip():
        lane_id, lane_err = _resolve_lane_token(str(lane))
        if lane_err is not None or lane_id is None:
            print(f"ERROR: {lane_err}", file=sys.stderr)
            return ec.CONFIG_INVALID
        effective, source = _effective_lane_output_dir(lane_id)
        if not effective:
            effective = _default_lane_output_hint(lane_id)
        print("lane_output_dir:")
        print(f"- lane: {lane_id}")
        print(f"- active: {effective}")
        print(f"  source: {source}")
        print(f"tool_config: {path}")
        if err is not None:
            print(f"config_status: {err}")
        else:
            print("config_status: ok")
        return ec.SUCCESS

    print("lane_output_dir settings:")
    if env_lane:
        print(f"- env_global: {env_lane} (effective lanes: <env_global>/<lane_id>)")
    else:
        print("- env_global: <not set>")
    if global_dir:
        print(f"- global_all_lanes: {global_dir} (effective lanes: <global>/<lane_id>)")
    else:
        print("- global_all_lanes: <not set>")
    if lanes_map:
        print("- per_lane_overrides:")
        for lid in sorted(lanes_map.keys()):
            print(f"  - {lid}: {lanes_map[lid]}")
    else:
        print("- per_lane_overrides: <none>")
    print(f"- default_when_unset: {_default_lane_output_hint(None)}")
    print(f"tool_config: {path}")
    if err is not None:
        print(f"config_status: {err}")
    else:
        print("config_status: ok")
    return ec.SUCCESS


def reset_output_dir(lane: str | None = None) -> int:
    path = _tool_config_path()
    cfg, err = _load_tool_config()
    if err is not None:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"ERROR: failed to reset output_dir: {e}", file=sys.stderr)
            return ec.IO_ERROR
        print("output_dir reset to defaults.")
        print(f"- default_when_unset: {_default_lane_output_hint(None)}")
        return ec.SUCCESS

    if not isinstance(cfg, dict):
        cfg = {}

    lanes_map = _lane_output_lanes_map(cfg)
    if lane is not None and str(lane).strip():
        lane_id, lane_err = _resolve_lane_token(str(lane))
        if lane_err is not None or lane_id is None:
            print(f"ERROR: {lane_err}", file=sys.stderr)
            return ec.CONFIG_INVALID
        if lane_id in lanes_map:
            del lanes_map[lane_id]
        cfg[_LANE_OUTPUT_DIR_LANES_KEY] = lanes_map
        cfg.pop(_LANE_OUTPUT_DIR_LEGACY_KEY, None)
        keep_cfg = {k: v for k, v in cfg.items() if k != "updated_at" and not (k == _LANE_OUTPUT_DIR_LANES_KEY and not lanes_map)}
        if not lanes_map and _LANE_OUTPUT_DIR_LANES_KEY in cfg:
            del cfg[_LANE_OUTPUT_DIR_LANES_KEY]
        try:
            if keep_cfg:
                cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                _save_tool_config(cfg)
            elif path.exists():
                path.unlink()
        except Exception as e:
            print(f"ERROR: failed to reset output_dir for lane: {e}", file=sys.stderr)
            return ec.IO_ERROR
        print(f"output_dir reset for lane: {lane_id}")
        print(f"- fallback: global setting or default {_default_lane_output_hint(lane_id)}")
        print(f"tool_config: {path}")
        return ec.SUCCESS

    cfg.pop(_LANE_OUTPUT_DIR_GLOBAL_KEY, None)
    cfg.pop(_LANE_OUTPUT_DIR_LEGACY_KEY, None)
    cfg.pop(_LANE_OUTPUT_DIR_LANES_KEY, None)
    keep_cfg = {k: v for k, v in cfg.items() if k != "updated_at"}
    try:
        if keep_cfg:
            cfg["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            _save_tool_config(cfg)
        elif path.exists():
            path.unlink()
    except Exception as e:
        print(f"ERROR: failed to reset output_dir: {e}", file=sys.stderr)
        return ec.IO_ERROR

    print("output_dir reset for all lanes.")
    print(f"- default_when_unset: {_default_lane_output_hint(None)}")
    print(f"tool_config: {path}")
    return ec.SUCCESS


def help_validator() -> int:
    print("# Validator Help")
    print("- Purpose: control default validator strictness used by `build lane` and `gate lane`.")
    print("- Levels:")
    print("  - `01`: baseline (legacy checks)")
    print("  - `02`: strict (v17 lane rules)")
    print("  - `03`: strict + dataset duplicate checks")
    print("- Commands:")
    print("  - `dino-ds validator_level_set 01|02|03`")
    print("  - `dino-ds validator_level_check`")
    print("  - `dino-ds validator_level_reset`")
    print("- Behavior:")
    print("  - If `--rule` is provided on `build lane`/`gate lane`, it overrides saved default.")
    print("  - If no saved level exists, default is `03`.")
    print("- Config file:")
    print(f"  - Default path: `{_TOOL_CONFIG_DEFAULT}`")
    print(f"  - Override with env: `{_TOOL_CONFIG_ENV}`")
    print("- QC report output:")
    print(f"  - Default folder: `{QC_REPORT_DIRNAME}` under repo/package root")
    print(f"  - Override with env: `{QC_REPORT_DIR_ENV}`")
    return ec.SUCCESS


def help_run() -> int:
    print("# Run Help")
    print("- `./dino-ds lane_XX_<lang> [--teacher] [--rule 0X] [--limit N] [--seed N]`: run one lane language YAML.")
    print("- `./dino-ds lane_XX [--teacher] [--rule 0X] [--limit N] [--seed N]`: run one lane, default `lane_en.yaml`.")
    print("- `./dino-ds run lane_XX [--teacher] [--rule 0X] [--seed N]`: full 14-language prod sweep + auto-combine.")
    print("- `./dino-ds qc lane_XX_<lang> [--teacher] [--rule 0X] [--seed N]`: one-language QC run with QC sample limit.")
    print("- `./dino-ds qc lane_XX [--teacher] [--rule 0X] [--seed N]`: 14-language QC sweep (sample limits) + auto-combine.")
    print("- `./dino-ds lane_XX run ...` and `./dino-ds lane_XX qc ...`: compatibility aliases.")
    print("- `--teacher` behavior (run/lane/qc commands):")
    print("  - Forces teacher runtime rewrite for this invocation only (no YAML edit needed).")
    print("  - Enables teacher sampling if lane YAML had 0% sampling.")
    print("  - Uses lane teacher config (provider/model/prompt path/policy).")
    print("  - Requires reachable Ollama + model.")
    print("- `--rule 01|02|03`: one-run strictness override; does not change saved default.")
    print("- QC report output:")
    print(f"  - Default folder: `{QC_REPORT_DIRNAME}`")
    print(f"  - Override with env: `{QC_REPORT_DIR_ENV}=<path>`")
    print("- Lane output root:")
    print(f"  - Override with env: `{_LANE_OUTPUT_DIR_ENV}=<path>` (outputs go to `<path>/<lane_id>/...`)")
    print("  - Persistent: `dino-ds set_output_dir <path>` or `dino-ds set_output_dir lane_xx <path>`")
    print("- Package bare-command mode (wrapped package):")
    print("  - `source ./dino-shell.sh`")
    print("  - After this command, `dino-ds` commands can be used bare in that shell session.")
    print("  - Examples: `help`, `run lane_XX`, `qc lane_XX`, `validator_level_check`, `lane_XX_<lang>`.")
    print("  - Open a new terminal? Run `source ./dino-shell.sh` again.")
    print("  - Without sourcing, bare commands return `command not found`.")
    return ec.SUCCESS


def help_quickstart() -> int:
    print("# Quickstart")
    print("## 1) Check / set validator strictness")
    print("- `dino-ds validator_level_check`")
    print("- `dino-ds validator_level_set 03`")
    print("")
    print("## 2) Run one lane language")
    print("- `./dino-ds lane_03_en --limit 20`")
    print("- `./dino-ds lane_03_en --teacher --limit 20`")
    print("")
    print("## 3) Run full lane sweep")
    print("- `./dino-ds run lane_03`")
    print("- `./dino-ds qc lane_03`")
    print("")
    print("## 4) Useful help pages")
    print("- `dino-ds help spec lane_03`")
    print("- `dino-ds help validator`")
    print("- `dino-ds help run`")
    print("- `dino-ds help paths`")
    print("- `dino-ds help prompts`")
    print("")
    print("## 5) Optional output directory settings")
    print("- `dino-ds qc_report_dir_set ./output\\ QC\\ report`")
    print("- `dino-ds set_output_dir ./out_runs`")
    print("")
    print("## 6) Optional package bare-command mode")
    print("- `source ./dino-shell.sh`")
    print("- After this command, all `dino-ds` commands work bare in this shell session.")
    print("- `help`")
    print("- `run lane_03`")
    print("- `lane_03_en --limit 20`")
    print("- If you open a new terminal, source it again.")
    print("")
    print("Notes:")
    print("- `--rule 01|02|03` overrides saved validator level for that run.")
    print("- If no saved level exists, default is `03`.")
    return ec.SUCCESS


def help_paths() -> int:
    print("# Paths Help")
    print("- QC report directory (separate setting):")
    print("  - `dino-ds qc_report_dir_set <path>`")
    print("  - `dino-ds qc_report_dir_check`")
    print("  - `dino-ds qc_report_dir_reset`")
    print("- Dataset output directory (separate setting):")
    print("  - `dino-ds set_output_dir <path>` (apply to all lanes as base, writes to `<path>/<lane_id>/...`)")
    print("  - `dino-ds set_output_dir lane_xx <path>` (only that lane)")
    print("  - `dino-ds output_dir_check [lane_xx]`")
    print("  - `dino-ds reset_output_dir` (all lanes)")
    print("  - `dino-ds reset_output_dir lane_xx` (only that lane)")
    print("- Env overrides (highest priority):")
    print(f"  - `{QC_REPORT_DIR_ENV}=<path>`")
    print(f"  - `{_LANE_OUTPUT_DIR_ENV}=<path>`")
    print("- Defaults when nothing is set:")
    print(f"  - qc_report_dir: `{(Path.cwd() / QC_REPORT_DIRNAME).resolve()}`")
    print(f"  - lane_output_dir: `{_default_lane_output_hint(None)}`")
    return ec.SUCCESS


def help_prompts() -> int:
    print("# Prompts Help")
    print("- System prompt file (injected as `role: system`):")
    print("  - `prompts/system/dino_system_prompt.txt`")
    print("  - Controlled by lane YAML: `system_prompt_path`")
    print("- Teacher prompt files (used when teacher runtime is active):")
    print("  - `prompts/teacher/lane_XX_teacher_system_prompt.txt`")
    print("  - Controlled by lane YAML: `teacher_runtime.system_prompt_path`")
    print("- Optional shared teacher prompt file to keep in package:")
    print("  - `prompts/teacher/teacher_system_prompt.v1.txt.txt`")
    print("- Operator workflow:")
    print("  - Edit the prompt file(s) in package folder directly.")
    print("  - Re-run lane command (`lane_xx`, `run lane_xx`, or `qc lane_xx`).")
    return ec.SUCCESS


def help_index() -> int:
    print("# Help Index")
    print("- Run commands:")
    print("  - `./dino-ds lane_XX_<lang> ...`: run one language file for one lane.")
    print("  - `./dino-ds lane_XX ...`: run lane default language (`lane_en.yaml`).")
    print("  - `./dino-ds run lane_XX ...`: full 14-language prod sweep + auto-combine.")
    print("  - `./dino-ds qc lane_XX_<lang> ...`: one-language QC run with QC sample limit.")
    print("  - `./dino-ds qc lane_XX ...`: full 14-language QC sweep + auto-combine.")
    print("- Validator commands:")
    print("  - `dino-ds validator_level_set 01|02|03`: save default strictness.")
    print("  - `dino-ds validator_level_check`: show active strictness + source.")
    print("  - `dino-ds validator_level_reset`: clear saved strictness (fallback to 03).")
    print("- Path commands:")
    print("  - `dino-ds qc_report_dir_set|check|reset`: QC markdown report directory setting.")
    print("  - `dino-ds set_output_dir <path>`: set output base for all lanes.")
    print("  - `dino-ds set_output_dir lane_xx <path>`: set output for one lane only.")
    print("  - `dino-ds output_dir_check [lane_xx]`: show effective output directory.")
    print("  - `dino-ds reset_output_dir [lane_xx]`: reset output path setting.")
    print("- Help commands:")
    print("  - `dino-ds help spec lane_XX`: show effective validator contract for that lane.")
    print("  - `dino-ds help run|validator|paths|prompts|quickstart`: focused help pages.")
    print("- `--teacher` flag (run/lane/qc):")
    print("  - Turns on teacher runtime rewrite for that run only.")
    print("  - Uses lane teacher config (provider/model/prompt/policy).")
    print("  - If teacher sampling is 0 in YAML, CLI lifts it for the run.")
    print("  - Requires Ollama/model availability.")
    print("- Wrapped package bare-command mode:")
    print("  - Run `source ./dino-shell.sh` once in package root.")
    print("  - Then commands can be bare: `help`, `run lane_XX`, `qc lane_XX`, `lane_XX_<lang>`.")
    print("  - New shell needs sourcing again.")
    return ec.SUCCESS


def _is_lane05_record(rec: dict[str, object]) -> bool:
    lane_id = rec.get("lane_id")
    if isinstance(lane_id, str) and lane_id.strip():
        return lane_id.strip() == "lane_05_conversation_mode"
    lane_meta = rec.get("_lane")
    if isinstance(lane_meta, dict):
        lane_id2 = lane_meta.get("lane_id")
        if isinstance(lane_id2, str) and lane_id2.strip():
            return lane_id2.strip() == "lane_05_conversation_mode"
    for key in ("sample_id", "id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip().startswith("lane_05_conversation_mode_"):
            return True
    return False


def _pick_second_turn_text(rec: dict[str, object], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _normalize_messages(messages: object) -> list[dict[str, str]] | None:
    if not isinstance(messages, list):
        return None
    out: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            return None
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            return None
        role = role.strip()
        if role not in {"system", "user", "assistant"}:
            return None
        out.append({"role": role, "content": content.strip()})
    return out


def _labels_allowlist_v16() -> list[str]:
    allow = set(ALLOWED_LABEL_KEYS)
    for k in ("messages", "user_message", "assistant_response", "system_prompt_id", "sample_id", "id", "target_base"):
        allow.discard(k)
    return sorted(allow)


def _run_uuid() -> str:
    rid = os.environ.get("DINO_DS_RUN_UUID", "").strip()
    if rid:
        return rid
    return uuid.uuid4().hex


def _lane_language_tag(
    lane_obj: dict[str, object],
    te_base: dict[str, object],
    base_row: dict[str, object],
) -> str:
    # Prefer explicit language keys; fall back to template_expand.slot_banks.language if it is a single value.
    for v in (lane_obj.get("language"), te_base.get("language"), base_row.get("language")):
        if isinstance(v, str) and v.strip():
            return v.strip()
    te = lane_obj.get("template_expand")
    if isinstance(te, dict):
        slot_banks = te.get("slot_banks")
        if isinstance(slot_banks, dict):
            langs = slot_banks.get("language")
            if isinstance(langs, list) and len(langs) == 1 and isinstance(langs[0], str) and langs[0].strip():
                return langs[0].strip()
    return "en"


def _parse_lane_num(raw: str) -> int | None:
    s = str(raw or "").strip().lower()
    if not s:
        return None
    m = re.match(r"^lane_(\d{1,2})(?:\b|_)", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    if s.isdigit():
        try:
            return int(s)
        except Exception:
            return None
    return None


def _pick_latest_validator_config(search_root: Path) -> Path | None:
    cands = [p for p in search_root.glob(_VALIDATOR_CONFIG_GLOB) if p.is_file()]
    if not cands:
        return None

    ranked: list[tuple[datetime, float, Path]] = []
    for p in cands:
        ts = datetime.min
        m = _HELP_SPEC_FILENAME_RE.match(p.name)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d")
            except Exception:
                ts = datetime.min
        try:
            mtime = p.stat().st_mtime
        except Exception:
            mtime = 0.0
        ranked.append((ts, mtime, p))
    ranked.sort(key=lambda x: (x[0], x[1], x[2].name))
    return ranked[-1][2]


def _resolve_validator_config_path(explicit_path: str | None = None) -> Path | None:
    if isinstance(explicit_path, str) and explicit_path.strip():
        p = Path(explicit_path.strip())
        if p.exists() and p.is_file():
            return p
        return None

    cwd = Path.cwd()
    for base in (cwd, *cwd.parents):
        picked = _pick_latest_validator_config(base)
        if picked is not None:
            return picked
    return None


def _extract_lane_section(md_text: str, lane_num: int) -> str | None:
    lines = md_text.splitlines()
    header = f"### Lane {lane_num:02d}"
    start = -1
    for i, ln in enumerate(lines):
        if ln.startswith(header):
            start = i
            break
    if start < 0:
        return None

    end = len(lines)
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.startswith("### Lane "):
            end = j
            break
        if ln.startswith("## ") and j > start:
            end = j
            break

    return "\n".join(lines[start:end]).strip()


def help_spec_lane(lane_ref: str, file_path: str | None = None) -> int:
    lane_num = _parse_lane_num(lane_ref)
    if lane_num is None:
        print("ERROR: invalid lane id. Use e.g. lane_01, lane_1, 01, or 1.", file=sys.stderr)
        return ec.CONFIG_INVALID

    if lane_num not in _HELP_SPEC_ALLOWED_LANES:
        allow = ", ".join([*(f"{n:02d}" for n in range(1, 36)), "37"])
        print(f"ERROR: lane_{lane_num:02d} is not supported in help spec. Allowed lanes: {allow}", file=sys.stderr)
        return ec.CONFIG_INVALID

    cfg_path = _resolve_validator_config_path(file_path)
    if cfg_path is None:
        msg = (
            f"ERROR: validator config markdown not found. Expected file matching "
            f"'{_VALIDATOR_CONFIG_GLOB}' in current/parent directories"
        )
        if isinstance(file_path, str) and file_path.strip():
            msg = f"ERROR: file not found: {file_path}"
        print(msg, file=sys.stderr)
        return ec.IO_ERROR

    try:
        text = cfg_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"ERROR: failed to read {cfg_path}: {e}", file=sys.stderr)
        return ec.IO_ERROR

    section = _extract_lane_section(text, lane_num)
    if not section:
        print(
            f"ERROR: lane_{lane_num:02d} section not found in {cfg_path.name}.",
            file=sys.stderr,
        )
        return ec.CONFIG_INVALID

    print(f"# Validator Help — lane_{lane_num:02d}")
    print(f"- source: {cfg_path}")
    print()
    print(section)
    return ec.SUCCESS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dino-ds",
        description=(
            "Dino dataset build and gate CLI. "
            "If --rule is omitted, use saved validator level from tool config (or default 03)."
        ),
    )
    p.add_argument("--version", action="version", version=f"dino-ds {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    ph = sub.add_parser("help", help="Show help index or a specific help page")
    hsub = ph.add_subparsers(dest="help_cmd", required=False)
    hs = hsub.add_parser("spec", help="Show effective validator rules for a lane")
    hs.add_argument("lane", help="Lane id, e.g. lane_01 (also accepts 01 or 1)")
    hs.add_argument(
        "--file",
        required=False,
        default=None,
        help="Optional path to DinoDS_full_validator_config_<date>.md",
    )
    hsub.add_parser("validator", help="Show validator strictness commands and behavior")
    hsub.add_parser("run", help="Show run/qc command usage and behavior")
    hsub.add_parser("quickstart", help="Show one-screen operator quickstart")
    hsub.add_parser("paths", help="Show output directory settings and commands")
    hsub.add_parser("prompts", help="Show editable prompt files in package")

    pset_alias = sub.add_parser(
        "validator_level_set",
        help="Persist default validator profile for build/gate (01/02/03)",
    )
    pset_alias.add_argument("level", help="Validator level: 01, 02, or 03")

    sub.add_parser(
        "validator_level_check",
        help="Show active validator profile and where it comes from",
    )
    sub.add_parser(
        "validator_level_reset",
        help="Clear saved validator level and revert to default 03",
    )
    qset = sub.add_parser(
        "qc_report_dir_set",
        help="Persist QC markdown output directory",
    )
    qset.add_argument("path", help="Directory path for QC markdown reports")

    sub.add_parser(
        "qc_report_dir_check",
        help="Show active QC markdown output directory setting",
    )

    sub.add_parser(
        "qc_report_dir_reset",
        help="Reset QC markdown output directory to default",
    )

    sout = sub.add_parser(
        "set_output_dir",
        help="Set dataset output directory (all lanes or lane-specific)",
    )
    sout.add_argument(
        "arg1",
        help="Either <path> for all lanes, or lane token (e.g. lane_03) for lane-specific setting",
    )
    sout.add_argument(
        "arg2",
        nargs="?",
        default=None,
        help="Path for lane-specific setting when arg1 is a lane token",
    )

    pcheck = sub.add_parser(
        "output_dir_check",
        help="Show active dataset output directory settings",
    )
    # Optional lane selector for targeted inspection.
    pcheck.add_argument(
        "lane",
        nargs="?",
        default=None,
        help="Optional lane token to check effective output dir for one lane",
    )

    rset = sub.add_parser(
        "reset_output_dir",
        help="Reset dataset output directory settings (all lanes or one lane)",
    )
    rset.add_argument(
        "lane",
        nargs="?",
        default=None,
        help="Optional lane token; omit to reset all lanes",
    )

    # P0 hard gates
    pv = sub.add_parser("validate", help="Validate config against schema(s)")
    pv.add_argument("--schema", required=False, default="lane")  # invalid schema must return exit=6
    pv.add_argument("--config", required=True)

    pl = sub.add_parser("lint", help="Run local lint gates (no-network)")
    pl.add_argument("--qa-jsonl", required=False, default=None)
    pl.add_argument("--pct-jsonl", required=False, default=None)

    # P1: build lane (+ stub build qa for now)
    pb = sub.add_parser("build", help="Build datasets")
    bsub = pb.add_subparsers(dest="build_cmd", required=True)

    bl = bsub.add_parser("lane", help="Build a lane dataset -> JSONL")
    bl.add_argument("--config", required=True)
    bl.add_argument("--out", required=True)
    bl.add_argument("--seed", required=False, default="0")
    bl.add_argument("--limit", required=False, default=None)
    bl.add_argument(
        "--rule",
        required=False,
        default=None,
        help=_RULE_HELP_TEXT,
    )
    bl.add_argument(
        "--teacher",
        action="store_true",
        help="Force teacher_runtime for this run without editing lane YAML",
    )

    bq = bsub.add_parser("qa", help="Build QA dataset (NYI in P1)")
    bq.add_argument("--config", required=True)
    bq.add_argument("--out", required=True)
    bq.add_argument("--seed", required=False, default="0")

    # P1: split / pack
    ps = sub.add_parser("split", help="Split JSONL -> train/val/test")
    ps.add_argument("--in", dest="in_path", required=True)
    ps.add_argument("--outdir", required=True)
    ps.add_argument("--seed", required=False, default="0")
    ps.add_argument("--train", required=False, default="0.9")
    ps.add_argument("--val", required=False, default="0.05")
    ps.add_argument("--test", required=False, default="0.05")
    ps.add_argument("--min-per-nonzero-split", required=False, default="0")

    pp = sub.add_parser("pack", help="Emit dataset_manifest.json (sha256/rows)")
    pp.add_argument("--indir", required=True)
    pp.add_argument("--out", required=True)

    # P3: export (train-ready formats)
    pe = sub.add_parser("export", help="Export train-ready formats")
    esub = pe.add_subparsers(dest="export_cmd", required=True)

    eq = esub.add_parser("qwen", help="Export label-standard JSONL -> Qwen chat JSONL")
    eq.add_argument("--indir", required=True, help="Directory containing train/val/test.jsonl")
    eq.add_argument("--outdir", required=True, help="Output directory for exported JSONL")
    eq.add_argument("--system", required=False, default="", help="System prompt ID (key in system_prompt_registry.json)")
    eq.add_argument("--system-file", required=False, default=None, help="Path to a text file containing the system prompt ID")
    eq.add_argument(
        "--target-base",
        dest="target_base",
        required=False,
        default="",
        help="Override target_base for TEF output when input records are missing target_base",
    )
    eq.add_argument("--keep-labels", action="store_true", help="Include label fields under a `labels` object")
    eq.add_argument("--include-id", action="store_true", help="Include sample_id as `id` in the exported record")

    # Gate (single-entrypoint teammate workflow): validate -> build -> split -> export -> pack -> proofs -> zip
    pgate = sub.add_parser("gate", help="Run end-to-end lane gate (no-network)")
    gsub2 = pgate.add_subparsers(dest="gate_cmd", required=True)

    gl = gsub2.add_parser("lane", help="Gate a lane end-to-end and produce uploadable zip")
    gl.add_argument("--config", required=True)
    gl.add_argument("--limit", required=False, default=None)
    gl.add_argument("--seed", required=False, default="0")
    gl.add_argument(
        "--rule",
        required=False,
        default=None,
        help=_RULE_HELP_TEXT,
    )
    gl.add_argument(
        "--teacher",
        action="store_true",
        help="Force teacher_runtime for this run without editing lane YAML",
    )
    # P2: golden
    pg = sub.add_parser("golden", help="Golden suite ops")
    gsub = pg.add_subparsers(dest="golden_cmd", required=True)

    gg = gsub.add_parser("gen", help="Generate golden_eval.jsonl (CPU-only)")
    gg.add_argument("--out", required=True)
    gg.add_argument("--count", required=False, default="400")
    gg.add_argument("--seed", required=False, default="0")

    gr = gsub.add_parser("run", help="Run golden eval (structure-only for engine=none)")
    gr.add_argument("--engine", required=False, default="none", choices=["none", "dino", "dino_pro"])
    gr.add_argument("--golden", required=True)

    # PCT addendum
    psr = sub.add_parser("sources", help="SourcePack ops")
    ss = psr.add_subparsers(dest="sources_cmd", required=True)
    sv = ss.add_parser("verify", help="Verify SourcePack manifest + sha256")
    sv.add_argument("--manifest", required=True)

    pfr = sub.add_parser("fixtures", help="ToolReplayFixture ops")
    fs = pfr.add_subparsers(dest="fixtures_cmd", required=True)
    fv = fs.add_parser("verify", help="Verify fixture manifest + sha256")
    fv.add_argument("--manifest", required=True)

    sub.add_parser("smoke", help="Quick smoke test (NYI)")

    return p


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sha256_sidecar(path: Path) -> Path:
    digest = _sha256_file(path)
    side = Path(str(path) + ".sha256")
    side.write_text(digest + "\n", encoding="utf-8")
    return side


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        s = out.decode("utf-8").strip()
        return s if s else "unknown"
    except Exception:
        return "unknown"


def _canonicalize_target_base(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    aliases = {
        "dino_4b": "dino_qwen4b",
        "dinoPro-7b": "dinoPro_qwen7b",
        "dinoPro-qwen7b": "dinoPro_qwen7b",
    }
    s2 = aliases.get(s, s)
    return s2


def _require_allowed_target_base(tb: str) -> tuple[bool, str]:
    # Hard-ban qa/test in trainer-facing TEF
    banned = {"qa", "test"}
    if tb in banned:
        return False, f"target_base is banned: {tb}"
    allowed = {"dino_qwen4b", "dinoPro_qwen7b"}
    if tb not in allowed:
        return False, f"target_base not allowed: {tb} (allowed: {sorted(allowed)})"
    return True, ""


def _export_qwen_tef_v1(
    *,
    indir: Path,
    outdir: Path,
    system_prompt_id: str,
    registry: dict[str, str],
    split_name: str,
    target_base: str,
    labels_allowlist: list[str],
) -> int:
    """Export split JSONL -> dino-tef-v1 strict rows.

    Output keys include: sample_id, id, target_base, messages, user_message, assistant_response,
    and all allowlisted label fields copied to the top level (no nested labels object).
    Messages roles/order: system -> user -> assistant
    """
    in_path = indir / f"{split_name}.jsonl"
    if not in_path.exists():
        print(f"ERROR: input split not found: {in_path}", file=sys.stderr)
        return 2

    out_path = outdir / f"{split_name}.jsonl"
    tmp_path = outdir / f".{split_name}.jsonl.tmp"

    if not isinstance(registry, dict) or not registry:
        print("ERROR: system prompt registry is empty or invalid", file=sys.stderr)
        return 2

    wrote = 0
    try:
        with in_path.open("r", encoding="utf-8") as fin, tmp_path.open("w", encoding="utf-8") as fout:
            for line_no, line in enumerate(fin, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print(f"ERROR: bad JSON at {in_path}:{line_no}: {e}", file=sys.stderr)
                    return 2

                # Resolve ids
                sample_id = None
                if isinstance(rec.get("sample_id"), str) and rec.get("sample_id").strip():
                    sample_id = rec.get("sample_id").strip()
                elif isinstance(rec.get("id"), str) and rec.get("id").strip():
                    sample_id = rec.get("id").strip()
                if not sample_id:
                    print(f"ERROR: missing sample_id/id at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                rec_id = None
                if isinstance(rec.get("id"), str) and rec.get("id").strip():
                    rec_id = rec.get("id").strip()
                else:
                    # If id not present, set it to sample_id (still stable and non-empty)
                    rec_id = sample_id

                # Build messages (system prompt resolved by system_prompt_id + registry)
                msgs: list[dict[str, str]] = []
                spid = ""
                rec_spid = rec.get("system_prompt_id")
                if isinstance(rec_spid, str) and rec_spid.strip():
                    spid = rec_spid.strip()
                elif isinstance(system_prompt_id, str) and system_prompt_id.strip():
                    spid = system_prompt_id.strip()

                if not spid:
                    print(f"ERROR: missing system_prompt_id at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                system_text = registry.get(spid, "")
                if not system_text:
                    print(f"ERROR: unknown system_prompt_id '{spid}' at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                msgs.append({"role": "system", "content": system_text})

                rec_messages = rec.get("messages")
                system_extra = ""
                user_text = rec.get("user_message")
                if not (isinstance(user_text, str) and user_text.strip()):
                    user_text = rec.get("user_prompt")
                assistant_text = rec.get("assistant_response")

                multi_turn_msgs: list[dict[str, str]] | None = None
                if isinstance(rec_messages, list) and rec_messages:
                    norm_messages = _normalize_messages(rec_messages)
                    if norm_messages is None:
                        print(f"ERROR: invalid messages payload at {in_path}:{line_no}", file=sys.stderr)
                        return 2
                    non_system_roles = [m["role"] for m in norm_messages if m["role"] != "system"]
                    if len(non_system_roles) >= 4:
                        if tuple(non_system_roles[:4]) != _MULTI_TURN_PREFIX:
                            print(
                                f"ERROR: first four non-system roles must be user,assistant,user,assistant at {in_path}:{line_no}",
                                file=sys.stderr,
                            )
                            return 2
                        non_system_msgs = [m for m in norm_messages if m["role"] != "system"]
                        user_text = non_system_msgs[0]["content"]
                        assistant_text = non_system_msgs[1]["content"]
                        multi_turn_msgs = [{"role": "system", "content": system_text}]
                        multi_turn_msgs.extend(non_system_msgs)
                    else:
                        if len(norm_messages) < 3:
                            print(f"ERROR: messages must be [system,user,assistant] at {in_path}:{line_no}", file=sys.stderr)
                            return 2
                        m0, m1, m2 = norm_messages[0], norm_messages[1], norm_messages[2]
                        if not (m0.get("role") == "system" and m1.get("role") == "user" and m2.get("role") == "assistant"):
                            print(f"ERROR: messages must be [system,user,assistant] at {in_path}:{line_no}", file=sys.stderr)
                            return 2
                        if m0.get("content"):
                            system_extra = m0["content"]
                        if not (isinstance(user_text, str) and user_text.strip()):
                            user_text = m1.get("content")
                        if not (isinstance(assistant_text, str) and (assistant_text.strip() or assistant_text == "")):
                            assistant_text = m2.get("content")

                if multi_turn_msgs is None and _is_lane05_record(rec):
                    u2_text = _pick_second_turn_text(rec, _SECOND_USER_KEYS)
                    a2_text = _pick_second_turn_text(rec, _SECOND_ASSISTANT_KEYS)
                    if u2_text and a2_text:
                        if not (isinstance(user_text, str) and user_text.strip()):
                            print(f"ERROR: missing first-turn user_message at {in_path}:{line_no}", file=sys.stderr)
                            return 2
                        if not (isinstance(assistant_text, str) and (assistant_text.strip() or assistant_text == "")):
                            print(f"ERROR: missing first-turn assistant_response at {in_path}:{line_no}", file=sys.stderr)
                            return 2
                        multi_turn_msgs = [
                            {"role": "system", "content": system_text},
                            {"role": "user", "content": user_text.strip()},
                            {"role": "assistant", "content": assistant_text.strip()},
                            {"role": "user", "content": u2_text},
                            {"role": "assistant", "content": a2_text},
                        ]

                if not (isinstance(user_text, str) and user_text.strip()):
                    print(f"ERROR: missing user_message/user_prompt at {in_path}:{line_no}", file=sys.stderr)
                    return 2
                if not (isinstance(assistant_text, str) and (assistant_text.strip() or assistant_text == "")):
                    print(f"ERROR: missing assistant_response at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                user_content = user_text.strip()
                assistant_content = assistant_text.strip()

                if multi_turn_msgs is not None:
                    non_system_roles = [m["role"] for m in multi_turn_msgs if m["role"] != "system"]
                    if len(non_system_roles) < 4 or tuple(non_system_roles[:4]) != _MULTI_TURN_PREFIX:
                        print(
                            f"ERROR: first four non-system roles must be user,assistant,user,assistant at {in_path}:{line_no}",
                            file=sys.stderr,
                        )
                        return 2
                    non_system_msgs = [m for m in multi_turn_msgs if m["role"] != "system"]
                    user_content = non_system_msgs[0]["content"].strip()
                    assistant_content = non_system_msgs[1]["content"].strip()
                    if not user_content:
                        print(f"ERROR: first user message is empty at {in_path}:{line_no}", file=sys.stderr)
                        return 2
                    msgs = [{"role": "system", "content": system_text}]
                    for m in non_system_msgs:
                        msgs.append({"role": m["role"], "content": m["content"].strip()})
                else:
                    if system_extra and _CONTEXT_RE.search(system_extra):
                        user_content = system_extra + "\n\n" + user_content
                    msgs.append({"role": "user", "content": user_content})
                    msgs.append({"role": "assistant", "content": assistant_content})

                # Enforce role order presence
                roles = [m.get("role") for m in msgs if isinstance(m, dict)]
                if roles.count("system") > 1:
                    print(f"ERROR: multiple system messages at {in_path}:{line_no}", file=sys.stderr)
                    return 2
                if "user" not in roles or "assistant" not in roles:
                    print(f"ERROR: messages missing user/assistant roles at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                # Build compact labels (must be non-empty)
                labels: dict[str, object] = {}
                src_labels = rec.get("labels")
                if isinstance(src_labels, dict) and src_labels:
                    labels = {
                        k: v
                        for k, v in src_labels.items()
                        if k in labels_allowlist and k != "messages" and isinstance(v, (str, int, float, bool))
                    }
                    # Normalize strings
                    for k, v in list(labels.items()):
                        if isinstance(v, str):
                            v2 = v.strip()
                            if not v2:
                                labels.pop(k, None)
                            else:
                                labels[k] = v2
                else:
                    for k in labels_allowlist:
                        if k == "messages":
                            continue
                        v = rec.get(k)
                        if isinstance(v, (str, int, float, bool)):
                            if isinstance(v, str):
                                v2 = v.strip()
                                if not v2:
                                    continue
                                labels[k] = v2
                            else:
                                labels[k] = v

                if not isinstance(labels, dict) or not labels:
                    print(f"ERROR: labels empty after allowlist at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                tef = {
                    "sample_id": sample_id,
                    "id": rec_id,
                    "target_base": target_base,
                    "messages": msgs,
                    "user_message": user_content,
                    "assistant_response": assistant_content,
                }

                # Flatten labels into top-level fields
                for k, v in labels.items():
                    if k not in tef:
                        tef[k] = v

                # Required top-level keys must exist
                required_keys = {"sample_id", "id", "target_base", "messages", "user_message", "assistant_response"}
                if not required_keys.issubset(set(tef.keys())):
                    print(f"ERROR: internal TEF key set mismatch at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                fout.write(json.dumps(tef, ensure_ascii=False) + "\n")
                wrote += 1

        if wrote == 0:
            print(f"ERROR: no rows written for split={split_name} (input empty?)", file=sys.stderr)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return 2

        tmp_path.replace(out_path)
        print(f"[export:dino-tef-v1] wrote {wrote} rows -> {out_path}")
        return 0
    finally:
        if tmp_path.exists() and not out_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def _write_teacher_mode_proof(tef_dir: Path, cfg_path: Path, lane_obj: dict[str, object]) -> Path:
    generation_mode = str(lane_obj.get("generation_mode") or "template_expand").strip() or "template_expand"
    tr = lane_obj.get("teacher_runtime")
    tr = tr if isinstance(tr, dict) else {}
    enabled = bool(tr.get("enabled", False))
    provider = str(tr.get("provider") or "ollama").strip() or "ollama"
    model = str(tr.get("model") or "dino-pro-7b").strip() or "dino-pro-7b"
    policy = str(tr.get("policy") or "structure_only").strip() or "structure_only"
    on_missing = str(tr.get("on_missing_evidence") or "abstain").strip() or "abstain"

    out = tef_dir / "teacher_mode_proof.txt"
    out.write_text(
        "TEACHER_MODE_PROOF v1\n"
        f"config={cfg_path}\n"
        f"generation_mode={generation_mode}\n"
        f"teacher_runtime.enabled={str(enabled).lower()}\n"
        f"teacher_runtime.provider={provider}\n"
        f"teacher_runtime.model={model}\n"
        f"teacher_runtime.policy={policy}\n"
        f"teacher_runtime.on_missing_evidence={on_missing}\n",
        encoding="utf-8",
    )
    return out


def _write_gate_summary(tef_dir: Path, lane_id: str) -> Path:
    # Minimal smoke: first row keys + message role order
    train = tef_dir / "train.jsonl"
    first = None
    with train.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            first = json.loads(line)
            break
    if not isinstance(first, dict):
        raise RuntimeError("GATE_FAIL: train.jsonl missing first record")

    keys = list(first.keys())
    msgs = first.get("messages")
    roles = [m.get("role") for m in msgs] if isinstance(msgs, list) else []

    out = tef_dir / "gate_summary.txt"
    out.write_text(
        "GATE_SUMMARY v1\n"
        f"lane_id={lane_id}\n"
        f"first_row_keys={keys}\n"
        f"first_row_roles={roles}\n",
        encoding="utf-8",
    )
    return out


def _write_tef_labels_compact_proof(tef_dir: Path, labels_allowlist: list[str]) -> Path:
    # Scan first ~50 rows of train.jsonl and prove labels are compact + allowlisted
    train = tef_dir / "train.jsonl"
    bad: list[str] = []
    checked = 0
    with train.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            labels = rec.get("labels")
            if not isinstance(labels, dict) or not labels:
                # Fall back to top-level label fields
                labels = {k: rec.get(k) for k in labels_allowlist if k in rec}
            if not isinstance(labels, dict) or not labels:
                bad.append(f"line {line_no}: labels missing/empty")
            else:
                for k in labels.keys():
                    if k not in labels_allowlist:
                        bad.append(f"line {line_no}: forbidden label key: {k}")
            checked += 1
            if checked >= 50:
                break

    out = tef_dir / "tef_labels_compact_proof.txt"
    if bad:
        out.write_text("FAIL\n" + "\n".join(bad) + "\n", encoding="utf-8")
    else:
        out.write_text("OK\nchecked_rows=50_or_less\n", encoding="utf-8")
    return out


def _write_tef_strict_lint_report(tef_dir: Path) -> Path:
    # Local strict lint: keys + role order for train/val/test
    splits = ["train", "val", "test"]
    lines: list[str] = ["TEF_STRICT_LINT v1"]
    ok = True

    for s in splits:
        path = tef_dir / f"{s}.jsonl"
        if not path.exists():
            ok = False
            lines.append(f"{s}: MISSING")
            continue
        total = 0
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                except Exception as e:
                    ok = False
                    lines.append(f"{s}:{line_no}: bad json: {e}")
                    break
                required_keys = {"sample_id", "id", "target_base", "messages", "user_message", "assistant_response"}
                if not required_keys.issubset(set(rec.keys())):
                    ok = False
                    lines.append(f"{s}:{line_no}: bad top-level keys")
                    break
                msgs = rec.get("messages")
                if not isinstance(msgs, list) or len(msgs) < 2:
                    ok = False
                    lines.append(f"{s}:{line_no}: messages invalid")
                    break
                roles = [m.get("role") for m in msgs if isinstance(m, dict)]
                # Must contain exactly one system at most, and must include user then assistant
                if "user" not in roles or "assistant" not in roles:
                    ok = False
                    lines.append(f"{s}:{line_no}: missing user/assistant")
                    break
                # Enforce system -> user -> assistant ordering (system optional)
                def _idx(r: str) -> int:
                    return roles.index(r) if r in roles else -1
                si = _idx("system")
                ui = _idx("user")
                ai = _idx("assistant")
                if ui == -1 or ai == -1 or ui > ai:
                    ok = False
                    lines.append(f"{s}:{line_no}: role order invalid")
                    break
                if si != -1 and si > ui:
                    ok = False
                    lines.append(f"{s}:{line_no}: system must be before user")
                    break

        lines.append(f"{s}: rows={total}")

    out = tef_dir / "lint_tef_strict_report.txt"
    out.write_text(("OK\n" if ok else "FAIL\n") + "\n".join(lines) + "\n", encoding="utf-8")
    return out


def _read_report_status(path: Path) -> tuple[bool, str]:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"failed to read report: {path}: {e}"
    lines = txt.splitlines()
    head = lines[0].strip().upper() if lines else ""
    if head.startswith("OK"):
        return True, ""
    if head.startswith("FAIL"):
        excerpt = "\n".join(lines[:20]) if lines else "FAIL (empty report)"
        return False, excerpt
    # Unknown format: treat as non-fatal but surface in output.
    excerpt = "\n".join(lines[:8]) if lines else "<empty>"
    return True, f"report had non-standard header: {path.name}\n{excerpt}"


def _safe_token(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", str(raw or "").strip().replace("-", "_"))
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _latest_qc_report_for_lane(lane_id: str) -> Path | None:
    lane_safe = _safe_token(lane_id)
    if not lane_safe:
        return None
    cands: list[Path] = []
    root = Path.cwd()

    # Preferred location: dedicated QC report folder (supports env override).
    env_dir = str(os.environ.get(QC_REPORT_DIR_ENV, "")).strip()
    report_dir: Path
    if env_dir:
        p = Path(env_dir).expanduser()
        report_dir = p if p.is_absolute() else (root / p)
    else:
        report_dir = root / QC_REPORT_DIRNAME
    if report_dir.exists() and report_dir.is_dir():
        cands.extend([p for p in report_dir.glob(f"QC_{lane_safe}_*.md") if p.is_file()])

    # Backward compatibility: legacy root location.
    cands.extend([p for p in root.glob(f"QC_{lane_safe}_*.md") if p.is_file()])
    if not cands:
        return None
    cands.sort(key=lambda p: p.stat().st_mtime)
    return cands[-1]


def _extract_section(lines: list[str], title: str, *, max_lines: int) -> list[str]:
    needle = f"## {title}".strip()
    start = -1
    for i, ln in enumerate(lines):
        if ln.strip() == needle:
            start = i + 1
            break
    if start < 0:
        return []
    out: list[str] = []
    for j in range(start, len(lines)):
        ln = lines[j]
        if ln.startswith("## "):
            break
        if ln.strip():
            out.append(ln.rstrip())
        if len(out) >= max_lines:
            break
    return out


def _emit_qc_failure_indicator(lane_id: str) -> None:
    qc = _latest_qc_report_for_lane(lane_id)
    if qc is None:
        print("[2/6] validator detail: no QC markdown found in repo root", file=sys.stderr)
        return
    try:
        lines = qc.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        print(f"[2/6] validator detail: failed to read {qc}: {e}", file=sys.stderr)
        return
    fatal = _extract_section(lines, "Fatal Summary", max_lines=12)
    warns = _extract_section(lines, "Warning Summary", max_lines=8)
    diag = _extract_section(lines, "Failure Diagnostics", max_lines=14)
    ex = _extract_section(lines, "Top Examples", max_lines=14)
    print(f"[2/6] validator detail report: {qc}", file=sys.stderr)
    if fatal:
        print("[2/6] fatal summary:", file=sys.stderr)
        for ln in fatal:
            print(f"  {ln}", file=sys.stderr)
    if diag:
        print("[2/6] diagnostics:", file=sys.stderr)
        for ln in diag:
            print(f"  {ln}", file=sys.stderr)
    if ex:
        print("[2/6] top examples:", file=sys.stderr)
        for ln in ex:
            print(f"  {ln}", file=sys.stderr)
    elif warns:
        print("[2/6] warning summary:", file=sys.stderr)
        for ln in warns:
            print(f"  {ln}", file=sys.stderr)


def _lang_from_cfg_filename(cfg_path: Path) -> str:
    stem = cfg_path.stem
    m = re.match(r"^lane_(.+)$", stem)
    if not m:
        return "unknown"
    raw = m.group(1).strip()
    if not raw:
        return "unknown"
    return raw


def _build_schema_failure_message(details: dict[str, object] | None, *, exit_code: int) -> str:
    if not isinstance(details, dict):
        return f"schema/config validation failed (exit={exit_code})"
    kind = str(details.get("kind") or "schema_failure")
    msg = str(details.get("message") or "").strip()
    instance_path = str(details.get("instance_path") or "").strip()
    schema_path = str(details.get("schema_path") or "").strip()
    validator = str(details.get("validator") or "").strip()
    bits: list[str] = [f"{kind}"]
    if msg:
        bits.append(f"message={msg}")
    if instance_path:
        bits.append(f"instance_path={instance_path}")
    if schema_path:
        bits.append(f"schema_path={schema_path}")
    if validator:
        bits.append(f"validator={validator}")
    bits.append(f"exit={exit_code}")
    return " | ".join(bits)


def _write_schema_failure_qc_report(*, cfg_path: Path, lane_id: str, exit_code: int) -> str | None:
    details = validate_cmd.get_last_error_details()
    lang = _lang_from_cfg_filename(cfg_path)
    run_id = _run_uuid()
    report_date = datetime.now(timezone.utc).date().isoformat()
    msg = _build_schema_failure_message(details, exit_code=exit_code)

    kind = str(details.get("kind") if isinstance(details, dict) else "schema_failure")
    fatal_code = "schema_stage_validation_failed"
    if kind == "schema_validation_failed":
        fatal_code = "schema_validation_failed"
    elif kind == "config_invalid":
        fatal_code = "config_invalid"
    elif kind == "io_error":
        fatal_code = "config_io_error"
    elif kind == "internal_error":
        fatal_code = "config_internal_error"

    gate_names = (
        "invariants",
        "malformed",
        "repetition",
        "leakage",
        "duplication",
        "proportions",
        "viability",
        "warn_only",
    )
    gates: list[dict[str, object]] = []
    for gate in gate_names:
        if gate == "invariants":
            gates.append(
                {
                    "name": gate,
                    "status": "FAIL",
                    "fatal_codes": {fatal_code: 1},
                    "details": {"notes": "failed_at_schema_stage_before_row_generation"},
                }
            )
        else:
            gates.append(
                {
                    "name": gate,
                    "status": "PASS",
                    "details": {"notes": "not_reached_due_to_schema_stage_failure"},
                }
            )

    qc_result: dict[str, object] = {
        "meta": {
            "lane_id": lane_id,
            "lang": lang,
            "run_id": run_id,
            "date": report_date,
            "rule_profile": "schema_stage",
            "spec_version": "lane_schema.v1",
            "equator_version": "not_reached",
            "generator_commit": _git_sha(),
        },
        "counts": {
            "rows_input": 0,
            "rows_generated": 0,
            "rows_validated": 0,
            "fatal_violations": 1,
            "warn_non_blocking": 0,
            "unique_fatal_codes": 1,
            "unique_warn_codes": 0,
        },
        "gates": gates,
        "fatals": {fatal_code: 1},
        "warns": {},
        "top_examples": {
            fatal_code: [
                {
                    "row_id": cfg_path.name,
                    "message": msg,
                }
            ]
        },
        "thresholds": {},
    }

    try:
        return write_qc_report(
            repo_root=str(Path.cwd()),
            lane_id=lane_id,
            lang=lang,
            run_id=run_id,
            date_yyyy_mm_dd=report_date,
            qc_result=qc_result,
        )
    except Exception as e:
        print(f"[1/6] WARN: failed to write schema failure QC report: {e}", file=sys.stderr)
        return None


def gate_lane(
    *,
    config: str,
    limit: int | None,
    seed: int,
    rule_profile: str | None = None,
    teacher_force: bool = False,
) -> int:
    cfg_path = Path(config)
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        return ec.CONFIG_INVALID

    # Lane config is lanes/<lane_id>/lane_en.yaml (legacy fallback: lane_en.yaml)
    lane_dir = cfg_path.parent
    lane_id = lane_dir.name

    # Default output root:
    # - wrapped package mode -> <package_root>/out_runs/<lane_id>
    # - repo mode -> lanes/<lane_id>/out
    out_root = lane_dir / "out"
    if _is_wrapped_package_mode(Path.cwd()):
        out_root = (Path.cwd() / "out_runs" / lane_id).resolve()
    lane_out_override_active = False
    effective_lane_out, effective_lane_out_src = _effective_lane_output_dir(lane_id)
    if effective_lane_out:
        out_root = Path(effective_lane_out)
        lane_out_override_active = True

    # Validate first (schema)
    print("[1/6] validate lane config (schema)")
    rc = validate_cmd.run(config=str(cfg_path), schema="lane")
    if rc == 0:
        print("[1/6] OK")
    if rc != 0:
        details = validate_cmd.get_last_error_details()
        if isinstance(details, dict):
            kind = str(details.get("kind") or "schema_failure")
            msg = str(details.get("message") or "").strip()
            instance_path = str(details.get("instance_path") or "").strip()
            schema_path = str(details.get("schema_path") or "").strip()
            validator = str(details.get("validator") or "").strip()
            print(f"[1/6] detail kind: {kind}", file=sys.stderr)
            if msg:
                print(f"[1/6] detail message: {msg}", file=sys.stderr)
            if instance_path:
                print(f"[1/6] detail instance_path: {instance_path}", file=sys.stderr)
            if schema_path:
                print(f"[1/6] detail schema_path: {schema_path}", file=sys.stderr)
            if validator:
                print(f"[1/6] detail validator: {validator}", file=sys.stderr)
        report_path = _write_schema_failure_qc_report(cfg_path=cfg_path, lane_id=lane_id, exit_code=rc)
        if isinstance(report_path, str) and report_path.strip():
            print(f"[1/6] schema failure report: {report_path}", file=sys.stderr)
        print(f"[1/6] FAIL (schema/config validation, exit={rc})", file=sys.stderr)
        return rc

    # Read lane config for target_base + teacher proof
    try:
        lane_obj = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if not isinstance(lane_obj, dict):
            print("ERROR: lane config is not a mapping", file=sys.stderr)
            return ec.CONFIG_INVALID
    except Exception as e:
        print(f"ERROR: failed to read lane config: {e}", file=sys.stderr)
        return ec.CONFIG_INVALID

    if teacher_force:
        tr = lane_obj.get("teacher_runtime")
        if not isinstance(tr, dict):
            tr = {}
            lane_obj["teacher_runtime"] = tr
        tr["enabled"] = True
        sr = tr.get("sample_ratio")
        sp = tr.get("sample_percent")
        if isinstance(sr, (int, float)):
            if float(sr) <= 0.0:
                tr["sample_ratio"] = 1.0
        elif isinstance(sp, (int, float)):
            if float(sp) <= 0.0:
                tr["sample_percent"] = 100
        else:
            tr["sample_percent"] = 100

    # Apply lane-config output_dir only when global lane-output override is not active.
    if not lane_out_override_active:
        od = lane_obj.get("output_dir")
        if isinstance(od, str) and od.strip():
            od_path = Path(od.strip())
            out_root = od_path if od_path.is_absolute() else (lane_dir / od_path)

    out_root.mkdir(parents=True, exist_ok=True)
    if lane_out_override_active:
        print(f"[2/6] output_dir override ({effective_lane_out_src}): {out_root}")

    raw_tb = str(lane_obj.get("target_base") or "").strip()
    tb = _canonicalize_target_base(raw_tb)
    ok, msg = _require_allowed_target_base(tb)
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        return ec.CONFIG_INVALID

    # Resolve system prompt via registry + system_prompt_id (no hard-coded text)
    registry = pack_cmd._load_system_prompt_registry()
    if not registry:
        print("ERROR: system prompt registry not found or empty", file=sys.stderr)
        return ec.CONFIG_INVALID

    base_row = lane_obj.get("base_row") if isinstance(lane_obj.get("base_row"), dict) else {}
    te = lane_obj.get("template_expand") if isinstance(lane_obj.get("template_expand"), dict) else {}
    te_base = te.get("base_row") if isinstance(te.get("base_row"), dict) else {}

    default_spid = str(
        lane_obj.get("system_prompt_id")
        or te_base.get("system_prompt_id")
        or base_row.get("system_prompt_id")
        or lane_obj.get("system_id")
        or ""
    ).strip()

    # Build
    rule_tag = (
        str(rule_profile).strip()
        if isinstance(rule_profile, str) and str(rule_profile).strip()
        else "auto(saved/default=03)"
    )
    print(f"[2/6] build lane -> built_N.jsonl (rule={rule_tag})")
    # Name outputs using limit if provided, else use lane count_target (or 'full')
    count_target = None
    te = lane_obj.get("template_expand")
    if isinstance(te, dict):
        te_ct = te.get("count_target")
        if isinstance(te_ct, int) and te_ct > 0:
            count_target = te_ct
    if count_target is None:
        ct = lane_obj.get("count_target")
        if isinstance(ct, int) and ct > 0:
            count_target = ct
    limit_tag = None
    if isinstance(limit, int) and limit > 0:
        limit_tag = str(limit)
    elif isinstance(count_target, int) and count_target > 0:
        limit_tag = str(count_target)
    else:
        limit_tag = "full"

    built_path = out_root / f"built_{limit_tag}.jsonl"
    rc = build_cmd.run_lane(
        config=str(cfg_path),
        out=str(built_path),
        seed=seed,
        limit=limit,
        rule_profile=rule_profile,
        teacher_force=teacher_force,
    )
    if rc != 0:
        _emit_qc_failure_indicator(lane_id)
        print(f"[2/6] FAIL (build/row-validation, exit={rc})", file=sys.stderr)
        return rc

    # Split
    print("[3/6] split built -> train/val/test")
    split_dir = out_root / f"split_{limit_tag}"
    split_dir.mkdir(parents=True, exist_ok=True)
    rc = split_cmd.run(
        in_path=str(built_path),
        outdir=str(split_dir),
        seed=seed,
        train=0.9,
        val=0.05,
        test=0.05,
        min_per_nonzero_split=1,
    )
    if rc != 0:
        print(f"[3/6] FAIL (split, exit={rc})", file=sys.stderr)
        return rc

    print("[4/6] export -> dino-tef-v1")
    # Export strict dino-tef-v1
    lang_tag = _lane_language_tag(lane_obj, te_base, base_row)
    run_uuid = _run_uuid()
    tef_dir = out_root / f"dino-tef-{lang_tag}-{limit_tag}-{run_uuid}"
    tef_dir.mkdir(parents=True, exist_ok=True)

    labels_allow = _labels_allowlist_v16()

    for split_name in ("train", "val", "test"):
        rc = _export_qwen_tef_v1(
            indir=split_dir,
            outdir=tef_dir,
            system_prompt_id=default_spid,
            registry=registry,
            split_name=split_name,
            target_base=tb,
            labels_allowlist=labels_allow,
        )
        if rc != 0:
            print(f"[4/6] FAIL (export split={split_name}, exit={rc})", file=sys.stderr)
            return rc

    print("[5/6] pack + proofs")
    # Pack manifest (tool-owned)
    manifest_path = tef_dir / "dataset_manifest.v1.json"
    rc = pack_cmd.run(indir=str(tef_dir), out=str(manifest_path))
    if rc != 0:
        print(f"[5/6] FAIL (pack manifest, exit={rc})", file=sys.stderr)
        return rc

    # Proofs (tool-only)
    tool_sha = _git_sha()
    tool_sha_path = tef_dir / "tool_git_sha.txt"
    tool_sha_path.write_text(tool_sha + "\n", encoding="utf-8")

    proof_teacher = _write_teacher_mode_proof(tef_dir, cfg_path, lane_obj)
    proof_summary = _write_gate_summary(tef_dir, lane_id)
    proof_labels = _write_tef_labels_compact_proof(tef_dir, labels_allow)
    proof_lint = _write_tef_strict_lint_report(tef_dir)

    ok_labels, detail_labels = _read_report_status(proof_labels)
    if not ok_labels:
        print("[5/6] FAIL (labels proof)", file=sys.stderr)
        print(detail_labels, file=sys.stderr)
        return ec.LINT_FAILED
    if detail_labels:
        print(f"[5/6] WARN: {detail_labels}", file=sys.stderr)

    ok_lint, detail_lint = _read_report_status(proof_lint)
    if not ok_lint:
        print("[5/6] FAIL (TEF strict lint)", file=sys.stderr)
        print(detail_lint, file=sys.stderr)
        return ec.LINT_FAILED
    if detail_lint:
        print(f"[5/6] WARN: {detail_lint}", file=sys.stderr)

    # Sha256 sidecars
    sidecars: list[Path] = []
    for p in [
        built_path,
        tef_dir / "train.jsonl",
        tef_dir / "val.jsonl",
        tef_dir / "test.jsonl",
        manifest_path,
        tool_sha_path,
        proof_teacher,
        proof_summary,
        proof_labels,
        proof_lint,
    ]:
        sidecars.append(_write_sha256_sidecar(p))

    print("[6/6] zip flat-root gate bundle + sha256")
    # Flat-root gate zip
    zip_tmp = out_root / f"lane_gate_zip_{lane_id}.zip"
    files_to_zip: list[Path] = [
        built_path,
        Path(str(built_path) + ".sha256"),
        tef_dir / "train.jsonl",
        tef_dir / "train.jsonl.sha256",
        tef_dir / "val.jsonl",
        tef_dir / "val.jsonl.sha256",
        tef_dir / "test.jsonl",
        tef_dir / "test.jsonl.sha256",
        manifest_path,
        Path(str(manifest_path) + ".sha256"),
        tool_sha_path,
        Path(str(tool_sha_path) + ".sha256"),
        proof_labels,
        Path(str(proof_labels) + ".sha256"),
        proof_summary,
        Path(str(proof_summary) + ".sha256"),
        proof_teacher,
        Path(str(proof_teacher) + ".sha256"),
        proof_lint,
        Path(str(proof_lint) + ".sha256"),
    ]

    with zipfile.ZipFile(zip_tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files_to_zip:
            if p.exists():
                z.write(p, arcname=p.name)

    zip_sha = _sha256_file(zip_tmp)
    zip_hash8 = zip_sha[:8]
    zip_final = out_root / f"lane_gate_zip_{zip_hash8}.zip"
    try:
        if zip_final.exists():
            zip_final.unlink()
    except Exception:
        pass
    zip_tmp.replace(zip_final)

    print(f"UPLOAD_THIS: {zip_final}")
    print(f"ZIP_SHA256={zip_sha}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "set_validator_level":
        argv = ["validator_level_set", *argv[1:]]
    if argv and argv[0] == "lane_output_dir_set":
        argv = ["set_output_dir", *argv[1:]]
    if argv and argv[0] == "output_dir_reset":
        argv = ["reset_output_dir", *argv[1:]]
    args = build_parser().parse_args(argv)

    # Apply persisted path settings only for runtime commands that need them.
    if args.cmd in {"build", "gate"}:
        _apply_persisted_path_overrides()

    try:
        if args.cmd == "help" and not getattr(args, "help_cmd", None):
            return help_index()
        if args.cmd == "help" and args.help_cmd == "spec":
            return help_spec_lane(lane_ref=args.lane, file_path=getattr(args, "file", None))
        if args.cmd == "help" and args.help_cmd == "validator":
            return help_validator()
        if args.cmd == "help" and args.help_cmd == "run":
            return help_run()
        if args.cmd == "help" and args.help_cmd == "quickstart":
            return help_quickstart()
        if args.cmd == "help" and args.help_cmd == "paths":
            return help_paths()
        if args.cmd == "help" and args.help_cmd == "prompts":
            return help_prompts()

        if args.cmd == "validator_level_set":
            return set_validator_level(level_raw=str(getattr(args, "level", "")))

        if args.cmd == "validator_level_check":
            return validator_level_check()

        if args.cmd == "validator_level_reset":
            return validator_level_reset()

        if args.cmd == "qc_report_dir_set":
            return set_qc_report_dir(path_raw=str(getattr(args, "path", "")))

        if args.cmd == "qc_report_dir_check":
            return qc_report_dir_check()

        if args.cmd == "qc_report_dir_reset":
            return qc_report_dir_reset()

        if args.cmd == "set_output_dir":
            return set_output_dir(
                arg1=str(getattr(args, "arg1", "")),
                arg2=getattr(args, "arg2", None),
            )

        if args.cmd == "output_dir_check":
            return output_dir_check(lane=getattr(args, "lane", None))

        if args.cmd == "reset_output_dir":
            return reset_output_dir(lane=getattr(args, "lane", None))

        if args.cmd == "validate":
            return validate_cmd.run(config=args.config, schema=str(args.schema))

        if args.cmd == "lint":
            return lint_cmd.run(qa_jsonl=args.qa_jsonl, pct_jsonl=getattr(args, "pct_jsonl", None))

        if args.cmd == "sources" and args.sources_cmd == "verify":
            return sources_cmd.verify(manifest=args.manifest)

        if args.cmd == "fixtures" and args.fixtures_cmd == "verify":
            return fixtures_cmd.verify(manifest=args.manifest)

        if args.cmd == "build" and args.build_cmd == "lane":
            lim = None
            if args.limit is not None and str(args.limit).strip().lower() not in ("none", ""):
                lim = int(args.limit)
            eff_rule, _rule_src = _effective_validator_level(getattr(args, "rule", None))
            return build_cmd.run_lane(
                config=args.config,
                out=args.out,
                seed=int(args.seed),
                limit=lim,
                rule_profile=eff_rule,
                teacher_force=bool(getattr(args, "teacher", False)),
            )

        if args.cmd == "build" and args.build_cmd == "qa":
            return stubs.nyi()

        if args.cmd == "split":
            return split_cmd.run(
                in_path=args.in_path,
                outdir=args.outdir,
                seed=int(args.seed),
                train=float(args.train),
                val=float(args.val),
                test=float(args.test),
                min_per_nonzero_split=int(getattr(args, "min_per_nonzero_split", 0)),
            )

        if args.cmd == "pack":
            return pack_cmd.run(indir=args.indir, out=args.out)

        if args.cmd == "gate" and args.gate_cmd == "lane":
            raw_limit = getattr(args, "limit", None)
            lim = None
            if raw_limit is not None:
                s = str(raw_limit).strip()
                if s:
                    lim = int(s)
            seed = int(str(getattr(args, "seed", "0")).strip() or "0")
            eff_rule, _rule_src = _effective_validator_level(getattr(args, "rule", None))
            return gate_lane(
                config=args.config,
                limit=lim,
                seed=seed,
                rule_profile=eff_rule,
                teacher_force=bool(getattr(args, "teacher", False)),
            )

        if args.cmd == "export" and args.export_cmd == "qwen":
            indir = Path(args.indir)
            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)

            # For TEF export, --system is a registry ID (not free-form text).
            system_prompt_id = str(getattr(args, "system", "") or "").strip()
            system_file = getattr(args, "system_file", None)
            if system_file is not None and str(system_file).strip() not in ("", "none", "None"):
                with open(system_file, "r", encoding="utf-8") as f:
                    system_prompt_id = f.read().strip()

            registry = pack_cmd._load_system_prompt_registry()
            if not registry:
                print("ERROR: system prompt registry not found or empty", file=sys.stderr)
                return ec.CONFIG_INVALID

            # Split name input/output selection
            split_name = str(getattr(args, "target_base", "") or "").strip() or "test"

            # Target base enforcement (trainer-facing)
            tb = str(getattr(args, "target_base", "") or "").strip() or "test"
            tb = _canonicalize_target_base(tb)
            ok, msg = _require_allowed_target_base(tb)
            if not ok:
                print(f"ERROR: {msg}", file=sys.stderr)
                return ec.CONFIG_INVALID

            labels_allow = _labels_allowlist_v16()

            return _export_qwen_tef_v1(
                indir=indir,
                outdir=outdir,
                system_prompt_id=system_prompt_id,
                registry=registry,
                split_name=split_name,
                target_base=tb,
                labels_allowlist=labels_allow,
            )

        if args.cmd == "golden" and args.golden_cmd == "gen":
            return golden_cmd.gen(out=args.out, count=int(args.count), seed=int(args.seed))

        if args.cmd == "golden" and args.golden_cmd == "run":
            return golden_cmd.run(golden=args.golden, engine=args.engine)

        return stubs.nyi()
    except Exception:
        traceback.print_exc()
        return ec.INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

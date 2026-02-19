from __future__ import annotations

import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .. import exit_codes as ec
from ..utils import sha256_file, atomic_write_text


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
_BOOL_FIELDS = {
    "adult_gate",
    "profanity_allowed",
    "needs_search",
    "needs_history_search",
    "connector_needed",
    "deeplink_needed",
}
_MAPPING_TOOLCALLS = {"connector_action", "deeplink_action", "image_tool_action"}


def _is_lane05_record(rec: Dict[str, Any]) -> bool:
    lane_id = rec.get("lane_id")
    if isinstance(lane_id, str) and lane_id.strip():
        return lane_id.strip() == "lane_05_conversation_mode"
    for key in ("sample_id", "id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip().startswith("lane_05_conversation_mode_"):
            return True
    return False


def _pick_second_turn_text(rec: Dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _normalize_messages(messages: object) -> list[Dict[str, str]] | None:
    if not isinstance(messages, list):
        return None
    out: list[Dict[str, str]] = []
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


def _count_lines(path: Path) -> int:
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def run(indir: str, out: str) -> int:
    try:
        d = Path(indir).expanduser().resolve()
        if not d.exists() or not d.is_dir():
            return ec.IO_ERROR

        files = [p for p in sorted(d.glob("*.jsonl")) if p.is_file()]
        if not files:
            return ec.CONFIG_INVALID

        items = []
        total_rows = 0
        for p in files:
            rows = _count_lines(p)
            total_rows += rows
            items.append(
                {
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                    "rows": rows,
                }
            )

        manifest = {
            "dataset_manifest_version": "dino.dataset_manifest.v1",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "items": items,
            "total_rows": total_rows,
        }

        out_path = Path(out).expanduser().resolve()
        atomic_write_text(out_path, json.dumps(manifest, indent=2) + "\n")
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR



def _strip_private_keys(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in rec.items() if not (isinstance(k, str) and k.startswith("_"))}


def _load_system_prompt_registry() -> Dict[str, str]:
    """Load the system prompt registry.

    Supports either:
      A) {"prompts": [{"id": "...", "text": "..."}, ...]}
      B) {"<id>": "<text>", ...}

    Search order:
      - CWD/system_prompt_registry.json
      - PyInstaller bundle (_MEIPASS)/system_prompt_registry.json
      - PyInstaller binary dir/system_prompt_registry.json
      - repo_root/system_prompt_registry.json
      - src/dino_ds/system_prompt_registry.json
      - src/dino_ds/schemas/system_prompt_registry.json
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    candidates = [
        Path.cwd() / "system_prompt_registry.json",
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str) and meipass:
        candidates.append(Path(meipass) / "system_prompt_registry.json")
    exe_dir = Path(sys.executable).resolve().parent if hasattr(sys, "executable") else None
    if exe_dir:
        candidates.append(exe_dir / "system_prompt_registry.json")
    candidates.extend(
        [
            repo_root / "system_prompt_registry.json",
            repo_root / "src" / "dino_ds" / "system_prompt_registry.json",
            repo_root / "src" / "dino_ds" / "schemas" / "system_prompt_registry.json",
        ]
    )

    for p in candidates:
        if not p.exists() or not p.is_file():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        reg: Dict[str, str] = {}
        if isinstance(raw, dict) and "prompts" in raw and isinstance(raw["prompts"], list):
            for it in raw["prompts"]:
                if not isinstance(it, dict):
                    continue
                pid = it.get("id")
                txt = it.get("text")
                if isinstance(pid, str) and pid.strip() and isinstance(txt, str):
                    reg[pid.strip()] = txt
        elif isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(k, str) and k.strip() and isinstance(v, str):
                    reg[k.strip()] = v

        if reg:
            return reg

    return {}


def _resolve_system_text(system_prompt_id: str, registry: Dict[str, str]) -> str:
    pid = (system_prompt_id or "").strip()
    if not pid:
        return ""
    return registry.get(pid, "")


def export_qwen(
    *,
    indir: str,
    outdir: str,
    system: str = "",
    target_base: str = "",
    keep_labels: bool = False,
    include_id: bool = False,
) -> int:
    """Export label-standard JSONL (train/val/test) into TEF v1 (A-format) for Qwen/Owen ingestion.

    Input: directory with *.jsonl (typically train.jsonl / val.jsonl / test.jsonl)
    Output: directory with same filenames, each line a JSON object:
      - sample_id: stable id for the row (from sample_id, otherwise from id)
      - target_base: required string (copied through)
      - user_message: user content (top-level)
      - assistant_response: assistant content (top-level)
      - messages: [{role: system, content: ...}, {role: user, content: ...}, {role: assistant, content: ...}]
      - plus all label fields copied to the top level (no nested labels object by default)

    The system message MUST be sourced from the system prompt registry via system_prompt_id.
    We accept either:
      - `system` argument as the system_prompt_id override, or
      - per-record `system_prompt_id` field.

    Private metadata keys starting with '_' are dropped.
    """
    try:
        src = Path(indir).expanduser().resolve()
        if not src.exists() or not src.is_dir():
            return ec.IO_ERROR

        dst = Path(outdir).expanduser().resolve()
        dst.mkdir(parents=True, exist_ok=True)

        files = [p for p in sorted(src.glob("*.jsonl")) if p.is_file()]
        if not files:
            return ec.CONFIG_INVALID

        registry = _load_system_prompt_registry()

        for p in files:
            out_path = dst / p.name
            with p.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec_any = json.loads(line)
                    except Exception:
                        return ec.LINT_FAILED
                    if not isinstance(rec_any, dict):
                        return ec.LINT_FAILED

                    rec: Dict[str, Any] = _strip_private_keys(rec_any)

                    user_msg = rec.get("user_message")
                    asst_msg = rec.get("assistant_response")

                    # Pack-time golden invariants: bools must be real bools (no "true"/"false" strings).
                    for bf in _BOOL_FIELDS:
                        if bf in rec:
                            val = rec.get(bf)
                            if isinstance(val, str) and val.strip().lower() in ("true", "false"):
                                return ec.LINT_FAILED
                            if not isinstance(val, bool):
                                return ec.LINT_FAILED

                    rec_messages = rec.get("messages")
                    system_extra = ""
                    multi_turn_messages: list[Dict[str, str]] | None = None
                    if isinstance(rec_messages, list) and rec_messages:
                        norm_messages = _normalize_messages(rec_messages)
                        if norm_messages is None:
                            return ec.LINT_FAILED
                        non_system_roles = [m["role"] for m in norm_messages if m["role"] != "system"]
                        if len(non_system_roles) >= 4:
                            if tuple(non_system_roles[:4]) != _MULTI_TURN_PREFIX:
                                return ec.LINT_FAILED
                            non_system_msgs = [m for m in norm_messages if m["role"] != "system"]
                            user_msg = non_system_msgs[0]["content"]
                            asst_msg = non_system_msgs[1]["content"]
                            multi_turn_messages = non_system_msgs
                        else:
                            if len(norm_messages) < 3:
                                return ec.LINT_FAILED
                            m0, m1, m2 = norm_messages[0], norm_messages[1], norm_messages[2]
                            if not (m0.get("role") == "system" and m1.get("role") == "user" and m2.get("role") == "assistant"):
                                return ec.LINT_FAILED
                            if m0.get("content"):
                                system_extra = m0["content"]
                            if not (isinstance(user_msg, str) and user_msg.strip()):
                                user_msg = m1.get("content")
                            if not (isinstance(asst_msg, str) and (asst_msg.strip() or asst_msg == "")):
                                asst_msg = m2.get("content")

                    if multi_turn_messages is None and _is_lane05_record(rec):
                        u2_text = _pick_second_turn_text(rec, _SECOND_USER_KEYS)
                        a2_text = _pick_second_turn_text(rec, _SECOND_ASSISTANT_KEYS)
                        if u2_text and a2_text:
                            if not (isinstance(user_msg, str) and user_msg.strip()):
                                return ec.LINT_FAILED
                            if not (isinstance(asst_msg, str) and (asst_msg.strip() or asst_msg == "")):
                                return ec.LINT_FAILED
                            multi_turn_messages = [
                                {"role": "user", "content": user_msg.strip()},
                                {"role": "assistant", "content": asst_msg.strip()},
                                {"role": "user", "content": u2_text},
                                {"role": "assistant", "content": a2_text},
                            ]

                    if not isinstance(user_msg, str) or not (user_msg.strip()):
                        return ec.LINT_FAILED
                    if not isinstance(asst_msg, str):
                        return ec.LINT_FAILED

                    tool_call = rec.get("tool_call")
                    if isinstance(tool_call, dict) and tool_call.get("name") in _MAPPING_TOOLCALLS:
                        if asst_msg.strip() != "":
                            return ec.LINT_FAILED

                    # Required TEF fields
                    sample_id_any = rec.get("sample_id")
                    if not isinstance(sample_id_any, str) or not sample_id_any.strip():
                        sample_id_any = rec.get("id")
                    if not isinstance(sample_id_any, str) or not sample_id_any.strip():
                        return ec.LINT_FAILED
                    sample_id = sample_id_any.strip()

                    target_base_rec = rec.get("target_base")
                    if isinstance(target_base_rec, str) and target_base_rec.strip():
                        target_base_val = target_base_rec.strip()
                    else:
                        target_base_val = (target_base or "").strip()
                    if not target_base_val:
                        return ec.LINT_FAILED

                    # System prompt: registry-backed only
                    system_prompt_id = (system or "").strip() or str(rec.get("system_prompt_id") or "").strip()
                    sys_text = _resolve_system_text(system_prompt_id, registry)
                    if not sys_text:
                        # Missing or unknown system prompt id is a lint failure
                        return ec.LINT_FAILED

                    user_content = user_msg.strip()
                    assistant_content = asst_msg.strip()

                    if multi_turn_messages is not None:
                        non_system_roles = [m["role"] for m in multi_turn_messages if m["role"] != "system"]
                        if len(non_system_roles) < 4 or tuple(non_system_roles[:4]) != _MULTI_TURN_PREFIX:
                            return ec.LINT_FAILED
                        non_system_msgs = [m for m in multi_turn_messages if m["role"] != "system"]
                        user_content = non_system_msgs[0]["content"].strip()
                        assistant_content = non_system_msgs[1]["content"].strip()
                        if not user_content:
                            return ec.LINT_FAILED
                        messages = [{"role": "system", "content": sys_text}]
                        for m in non_system_msgs:
                            messages.append({"role": m["role"], "content": m["content"].strip()})
                    else:
                        if system_extra and _CONTEXT_RE.search(system_extra):
                            user_content = system_extra + "\n\n" + user_content
                        messages = [
                            {"role": "system", "content": sys_text},
                            {"role": "user", "content": user_content},
                            {"role": "assistant", "content": assistant_content},
                        ]

                    labels: Dict[str, Any] = {}
                    for k, v in rec.items():
                        if k in ("user_message", "assistant_response", "messages"):
                            continue
                        if k in ("sample_id", "id", "target_base", "system_prompt_id"):
                            continue
                        if isinstance(v, (str, int, float, bool)):
                            if isinstance(v, str):
                                v2 = v.strip()
                                if not v2:
                                    continue
                                labels[k] = v2
                            else:
                                labels[k] = v

                    # TEF compact labels: forbidden keys must never appear in labels.
                    labels.pop("answer_steps", None)
                    labels.pop("legacy_id", None)

                    # Labels must not be empty (hard-gate requirement).
                    if not labels:
                        return ec.LINT_FAILED

                    out_rec: Dict[str, Any] = {
                        "sample_id": sample_id,
                        "target_base": target_base_val,
                        "messages": messages,
                        "user_message": user_content,
                        "assistant_response": assistant_content,
                    }

                    if include_id:
                        out_rec["id"] = sample_id

                    # Flatten labels into top-level fields
                    for k, v in labels.items():
                        if k not in out_rec:
                            out_rec[k] = v

                    if keep_labels:
                        out_rec["labels"] = labels

                    fout.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR

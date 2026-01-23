from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .. import exit_codes as ec
from ..utils import sha256_file, atomic_write_text


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
      - repo_root/system_prompt_registry.json
      - src/dino_ds/system_prompt_registry.json
      - src/dino_ds/schemas/system_prompt_registry.json
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    candidates = [
        repo_root / "system_prompt_registry.json",
        repo_root / "src" / "dino_ds" / "system_prompt_registry.json",
        repo_root / "src" / "dino_ds" / "schemas" / "system_prompt_registry.json",
    ]

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
      - labels: {} or full label object (when keep_labels=True)
      - messages: [{role: system, content: ...}, {role: user, content: ...}, {role: assistant, content: ...}]

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
                    if not isinstance(user_msg, str) or not isinstance(asst_msg, str):
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

                    messages = [
                        {"role": "system", "content": sys_text},
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": asst_msg},
                    ]

                    labels: Dict[str, Any] = {}
                    if keep_labels:
                        for k, v in rec.items():
                            if k in ("user_message", "assistant_response"):
                                continue
                            if k in ("sample_id", "id", "target_base", "system_prompt_id"):
                                continue
                            labels[k] = v

                        # TEF compact labels: forbidden keys must never appear in labels.
                        labels.pop("answer_steps", None)
                        labels.pop("legacy_id", None)

                        # Keep-labels must not produce empty labels (hard-gate requirement).
                        if not labels:
                            return ec.LINT_FAILED

                    out_rec: Dict[str, Any] = {
                        "sample_id": sample_id,
                        "target_base": target_base_val,
                        "labels": labels,
                        "messages": messages,
                    }

                    if include_id:
                        out_rec["id"] = sample_id

                    fout.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR

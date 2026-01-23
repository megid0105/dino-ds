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


def export_qwen(
    *,
    indir: str,
    outdir: str,
    system: str = "",
    keep_labels: bool = False,
    include_id: bool = False,
) -> int:
    """Export label-standard JSONL (train/val/test) into Qwen chat JSONL.

    Input: directory with *.jsonl (typically train.jsonl / val.jsonl / test.jsonl)
    Output: directory with same filenames, each line a JSON object:
      - messages: [{role: user, content: ...}, {role: assistant, content: ...}]
      - optionally prepended system message if `system` provided
      - optional `labels` object if keep_labels
      - optional `id` if include_id (copied from sample_id)

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

                    sample_id = rec.get("sample_id")

                    # Build Qwen chat record
                    messages = []
                    sys_text = (system or "").strip()
                    if sys_text:
                        messages.append({"role": "system", "content": sys_text})
                    messages.append({"role": "user", "content": user_msg})
                    messages.append({"role": "assistant", "content": asst_msg})

                    out_rec: Dict[str, Any] = {"messages": messages}

                    if include_id and isinstance(sample_id, str) and sample_id.strip():
                        out_rec["id"] = sample_id

                    if keep_labels:
                        labels: Dict[str, Any] = {}
                        for k, v in rec.items():
                            if k in ("user_message", "assistant_response"):
                                continue
                            # Do not duplicate id if include_id already promoted sample_id.
                            if include_id and k == "sample_id":
                                continue
                            labels[k] = v
                        out_rec["labels"] = labels

                    fout.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR

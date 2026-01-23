from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .. import exit_codes as ec
from ..utils import atomic_write_text


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def run(in_path: str, outdir: str, seed: int = 0, train: float = 0.9, val: float = 0.05, test: float = 0.05, min_per_nonzero_split: int = 0) -> int:
    try:
        src = Path(in_path).expanduser().resolve()
        if not src.exists():
            return ec.IO_ERROR

        if train <= 0 or val < 0 or test < 0:
            return ec.CONFIG_INVALID
        s = train + val + test
        if abs(s - 1.0) > 1e-6:
            return ec.CONFIG_INVALID

        rows = _read_jsonl(src)
        if not rows:
            return ec.CONFIG_INVALID

        rnd = random.Random(seed)
        rnd.shuffle(rows)

        n = len(rows)
        n_train = int(n * train)
        n_val = int(n * val)
        # remainder goes to test
        n_test = n - n_train - n_val

        # Optional floors: if a split ratio is > 0, enforce at least N rows (default N=0 => disabled)
        m = int(min_per_nonzero_split)
        if m < 0:
            return ec.CONFIG_INVALID
        if m > 0:
            if train > 0 and n_train < m:
                return ec.CONFIG_INVALID
            if val > 0 and n_val < m:
                return ec.CONFIG_INVALID
            if test > 0 and n_test < m:
                return ec.CONFIG_INVALID

        train_rows = rows[:n_train]
        val_rows = rows[n_train:n_train + n_val]
        test_rows = rows[n_train + n_val:]

        outd = Path(outdir).expanduser().resolve()
        outd.mkdir(parents=True, exist_ok=True)

        atomic_write_text(outd / "train.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train_rows))
        atomic_write_text(outd / "val.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in val_rows))
        atomic_write_text(outd / "test.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in test_rows))

        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR

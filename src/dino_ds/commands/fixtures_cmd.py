from __future__ import annotations

from pathlib import Path

from .. import exit_codes as ec
from ..utils import load_json, sha256_file


def verify(manifest: str) -> int:
    try:
        mpath = Path(manifest).expanduser().resolve()
        root = mpath.parent
        m = load_json(mpath)

        items = m.get("items", [])
        if not isinstance(items, list):
            return ec.CONFIG_INVALID

        for it in items:
            resp_path = it.get("response_file_path")
            expected = (it.get("response_sha256") or "").lower()
            if not resp_path or not expected:
                return ec.CONFIG_INVALID

            fpath = (root / resp_path).resolve()
            if not fpath.exists():
                return ec.IO_ERROR

            got = sha256_file(fpath).lower()
            if got != expected:
                return ec.LINT_FAILED  # hard gate
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except Exception:
        return ec.INTERNAL_ERROR
